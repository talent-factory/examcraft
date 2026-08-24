"""GradingService: orchestrates grading + aggregation.

* MC / true-false → ``DeterministicGrader`` (pure-functional, no LLM call).
* open-ended → ``LlmGrader`` (Anthropic + Pydantic schema, with
  prompt caching).
* Unknown ``question_type`` falls back to the stub with
  ``is_correct=None``, so a single misconfiguration case never fails
  an entire import.

Grade history (audit trail per Spec 6.5/6.6) is written exclusively for
*later* status transitions:
``approved_by_reviewer``, ``manual_override_by_reviewer``,
``regrade_after_correct_answer_update``. The initial ``proposed``
creation stays history-free — it would just be noise.
"""

from __future__ import annotations

import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy.orm import Session, joinedload

from enums import GradeStatus, ScoringStrategy, SubmissionGradeStatus
from models.exam import ExamQuestion
from models.question_review import QuestionReview
from models.submission import (
    Attempt,
    AttemptAnswer,
    Grade,
    GradeHistory,
    Submission,
)
from services.grading.deterministic_grader import (
    DeterministicGrader,
    GradeOutcome,
)
from services.grading.llm_grader import LlmGradeOutcome, LlmGrader


logger = logging.getLogger(__name__)

# Sentinels for ordering attempts whose timestamps are NULL.
# Attempts use timezone-aware datetimes (DateTime(timezone=True)), so the
# sentinels must be tz-aware too — comparing tz-aware with naive raises
# TypeError under min/max.
_FAR_PAST = datetime.min.replace(tzinfo=timezone.utc)
_FAR_FUTURE = datetime.max.replace(tzinfo=timezone.utc)


# change_reason constants for GradeHistory (Spec 6.5/6.6).
CHANGE_REASON_APPROVED = "approved_by_reviewer"
CHANGE_REASON_OVERRIDE = "manual_override_by_reviewer"
CHANGE_REASON_REGRADE = "regrade_after_correct_answer_update"


def _grading_concurrency() -> int:
    """Max parallel free-text LLM calls during an import (TF-428).

    Bounded so a large import does not fan out unbounded Claude requests
    (rate limits, broker/DB pressure). Tunable via ``CLAUDE_GRADING_CONCURRENCY``;
    invalid/<1 values fall back to the default.
    """
    raw = os.getenv("CLAUDE_GRADING_CONCURRENCY", "5")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 5
    return value if value >= 1 else 5


@dataclass(frozen=True)
class _QuestionMeta:
    """Internal tuple — all fields a grader needs for one question.

    A single data type instead of two lookups (deterministic / LLM)
    keeps the logic in ``_grade_attempt_answers`` linear.
    """

    points: float
    question_type: str
    correct_answer: str | None
    question_text: str | None
    explanation: str | None
    difficulty: str | None
    bloom_level: str | None
    # TF-403: answer options (JSON list) for multiple_choice partial
    # credit; None/empty for other types.
    options: list[str] | None = None


class UnknownQuestionTypeError(Exception):
    """Question type has no grading strategy.

    Kept as a typed exception so a future strict-mode flag can re-enable
    raising; the current default is to log + stub so one bad question
    cannot abort an entire CSV import.
    """


class SubmissionNotFoundError(LookupError):
    """grade_submission was called with an id that does not exist."""


class GradeNotFoundError(LookupError):
    """approve/override called with an id that does not exist."""


class GradingService:
    """Orchestrates grading of all attempts within a submission."""

    def __init__(
        self,
        db: Session,
        *,
        deterministic_grader: DeterministicGrader | None = None,
        llm_grader: LlmGrader | None = None,
    ) -> None:
        self.db = db
        self.grader = deterministic_grader or DeterministicGrader()
        # Constructing an LlmGrader is cheap (no API call); in demo
        # mode (no Gateway configured, TF-440) it returns a 0-point
        # stub.
        self._explicit_llm_grader = llm_grader
        self.llm_grader = llm_grader or LlmGrader()
        # TF-336: cache per model string, so enterprise institutions with
        # their own ``llm_model_for_grading`` don't pay for rebuilding
        # the Gateway client construction on every submission, while
        # still not sharing two different models within one pipeline.
        self._llm_grader_by_model: dict[str | None, LlmGrader] = {None: self.llm_grader}

    def _resolve_llm_grader(self, *, submission: Submission) -> LlmGrader:
        """Get the right ``LlmGrader`` for the submission's institution.

        Honours ``Institution.llm_model_for_grading`` (Enterprise-only
        setting). Tests that inject a fixture ``llm_grader`` keep their
        instance — we only branch when no explicit grader was passed.
        """
        if self._explicit_llm_grader is not None:
            return self._explicit_llm_grader
        exam = getattr(submission, "exam", None)
        if exam is None:
            logger.warning(
                "_resolve_llm_grader: submission %s has no loaded exam relationship "
                "— using default LLM grader; Enterprise model override will not apply.",
                submission.id,
            )
        institution = getattr(exam, "institution", None) if exam else None
        model_override = (
            getattr(institution, "llm_model_for_grading", None) if institution else None
        )
        if model_override:
            cached = self._llm_grader_by_model.get(model_override)
            if cached is None:
                # TF-440: no write path in the app currently sets a raw
                # model name (no admin endpoint/schema for this field) —
                # the TF-439 migration `tf439_grade_logical` already
                # normalized existing values to 'examcraft/grading'. If a
                # raw value shows up anyway (legacy data/direct DB
                # access), it would otherwise only fail at the Gateway
                # with a hard-to-diagnose allowlist rejection — AND
                # degrade EVERY open-ended grading for this institution
                # to the 0-point stub until someone notices. Hence
                # `error`, not `warning`, and only once per first-seen
                # model value (cache miss), not per submission.
                if "/" not in model_override:
                    logger.error(
                        "_resolve_llm_grader: Institution %s hat llm_model_for_grading=%r "
                        "gesetzt — sieht nicht wie ein logischer Gateway-Alias aus "
                        "(erwartet z. B. 'examcraft/grading'). Der Gateway wird diesen "
                        "Wert vermutlich ablehnen, sofern er nicht in der Virtual-Key-"
                        "Allowlist steht — Freitext-Bewertung dieser Institution "
                        "degradiert dadurch auf den 0-Punkte-Stub.",
                        getattr(institution, "id", None),
                        model_override,
                    )
                cached = LlmGrader(model=model_override)
                self._llm_grader_by_model[model_override] = cached
            return cached
        return self.llm_grader

    # ------------------------------------------------------------------
    # Parallel free-text pre-grading (TF-428)
    # ------------------------------------------------------------------

    def precompute_open_ended_outcomes(
        self, submission_ids: list[int]
    ) -> dict[int, LlmGradeOutcome]:
        """Grade every open-ended answer across ``submission_ids`` in parallel.

        The dominant cost of a free-text-heavy result import is N sequential
        ``LlmGrader.grade()`` calls. Those calls are pure and network-bound
        (no DB, fail-soft), so we run them through a bounded thread pool and
        return an ``{answer_id: outcome}`` map. ``grade_submission`` then
        consumes that map and persists serially on the caller's session — so
        SQLAlchemy stays single-threaded and the per-submission savepoint /
        partial-failure semantics are untouched. Only the LLM round-trips are
        parallelised.

        No-op (returns ``{}``) when there is nothing to grade; callers fall
        back to the inline serial path transparently.
        """
        if not submission_ids:
            return {}

        attempts = (
            self.db.query(Attempt)
            .options(joinedload(Attempt.answers).joinedload(AttemptAnswer.grade))
            .filter(Attempt.submission_id.in_(submission_ids))
            .all()
        )
        all_answers = [answer for attempt in attempts for answer in attempt.answers]
        if not all_answers:
            return {}

        lookup = self._load_question_lookup(all_answers)
        work: list[tuple[int, dict]] = []
        for answer in all_answers:
            existing = answer.grade
            if existing and existing.status == GradeStatus.MANUAL_OVERRIDE.value:
                continue  # manual_override is sacrosanct — never re-grade.
            qmeta = lookup.get(answer.exam_question_id)
            if qmeta is None or qmeta.question_type != "open_ended":
                continue  # closed/missing-meta handled inline by the serial path.
            work.append((answer.id, self._open_ended_inputs(qmeta, answer)))

        if not work:
            return {}

        # Resolve the institution model once (Enterprise override); each worker
        # thread builds its own LlmGrader/Anthropic client from it, since the
        # sync SDK client and the per-model cache are not concurrency-safe.
        model_for_threads: str | None = None
        if self._explicit_llm_grader is None:
            sample = self.db.get(Submission, submission_ids[0])
            if sample is not None:
                model_for_threads = getattr(
                    self._resolve_llm_grader(submission=sample), "model", None
                )

        thread_state = threading.local()

        def _grade_one(item: tuple[int, dict]) -> tuple[int, LlmGradeOutcome]:
            answer_id, inputs = item
            grader = self._thread_grader(thread_state, model_for_threads)
            try:
                return answer_id, grader.grade(**inputs)
            except Exception:  # noqa: BLE001 — isolate per-answer failure
                # ``LlmGrader.grade`` is contracted never to raise (it returns a
                # 0-point stub on any API/schema error). This guard is defence
                # in depth: precompute runs OUTSIDE the per-submission savepoint,
                # so an escaping exception here would abort the whole import
                # instead of degrading one answer. Mirror the serial path's
                # fail-soft behaviour with a 0-point stub for just this answer.
                logger.exception(
                    "precompute_open_ended_outcomes: Grading für AttemptAnswer "
                    "%s fehlgeschlagen — 0-Punkte-Stub, Import läuft weiter",
                    answer_id,
                )
                return answer_id, LlmGradeOutcome(
                    points_awarded=0.0,
                    points_max=inputs["points_max"],
                    confidence=0.0,
                    rationale="Bewertung fehlgeschlagen (Stub).",
                    matched_aspects=[],
                    missing_aspects=[],
                )

        workers = max(1, min(_grading_concurrency(), len(work)))
        results: dict[int, LlmGradeOutcome] = {}
        with ThreadPoolExecutor(
            max_workers=workers, thread_name_prefix="grade"
        ) as pool:
            for answer_id, outcome in pool.map(_grade_one, work):
                results[answer_id] = outcome
        logger.info(
            "precompute_open_ended_outcomes: %d Freitext-Antworten über %d Threads bewertet",
            len(work),
            workers,
        )
        return results

    def _thread_grader(
        self, thread_state: threading.local, model: str | None
    ) -> LlmGrader:
        """Per-thread ``LlmGrader`` (own Anthropic client) for parallel grading.

        Injected test graders are reused as-is (fakes are trivially safe); in
        production each worker thread lazily builds one grader bound to the
        resolved model.
        """
        if self._explicit_llm_grader is not None:
            return self._explicit_llm_grader
        grader = getattr(thread_state, "grader", None)
        if grader is None:
            grader = LlmGrader(model=model) if model else LlmGrader()
            thread_state.grader = grader
        return grader

    @staticmethod
    def _open_ended_inputs(qmeta: _QuestionMeta, answer: AttemptAnswer) -> dict:
        """Keyword args for ``LlmGrader.grade`` — shared by the parallel and
        inline paths so they stay in lockstep."""
        return dict(
            question_text=qmeta.question_text or "",
            correct_answer=qmeta.correct_answer or "",
            given_answer=answer.given_answer,
            points_max=qmeta.points,
            explanation=qmeta.explanation,
            difficulty=qmeta.difficulty,
            bloom_level=qmeta.bloom_level,
        )

    # ------------------------------------------------------------------
    # Grading
    # ------------------------------------------------------------------

    def grade_submission(
        self,
        submission_id: int,
        *,
        precomputed_open_ended: dict[int, LlmGradeOutcome] | None = None,
    ) -> Submission:
        """Grade every attempt of a submission and update aggregates.

        Idempotent: existing ``manual_override`` grades are preserved
        — the teacher's manual grade wins over automated re-grading.

        ``precomputed_open_ended`` (TF-428): optional ``{answer_id: outcome}``
        map from ``precompute_open_ended_outcomes`` — when an open-ended answer
        is present here its LLM call is skipped and the precomputed outcome
        reused. ``None`` preserves the original inline serial behaviour for
        non-import callers (manual re-grade endpoints).

        Raises:
            SubmissionNotFoundError: when ``submission_id`` does not
                exist; callers must observe the failure (silent ``None``
                returns previously masked typos).
        """
        submission = self.db.get(Submission, submission_id)
        if submission is None:
            raise SubmissionNotFoundError(f"Submission {submission_id} nicht gefunden")

        # TF-336: pick the institution-configured LLM model (Enterprise
        # tier). For all other tiers the default is reused. Service is
        # per-DB-session, so swapping the attribute is safe.
        self.llm_grader = self._resolve_llm_grader(submission=submission)

        attempts = (
            self.db.query(Attempt)
            .options(
                joinedload(Attempt.answers).joinedload(AttemptAnswer.grade),
            )
            .filter(Attempt.submission_id == submission_id)
            .all()
        )
        if not attempts:
            logger.warning(
                "grade_submission: submission %s has no attempts — "
                "resetting aggregates so stale points don't survive a "
                "delete-and-re-import cycle",
                submission_id,
            )
            submission.graded_attempt_id = None
            submission.total_points_awarded = 0.0
            submission.percentage = 0.0
            submission.grade_status = SubmissionGradeStatus.PENDING_REVIEW.value
            self.db.flush()
            return submission

        # Grade answers across all attempts (not only the graded_attempt).
        # That way 'best' can later switch attempts without re-grading.
        for attempt in attempts:
            self._grade_attempt_answers(attempt, precomputed=precomputed_open_ended)

        self._aggregate(submission, attempts)
        self.db.flush()
        return submission

    def _grade_attempt_answers(
        self,
        attempt: Attempt,
        *,
        precomputed: dict[int, LlmGradeOutcome] | None = None,
    ) -> None:
        if not attempt.answers:
            return

        question_lookup = self._load_question_lookup(attempt.answers)

        for answer in attempt.answers:
            existing = answer.grade
            # manual_override is sacrosanct — the teacher takes priority.
            if existing and existing.status == GradeStatus.MANUAL_OVERRIDE.value:
                continue

            qmeta = question_lookup.get(answer.exam_question_id)
            if qmeta is None:
                # Surface as a visible 0-point Grade rather than silently
                # skipping — otherwise the aggregate counts 0 for it but
                # grade_status reads "fully_reviewed" and the operator
                # has no idea points are under-counted.
                logger.error(
                    "ExamQuestion %s ohne Frage-Metadaten — kein "
                    "Grading möglich, persistiere 0-Point-Grade als "
                    "sichtbares Signal.",
                    answer.exam_question_id,
                )
                self._upsert_grade(
                    answer,
                    GradeOutcome(
                        points_awarded=0.0,
                        points_max=0.0,
                        is_correct=False,
                        status=GradeStatus.PROPOSED.value,
                    ),
                )
                continue

            try:
                outcome = self._compute_outcome(
                    qmeta=qmeta, answer=answer, precomputed=precomputed
                )
            except UnknownQuestionTypeError:
                logger.error(
                    "Unbekannter question_type %r für AttemptAnswer %s — "
                    "stub mit is_correct=None (needs-review)",
                    qmeta.question_type,
                    answer.id,
                )
                outcome = DeterministicGrader.stub_for_open_ended(
                    points_max=qmeta.points
                )
            self._upsert_grade(answer, outcome)

    def _compute_outcome(
        self,
        *,
        qmeta: _QuestionMeta,
        answer: AttemptAnswer,
        precomputed: dict[int, LlmGradeOutcome] | None = None,
    ) -> GradeOutcome | LlmGradeOutcome:
        if qmeta.question_type in ("single_choice", "multiple_choice", "true_false"):
            return self.grader.grade(
                question_type=qmeta.question_type,
                given_answer=answer.given_answer,
                correct_answer=qmeta.correct_answer,
                points_max=qmeta.points,
                num_options=len(qmeta.options or []),
            )
        if qmeta.question_type == "open_ended":
            # TF-428: reuse the outcome already computed in parallel during an
            # import; only fall back to an inline LLM call when there is none
            # (non-import callers, or an answer added after pre-grading).
            if precomputed is not None and answer.id in precomputed:
                return precomputed[answer.id]
            # LlmGrader catches API/schema errors internally and returns
            # a 0-point stub — no exception propagates up to here.
            return self.llm_grader.grade(**self._open_ended_inputs(qmeta, answer))
        raise UnknownQuestionTypeError(
            f"question_type {qmeta.question_type!r} hat keinen Grading-Pfad"
        )

    def _upsert_grade(
        self,
        answer: AttemptAnswer,
        outcome: GradeOutcome | LlmGradeOutcome,
    ) -> None:
        """Persists or updates the Grade for an AttemptAnswer.

        LLM fields are only set for ``LlmGradeOutcome`` — for
        deterministic outcomes they are written back as NULL, otherwise
        leftovers from a previous LLM run (e.g. a question-type change
        in the composer) would remain in the DB record.
        """
        is_llm = isinstance(outcome, LlmGradeOutcome)

        if answer.grade is None:
            grade = Grade(
                attempt_answer_id=answer.id,
                points_awarded=outcome.points_awarded,
                points_max=outcome.points_max,
                status=outcome.status,
                is_correct=outcome.is_correct,
                llm_confidence=outcome.confidence if is_llm else None,
                llm_rationale=outcome.rationale if is_llm else None,
                llm_matched_aspects=outcome.matched_aspects if is_llm else None,
                llm_missing_aspects=outcome.missing_aspects if is_llm else None,
            )
            self.db.add(grade)
            answer.grade = grade
            return

        # 'proposed'/'approved' is overwritten on re-grade;
        # 'manual_override' was filtered out by the caller.
        answer.grade.points_awarded = outcome.points_awarded
        answer.grade.points_max = outcome.points_max
        answer.grade.status = outcome.status
        answer.grade.is_correct = outcome.is_correct
        answer.grade.llm_confidence = outcome.confidence if is_llm else None
        answer.grade.llm_rationale = outcome.rationale if is_llm else None
        answer.grade.llm_matched_aspects = outcome.matched_aspects if is_llm else None
        answer.grade.llm_missing_aspects = outcome.missing_aspects if is_llm else None

    # ------------------------------------------------------------------
    # Review actions (Spec 6.4 / 6.5)
    # ------------------------------------------------------------------

    def approve_grade(self, *, grade_id: int, reviewer_id: int) -> Grade:
        """Teacher accepts the LLM suggestion → ``status=approved``.

        Idempotent: repeatedly approving an already-approved grade
        doesn't write a second history row (`old==new`).
        """
        grade = self.db.get(Grade, grade_id)
        if grade is None:
            raise GradeNotFoundError(f"Grade {grade_id} nicht gefunden")

        old_status = grade.status
        old_points = grade.points_awarded
        if old_status == GradeStatus.APPROVED.value:
            return grade

        grade.status = GradeStatus.APPROVED.value
        grade.reviewer_id = reviewer_id
        grade.reviewed_at = datetime.now(timezone.utc)
        self._log_history(
            grade=grade,
            old_status=old_status,
            new_status=grade.status,
            old_points=old_points,
            new_points=grade.points_awarded,
            changed_by=reviewer_id,
            change_reason=CHANGE_REASON_APPROVED,
        )
        self._refresh_submission_aggregate_for(grade)
        self.db.flush()
        return grade

    def override_grade(
        self,
        *,
        grade_id: int,
        reviewer_id: int,
        points_awarded: float,
        reviewer_note: str | None = None,
    ) -> Grade:
        """Teacher overrides → ``status=manual_override``.

        Auditable: every change to status, points, or reviewer note
        creates a history row. If all three are identical to the
        existing state, the call is a genuine no-op and ``reviewed_at``
        stays unchanged.
        """
        grade = self.db.get(Grade, grade_id)
        if grade is None:
            raise GradeNotFoundError(f"Grade {grade_id} nicht gefunden")

        if points_awarded < 0 or points_awarded > grade.points_max:
            raise ValueError(
                f"points_awarded {points_awarded} ausserhalb [0, {grade.points_max}]"
            )

        old_status = grade.status
        old_points = grade.points_awarded
        old_note = grade.reviewer_note
        truly_unchanged = (
            old_status == GradeStatus.MANUAL_OVERRIDE.value
            and old_points == points_awarded
            and old_note == reviewer_note
        )
        if truly_unchanged:
            return grade

        grade.status = GradeStatus.MANUAL_OVERRIDE.value
        grade.points_awarded = points_awarded
        grade.reviewer_id = reviewer_id
        grade.reviewer_note = reviewer_note
        grade.reviewed_at = datetime.now(timezone.utc)
        self._log_history(
            grade=grade,
            old_status=old_status,
            new_status=grade.status,
            old_points=old_points,
            new_points=points_awarded,
            changed_by=reviewer_id,
            change_reason=CHANGE_REASON_OVERRIDE,
        )
        self._refresh_submission_aggregate_for(grade)
        self.db.flush()
        return grade

    def bulk_approve(
        self,
        *,
        reviewer_id: int,
        institution_id: int,
        exam_id: int,
        confidence_min: float | None = None,
        grade_ids: Iterable[int] | None = None,
    ) -> list[Grade]:
        """Approve multiple grades in a single call.

        Teacher-triggered explicitly (Spec 6.4 — no auto-approve).
        Filters are exclusive: either ``grade_ids`` (explicit list)
        or ``confidence_min`` (all proposed grades for this exam with
        confidence >= threshold). The multi-tenancy check via
        ``institution_id`` is mandatory — otherwise tenant A could
        approve tenant B's grades.
        """
        if (grade_ids is None) == (confidence_min is None):
            raise ValueError(
                "bulk_approve braucht genau einen Filter: grade_ids ODER confidence_min"
            )

        query = (
            self.db.query(Grade)
            .join(AttemptAnswer, AttemptAnswer.id == Grade.attempt_answer_id)
            .join(Attempt, Attempt.id == AttemptAnswer.attempt_id)
            .join(Submission, Submission.id == Attempt.submission_id)
            .filter(
                Submission.exam_id == exam_id,
                Attempt.institution_id == institution_id,
                Grade.status == GradeStatus.PROPOSED.value,
            )
        )
        if grade_ids is not None:
            ids = list(grade_ids)
            if not ids:
                return []
            query = query.filter(Grade.id.in_(ids))
        elif confidence_min is not None:
            query = query.filter(Grade.llm_confidence >= confidence_min)

        approved: list[Grade] = []
        now = datetime.now(timezone.utc)
        for grade in query.all():
            old_status = grade.status
            old_points = grade.points_awarded
            grade.status = GradeStatus.APPROVED.value
            grade.reviewer_id = reviewer_id
            grade.reviewed_at = now
            self._log_history(
                grade=grade,
                old_status=old_status,
                new_status=grade.status,
                old_points=old_points,
                new_points=grade.points_awarded,
                changed_by=reviewer_id,
                change_reason=CHANGE_REASON_APPROVED,
            )
            approved.append(grade)

        # Refresh the aggregate once per submission instead of once per grade.
        submission_ids: set[int] = set()
        for g in approved:
            sid = self._submission_id_for_grade(g)
            if sid is not None:
                submission_ids.add(sid)
        for sid in submission_ids:
            self._refresh_submission_aggregate(sid)
        self.db.flush()
        return approved

    # ------------------------------------------------------------------
    # Re-Grading (Spec 6.6)
    # ------------------------------------------------------------------

    def regrade_after_correct_answer_update(
        self,
        *,
        exam_question_id: int,
        triggered_by: int | None = None,
    ) -> int:
        """Re-grade after a question's ``correct_answer`` change.

        Resets all ``proposed``/``approved`` grades of this ExamQuestion
        back to ``proposed`` and re-grades them. ``manual_override``
        stays untouched — the teacher has already explicitly decided
        there (Spec 6.6).

        Returns:
            Number of re-graded grades.
        """
        affected_answers = (
            self.db.query(AttemptAnswer)
            .options(joinedload(AttemptAnswer.grade))
            .filter(AttemptAnswer.exam_question_id == exam_question_id)
            .all()
        )
        if not affected_answers:
            return 0

        question_lookup = self._load_question_lookup(affected_answers)
        qmeta = question_lookup.get(exam_question_id)
        if qmeta is None:
            logger.error(
                "regrade: ExamQuestion %s ohne Metadaten — Re-Grading übersprungen.",
                exam_question_id,
            )
            return 0

        regraded = 0
        affected_submission_ids: set[int] = set()
        for answer in affected_answers:
            grade = answer.grade
            if grade is None:
                continue
            if grade.status == GradeStatus.MANUAL_OVERRIDE.value:
                continue

            old_status = grade.status
            old_points = grade.points_awarded
            try:
                outcome = self._compute_outcome(qmeta=qmeta, answer=answer)
            except UnknownQuestionTypeError:
                outcome = DeterministicGrader.stub_for_open_ended(
                    points_max=qmeta.points
                )
            self._upsert_grade(answer, outcome)
            # Re-grading forces it back to proposed, even if it was
            # already approved before — the teacher must review it again
            # (Spec 6.6).
            grade.status = GradeStatus.PROPOSED.value
            grade.reviewer_id = None
            grade.reviewed_at = None
            grade.reviewer_note = None

            self._log_history(
                grade=grade,
                old_status=old_status,
                new_status=grade.status,
                old_points=old_points,
                new_points=grade.points_awarded,
                changed_by=triggered_by,
                change_reason=CHANGE_REASON_REGRADE,
            )
            regraded += 1
            sid = self._submission_id_for_grade(grade)
            if sid is not None:
                affected_submission_ids.add(sid)

        for sid in affected_submission_ids:
            self._refresh_submission_aggregate(sid)
        self.db.flush()
        return regraded

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def _aggregate(self, submission: Submission, attempts: list[Attempt]) -> None:
        """Pick an attempt per scoring_strategy and sum its points."""
        if not attempts:
            return

        per_attempt_totals = [
            (
                attempt,
                sum(
                    (a.grade.points_awarded if a.grade else 0.0)
                    for a in attempt.answers
                ),
                sum((a.grade.points_max if a.grade else 0.0) for a in attempt.answers),
            )
            for attempt in attempts
        ]

        chosen = self._pick_attempt(submission.scoring_strategy, per_attempt_totals)
        attempt, awarded, max_points = chosen

        submission.graded_attempt_id = attempt.id
        submission.total_points_awarded = awarded
        submission.total_points_max = max_points
        submission.percentage = (
            (awarded / max_points * 100.0) if max_points > 0 else 0.0
        )
        submission.grade_status = self._compute_grade_status(attempt)

    @staticmethod
    def _pick_attempt(
        strategy: str,
        candidates: list[tuple[Attempt, float, float]],
    ) -> tuple[Attempt, float, float]:
        """Pick one attempt; raise on unknown strategy.

        Attempts with NULL timestamps are normalised to a sentinel that
        sorts them *after* dated attempts (so a dateless attempt does
        not beat a dated one in either direction). When all attempts
        lack dates, ordering falls through to the attempt id.
        """
        try:
            normalised = ScoringStrategy(strategy)
        except ValueError as exc:
            raise ValueError(
                f"Unbekannte scoring_strategy {strategy!r}; "
                f"erlaubt: {[s.value for s in ScoringStrategy]}"
            ) from exc

        def _normalise_dt(value):
            if value is None:
                return None
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value

        match normalised:
            case ScoringStrategy.FIRST:
                # Dated attempts must beat dateless ones — fall back to
                # _FAR_FUTURE so dateless candidates sort last under min.
                return min(
                    candidates,
                    key=lambda t: (
                        _normalise_dt(t[0].started_at)
                        or _normalise_dt(t[0].submitted_at)
                        or _FAR_FUTURE,
                        t[0].id,
                    ),
                )
            case ScoringStrategy.BEST:
                # Tie-break: lower id wins (== first imported attempt) so
                # re-imports stay deterministic even if multiple attempts
                # share the max points.
                return max(candidates, key=lambda t: (t[1], -t[0].id))
            case ScoringStrategy.LATEST:
                # Symmetric: fall back to _FAR_PAST so dateless candidates
                # sort first (lowest) under max.
                return max(
                    candidates,
                    key=lambda t: (
                        _normalise_dt(t[0].submitted_at)
                        or _normalise_dt(t[0].started_at)
                        or _FAR_PAST,
                        t[0].id,
                    ),
                )

    @staticmethod
    def _compute_grade_status(attempt: Attempt) -> str:
        """Aggregate ``submission.grade_status`` from the open-ended grades.

        We recognize open-ended answers by the ``is_correct=None``
        sentinel (LLM and stub outcomes). MC/true-false answers always
        have ``True``/``False`` and are considered review-equivalent —
        the teacher can still intervene on them via ``manual_override``
        from the submission detail view at any time, but that doesn't
        gate the grade export.

        Logic (Spec 6.5):

        * no open-ended answer → ``fully_reviewed``
        * at least one ``proposed`` and at least one ``approved``/
          ``manual_override`` → ``partially_reviewed``
        * all ``approved``/``manual_override`` → ``fully_reviewed``
        * otherwise → ``pending_review``
        """
        open_ended_grades = [
            g
            for answer in attempt.answers
            if (g := answer.grade) is not None and g.is_correct is None
        ]
        if not open_ended_grades:
            return SubmissionGradeStatus.FULLY_REVIEWED.value

        any_proposed = False
        any_reviewed = False
        for g in open_ended_grades:
            if g.status == GradeStatus.PROPOSED.value:
                any_proposed = True
            elif g.status in (
                GradeStatus.APPROVED.value,
                GradeStatus.MANUAL_OVERRIDE.value,
            ):
                any_reviewed = True

        if any_proposed and any_reviewed:
            return SubmissionGradeStatus.PARTIALLY_REVIEWED.value
        if not any_proposed:
            return SubmissionGradeStatus.FULLY_REVIEWED.value
        return SubmissionGradeStatus.PENDING_REVIEW.value

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load_question_lookup(
        self, answers: Iterable[AttemptAnswer]
    ) -> dict[int, _QuestionMeta]:
        """Fetch question meta (incl. fields for LLM grading) in a single roundtrip."""
        ids = {a.exam_question_id for a in answers}
        if not ids:
            return {}

        rows = (
            self.db.query(
                ExamQuestion.id,
                ExamQuestion.points,
                QuestionReview.question_type,
                QuestionReview.correct_answer,
                QuestionReview.question_text,
                QuestionReview.explanation,
                QuestionReview.difficulty,
                QuestionReview.bloom_level,
                QuestionReview.options,
            )
            .join(QuestionReview, ExamQuestion.question_id == QuestionReview.id)
            .filter(ExamQuestion.id.in_(ids))
            .all()
        )
        return {
            row.id: _QuestionMeta(
                points=row.points,
                question_type=row.question_type,
                correct_answer=row.correct_answer,
                question_text=row.question_text,
                explanation=row.explanation,
                difficulty=row.difficulty,
                bloom_level=str(row.bloom_level)
                if row.bloom_level is not None
                else None,
                options=row.options,
            )
            for row in rows
        }

    def _log_history(
        self,
        *,
        grade: Grade,
        old_status: str | None,
        new_status: str | None,
        old_points: float | None,
        new_points: float | None,
        changed_by: int | None,
        change_reason: str,
    ) -> None:
        entry = GradeHistory(
            grade_id=grade.id,
            old_status=old_status,
            new_status=new_status,
            old_points=old_points,
            new_points=new_points,
            changed_by=changed_by,
            change_reason=change_reason,
        )
        self.db.add(entry)

    def _submission_id_for_grade(self, grade: Grade) -> int | None:
        """Return submission_id of a grade by walking the FK chain.

        Used by ``bulk_approve`` and ``regrade`` to deduplicate
        per-submission aggregate refreshes — without it a 50-grade bulk
        approve would recompute the same submission's aggregate 50
        times.
        """
        row = (
            self.db.query(Attempt.submission_id)
            .join(AttemptAnswer, AttemptAnswer.attempt_id == Attempt.id)
            .filter(AttemptAnswer.id == grade.attempt_answer_id)
            .first()
        )
        return row[0] if row else None

    def _refresh_submission_aggregate_for(self, grade: Grade) -> None:
        sid = self._submission_id_for_grade(grade)
        if sid is not None:
            self._refresh_submission_aggregate(sid)

    def _refresh_submission_aggregate(self, submission_id: int) -> None:
        """Recompute submission totals after a status / points change.

        Re-uses ``_aggregate`` so the source of truth for
        scoring-strategy + grade_status logic stays in one place.
        """
        submission = self.db.get(Submission, submission_id)
        if submission is None:
            return
        attempts = (
            self.db.query(Attempt)
            .options(
                joinedload(Attempt.answers).joinedload(AttemptAnswer.grade),
            )
            .filter(Attempt.submission_id == submission_id)
            .all()
        )
        if attempts:
            self._aggregate(submission, attempts)
