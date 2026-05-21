"""End-to-end tests for the Moodle Question-ID round-trip (TF-336 Subarea D).

Covers:

* ``MoodleXmlExporter.export_with_slot_mapping`` returns a slot/position
  mapping alongside the XML.
* ``POST /api/v1/exams/{id}/sync-moodle-question-ids`` writes
  ``external_refs`` and verifies the quiz via ``mod_quiz_get_quizzes_by_courses``.
* The full round-trip: after sync, ``MoodleApiDriver`` matches answers
  via ``moodle_slot`` instead of falling back to position.
"""

from __future__ import annotations

import json
from datetime import date

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import get_db
from main import app
from models.auth import Institution, User, UserStatus
from models.exam import Exam, ExamQuestion
from models.question_review import QuestionReview
from models.submission import MoodleConnection
from services.exam_export_service import MoodleXmlExporter
from services.import_drivers import MoodleApiDriver
from utils.auth_utils import get_current_user, get_current_active_user
from utils.secret_encryption import encrypt_secret, reset_cache_for_tests


@pytest.fixture(autouse=True)
def _crypto_env(monkeypatch):
    monkeypatch.delenv("MOODLE_TOKEN_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("SECRET_KEY", "dev-secret-key-for-tests")
    reset_cache_for_tests()
    yield
    reset_cache_for_tests()


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


def _make_user(db: Session, institution_id: int) -> User:
    user = User(
        email=f"u-{institution_id}@test.ch",
        first_name="U",
        last_name="X",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
        is_superuser=True,
    )
    db.add(user)
    db.flush()
    return user


def _setup_exam(db: Session, institution_id: int) -> Exam:
    q1 = QuestionReview(
        question_text="Hauptstadt der Schweiz?",
        question_type="multiple_choice",
        options=["A", "B"],
        correct_answer="Bern",
        difficulty="easy",
        topic="Geo",
        institution_id=institution_id,
    )
    q2 = QuestionReview(
        question_text="Bern ist Hauptstadt.",
        question_type="true_false",
        correct_answer="wahr",
        difficulty="easy",
        topic="Geo",
        institution_id=institution_id,
    )
    db.add_all([q1, q2])
    db.flush()
    exam = Exam(
        title="Round-Trip-Test",
        course="TF-336",
        exam_date=date(2026, 5, 15),
        passing_percentage=50.0,
        total_points=5.0,
        status="finalized",
        language="de",
        institution_id=institution_id,
    )
    db.add(exam)
    db.flush()
    db.add_all(
        [
            ExamQuestion(exam_id=exam.id, question_id=q1.id, position=1, points=4.0),
            ExamQuestion(exam_id=exam.id, question_id=q2.id, position=2, points=1.0),
        ]
    )
    db.flush()
    return exam


def _client(test_db: Session, user: User) -> TestClient:
    import api.moodle_roundtrip as roundtrip_module

    if roundtrip_module.router not in app.router.routes:
        app.include_router(roundtrip_module.router)

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Exporter
# ---------------------------------------------------------------------------


def test_exporter_returns_slot_mapping() -> None:
    exam_data = {
        "title": "T",
        "total_points": 5.0,
        "passing_percentage": 50.0,
        "questions": [
            {
                "exam_question_id": 100,
                "position": 1,
                "points": 4.0,
                "question_text": "Q1",
                "question_type": "multiple_choice",
                "options": ["A", "B"],
                "correct_answer": "A",
            },
            {
                "exam_question_id": 200,
                "position": 2,
                "points": 1.0,
                "question_text": "Q2",
                "question_type": "true_false",
                "correct_answer": "wahr",
            },
        ],
    }
    xml, mapping = MoodleXmlExporter.export_with_slot_mapping(exam_data)
    assert "<quiz>" in xml
    assert mapping == [
        {"exam_question_id": 100, "position": 1, "slot": 1},
        {"exam_question_id": 200, "position": 2, "slot": 2},
    ]


def test_exporter_legacy_export_unchanged() -> None:
    """``export()`` still returns just XML for backwards compatibility."""
    exam_data = {
        "title": "T",
        "total_points": 1.0,
        "passing_percentage": 50.0,
        "questions": [
            {
                "position": 1,
                "points": 1.0,
                "question_text": "Q",
                "question_type": "true_false",
                "correct_answer": "wahr",
            },
        ],
    }
    xml = MoodleXmlExporter.export(exam_data)
    assert isinstance(xml, str)
    assert "<quiz>" in xml


# ---------------------------------------------------------------------------
# Sync endpoint
# ---------------------------------------------------------------------------


def test_sync_writes_slot_mapping_when_connection_present(
    test_db: Session,
) -> None:
    inst = _make_institution(test_db, slug="tf336-rt-1")
    user = _make_user(test_db, inst.id)
    exam = _setup_exam(test_db, inst.id)
    test_db.add(
        MoodleConnection(
            institution_id=inst.id,
            base_url="https://moodle.example.org",
            token_encrypted=encrypt_secret("validtokenABCD"),
        )
    )
    test_db.commit()

    client = _client(test_db, user)
    endpoint = "https://moodle.example.org/webservice/rest/server.php"

    with respx.mock() as mock:
        mock.post(endpoint).mock(
            return_value=httpx.Response(
                200,
                json={
                    "quizzes": [
                        {"id": 42, "course": 1, "name": "Geo Quiz", "cmid": 100}
                    ]
                },
            )
        )
        resp = client.post(
            f"/api/v1/exams/{exam.id}/sync-moodle-question-ids",
            json={"moodle_quiz_id": 42},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["moodle_quiz_id"] == 42
    assert body["moodle_quiz_name"] == "Geo Quiz"
    assert {q["moodle_slot"] for q in body["questions"]} == {1, 2}

    refreshed = (
        test_db.query(ExamQuestion)
        .filter(ExamQuestion.exam_id == exam.id)
        .order_by(ExamQuestion.position)
        .all()
    )
    assert refreshed[0].external_refs == {
        "moodle_slot": 1,
        "moodle_quiz_id": 42,
    }
    assert refreshed[1].external_refs == {
        "moodle_slot": 2,
        "moodle_quiz_id": 42,
    }


def test_sync_writes_question_ids_when_provided(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="tf336-rt-2")
    user = _make_user(test_db, inst.id)
    exam = _setup_exam(test_db, inst.id)
    # No MoodleConnection — endpoint should still work (verify is skipped).
    test_db.commit()
    client = _client(test_db, user)

    resp = client.post(
        f"/api/v1/exams/{exam.id}/sync-moodle-question-ids",
        json={
            "moodle_quiz_id": 7,
            "moodle_question_ids": [9001, 9002],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["moodle_quiz_name"] is None  # No connection → no metadata.
    refreshed = (
        test_db.query(ExamQuestion)
        .filter(ExamQuestion.exam_id == exam.id)
        .order_by(ExamQuestion.position)
        .all()
    )
    assert refreshed[0].external_refs["moodle_question_id"] == 9001
    assert refreshed[1].external_refs["moodle_question_id"] == 9002


def test_sync_rejects_quiz_id_not_visible_to_token(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="tf336-rt-3")
    user = _make_user(test_db, inst.id)
    exam = _setup_exam(test_db, inst.id)
    test_db.add(
        MoodleConnection(
            institution_id=inst.id,
            base_url="https://moodle.example.org",
            token_encrypted=encrypt_secret("validtokenABCD"),
        )
    )
    test_db.commit()
    client = _client(test_db, user)
    endpoint = "https://moodle.example.org/webservice/rest/server.php"

    with respx.mock() as mock:
        mock.post(endpoint).mock(
            return_value=httpx.Response(
                200, json={"quizzes": [{"id": 99, "name": "Other"}]}
            )
        )
        resp = client.post(
            f"/api/v1/exams/{exam.id}/sync-moodle-question-ids",
            json={"moodle_quiz_id": 42},
        )
    assert resp.status_code == 404
    assert "nicht sichtbar" in resp.json()["detail"]


def test_sync_rejects_mismatched_question_count(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="tf336-rt-4")
    user = _make_user(test_db, inst.id)
    exam = _setup_exam(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    resp = client.post(
        f"/api/v1/exams/{exam.id}/sync-moodle-question-ids",
        json={
            "moodle_quiz_id": 7,
            "moodle_question_ids": [9001],  # Only 1 ID for 2 questions.
        },
    )
    assert resp.status_code == 400


def test_sync_rejects_duplicate_question_ids(test_db: Session) -> None:
    """Two slots may not map to the same Moodle-question-id — that
    would silently corrupt ``external_refs`` so a later API import
    routes both answers to the same exam_question."""
    inst = _make_institution(test_db, slug="tf336-rt-dup")
    user = _make_user(test_db, inst.id)
    exam = _setup_exam(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    resp = client.post(
        f"/api/v1/exams/{exam.id}/sync-moodle-question-ids",
        json={
            "moodle_quiz_id": 7,
            "moodle_question_ids": [9001, 9001],  # Same ID twice.
        },
    )
    assert resp.status_code == 422
    body = resp.json()
    # Pydantic 422 carries the validator message in detail[0].msg.
    assert any("Duplikate" in (item.get("msg") or "") for item in body["detail"])


def test_sync_rejects_null_question_id(test_db: Session) -> None:
    """A ``null`` entry must be rejected — partial maps are not
    supported. Pydantic would reject this at schema level even without
    the explicit validator, but we lock the message in for clarity."""
    inst = _make_institution(test_db, slug="tf336-rt-null")
    user = _make_user(test_db, inst.id)
    exam = _setup_exam(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    resp = client.post(
        f"/api/v1/exams/{exam.id}/sync-moodle-question-ids",
        json={
            "moodle_quiz_id": 7,
            "moodle_question_ids": [9001, None],
        },
    )
    assert resp.status_code == 422


def test_sync_rejects_non_positive_question_id(test_db: Session) -> None:
    """``0`` and negative values are not valid Moodle question ids."""
    inst = _make_institution(test_db, slug="tf336-rt-neg")
    user = _make_user(test_db, inst.id)
    exam = _setup_exam(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    resp = client.post(
        f"/api/v1/exams/{exam.id}/sync-moodle-question-ids",
        json={
            "moodle_quiz_id": 7,
            "moodle_question_ids": [9001, 0],
        },
    )
    assert resp.status_code == 422


def test_sync_404_for_other_institution(test_db: Session) -> None:
    inst_a = _make_institution(test_db, slug="tf336-rt-5a")
    inst_b = _make_institution(test_db, slug="tf336-rt-5b")
    exam_a = _setup_exam(test_db, inst_a.id)
    user_b = _make_user(test_db, inst_b.id)
    test_db.commit()

    client = _client(test_db, user_b)
    resp = client.post(
        f"/api/v1/exams/{exam_a.id}/sync-moodle-question-ids",
        json={"moodle_quiz_id": 7},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Round-Trip end-to-end with the API driver
# ---------------------------------------------------------------------------


def _quizzes(quiz_id: int) -> dict:
    return {"quizzes": [{"id": quiz_id, "course": 1, "name": "Geo Quiz", "cmid": 100}]}


def _attempts() -> dict:
    return {
        "attempts": [
            {
                "id": 501,
                "userid": 1001,
                "useremail": "anna@example.org",
                "fullname": "Anna B.",
                "attempt": 1,
                "timestart": 1747299600,
                "timefinish": 1747301400,
                "state": "finished",
            }
        ]
    }


def _attempt_review() -> dict:
    return {
        "questions": [
            {
                "slot": 1,
                "questionid": 9001,
                "responsesummary": "Bern",
                "mark": 4.0,
            },
            {
                "slot": 2,
                "questionid": 9002,
                "responsesummary": "wahr",
                "mark": 1.0,
            },
        ]
    }


def test_round_trip_sync_then_api_import_matches_via_slot(
    test_db: Session,
) -> None:
    inst = _make_institution(test_db, slug="tf336-rt-e2e")
    user = _make_user(test_db, inst.id)
    exam = _setup_exam(test_db, inst.id)
    test_db.add(
        MoodleConnection(
            institution_id=inst.id,
            base_url="https://moodle.example.org",
            token_encrypted=encrypt_secret("validtokenABCD"),
        )
    )
    test_db.commit()
    client = _client(test_db, user)
    endpoint = "https://moodle.example.org/webservice/rest/server.php"

    # Step 1: sync.
    with respx.mock() as mock:
        mock.post(endpoint).mock(return_value=httpx.Response(200, json=_quizzes(42)))
        sync_resp = client.post(
            f"/api/v1/exams/{exam.id}/sync-moodle-question-ids",
            json={
                "moodle_quiz_id": 42,
                "moodle_question_ids": [9001, 9002],
            },
        )
    assert sync_resp.status_code == 200

    # Step 2: refresh exam_questions in the test session, then run the
    # API-Driver against a mock Moodle. With external_refs now populated,
    # the driver should match via slot — no warning about missing refs.
    test_db.expire_all()
    fresh_exam = test_db.query(Exam).filter(Exam.id == exam.id).one()

    responses = [_quizzes(42), _attempts(), _attempt_review()]
    with respx.mock() as mock:
        mock.post(endpoint).mock(
            side_effect=lambda req: httpx.Response(200, json=responses.pop(0))
        )
        payload = MoodleApiDriver().parse(
            json.dumps({"quiz_id": 42}).encode("utf-8"),
            exam=fresh_exam,
            db=test_db,
        )

    assert not any("Moodle-IDs erfassen" in w for w in payload.warnings), (
        "Driver fell back to position despite slot mapping"
    )
    assert len(payload.attempts) == 1
    assert len(payload.attempts[0].answers) == 2
    expected_eq_ids = sorted(q.id for q in fresh_exam.questions)
    assert sorted(a.exam_question_id for a in payload.attempts[0].answers) == (
        expected_eq_ids
    )
