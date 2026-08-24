"""Tests for the ``submission.grade_status`` aggregation in phase 2.

Spec 6.5:

* no open_ended answer  → ``fully_reviewed``
* all proposed (open_ended) → ``pending_review``
* at least one proposed + at least one approved/manual_override → ``partially``
* all approved/manual_override → ``fully_reviewed``

MC/true-false answers have ``is_correct`` ∈ {True, False} and count as
review-equivalent (gating only works via is_correct=None).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from enums import GradeStatus, SubmissionGradeStatus
from models.auth import Institution, User, UserStatus
from models.exam import Exam, ExamQuestion
from models.question_review import QuestionReview
from models.student import Student
from models.submission import (
    Attempt,
    AttemptAnswer,
    Grade,
    Submission,
)
from services.grading_service import GradingService


def _seed_two_open_ended(test_db: Session) -> tuple[Submission, Grade, Grade, User]:
    inst = Institution(
        name="Agg",
        slug="agg",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.flush()
    user = User(
        email="agg@test.ch",
        first_name="A",
        last_name="G",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=True,
    )
    test_db.add(user)
    test_db.flush()
    qr1 = QuestionReview(
        question_text="Q1",
        question_type="open_ended",
        correct_answer="A1",
        difficulty="medium",
        topic="T",
        institution_id=inst.id,
    )
    qr2 = QuestionReview(
        question_text="Q2",
        question_type="open_ended",
        correct_answer="A2",
        difficulty="medium",
        topic="T",
        institution_id=inst.id,
    )
    test_db.add_all([qr1, qr2])
    test_db.flush()
    exam = Exam(
        title="Agg",
        course="C",
        exam_date=date(2026, 5, 15),
        passing_percentage=50.0,
        total_points=8.0,
        status="finalized",
        language="de",
        institution_id=inst.id,
    )
    test_db.add(exam)
    test_db.flush()
    eq1 = ExamQuestion(exam_id=exam.id, question_id=qr1.id, position=1, points=4.0)
    eq2 = ExamQuestion(exam_id=exam.id, question_id=qr2.id, position=2, points=4.0)
    test_db.add_all([eq1, eq2])
    test_db.flush()
    student = Student(institution_id=inst.id, external_id="s@a.org")
    test_db.add(student)
    test_db.flush()
    sub = Submission(exam_id=exam.id, student_id=student.id, scoring_strategy="latest")
    test_db.add(sub)
    test_db.flush()
    att = Attempt(
        submission_id=sub.id,
        institution_id=inst.id,
        attempt_number=1,
        source="moodle_csv",
        source_attempt_id="s|1",
    )
    test_db.add(att)
    test_db.flush()
    sub.graded_attempt_id = att.id
    ans1 = AttemptAnswer(attempt_id=att.id, exam_question_id=eq1.id, given_answer="x")
    ans2 = AttemptAnswer(attempt_id=att.id, exam_question_id=eq2.id, given_answer="y")
    test_db.add_all([ans1, ans2])
    test_db.flush()
    g1 = Grade(
        attempt_answer_id=ans1.id,
        points_awarded=2.0,
        points_max=4.0,
        status=GradeStatus.PROPOSED.value,
        is_correct=None,
        llm_confidence=0.6,
    )
    g2 = Grade(
        attempt_answer_id=ans2.id,
        points_awarded=2.0,
        points_max=4.0,
        status=GradeStatus.PROPOSED.value,
        is_correct=None,
        llm_confidence=0.5,
    )
    test_db.add_all([g1, g2])
    test_db.commit()
    return sub, g1, g2, user


def _refresh_aggregate(test_db: Session, submission_id: int) -> Submission:
    """Re-aggregate by approving an unrelated path? Easiest: call
    GradingService internal method via approve on a no-op grade.
    Cleaner: hit the public method via a dummy approve+revert? No —
    we expose ``_refresh_submission_aggregate`` because it's the
    canonical entry point. Test calls it directly, accepting the
    private-name surface."""
    service = GradingService(test_db)
    service._refresh_submission_aggregate(submission_id)
    test_db.commit()
    return test_db.get(Submission, submission_id)


def test_all_proposed_open_ended_stays_pending_review(test_db: Session) -> None:
    sub, _, _, _ = _seed_two_open_ended(test_db)
    sub = _refresh_aggregate(test_db, sub.id)
    assert sub.grade_status == SubmissionGradeStatus.PENDING_REVIEW.value


def test_one_approved_one_proposed_is_partially_reviewed(test_db: Session) -> None:
    sub, g1, _, user = _seed_two_open_ended(test_db)
    GradingService(test_db).approve_grade(grade_id=g1.id, reviewer_id=user.id)
    test_db.commit()
    test_db.refresh(sub)
    assert sub.grade_status == SubmissionGradeStatus.PARTIALLY_REVIEWED.value


def test_all_reviewed_becomes_fully_reviewed(test_db: Session) -> None:
    sub, g1, g2, user = _seed_two_open_ended(test_db)
    service = GradingService(test_db)
    service.approve_grade(grade_id=g1.id, reviewer_id=user.id)
    service.override_grade(grade_id=g2.id, reviewer_id=user.id, points_awarded=3.0)
    test_db.commit()
    test_db.refresh(sub)
    assert sub.grade_status == SubmissionGradeStatus.FULLY_REVIEWED.value


def test_only_mc_answers_are_fully_reviewed_immediately(test_db: Session) -> None:
    """MC + true-false answers with is_correct ∈ {True, False} should count
    as ``fully_reviewed`` without review — this is the default case expected
    after a phase-1 import (purely deterministic)."""
    inst = Institution(
        name="MC",
        slug="mc-only",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.flush()
    qr = QuestionReview(
        question_text="MC",
        question_type="single_choice",
        correct_answer="A",
        difficulty="easy",
        topic="T",
        institution_id=inst.id,
    )
    test_db.add(qr)
    test_db.flush()
    exam = Exam(
        title="MC",
        course="C",
        exam_date=date(2026, 5, 15),
        passing_percentage=50.0,
        total_points=4.0,
        status="finalized",
        language="de",
        institution_id=inst.id,
    )
    test_db.add(exam)
    test_db.flush()
    eq = ExamQuestion(exam_id=exam.id, question_id=qr.id, position=1, points=4.0)
    test_db.add(eq)
    test_db.flush()
    student = Student(institution_id=inst.id, external_id="mc@a.org")
    test_db.add(student)
    test_db.flush()
    sub = Submission(exam_id=exam.id, student_id=student.id, scoring_strategy="latest")
    test_db.add(sub)
    test_db.flush()
    att = Attempt(
        submission_id=sub.id,
        institution_id=inst.id,
        attempt_number=1,
        source="moodle_csv",
        source_attempt_id="mc|1",
    )
    test_db.add(att)
    test_db.flush()
    ans = AttemptAnswer(attempt_id=att.id, exam_question_id=eq.id, given_answer="A")
    test_db.add(ans)
    test_db.flush()
    test_db.add(
        Grade(
            attempt_answer_id=ans.id,
            points_awarded=4.0,
            points_max=4.0,
            status=GradeStatus.PROPOSED.value,
            is_correct=True,
        )
    )
    test_db.commit()

    # GradingService.grade_submission sets grade_status; here we only test
    # the aggregation result via the internal refresh path.
    sub = _refresh_aggregate(test_db, sub.id)
    assert sub.grade_status == SubmissionGradeStatus.FULLY_REVIEWED.value
