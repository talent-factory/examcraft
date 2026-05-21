"""Audit-Trail-Tests für ``GradingService`` Status-Transitionen.

Spec 6.5 verlangt, dass jede Status-Transition eine
``grade_history``-Zeile erzeugt mit aussagekräftigem
``change_reason``. Re-Grading-Eintrag ist bereits in
``test_grading_regrade.py`` getestet — hier konzentrieren wir uns auf
die Reviewer-getriebenen Pfade ``approve`` und ``override``.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from enums import GradeStatus
from models.auth import Institution, User, UserStatus
from models.exam import Exam, ExamQuestion
from models.question_review import QuestionReview
from models.student import Student
from models.submission import (
    Attempt,
    AttemptAnswer,
    Grade,
    GradeHistory,
    Submission,
)
from services.grading_service import (
    CHANGE_REASON_APPROVED,
    CHANGE_REASON_OVERRIDE,
    GradingService,
)


def _seed_proposed_grade(test_db: Session) -> tuple[Grade, User, Institution]:
    inst = Institution(
        name="History",
        slug="history",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.flush()
    user = User(
        email="rev@test.ch",
        first_name="R",
        last_name="V",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=True,
    )
    test_db.add(user)
    test_db.flush()
    qr = QuestionReview(
        question_text="X?",
        question_type="open_ended",
        correct_answer="Y",
        difficulty="medium",
        topic="T",
        institution_id=inst.id,
    )
    test_db.add(qr)
    test_db.flush()
    exam = Exam(
        title="H",
        course="H",
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
    student = Student(institution_id=inst.id, external_id="s@h.org")
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
    ans = AttemptAnswer(attempt_id=att.id, exam_question_id=eq.id, given_answer="A")
    test_db.add(ans)
    test_db.flush()
    grade = Grade(
        attempt_answer_id=ans.id,
        points_awarded=2.5,
        points_max=4.0,
        status=GradeStatus.PROPOSED.value,
        is_correct=None,
        llm_confidence=0.7,
    )
    test_db.add(grade)
    test_db.commit()
    return grade, user, inst


def test_approve_writes_history_with_reason(test_db: Session) -> None:
    grade, user, _ = _seed_proposed_grade(test_db)
    service = GradingService(test_db)
    result = service.approve_grade(grade_id=grade.id, reviewer_id=user.id)
    test_db.commit()

    assert result.status == GradeStatus.APPROVED.value
    assert result.reviewer_id == user.id

    history = (
        test_db.query(GradeHistory).filter(GradeHistory.grade_id == grade.id).all()
    )
    assert len(history) == 1
    assert history[0].change_reason == CHANGE_REASON_APPROVED
    assert history[0].old_status == GradeStatus.PROPOSED.value
    assert history[0].new_status == GradeStatus.APPROVED.value
    assert history[0].changed_by == user.id


def test_repeated_approve_is_idempotent(test_db: Session) -> None:
    grade, user, _ = _seed_proposed_grade(test_db)
    service = GradingService(test_db)
    service.approve_grade(grade_id=grade.id, reviewer_id=user.id)
    service.approve_grade(grade_id=grade.id, reviewer_id=user.id)
    test_db.commit()
    history = (
        test_db.query(GradeHistory).filter(GradeHistory.grade_id == grade.id).all()
    )
    # Genau ein Eintrag: das zweite Approve ist no-op.
    assert len(history) == 1


def test_override_writes_history_with_reason(test_db: Session) -> None:
    grade, user, _ = _seed_proposed_grade(test_db)
    service = GradingService(test_db)
    service.override_grade(
        grade_id=grade.id,
        reviewer_id=user.id,
        points_awarded=3.0,
        reviewer_note="Studi hat den zweiten Aspekt korrekt erfasst.",
    )
    test_db.commit()

    test_db.refresh(grade)
    assert grade.status == GradeStatus.MANUAL_OVERRIDE.value
    assert grade.points_awarded == 3.0
    assert grade.reviewer_note.startswith("Studi")

    history = (
        test_db.query(GradeHistory).filter(GradeHistory.grade_id == grade.id).all()
    )
    assert len(history) == 1
    assert history[0].change_reason == CHANGE_REASON_OVERRIDE
    assert history[0].old_status == GradeStatus.PROPOSED.value
    assert history[0].new_status == GradeStatus.MANUAL_OVERRIDE.value
    assert history[0].old_points == 2.5
    assert history[0].new_points == 3.0


def test_override_rejects_points_outside_bounds(test_db: Session) -> None:
    grade, user, _ = _seed_proposed_grade(test_db)
    service = GradingService(test_db)
    try:
        service.override_grade(
            grade_id=grade.id,
            reviewer_id=user.id,
            points_awarded=99.0,
        )
    except ValueError as exc:
        assert "ausserhalb" in str(exc)
    else:
        raise AssertionError("override_grade akzeptierte Punkte > points_max")


def test_override_idempotent_when_status_points_and_note_unchanged(
    test_db: Session,
) -> None:
    """Ein zweiter override-Aufruf mit identischen Werten ist No-Op:
    keine zweite History-Zeile, reviewed_at bleibt stabil."""
    grade, user, _ = _seed_proposed_grade(test_db)
    service = GradingService(test_db)
    service.override_grade(
        grade_id=grade.id,
        reviewer_id=user.id,
        points_awarded=3.0,
        reviewer_note="Studi hat den zweiten Aspekt korrekt erfasst.",
    )
    test_db.commit()
    test_db.refresh(grade)
    first_reviewed_at = grade.reviewed_at

    service.override_grade(
        grade_id=grade.id,
        reviewer_id=user.id,
        points_awarded=3.0,
        reviewer_note="Studi hat den zweiten Aspekt korrekt erfasst.",
    )
    test_db.commit()
    test_db.refresh(grade)

    history = (
        test_db.query(GradeHistory).filter(GradeHistory.grade_id == grade.id).all()
    )
    assert len(history) == 1
    assert grade.reviewed_at == first_reviewed_at


def test_override_writes_history_when_only_note_changes(
    test_db: Session,
) -> None:
    """Note-Änderung allein ist eine Audit-Transition — Spec 6.5
    verlangt einen lückenlosen Trail."""
    grade, user, _ = _seed_proposed_grade(test_db)
    service = GradingService(test_db)
    service.override_grade(
        grade_id=grade.id,
        reviewer_id=user.id,
        points_awarded=3.0,
        reviewer_note="Erste Notiz",
    )
    service.override_grade(
        grade_id=grade.id,
        reviewer_id=user.id,
        points_awarded=3.0,
        reviewer_note="Korrigierte Notiz",
    )
    test_db.commit()
    test_db.refresh(grade)

    history = (
        test_db.query(GradeHistory)
        .filter(GradeHistory.grade_id == grade.id)
        .order_by(GradeHistory.id)
        .all()
    )
    assert len(history) == 2
    assert grade.reviewer_note == "Korrigierte Notiz"
