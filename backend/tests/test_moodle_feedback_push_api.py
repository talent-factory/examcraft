"""TF-435: Moodle feedback push API (POST enqueue + GET poll)."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import get_db
from main import app
from models.auth import Institution, Role, User, UserStatus
from models.exam import Exam, ExamQuestion
from models.question_review import QuestionReview
from models.submission import MoodleConnection, MoodleFeedbackPushJob
from utils.auth_utils import get_current_active_user, get_current_user
from utils.secret_encryption import encrypt_secret, reset_cache_for_tests

_PERM = "submissions:moodle_feedback_push"


@pytest.fixture(autouse=True)
def _crypto_env(monkeypatch):
    """Provide a deterministic Fernet key (CI sets neither key by default)."""
    monkeypatch.delenv("MOODLE_TOKEN_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("SECRET_KEY", "dev-secret-key-for-tests")
    reset_cache_for_tests()
    yield
    reset_cache_for_tests()


def _institution(db: Session, slug: str = "tf435") -> Institution:
    inst = Institution(
        name=f"Inst-{slug}",
        slug=slug,
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.flush()
    return inst


def _user(db: Session, inst_id: int, *, permissions=None, email="lp@test.ch") -> User:
    role = Role(
        name=f"role_{email}",
        display_name="Test Role",
        permissions=permissions if permissions is not None else [_PERM],
        is_system_role=False,
    )
    db.add(role)
    db.flush()
    user = User(
        email=email,
        first_name="Test",
        last_name="LP",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=inst_id,
        status=UserStatus.ACTIVE.value,
    )
    user.roles.append(role)
    db.add(user)
    db.flush()
    return user


def _exam(db: Session, inst_id: int, *, with_quiz_id: bool = True) -> Exam:
    exam = Exam(title="Statistik FS26", status="finalized", institution_id=inst_id)
    db.add(exam)
    db.flush()
    qr = QuestionReview(
        question_text="?",
        question_type="single_choice",
        difficulty="easy",
        topic="x",
        institution_id=inst_id,  # TF-642: default visibility='institution' requires this
    )
    db.add(qr)
    db.flush()
    refs = {"moodle_quiz_id": 4242, "moodle_slot": 1} if with_quiz_id else {}
    db.add(
        ExamQuestion(
            exam_id=exam.id,
            question_id=qr.id,
            position=1,
            points=5.0,
            external_refs=refs,
        )
    )
    db.flush()
    return exam


def _connection(db: Session, inst_id: int) -> MoodleConnection:
    conn = MoodleConnection(
        institution_id=inst_id,
        base_url="https://moodle.example",
        token_encrypted=encrypt_secret("tok"),
    )
    db.add(conn)
    db.flush()
    return conn


def _client(test_db: Session, user: User) -> TestClient:
    import api.moodle_feedback_push as mod

    if mod.router not in app.router.routes:
        app.include_router(mod.router)

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_push_returns_202_and_creates_job(test_db: Session) -> None:
    inst = _institution(test_db)
    user = _user(test_db, inst.id)
    exam = _exam(test_db, inst.id)
    _connection(test_db, inst.id)
    test_db.commit()

    client = _client(test_db, user)
    with patch("api.moodle_feedback_push.push_moodle_feedback.apply_async") as enq:
        resp = client.post(f"/api/v1/exams/{exam.id}/moodle/push-feedback")

    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "queued"
    enq.assert_called_once()
    job = (
        test_db.query(MoodleFeedbackPushJob)
        .filter(MoodleFeedbackPushJob.exam_id == exam.id)
        .one()
    )
    assert job.triggered_by == user.id


def test_push_412_without_quiz_id(test_db: Session) -> None:
    inst = _institution(test_db, slug="tf435b")
    user = _user(test_db, inst.id, email="lp2@test.ch")
    exam = _exam(test_db, inst.id, with_quiz_id=False)
    _connection(test_db, inst.id)
    test_db.commit()

    client = _client(test_db, user)
    resp = client.post(f"/api/v1/exams/{exam.id}/moodle/push-feedback")
    assert resp.status_code == 412


def test_push_403_without_permission(test_db: Session) -> None:
    inst = _institution(test_db, slug="tf435c")
    user = _user(
        test_db, inst.id, permissions=["submissions:read"], email="lp3@test.ch"
    )
    exam = _exam(test_db, inst.id)
    _connection(test_db, inst.id)
    test_db.commit()

    client = _client(test_db, user)
    resp = client.post(f"/api/v1/exams/{exam.id}/moodle/push-feedback")
    assert resp.status_code == 403


def test_push_404_cross_tenant_exam(test_db: Session) -> None:
    """A user must not enqueue a push for another institution's exam."""
    inst_a = _institution(test_db, slug="tf435x-a")
    inst_b = _institution(test_db, slug="tf435x-b")
    exam_a = _exam(test_db, inst_a.id)
    _connection(test_db, inst_b.id)
    user_b = _user(test_db, inst_b.id, email="lpb@test.ch")
    test_db.commit()

    client = _client(test_db, user_b)
    resp = client.post(f"/api/v1/exams/{exam_a.id}/moodle/push-feedback")
    assert resp.status_code == 404


def test_get_push_job_404_cross_tenant(test_db: Session) -> None:
    """A user must not read a push job belonging to another institution."""
    inst_a = _institution(test_db, slug="tf435y-a")
    inst_b = _institution(test_db, slug="tf435y-b")
    exam_a = _exam(test_db, inst_a.id)
    job = MoodleFeedbackPushJob(
        institution_id=inst_a.id,
        exam_id=exam_a.id,
        status="completed",
        transport="plugin",
    )
    test_db.add(job)
    user_b = _user(test_db, inst_b.id, email="lpb2@test.ch")
    test_db.commit()

    client = _client(test_db, user_b)
    resp = client.get(f"/api/v1/exams/{exam_a.id}/moodle/push-feedback/{job.id}")
    assert resp.status_code == 404


def test_get_push_job_returns_status(test_db: Session) -> None:
    inst = _institution(test_db, slug="tf435d")
    user = _user(test_db, inst.id, email="lp4@test.ch")
    exam = _exam(test_db, inst.id)
    job = MoodleFeedbackPushJob(
        institution_id=inst.id,
        exam_id=exam.id,
        status="completed",
        transport="plugin",
        students_total=3,
        students_pushed=3,
    )
    test_db.add(job)
    test_db.commit()

    client = _client(test_db, user)
    resp = client.get(f"/api/v1/exams/{exam.id}/moodle/push-feedback/{job.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["transport"] == "plugin"
    assert body["students_pushed"] == 3


def test_push_412_without_connection(test_db: Session) -> None:
    """No Moodle connection configured → 412 (distinct from the no-quiz-id 412)."""
    inst = _institution(test_db, slug="tf435e")
    user = _user(test_db, inst.id, email="lp5@test.ch")
    exam = _exam(test_db, inst.id)  # has quiz id, but no connection seeded
    test_db.commit()

    client = _client(test_db, user)
    resp = client.post(f"/api/v1/exams/{exam.id}/moodle/push-feedback")
    assert resp.status_code == 412
    assert "Verbindung" in resp.json()["detail"]


def test_push_broker_down_fails_job_and_returns_503(test_db: Session) -> None:
    """If enqueue raises (broker down), the job row is failed and we return 503."""
    inst = _institution(test_db, slug="tf435f")
    user = _user(test_db, inst.id, email="lp6@test.ch")
    exam = _exam(test_db, inst.id)
    _connection(test_db, inst.id)
    test_db.commit()

    client = _client(test_db, user)
    with patch(
        "api.moodle_feedback_push.push_moodle_feedback.apply_async",
        side_effect=Exception("broker down"),
    ):
        resp = client.post(f"/api/v1/exams/{exam.id}/moodle/push-feedback")

    assert resp.status_code == 503
    job = (
        test_db.query(MoodleFeedbackPushJob)
        .filter(MoodleFeedbackPushJob.exam_id == exam.id)
        .one()
    )
    assert job.status == "failed"
    assert job.finished_at is not None
    assert job.error_log[0]["scope"] == "job"
