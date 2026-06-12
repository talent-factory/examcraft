"""Tests for the cross-exam statistics service + API (TF-336 Subarea B).

Covers:

* ``StatisticsService.class_history`` — per-member chronology, per-exam
  aggregates, topic coverage; respects current-membership semantics.
* ``StatisticsService.student_history`` — chronological submissions,
  Bloom-Mix, Topic-Heatmap, attached classes.
* ``GET /api/v1/student-classes/{id}/stats``
* ``GET /api/v1/students/{id}/stats``
* multi-tenancy on both endpoints.
"""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import get_db
from main import app
from models.auth import Institution, User, UserStatus
from models.exam import Exam, ExamQuestion
from models.question_review import QuestionReview
from models.student import Student, StudentClass, StudentClassMembership
from models.submission import Attempt, AttemptAnswer, Grade, Submission
from services.statistics_service import StatisticsService
from utils.auth_utils import get_current_user, get_current_active_user


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _make_institution(db: Session, slug: str) -> Institution:
    inst = Institution(
        name=f"Inst-{slug}",
        slug=slug,
        subscription_tier="enterprise",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.flush()
    return inst


def _make_user(db: Session, institution_id: int, *, email: str | None = None) -> User:
    user = User(
        email=email or f"admin-{institution_id}@test.ch",
        first_name="Admin",
        last_name="Tester",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
        is_superuser=True,
    )
    db.add(user)
    db.flush()
    return user


def _make_question(
    db: Session, institution_id: int, *, topic: str, bloom_level: int = 2
) -> QuestionReview:
    q = QuestionReview(
        question_text=f"Q[{topic}]",
        question_type="single_choice",
        options=["A", "B"],
        correct_answer="A",
        difficulty="medium",
        topic=topic,
        bloom_level=bloom_level,
        institution_id=institution_id,
    )
    db.add(q)
    db.flush()
    return q


def _make_exam(
    db: Session,
    institution_id: int,
    *,
    title: str,
    exam_date_value: date,
    questions: list[tuple[QuestionReview, float]],
) -> Exam:
    exam = Exam(
        title=title,
        course="TF-336",
        exam_date=exam_date_value,
        passing_percentage=50.0,
        total_points=sum(p for _, p in questions),
        status="finalized",
        language="de",
        institution_id=institution_id,
    )
    db.add(exam)
    db.flush()
    for pos, (qr, points) in enumerate(questions, start=1):
        db.add(
            ExamQuestion(
                exam_id=exam.id, question_id=qr.id, position=pos, points=points
            )
        )
    db.flush()
    return exam


def _add_submission(
    db: Session,
    *,
    exam: Exam,
    student: Student,
    answers: list[tuple[ExamQuestion, float, float]],
    grade_status: str = "fully_reviewed",
) -> Submission:
    """answers = list of (exam_question, points_awarded, points_max)."""
    submission = Submission(
        exam_id=exam.id,
        student_id=student.id,
        scoring_strategy="latest",
        grade_status=grade_status,
        total_points_awarded=sum(p for _, p, _ in answers),
        total_points_max=sum(m for _, _, m in answers),
        percentage=(
            100.0 * sum(p for _, p, _ in answers) / sum(m for _, _, m in answers)
            if answers
            else 0.0
        ),
    )
    db.add(submission)
    db.flush()

    attempt = Attempt(
        submission_id=submission.id,
        institution_id=exam.institution_id,
        attempt_number=1,
        source="moodle_csv",
        source_attempt_id=f"{student.external_id}|{exam.id}",
    )
    db.add(attempt)
    db.flush()

    for eq, awarded, max_pts in answers:
        ans = AttemptAnswer(
            attempt_id=attempt.id,
            exam_question_id=eq.id,
            given_answer="A",
        )
        db.add(ans)
        db.flush()
        db.add(
            Grade(
                attempt_answer_id=ans.id,
                points_awarded=awarded,
                points_max=max_pts,
                status="approved",
                is_correct=awarded == max_pts,
            )
        )
    submission.graded_attempt_id = attempt.id
    db.flush()
    return submission


@pytest.fixture
def two_exams_setup(test_db: Session):
    inst = _make_institution(test_db, slug="tf336-stats")
    user = _make_user(test_db, inst.id)
    geo = _make_question(test_db, inst.id, topic="Geo", bloom_level=2)
    his = _make_question(test_db, inst.id, topic="History", bloom_level=3)

    exam1 = _make_exam(
        test_db,
        inst.id,
        title="Prüfung 1",
        exam_date_value=date(2026, 3, 1),
        questions=[(geo, 4.0), (his, 1.0)],
    )
    exam2 = _make_exam(
        test_db,
        inst.id,
        title="Prüfung 2",
        exam_date_value=date(2026, 4, 1),
        questions=[(geo, 4.0), (his, 1.0)],
    )

    anna = Student(
        institution_id=inst.id, external_id="anna@example.org", display_name="Anna B."
    )
    bruno = Student(
        institution_id=inst.id, external_id="bruno@example.org", display_name="Bruno M."
    )
    test_db.add_all([anna, bruno])
    test_db.flush()

    student_class = StudentClass(institution_id=inst.id, name="INF-23a")
    test_db.add(student_class)
    test_db.flush()
    test_db.add_all(
        [
            StudentClassMembership(student_id=anna.id, class_id=student_class.id),
            StudentClassMembership(student_id=bruno.id, class_id=student_class.id),
        ]
    )
    test_db.flush()

    eq1_geo = (
        test_db.query(ExamQuestion)
        .filter(ExamQuestion.exam_id == exam1.id, ExamQuestion.position == 1)
        .one()
    )
    eq1_his = (
        test_db.query(ExamQuestion)
        .filter(ExamQuestion.exam_id == exam1.id, ExamQuestion.position == 2)
        .one()
    )
    eq2_geo = (
        test_db.query(ExamQuestion)
        .filter(ExamQuestion.exam_id == exam2.id, ExamQuestion.position == 1)
        .one()
    )
    eq2_his = (
        test_db.query(ExamQuestion)
        .filter(ExamQuestion.exam_id == exam2.id, ExamQuestion.position == 2)
        .one()
    )

    # Anna improves: 60 % → 100 %
    _add_submission(
        test_db,
        exam=exam1,
        student=anna,
        answers=[(eq1_geo, 2.0, 4.0), (eq1_his, 1.0, 1.0)],
    )
    _add_submission(
        test_db,
        exam=exam2,
        student=anna,
        answers=[(eq2_geo, 4.0, 4.0), (eq2_his, 1.0, 1.0)],
    )
    # Bruno: 80 % → 40 % (drops)
    _add_submission(
        test_db,
        exam=exam1,
        student=bruno,
        answers=[(eq1_geo, 4.0, 4.0), (eq1_his, 0.0, 1.0)],
    )
    _add_submission(
        test_db,
        exam=exam2,
        student=bruno,
        answers=[(eq2_geo, 2.0, 4.0), (eq2_his, 0.0, 1.0)],
    )
    test_db.commit()

    return {
        "institution": inst,
        "user": user,
        "class": student_class,
        "anna": anna,
        "bruno": bruno,
        "exam1": exam1,
        "exam2": exam2,
    }


def _client(test_db: Session, user: User) -> TestClient:
    import api.student_classes as student_classes_module
    import api.students as students_module

    if student_classes_module.router not in app.router.routes:
        app.include_router(student_classes_module.router)
    if students_module.router not in app.router.routes:
        app.include_router(students_module.router)

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Service-level
# ---------------------------------------------------------------------------


def test_class_history_aggregates_per_member_and_per_exam(
    test_db: Session, two_exams_setup: dict
) -> None:
    inst = two_exams_setup["institution"]
    student_class = two_exams_setup["class"]

    stats = StatisticsService(test_db).class_history(
        class_id=student_class.id, institution_id=inst.id
    )
    assert stats is not None
    assert stats.member_count == 2
    assert {m.external_id for m in stats.members} == {
        "anna@example.org",
        "bruno@example.org",
    }
    anna_perf = next(m for m in stats.members if m.external_id == "anna@example.org")
    assert anna_perf.submission_count == 2
    # 60 % then 100 %
    assert anna_perf.submissions[0].percentage == pytest.approx(60.0)
    assert anna_perf.submissions[1].percentage == pytest.approx(100.0)
    assert anna_perf.avg_percentage == pytest.approx(80.0)

    # Per-exam aggregate sorted by date.
    titles = [a.exam_title for a in stats.exam_aggregates]
    assert titles == ["Prüfung 1", "Prüfung 2"]
    # Anna 60 % + Bruno 80 % = 70 % avg for exam 1.
    assert stats.exam_aggregates[0].avg_percentage == pytest.approx(70.0)
    # Anna 100 % + Bruno 40 % = 70 % avg for exam 2.
    assert stats.exam_aggregates[1].avg_percentage == pytest.approx(70.0)
    # 50 % passing → exam1: both pass → pass_rate=1.0; exam2: only Anna → 0.5
    assert stats.exam_aggregates[0].pass_rate == pytest.approx(1.0)
    assert stats.exam_aggregates[1].pass_rate == pytest.approx(0.5)

    topics = {t.topic for t in stats.topic_coverage}
    assert topics == {"Geo", "History"}


def test_class_history_excludes_removed_member(
    test_db: Session, two_exams_setup: dict
) -> None:
    inst = two_exams_setup["institution"]
    student_class = two_exams_setup["class"]
    bruno = two_exams_setup["bruno"]

    # Bruno aus der Klasse entfernen.
    test_db.query(StudentClassMembership).filter(
        StudentClassMembership.class_id == student_class.id,
        StudentClassMembership.student_id == bruno.id,
    ).delete()
    test_db.commit()

    stats = StatisticsService(test_db).class_history(
        class_id=student_class.id, institution_id=inst.id
    )
    assert stats is not None
    assert stats.member_count == 1
    assert {m.external_id for m in stats.members} == {"anna@example.org"}
    # Per-exam aggregate now reflects only Anna (60 %, 100 %).
    assert stats.exam_aggregates[0].avg_percentage == pytest.approx(60.0)
    assert stats.exam_aggregates[1].avg_percentage == pytest.approx(100.0)


def test_student_history_chronological_with_bloom_and_topics(
    test_db: Session, two_exams_setup: dict
) -> None:
    inst = two_exams_setup["institution"]
    anna = two_exams_setup["anna"]

    stats = StatisticsService(test_db).student_history(
        student_id=anna.id, institution_id=inst.id
    )
    assert stats is not None
    assert stats.submission_count == 2
    assert [s.percentage for s in stats.submissions] == pytest.approx([60.0, 100.0])
    assert stats.avg_percentage == pytest.approx(80.0)

    # Bloom-Mix: Geo bloom_level=2 in 2 attempts, History bloom_level=3 in 2.
    assert stats.bloom_mix == {2: 2, 3: 2}
    topics = {t.topic for t in stats.topic_heatmap}
    assert topics == {"Geo", "History"}

    # Anna ist Mitglied von INF-23a.
    assert {c.class_name for c in stats.classes} == {"INF-23a"}


# ---------------------------------------------------------------------------
# API-level
# ---------------------------------------------------------------------------


def test_class_stats_endpoint_returns_aggregates(
    test_db: Session, two_exams_setup: dict
) -> None:
    user = two_exams_setup["user"]
    student_class = two_exams_setup["class"]

    client = _client(test_db, user)
    resp = client.get(f"/api/v1/student-classes/{student_class.id}/stats")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["member_count"] == 2
    assert body["class_name"] == "INF-23a"
    assert len(body["exam_aggregates"]) == 2
    assert body["exam_aggregates"][0]["avg_percentage"] == pytest.approx(70.0)


def test_student_stats_endpoint_returns_history(
    test_db: Session, two_exams_setup: dict
) -> None:
    user = two_exams_setup["user"]
    anna = two_exams_setup["anna"]

    client = _client(test_db, user)
    resp = client.get(f"/api/v1/students/{anna.id}/stats")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["submission_count"] == 2
    assert body["avg_percentage"] == pytest.approx(80.0)
    # JSON serialises Bloom keys as strings.
    assert body["bloom_mix"] == {"2": 2, "3": 2}


def test_student_list_endpoint_paginates_and_filters(
    test_db: Session, two_exams_setup: dict
) -> None:
    user = two_exams_setup["user"]
    client = _client(test_db, user)

    resp = client.get("/api/v1/students")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert {item["external_id"] for item in body["items"]} == {
        "anna@example.org",
        "bruno@example.org",
    }
    # Search hits display_name as well.
    resp_search = client.get("/api/v1/students", params={"search": "anna"})
    assert resp_search.status_code == 200
    assert {item["external_id"] for item in resp_search.json()["items"]} == {
        "anna@example.org"
    }


def test_class_stats_404_for_other_institution(
    test_db: Session, two_exams_setup: dict
) -> None:
    other_inst = _make_institution(test_db, slug="tf336-stats-other")
    other_user = _make_user(test_db, other_inst.id)
    test_db.commit()

    client = _client(test_db, other_user)
    resp = client.get(f"/api/v1/student-classes/{two_exams_setup['class'].id}/stats")
    assert resp.status_code == 404


def test_student_stats_404_for_other_institution(
    test_db: Session, two_exams_setup: dict
) -> None:
    other_inst = _make_institution(test_db, slug="tf336-stats-other2")
    other_user = _make_user(test_db, other_inst.id)
    test_db.commit()

    client = _client(test_db, other_user)
    resp = client.get(f"/api/v1/students/{two_exams_setup['anna'].id}/stats")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Empty-class / empty-data edge cases — no divide-by-zero, no 500
# ---------------------------------------------------------------------------


def test_class_history_with_no_members(test_db: Session) -> None:
    """A class with no members must return zero-shaped stats, not 500.

    The dashboard renders this as an "empty" state; if the service
    crashed, the whole Klassen-page would 500."""
    inst = _make_institution(test_db, slug="tf336-stats-empty-cls")
    student_class = StudentClass(institution_id=inst.id, name="Leere-Klasse")
    test_db.add(student_class)
    test_db.commit()

    stats = StatisticsService(test_db).class_history(
        class_id=student_class.id, institution_id=inst.id
    )
    assert stats is not None
    assert stats.member_count == 0
    assert stats.members == []
    assert stats.exam_aggregates == []
    assert stats.topic_coverage == []


def test_class_history_with_member_zero_submissions(test_db: Session) -> None:
    """A class with members but zero submissions must yield an
    aggregate where ``avg_percentage`` is ``None``, not a ZeroDivisionError."""
    inst = _make_institution(test_db, slug="tf336-stats-empty-subs")
    student_class = StudentClass(institution_id=inst.id, name="Stille-Klasse")
    test_db.add(student_class)
    test_db.flush()
    student = Student(
        institution_id=inst.id,
        external_id="silent@example.org",
        display_name="Silent",
    )
    test_db.add(student)
    test_db.flush()
    test_db.add(
        StudentClassMembership(class_id=student_class.id, student_id=student.id)
    )
    test_db.commit()

    stats = StatisticsService(test_db).class_history(
        class_id=student_class.id, institution_id=inst.id
    )
    assert stats is not None
    assert stats.member_count == 1
    member = stats.members[0]
    assert member.submission_count == 0
    assert member.avg_percentage is None
    # No submissions ⇒ no exams to aggregate, no topics to cover.
    assert stats.exam_aggregates == []
    assert stats.topic_coverage == []


def test_student_history_with_no_submissions(test_db: Session) -> None:
    """A student who has never submitted must return an empty
    ``StudentHistoryStats``, not crash."""
    inst = _make_institution(test_db, slug="tf336-stats-empty-stu")
    student = Student(
        institution_id=inst.id,
        external_id="never@example.org",
        display_name="Never",
    )
    test_db.add(student)
    test_db.commit()

    stats = StatisticsService(test_db).student_history(
        student_id=student.id, institution_id=inst.id
    )
    assert stats is not None
    assert stats.submission_count == 0
    assert stats.avg_percentage is None
    assert stats.submissions == []
