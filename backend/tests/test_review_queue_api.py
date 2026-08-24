"""API tests for /api/v1/exams/{id}/review-queue + /api/v1/grades/*.

Covers: filters, RBAC, multi-tenancy, approve/override/bulk-approve.
The re-grading endpoint has its own test.
"""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import get_db
from enums import GradeStatus
from main import app
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
from utils.auth_utils import get_current_user, get_current_active_user


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------


def _make_institution(db: Session, slug: str) -> Institution:
    inst = Institution(
        name=f"RQ-{slug}",
        slug=f"rq-{slug}",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.flush()
    return inst


def _make_user(
    db: Session,
    inst: Institution,
    *,
    email: str,
    is_superuser: bool = True,
) -> User:
    user = User(
        email=email,
        first_name="X",
        last_name="Y",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=is_superuser,
    )
    db.add(user)
    db.flush()
    return user


def _seed_exam_with_proposed_grades(
    db: Session, inst: Institution, *, count: int = 3
) -> tuple[Exam, list[Grade]]:
    """``count`` open_ended answers from ``count`` different
    students. Confidence descending by index, so sorting is
    observable."""
    qr = QuestionReview(
        question_text="Erkläre Polymorphie.",
        question_type="open_ended",
        correct_answer="Methoden mit gleichem Namen, unterschiedlicher Implementierung.",
        difficulty="medium",
        topic="OOP",
        institution_id=inst.id,
    )
    db.add(qr)
    db.flush()
    exam = Exam(
        title="Review Queue API",
        course="OOP",
        exam_date=date(2026, 5, 15),
        passing_percentage=50.0,
        total_points=4.0,
        status="finalized",
        language="de",
        institution_id=inst.id,
    )
    db.add(exam)
    db.flush()
    eq = ExamQuestion(exam_id=exam.id, question_id=qr.id, position=1, points=4.0)
    db.add(eq)
    db.flush()

    grades: list[Grade] = []
    for idx in range(count):
        student = Student(
            institution_id=inst.id,
            external_id=f"st{idx}@rq.org",
            display_name=f"S{idx}",
        )
        db.add(student)
        db.flush()
        sub = Submission(
            exam_id=exam.id, student_id=student.id, scoring_strategy="latest"
        )
        db.add(sub)
        db.flush()
        att = Attempt(
            submission_id=sub.id,
            institution_id=inst.id,
            attempt_number=1,
            source="moodle_csv",
            source_attempt_id=f"st{idx}|1",
        )
        db.add(att)
        db.flush()
        ans = AttemptAnswer(
            attempt_id=att.id,
            exam_question_id=eq.id,
            given_answer=f"Antwort {idx}",
        )
        db.add(ans)
        db.flush()
        grade = Grade(
            attempt_answer_id=ans.id,
            points_awarded=2.0,
            points_max=4.0,
            status=GradeStatus.PROPOSED.value,
            is_correct=None,
            llm_confidence=0.3 + 0.2 * idx,  # 0.3 / 0.5 / 0.7
            llm_rationale=f"Begründung {idx}",
            llm_matched_aspects=[f"matched-{idx}"],
            llm_missing_aspects=[f"missing-{idx}"],
        )
        db.add(grade)
        grades.append(grade)
    db.commit()
    return exam, grades


def _client(test_db: Session, user: User) -> TestClient:
    """TestClient with DB + user override. Ensures the grades routes are
    registered in case the lifespan doesn't load them via importlib in
    test environments."""
    import api.grades as grades_module

    if grades_module.router_grades not in app.router.routes:
        app.include_router(grades_module.router_grades)
    if grades_module.router_exams_review_queue not in app.router.routes:
        app.include_router(grades_module.router_exams_review_queue)

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Review-Queue
# ---------------------------------------------------------------------------


def test_review_queue_returns_proposed_open_ended_sorted_by_confidence(
    test_db: Session,
) -> None:
    inst = _make_institution(test_db, "list")
    user = _make_user(test_db, inst, email="list@rq.org")
    exam, grades = _seed_exam_with_proposed_grades(test_db, inst, count=3)
    client = _client(test_db, user)

    response = client.get(f"/api/v1/exams/{exam.id}/review-queue")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 3
    confidences = [item["confidence"] for item in body["items"]]
    # Ascending order — lowest first.
    assert confidences == sorted(confidences)
    # First entry contains question + model answer + aspects.
    first = body["items"][0]
    assert first["question_text"] == "Erkläre Polymorphie."
    assert first["correct_answer"].startswith("Methoden")
    assert "matched-0" in first["matched_aspects"]


def test_review_queue_filter_by_confidence_min_max(test_db: Session) -> None:
    inst = _make_institution(test_db, "filter")
    user = _make_user(test_db, inst, email="filter@rq.org")
    exam, _ = _seed_exam_with_proposed_grades(test_db, inst, count=3)
    client = _client(test_db, user)

    response = client.get(
        f"/api/v1/exams/{exam.id}/review-queue",
        params={"confidence_min": 0.4, "confidence_max": 0.6},
    )
    assert response.status_code == 200
    confidences = [item["confidence"] for item in response.json()["items"]]
    assert all(0.4 <= c <= 0.6 for c in confidences)
    assert len(confidences) == 1


def test_review_queue_invalid_range_returns_400(test_db: Session) -> None:
    inst = _make_institution(test_db, "rng")
    user = _make_user(test_db, inst, email="rng@rq.org")
    exam, _ = _seed_exam_with_proposed_grades(test_db, inst, count=1)
    client = _client(test_db, user)

    response = client.get(
        f"/api/v1/exams/{exam.id}/review-queue",
        params={"confidence_min": 0.9, "confidence_max": 0.1},
    )
    assert response.status_code == 400


def test_review_queue_blocks_foreign_institution(test_db: Session) -> None:
    inst_a = _make_institution(test_db, "a")
    inst_b = _make_institution(test_db, "b")
    user_b = _make_user(test_db, inst_b, email="b@rq.org")
    exam_a, _ = _seed_exam_with_proposed_grades(test_db, inst_a, count=1)
    client = _client(test_db, user_b)

    response = client.get(f"/api/v1/exams/{exam_a.id}/review-queue")
    # 404 instead of 403 — no information leak.
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Approve / Override / Bulk-Approve
# ---------------------------------------------------------------------------


def test_approve_grade_changes_status(test_db: Session) -> None:
    inst = _make_institution(test_db, "approve")
    user = _make_user(test_db, inst, email="ap@rq.org")
    _, grades = _seed_exam_with_proposed_grades(test_db, inst, count=1)
    client = _client(test_db, user)

    response = client.post(f"/api/v1/grades/{grades[0].id}/approve")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "approved"
    assert body["reviewer_id"] == user.id


def test_override_grade_writes_points_and_note(test_db: Session) -> None:
    inst = _make_institution(test_db, "override")
    user = _make_user(test_db, inst, email="ov@rq.org")
    _, grades = _seed_exam_with_proposed_grades(test_db, inst, count=1)
    client = _client(test_db, user)

    response = client.post(
        f"/api/v1/grades/{grades[0].id}/override",
        json={"points_awarded": 3.5, "reviewer_note": "Vererbung erwähnt"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "manual_override"
    assert body["points_awarded"] == 3.5
    assert body["reviewer_note"] == "Vererbung erwähnt"


def test_override_rejects_points_above_max(test_db: Session) -> None:
    inst = _make_institution(test_db, "ovmax")
    user = _make_user(test_db, inst, email="ovmax@rq.org")
    _, grades = _seed_exam_with_proposed_grades(test_db, inst, count=1)
    client = _client(test_db, user)

    response = client.post(
        f"/api/v1/grades/{grades[0].id}/override",
        json={"points_awarded": 99.0},
    )
    assert response.status_code == 422


def test_grade_action_blocks_foreign_institution(test_db: Session) -> None:
    inst_a = _make_institution(test_db, "ga")
    inst_b = _make_institution(test_db, "gb")
    user_b = _make_user(test_db, inst_b, email="gb@rq.org")
    _, grades_a = _seed_exam_with_proposed_grades(test_db, inst_a, count=1)
    client = _client(test_db, user_b)

    response = client.post(f"/api/v1/grades/{grades_a[0].id}/approve")
    assert response.status_code == 404


def test_bulk_approve_by_confidence_min(test_db: Session) -> None:
    inst = _make_institution(test_db, "bulk")
    user = _make_user(test_db, inst, email="bulk@rq.org")
    exam, grades = _seed_exam_with_proposed_grades(test_db, inst, count=3)
    # Confidences 0.3 / 0.5 / 0.7 — threshold 0.5 matches 2.
    client = _client(test_db, user)

    response = client.post(
        "/api/v1/grades/bulk-approve",
        json={"exam_id": exam.id, "confidence_min": 0.5},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["approved_count"] == 2
    # All approved grades have confidence >= 0.5
    approved_ids = set(body["grade_ids"])
    high_confidence_ids = {g.id for g in grades if g.llm_confidence >= 0.5}
    assert approved_ids == high_confidence_ids


def test_bulk_approve_by_grade_ids(test_db: Session) -> None:
    inst = _make_institution(test_db, "bulkids")
    user = _make_user(test_db, inst, email="bulkids@rq.org")
    exam, grades = _seed_exam_with_proposed_grades(test_db, inst, count=3)
    client = _client(test_db, user)

    response = client.post(
        "/api/v1/grades/bulk-approve",
        json={"exam_id": exam.id, "grade_ids": [grades[0].id, grades[2].id]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["approved_count"] == 2


def test_bulk_approve_rejects_both_filters(test_db: Session) -> None:
    """Both filters set at once would be auto-approve through the back door —
    spec 6.4 explicitly says "no auto-approve". Same for no filter set:
    otherwise you'd unintentionally approve an entire exam."""
    inst = _make_institution(test_db, "bulkno")
    user = _make_user(test_db, inst, email="bulkno@rq.org")
    exam, _ = _seed_exam_with_proposed_grades(test_db, inst, count=1)
    client = _client(test_db, user)

    # both filters set
    r1 = client.post(
        "/api/v1/grades/bulk-approve",
        json={"exam_id": exam.id, "confidence_min": 0.5, "grade_ids": [1]},
    )
    assert r1.status_code == 422

    # neither filter set
    r2 = client.post(
        "/api/v1/grades/bulk-approve",
        json={"exam_id": exam.id},
    )
    assert r2.status_code == 422


def test_bulk_approve_blocks_foreign_grade_ids(test_db: Session) -> None:
    """Bulk-approve with grade IDs from another tenant — the service must
    filter out the grade set via institution_id, otherwise tenant A could
    approve grades belonging to tenant B."""
    inst_a = _make_institution(test_db, "fa")
    inst_b = _make_institution(test_db, "fb")
    user_b = _make_user(test_db, inst_b, email="fb@rq.org")
    exam_a, grades_a = _seed_exam_with_proposed_grades(test_db, inst_a, count=2)
    exam_b, _ = _seed_exam_with_proposed_grades(test_db, inst_b, count=1)
    client = _client(test_db, user_b)

    # Tenant B tries to approve grades from tenant A, but cheats by
    # setting the exam_id parameter to B's own exam.
    response = client.post(
        "/api/v1/grades/bulk-approve",
        json={"exam_id": exam_b.id, "grade_ids": [g.id for g in grades_a]},
    )
    # Endpoint accepts B's exam_id, but the filter finds no matching
    # grades → 0 approved.
    assert response.status_code == 200
    assert response.json()["approved_count"] == 0


# ---------------------------------------------------------------------------
# RBAC: A user without submissions:grade must not be able to approve
# ---------------------------------------------------------------------------


def test_approve_requires_submissions_grade_permission(test_db: Session) -> None:
    """The permission check is the safety net in case a frontend bug
    makes the approve button visible even to read-only users."""
    from models.auth import Role, UserRole

    inst = _make_institution(test_db, "rbac")
    role = test_db.query(Role).filter(Role.name == UserRole.VIEWER.value).one_or_none()
    if role is None:
        # Viewer role has NO submissions:grade permission.
        role = Role(
            name=UserRole.VIEWER.value,
            display_name="Viewer",
            description="Read-only",
            permissions=[],
            is_system_role=True,
        )
        test_db.add(role)
        test_db.flush()
    user = User(
        email="reader@rq.org",
        first_name="R",
        last_name="O",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    user.roles.append(role)
    test_db.add(user)
    _, grades = _seed_exam_with_proposed_grades(test_db, inst, count=1)
    test_db.commit()
    client = _client(test_db, user)

    response = client.post(f"/api/v1/grades/{grades[0].id}/approve")
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Re-Grade Endpoint
# ---------------------------------------------------------------------------


def test_regrade_question_endpoint_resets_grades(test_db: Session) -> None:
    inst = _make_institution(test_db, "regrade-api")
    user = _make_user(test_db, inst, email="rg@rq.org")
    exam, grades = _seed_exam_with_proposed_grades(test_db, inst, count=2)
    # Approve one, so re-grading also resets the approved path.
    test_db.query(Grade).filter(Grade.id == grades[0].id).update(
        {"status": GradeStatus.APPROVED.value, "reviewer_id": user.id}
    )
    test_db.commit()

    eq_id = (
        test_db.query(ExamQuestion.id).filter(ExamQuestion.exam_id == exam.id).scalar()
    )
    client = _client(test_db, user)

    response = client.post(f"/api/v1/exams/{exam.id}/questions/{eq_id}/regrade")
    assert response.status_code == 200, response.text
    body = response.json()
    # 2 were re-graded (proposed + approved); no manual_override in the
    # setup, otherwise count would be 1.
    assert body["regraded_count"] == 2
    assert body["exam_question_id"] == eq_id
