"""Build the transport-neutral feedback payload from graded submissions (TF-435)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from models.exam import Exam, ExamQuestion
from models.student import Student
from models.submission import AttemptAnswer, Grade, Submission


class MissingQuizIdError(Exception):
    """Exam has no moodle_quiz_id in any question's external_refs."""


@dataclass
class QuestionFeedback:
    slot: int
    mark: float
    comment: str

    def __post_init__(self) -> None:
        # Construction-boundary guards so a nonsense feedback row can't be
        # built. Both hold for every value sourced from the DB (Moodle slots
        # are 1-based; Grade.points_awarded is CHECK >= 0) — this just stops
        # the type from silently carrying an illegal state if that changes.
        if self.slot < 1:
            raise ValueError(f"QuestionFeedback.slot muss >= 1 sein, war {self.slot}")
        if self.mark < 0:
            raise ValueError(f"QuestionFeedback.mark muss >= 0 sein, war {self.mark}")


@dataclass
class StudentFeedback:
    # Student.external_id — may be an email, a Moodle username, or a numeric
    # Moodle user id. The gradebook transport picks the Moodle lookup field by
    # its shape; the plugin transport passes it through as `useridentifier`.
    external_id: str
    total_points_awarded: float
    total_points_max: float
    questions: list[QuestionFeedback] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Mirrors the Submission DB CHECK (0 <= awarded <= max).
        if self.total_points_awarded < 0:
            raise ValueError(
                "StudentFeedback.total_points_awarded muss >= 0 sein, war "
                f"{self.total_points_awarded}"
            )
        if self.total_points_awarded > self.total_points_max:
            raise ValueError(
                "StudentFeedback.total_points_awarded "
                f"({self.total_points_awarded}) > total_points_max "
                f"({self.total_points_max})"
            )


@dataclass
class FeedbackPayload:
    quiz_id: int
    students: list[StudentFeedback] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _resolve_quiz_id(db: Session, exam: Exam) -> int:
    rows = (
        db.query(ExamQuestion.external_refs)
        .filter(ExamQuestion.exam_id == exam.id)
        .all()
    )
    for (refs,) in rows:
        if refs and refs.get("moodle_quiz_id"):
            return int(refs["moodle_quiz_id"])
    raise MissingQuizIdError(
        "Diese Prüfung hat keine moodle_quiz_id. Bitte zuerst die "
        "Moodle-Fragen-IDs synchronisieren (sync-moodle-question-ids)."
    )


def build_feedback_payload(db: Session, exam: Exam) -> FeedbackPayload:
    """Collect per-student, per-question marks + comments for one exam.

    Only submissions with ``grade_status == 'fully_reviewed'`` are included.
    Comment falls back reviewer_note -> llm_rationale -> "". Questions
    without a moodle_slot are skipped and recorded as warnings.
    """
    quiz_id = _resolve_quiz_id(db, exam)
    payload = FeedbackPayload(quiz_id=quiz_id)

    submissions = (
        db.query(Submission, Student)
        .join(Student, Student.id == Submission.student_id)
        .filter(
            Submission.exam_id == exam.id,
            Submission.grade_status == "fully_reviewed",
        )
        .order_by(Student.external_id)
        .all()
    )

    # exam_question_id -> moodle_slot (or None)
    slot_by_question: dict[int, int | None] = {}
    for q in db.query(ExamQuestion).filter(ExamQuestion.exam_id == exam.id).all():
        refs = q.external_refs or {}
        slot_by_question[q.id] = refs.get("moodle_slot")

    # One grouped query for all attempts instead of one query per submission
    # (was an N+1 over the cohort). Group in Python by attempt_id.
    attempt_ids = [
        sub.graded_attempt_id
        for sub, _ in submissions
        if sub.graded_attempt_id is not None
    ]
    answers_by_attempt: dict[int, list[tuple[AttemptAnswer, Grade]]] = {}
    if attempt_ids:
        for answer, grade in (
            db.query(AttemptAnswer, Grade)
            .join(Grade, Grade.attempt_answer_id == AttemptAnswer.id)
            .filter(AttemptAnswer.attempt_id.in_(attempt_ids))
            .all()
        ):
            answers_by_attempt.setdefault(answer.attempt_id, []).append((answer, grade))

    for submission, student in submissions:
        sf = StudentFeedback(
            external_id=student.external_id,
            total_points_awarded=float(submission.total_points_awarded),
            total_points_max=float(submission.total_points_max),
        )
        for answer, grade in answers_by_attempt.get(submission.graded_attempt_id, []):
            slot = slot_by_question.get(answer.exam_question_id)
            if slot is None:
                payload.warnings.append(
                    f"{student.external_id}: Frage {answer.exam_question_id} "
                    "hat kein moodle_slot — übersprungen."
                )
                continue
            comment = (grade.reviewer_note or grade.llm_rationale or "").strip()
            sf.questions.append(
                QuestionFeedback(
                    slot=int(slot),
                    mark=float(grade.points_awarded),
                    comment=comment,
                )
            )
        payload.students.append(sf)

    return payload
