"""GradingService: orchestrates grading + aggregation.

* MC / W-F → ``DeterministicGrader`` (pure-functional, kein LLM-Call).
* offene Fragen → ``LlmGrader`` (Anthropic + Pydantic-Schema, mit
  Prompt-Caching).
* Unbekannte ``question_type`` fallen auf den Stub mit
  ``is_correct=None`` zurück, damit ein einzelner Mis-Konfigurations-
  Fall nie einen ganzen Import scheitern lässt.

Grade-History (Audit-Trail nach Spec 6.5/6.6) wird ausschliesslich für
*spätere* Status-Transitionen geschrieben:
``approved_by_reviewer``, ``manual_override_by_reviewer``,
``regrade_after_correct_answer_update``. Die initiale ``proposed``-
Erzeugung bleibt history-frei — sie wäre Rauschen.
"""

from __future__ import annotations

import logging
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


# change_reason-Konstanten für GradeHistory (Spec 6.5/6.6).
CHANGE_REASON_APPROVED = "approved_by_reviewer"
CHANGE_REASON_OVERRIDE = "manual_override_by_reviewer"
CHANGE_REASON_REGRADE = "regrade_after_correct_answer_update"


@dataclass(frozen=True)
class _QuestionMeta:
    """Internes Tupel — alle Felder, die ein Grader für eine Frage
    braucht.

    Ein einzelner Datentyp statt zwei Lookups (deterministisch /
    LLM) hält die Logik in ``_grade_attempt_answers`` linear.
    """

    points: float
    question_type: str
    correct_answer: str | None
    question_text: str | None
    explanation: str | None
    difficulty: str | None
    bloom_level: str | None


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
        # LlmGrader-Konstruktion ist günstig (kein API-Call); im Demo-
        # Mode (kein API-Key) liefert sie einen 0-Punkte-Stub.
        self._explicit_llm_grader = llm_grader
        self.llm_grader = llm_grader or LlmGrader()
        # TF-336: Cache pro Modell-String, damit Enterprise-
        # Institutionen mit eigenem ``llm_model_for_grading`` kein
        # Re-Build der Anthropic-Client-Konstruktion pro Submission
        # bezahlen, aber gleichzeitig zwei verschiedene Modelle in
        # einer Pipeline nicht teilen.
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
                cached = LlmGrader(model=model_override)
                self._llm_grader_by_model[model_override] = cached
            return cached
        return self.llm_grader

    # ------------------------------------------------------------------
    # Grading
    # ------------------------------------------------------------------

    def grade_submission(self, submission_id: int) -> Submission:
        """Grade every attempt of a submission and update aggregates.

        Idempotent: existing ``manual_override`` grades are preserved
        — the teacher's manual grade wins over automated re-grading.

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
            self._grade_attempt_answers(attempt)

        self._aggregate(submission, attempts)
        self.db.flush()
        return submission

    def _grade_attempt_answers(self, attempt: Attempt) -> None:
        if not attempt.answers:
            return

        question_lookup = self._load_question_lookup(attempt.answers)

        for answer in attempt.answers:
            existing = answer.grade
            # manual_override is sacrosanct — Lehrperson hat Vorrang.
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
                outcome = self._compute_outcome(qmeta=qmeta, answer=answer)
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
    ) -> GradeOutcome | LlmGradeOutcome:
        if qmeta.question_type in ("multiple_choice", "true_false"):
            return self.grader.grade(
                question_type=qmeta.question_type,
                given_answer=answer.given_answer,
                correct_answer=qmeta.correct_answer,
                points_max=qmeta.points,
            )
        if qmeta.question_type == "open_ended":
            # LlmGrader fängt API/Schema-Fehler intern ab und liefert
            # einen 0-Punkte-Stub — keine Ausnahme propagiert nach hier.
            return self.llm_grader.grade(
                question_text=qmeta.question_text or "",
                correct_answer=qmeta.correct_answer or "",
                given_answer=answer.given_answer,
                points_max=qmeta.points,
                explanation=qmeta.explanation,
                difficulty=qmeta.difficulty,
                bloom_level=qmeta.bloom_level,
            )
        raise UnknownQuestionTypeError(
            f"question_type {qmeta.question_type!r} hat keinen Grading-Pfad"
        )

    def _upsert_grade(
        self,
        answer: AttemptAnswer,
        outcome: GradeOutcome | LlmGradeOutcome,
    ) -> None:
        """Persistiert oder aktualisiert den Grade einer AttemptAnswer.

        LLM-Felder werden nur bei ``LlmGradeOutcome`` gesetzt — bei
        deterministischen Outcomes auf NULL zurückgeschrieben, sonst
        bleiben Reste eines vorherigen LLM-Laufs (z. B. Question-Type-
        Wechsel im Composer) im DB-Record.
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
        """Lehrperson übernimmt LLM-Vorschlag → ``status=approved``.

        Idempotent: Wiederholtes Approve eines bereits approveten
        Grades schreibt keine zweite History-Zeile (`old==new`).
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
        """Lehrperson überschreibt → ``status=manual_override``.

        Auditierbar: jede Änderung an Status, Punkten oder Reviewer-Note
        erzeugt eine History-Zeile. Wenn alle drei identisch zum
        bestehenden Stand sind, ist der Aufruf ein echter No-Op und
        ``reviewed_at`` bleibt unverändert.
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
        """Approve mehrere Grades in einem Aufruf.

        Lehrperson trigger explizit (Spec 6.4 — kein Auto-Approve).
        Filter sind exklusiv: entweder ``grade_ids`` (explizite Liste)
        oder ``confidence_min`` (alle proposed-Grades dieser Prüfung
        mit konfidenz >= Schwelle). Multi-Tenancy-Check via
        ``institution_id`` ist Pflicht — sonst kann Tenant A Grades
        von Tenant B approven.
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

        # Aggregate je Submission einmal nachziehen statt n-fach pro Grade.
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
        """Re-Grading nach ``correct_answer``-Änderung einer Frage.

        Setzt alle ``proposed``/``approved``-Grades dieser ExamQuestion
        zurück auf ``proposed`` und re-gradet sie. ``manual_override``
        bleibt unangetastet — die Lehrperson hat dort schon explizit
        entschieden (Spec 6.6).

        Returns:
            Anzahl der re-gradeten Grades.
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
            # Re-Grading zwingt zurück auf proposed, auch wenn vorher
            # bereits approved — Lehrperson muss neu reviewen (Spec 6.6).
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
        """Aggregiere ``submission.grade_status`` aus den open-ended-Grades.

        Open-ended-Antworten erkennen wir am ``is_correct=None``-
        Sentinel (LLM- und Stub-Outcomes). MC/W-F-Antworten haben
        immer ``True``/``False`` und gelten als review-äquivalent — die
        Lehrperson kann sie via ``manual_override`` aus der Submissions-
        Detailansicht heraus jederzeit eingreifen, aber das gated den
        Notenexport nicht.

        Logik (Spec 6.5):

        * keine open-ended-Antwort → ``fully_reviewed``
        * mind. ein ``proposed`` und mind. ein ``approved``/
          ``manual_override`` → ``partially_reviewed``
        * alle ``approved``/``manual_override`` → ``fully_reviewed``
        * sonst → ``pending_review``
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
        """Fetch question meta (incl. Felder für LLM-Grading) in einem Roundtrip."""
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
