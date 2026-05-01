"""GradingService: orchestrates grading + aggregation.

The deterministic path covers ``multiple_choice`` and ``true_false``;
``open_ended`` answers are stubbed with ``is_correct=None`` (the
"needs review" sentinel). Unknown question types fall back to the same
needs-review stub so a single misconfigured question cannot roll back
an entire import.
"""

from __future__ import annotations

import logging
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
    Submission,
)
from services.grading.deterministic_grader import (
    DeterministicGrader,
    GradeOutcome,
)


logger = logging.getLogger(__name__)

# Sentinels for ordering attempts whose timestamps are NULL.
# Attempts use timezone-aware datetimes (DateTime(timezone=True)), so the
# sentinels must be tz-aware too — comparing tz-aware with naive raises
# TypeError under min/max.
_FAR_PAST = datetime.min.replace(tzinfo=timezone.utc)
_FAR_FUTURE = datetime.max.replace(tzinfo=timezone.utc)


class UnknownQuestionTypeError(Exception):
    """Question type has no grading strategy.

    Kept as a typed exception so a future strict-mode flag can re-enable
    raising; the current default is to log + stub so one bad question
    cannot abort an entire CSV import.
    """


class SubmissionNotFoundError(LookupError):
    """grade_submission was called with an id that does not exist."""


class GradingService:
    """Orchestrates grading of all attempts within a submission."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.grader = DeterministicGrader()

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
                outcome = self._compute_outcome(
                    question_type=qmeta["question_type"],
                    given_answer=answer.given_answer,
                    correct_answer=qmeta["correct_answer"],
                    points_max=qmeta["points"],
                )
            except UnknownQuestionTypeError:
                logger.error(
                    "Unbekannter question_type %r für AttemptAnswer %s — "
                    "stub mit is_correct=None (needs-review)",
                    qmeta["question_type"],
                    answer.id,
                )
                outcome = DeterministicGrader.stub_for_open_ended(
                    points_max=qmeta["points"]
                )
            self._upsert_grade(answer, outcome)

    def _compute_outcome(
        self,
        *,
        question_type: str,
        given_answer: str | None,
        correct_answer: str | None,
        points_max: float,
    ) -> GradeOutcome:
        if question_type in ("multiple_choice", "true_false"):
            return self.grader.grade(
                question_type=question_type,
                given_answer=given_answer,
                correct_answer=correct_answer,
                points_max=points_max,
            )
        if question_type == "open_ended":
            # Stub with is_correct=None — the sentinel _compute_grade_status
            # interprets as "needs review". Once an LLM grader is wired up
            # this branch becomes the entry point for it.
            return DeterministicGrader.stub_for_open_ended(points_max=points_max)
        raise UnknownQuestionTypeError(
            f"question_type {question_type!r} hat keinen Grading-Pfad"
        )

    def _upsert_grade(self, answer: AttemptAnswer, outcome: GradeOutcome) -> None:
        if answer.grade is None:
            grade = Grade(
                attempt_answer_id=answer.id,
                points_awarded=outcome.points_awarded,
                points_max=outcome.points_max,
                status=outcome.status,
                is_correct=outcome.is_correct,
            )
            self.db.add(grade)
            answer.grade = grade
            return

        # 'proposed'/'approved' is overwritten on re-grade;
        # 'manual_override' was filtered out above.
        answer.grade.points_awarded = outcome.points_awarded
        answer.grade.points_max = outcome.points_max
        answer.grade.status = outcome.status
        answer.grade.is_correct = outcome.is_correct

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
        """Only ``open_ended`` (or otherwise unscored) answers gate
        ``fully_reviewed``.

        ``is_correct=None`` marks stubs and LLM-grades that still await
        human approval; ``True``/``False`` are deterministic and count
        as review-equivalent.
        """
        has_open_ended = any(
            (g := answer.grade) is not None and g.is_correct is None
            for answer in attempt.answers
        )
        return (
            SubmissionGradeStatus.PENDING_REVIEW.value
            if has_open_ended
            else SubmissionGradeStatus.FULLY_REVIEWED.value
        )

    def _load_question_lookup(
        self, answers: Iterable[AttemptAnswer]
    ) -> dict[int, dict]:
        """Fetch question_type + correct_answer + points for the given
        answers in one round-trip."""
        ids = {a.exam_question_id for a in answers}
        if not ids:
            return {}

        rows = (
            self.db.query(
                ExamQuestion.id,
                ExamQuestion.points,
                QuestionReview.question_type,
                QuestionReview.correct_answer,
            )
            .join(QuestionReview, ExamQuestion.question_id == QuestionReview.id)
            .filter(ExamQuestion.id.in_(ids))
            .all()
        )
        return {
            row.id: {
                "points": row.points,
                "question_type": row.question_type,
                "correct_answer": row.correct_answer,
            }
            for row in rows
        }
