"""Tests for ``GradingService.regrade_after_correct_answer_update``
(Spec 6.6).

Drei Garantien werden hier abgesichert:

1. ``manual_override`` bleibt unangetastet — die Lehrperson hat dort
   schon explizit entschieden.
2. ``proposed`` und ``approved`` werden zurückgesetzt auf ``proposed``
   und neu gegradet.
3. Jede Status-Transition landet als ``grade_history``-Zeile mit
   ``change_reason='regrade_after_correct_answer_update'``.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

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
from services.grading.llm_grader import LlmGradeOutcome, LlmGrader
from services.grading_service import (
    CHANGE_REASON_REGRADE,
    GradingService,
)


def _seed_three_open_ended_grades(
    test_db: Session,
) -> tuple[ExamQuestion, list[Grade], User, Institution]:
    """Bereite drei Submissions auf eine open_ended-Frage vor:
    eine ``proposed``, eine ``approved``, eine ``manual_override``."""
    inst = Institution(
        name="Regrade",
        slug="regrade",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.flush()

    user = User(
        email="reg@test.ch",
        first_name="R",
        last_name="E",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=True,
    )
    test_db.add(user)
    test_db.flush()

    qr = QuestionReview(
        question_text="Erkläre Kapselung.",
        question_type="open_ended",
        correct_answer="Daten + Verhalten in einem Objekt zusammenfassen.",
        difficulty="medium",
        topic="OOP",
        institution_id=inst.id,
    )
    test_db.add(qr)
    test_db.flush()

    exam = Exam(
        title="Regrade-Exam",
        course="OOP",
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

    statuses = [
        GradeStatus.PROPOSED.value,
        GradeStatus.APPROVED.value,
        GradeStatus.MANUAL_OVERRIDE.value,
    ]
    grades: list[Grade] = []
    for idx, status in enumerate(statuses):
        student = Student(institution_id=inst.id, external_id=f"s{idx}@example.org")
        test_db.add(student)
        test_db.flush()
        sub = Submission(
            exam_id=exam.id, student_id=student.id, scoring_strategy="latest"
        )
        test_db.add(sub)
        test_db.flush()
        att = Attempt(
            submission_id=sub.id,
            institution_id=inst.id,
            attempt_number=1,
            source="moodle_csv",
            source_attempt_id=f"s{idx}|1",
        )
        test_db.add(att)
        test_db.flush()
        ans = AttemptAnswer(
            attempt_id=att.id,
            exam_question_id=eq.id,
            given_answer=f"Antwort {idx}",
        )
        test_db.add(ans)
        test_db.flush()
        grade = Grade(
            attempt_answer_id=ans.id,
            points_awarded=2.0,
            points_max=4.0,
            status=status,
            is_correct=None,
        )
        if status == GradeStatus.MANUAL_OVERRIDE.value:
            grade.points_awarded = 1.5
        test_db.add(grade)
        grades.append(grade)
    test_db.commit()
    return eq, grades, user, inst


def test_regrade_keeps_manual_override_untouched(test_db: Session) -> None:
    eq, grades, user, _ = _seed_three_open_ended_grades(test_db)
    proposed_g, approved_g, override_g = grades

    fake_llm = MagicMock(spec=LlmGrader)
    fake_llm.grade.return_value = LlmGradeOutcome(
        points_awarded=3.5,
        points_max=4.0,
        confidence=0.8,
        rationale="Re-Grading nach geänderter Musterlösung.",
        matched_aspects=[],
        missing_aspects=[],
    )

    count = GradingService(
        test_db, llm_grader=fake_llm
    ).regrade_after_correct_answer_update(exam_question_id=eq.id, triggered_by=user.id)
    test_db.commit()

    # Zwei wurden re-gradet (proposed, approved); manual_override blieb.
    assert count == 2

    test_db.refresh(proposed_g)
    test_db.refresh(approved_g)
    test_db.refresh(override_g)

    # proposed bleibt proposed, hat aber neue Punkte
    assert proposed_g.status == GradeStatus.PROPOSED.value
    assert proposed_g.points_awarded == 3.5

    # approved wurde zurück auf proposed gesetzt + neu bewertet
    assert approved_g.status == GradeStatus.PROPOSED.value
    assert approved_g.points_awarded == 3.5
    assert approved_g.reviewer_id is None
    assert approved_g.reviewed_at is None

    # manual_override unverändert in Punktzahl + Status
    assert override_g.status == GradeStatus.MANUAL_OVERRIDE.value
    assert override_g.points_awarded == 1.5


def test_regrade_writes_history_entries(test_db: Session) -> None:
    eq, grades, user, _ = _seed_three_open_ended_grades(test_db)
    proposed_g, approved_g, override_g = grades

    fake_llm = MagicMock(spec=LlmGrader)
    fake_llm.grade.return_value = LlmGradeOutcome(
        points_awarded=2.0,
        points_max=4.0,
        confidence=0.6,
        rationale="...",
        matched_aspects=[],
        missing_aspects=[],
    )
    GradingService(test_db, llm_grader=fake_llm).regrade_after_correct_answer_update(
        exam_question_id=eq.id, triggered_by=user.id
    )
    test_db.commit()

    rows = (
        test_db.query(GradeHistory)
        .filter(GradeHistory.change_reason == CHANGE_REASON_REGRADE)
        .all()
    )
    grade_ids = {r.grade_id for r in rows}
    # Genau zwei history-Einträge — proposed + approved
    assert grade_ids == {proposed_g.id, approved_g.id}
    assert override_g.id not in grade_ids
    # changed_by gesetzt
    for r in rows:
        assert r.changed_by == user.id


def test_regrade_returns_zero_on_unknown_question(test_db: Session) -> None:
    """Defense-in-depth: unbekannte exam_question_id wirft nicht, sondern
    liefert 0 zurück. Endpoint-Schicht meldet 404 davor — aber Service
    bleibt robust für Background-Jobs."""
    count = GradingService(test_db).regrade_after_correct_answer_update(
        exam_question_id=99999999, triggered_by=None
    )
    assert count == 0
