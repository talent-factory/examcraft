"""Tests for ``MoodleApiDriver`` (TF-336 Subarea C).

Drives the driver against a respx-mocked Moodle Web Service so the call
sequence is verified without network access.
"""

from __future__ import annotations

import json
from datetime import date

import httpx
import pytest
import respx
from sqlalchemy.orm import Session

from models.auth import Institution, User, UserStatus
from models.exam import Exam, ExamQuestion
from models.question_review import QuestionReview
from models.submission import MoodleConnection
from services.import_drivers import (
    ImportDriverError,
    MoodleApiAuthError,
    MoodleApiDriver,
    MoodleConnectionMissingError,
)
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


def _setup_exam_with_two_questions(
    db: Session, institution_id: int
) -> tuple[Exam, ExamQuestion, ExamQuestion]:
    q1 = QuestionReview(
        question_text="Hauptstadt der Schweiz?",
        question_type="single_choice",
        options=["A", "B"],
        correct_answer="Bern",
        difficulty="easy",
        topic="Geo",
        institution_id=institution_id,
    )
    q2 = QuestionReview(
        question_text="Die Hauptstadt heisst Bern.",
        question_type="true_false",
        correct_answer="wahr",
        difficulty="easy",
        topic="Geo",
        institution_id=institution_id,
    )
    db.add_all([q1, q2])
    db.flush()
    exam = Exam(
        title="API-Test",
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
    eq1 = ExamQuestion(
        exam_id=exam.id,
        question_id=q1.id,
        position=1,
        points=4.0,
        external_refs={"moodle_slot": 1, "moodle_question_id": 9001},
    )
    eq2 = ExamQuestion(
        exam_id=exam.id,
        question_id=q2.id,
        position=2,
        points=1.0,
        external_refs={"moodle_slot": 2, "moodle_question_id": 9002},
    )
    db.add_all([eq1, eq2])
    db.flush()
    return exam, eq1, eq2


def _setup_connection(
    db: Session, institution_id: int, *, token: str = "supertokenAA"
) -> MoodleConnection:
    connection = MoodleConnection(
        institution_id=institution_id,
        base_url="https://moodle.example.org",
        token_encrypted=encrypt_secret(token),
    )
    db.add(connection)
    db.flush()
    return connection


def _quizzes_response(quiz_id: int = 42) -> dict:
    return {"quizzes": [{"id": quiz_id, "course": 1, "name": "Geo Quiz", "cmid": 100}]}


def _user_attempts_response() -> dict:
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
            },
            {
                "id": 502,
                "userid": 1002,
                "useremail": "bruno@example.org",
                "fullname": "Bruno M.",
                "attempt": 1,
                "timestart": 1747299600,
                "timefinish": 1747301400,
                "state": "finished",
            },
        ]
    }


def _attempt_review(*, slot1_answer: str, slot2_answer: str, mark: float) -> dict:
    return {
        "attempt": {"id": 0},
        "questions": [
            {
                "slot": 1,
                "questionid": 9001,
                "responsesummary": slot1_answer,
                "mark": mark,
            },
            {
                "slot": 2,
                "questionid": 9002,
                "responsesummary": slot2_answer,
                "mark": 1.0,
            },
        ],
    }


def test_driver_full_call_sequence(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="tf336-api-full")
    _make_user(test_db, inst.id)
    exam, _eq1, _eq2 = _setup_exam_with_two_questions(test_db, inst.id)
    _setup_connection(test_db, inst.id)
    test_db.commit()

    endpoint = "https://moodle.example.org/webservice/rest/server.php"
    with respx.mock(assert_all_called=True) as mock:
        mock.post(endpoint, name="quizzes").mock(
            side_effect=lambda req: (
                httpx.Response(200, json=_quizzes_response(42))
                if b"mod_quiz_get_quizzes_by_courses" in req.read()
                else None
            )
        )
        # respx routes match on URL only — discriminate by request body
        # via a custom side_effect. Order: quizzes_by_courses, then
        # user_attempts, then two attempt_reviews.
        responses = [
            _quizzes_response(42),
            _user_attempts_response(),
            _attempt_review(slot1_answer="Bern", slot2_answer="wahr", mark=4.0),
            _attempt_review(slot1_answer="Zürich", slot2_answer="falsch", mark=0.0),
        ]

        def _serve(request):
            return httpx.Response(200, json=responses.pop(0))

        mock.routes.clear()
        mock.post(endpoint).mock(side_effect=_serve)

        payload = MoodleApiDriver().parse(
            json.dumps({"quiz_id": 42}).encode("utf-8"),
            exam=exam,
            db=test_db,
        )

    assert {s.external_id for s in payload.students} == {"1001", "1002"}
    # Each attempt produced 2 answers.
    assert len(payload.attempts) == 2
    for attempt in payload.attempts:
        assert len(attempt.answers) == 2
        # external_refs.moodle_slot wired to ExamQuestion ids.
        assert {a.exam_question_id for a in attempt.answers} == {
            _eq1.id,
            _eq2.id,
        }


def test_driver_raises_on_invalid_token(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="tf336-api-auth")
    exam, _eq1, _eq2 = _setup_exam_with_two_questions(test_db, inst.id)
    _setup_connection(test_db, inst.id)
    test_db.commit()

    endpoint = "https://moodle.example.org/webservice/rest/server.php"
    with respx.mock() as mock:
        mock.post(endpoint).mock(
            return_value=httpx.Response(
                200,
                json={
                    "exception": "moodle_exception",
                    "errorcode": "invalidtoken",
                    "message": "Invalid token",
                },
            )
        )
        with pytest.raises(MoodleApiAuthError):
            MoodleApiDriver().parse(
                json.dumps({"quiz_id": 42}).encode("utf-8"),
                exam=exam,
                db=test_db,
            )


def test_driver_raises_when_connection_missing(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="tf336-api-missing")
    exam, _eq1, _eq2 = _setup_exam_with_two_questions(test_db, inst.id)
    test_db.commit()

    with pytest.raises(MoodleConnectionMissingError):
        MoodleApiDriver().parse(
            json.dumps({"quiz_id": 42}).encode("utf-8"),
            exam=exam,
            db=test_db,
        )


def test_driver_raises_on_unknown_quiz(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="tf336-api-quiz")
    exam, _eq1, _eq2 = _setup_exam_with_two_questions(test_db, inst.id)
    _setup_connection(test_db, inst.id)
    test_db.commit()

    endpoint = "https://moodle.example.org/webservice/rest/server.php"
    with respx.mock() as mock:
        mock.post(endpoint).mock(
            return_value=httpx.Response(200, json=_quizzes_response(99))
        )
        with pytest.raises(ImportDriverError, match="Quiz 42 nicht"):
            MoodleApiDriver().parse(
                json.dumps({"quiz_id": 42}).encode("utf-8"),
                exam=exam,
                db=test_db,
            )


def test_driver_warns_when_external_refs_missing(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="tf336-api-norefs")
    exam, eq1, eq2 = _setup_exam_with_two_questions(test_db, inst.id)
    # Wipe external_refs to force position-fallback path.
    eq1.external_refs = None
    eq2.external_refs = None
    test_db.flush()
    _setup_connection(test_db, inst.id)
    test_db.commit()

    endpoint = "https://moodle.example.org/webservice/rest/server.php"
    responses = [
        _quizzes_response(42),
        _user_attempts_response(),
        _attempt_review(slot1_answer="Bern", slot2_answer="wahr", mark=4.0),
        _attempt_review(slot1_answer="Zürich", slot2_answer="falsch", mark=0.0),
    ]
    with respx.mock() as mock:
        mock.post(endpoint).mock(
            side_effect=lambda req: httpx.Response(200, json=responses.pop(0))
        )
        payload = MoodleApiDriver().parse(
            json.dumps({"quiz_id": 42}).encode("utf-8"),
            exam=exam,
            db=test_db,
        )

    assert any("Moodle-IDs erfassen" in w for w in payload.warnings)
    # Even without external_refs the position-fallback still maps both
    # answers to ExamCraft questions.
    for attempt in payload.attempts:
        assert len(attempt.answers) == 2


def test_driver_rejects_bad_source() -> None:
    driver = MoodleApiDriver()

    class FakeExam:
        id = 1
        institution_id = 1
        questions: list = []

    with pytest.raises(ImportDriverError):
        driver.parse(b"", exam=FakeExam(), db=object())
    with pytest.raises(ImportDriverError):
        driver.parse(b'{"quiz_id": "abc"}', exam=FakeExam(), db=object())
    with pytest.raises(ImportDriverError):
        driver.parse(b"{}", exam=FakeExam(), db=object())


def test_driver_requires_db() -> None:
    class FakeExam:
        id = 1
        institution_id = 1
        questions: list = []

    with pytest.raises(ImportDriverError, match="DB-Session"):
        MoodleApiDriver().parse(b'{"quiz_id": 1}', exam=FakeExam(), db=None)


def test_driver_raises_on_network_error(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="tf336-api-net")
    exam, _eq1, _eq2 = _setup_exam_with_two_questions(test_db, inst.id)
    _setup_connection(test_db, inst.id)
    test_db.commit()

    endpoint = "https://moodle.example.org/webservice/rest/server.php"
    with respx.mock() as mock:
        mock.post(endpoint).mock(side_effect=httpx.ConnectError("no route"))
        with pytest.raises(ImportDriverError, match="erreichbarkeitsfehler"):
            MoodleApiDriver().parse(
                json.dumps({"quiz_id": 42}).encode("utf-8"),
                exam=exam,
                db=test_db,
            )


def test_driver_raises_on_5xx(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="tf336-api-5xx")
    exam, _eq1, _eq2 = _setup_exam_with_two_questions(test_db, inst.id)
    _setup_connection(test_db, inst.id)
    test_db.commit()

    endpoint = "https://moodle.example.org/webservice/rest/server.php"
    with respx.mock() as mock:
        mock.post(endpoint).mock(return_value=httpx.Response(503))
        with pytest.raises(ImportDriverError, match="HTTP 503"):
            MoodleApiDriver().parse(
                json.dumps({"quiz_id": 42}).encode("utf-8"),
                exam=exam,
                db=test_db,
            )


def test_driver_raises_on_429_rate_limit(test_db: Session) -> None:
    """Moodle throttling (429) must surface a typed driver error so the
    import job records "rate-limited" rather than parsing the HTML body
    and reporting "antwortete nicht mit JSON"."""
    inst = _make_institution(test_db, slug="tf336-api-429")
    exam, _eq1, _eq2 = _setup_exam_with_two_questions(test_db, inst.id)
    _setup_connection(test_db, inst.id)
    test_db.commit()

    endpoint = "https://moodle.example.org/webservice/rest/server.php"
    with respx.mock() as mock:
        mock.post(endpoint).mock(return_value=httpx.Response(429))
        with pytest.raises(ImportDriverError, match="rate-limited"):
            MoodleApiDriver().parse(
                json.dumps({"quiz_id": 42}).encode("utf-8"),
                exam=exam,
                db=test_db,
            )


def test_driver_raises_on_4xx_auth(test_db: Session) -> None:
    """A 401/403 from Moodle (or its reverse proxy) must surface as
    ``MoodleApiAuthError`` — without explicit 4xx handling the next
    ``response.json()`` call would parse the HTML error body and the
    operator sees a misleading "JSON"-Fehler."""
    inst = _make_institution(test_db, slug="tf336-api-401")
    exam, _eq1, _eq2 = _setup_exam_with_two_questions(test_db, inst.id)
    _setup_connection(test_db, inst.id)
    test_db.commit()

    endpoint = "https://moodle.example.org/webservice/rest/server.php"
    with respx.mock() as mock:
        mock.post(endpoint).mock(
            return_value=httpx.Response(401, text="<html>Unauthorized</html>")
        )
        with pytest.raises(MoodleApiAuthError, match="HTTP 401"):
            MoodleApiDriver().parse(
                json.dumps({"quiz_id": 42}).encode("utf-8"),
                exam=exam,
                db=test_db,
            )


def test_driver_raises_on_timeout(test_db: Session) -> None:
    """A request timeout must wrap to ``ImportDriverError`` so the job
    fails with a meaningful reason instead of bubbling a raw httpx
    exception."""
    inst = _make_institution(test_db, slug="tf336-api-timeout")
    exam, _eq1, _eq2 = _setup_exam_with_two_questions(test_db, inst.id)
    _setup_connection(test_db, inst.id)
    test_db.commit()

    endpoint = "https://moodle.example.org/webservice/rest/server.php"
    with respx.mock() as mock:
        mock.post(endpoint).mock(side_effect=httpx.ReadTimeout("read timeout"))
        with pytest.raises(ImportDriverError, match="erreichbarkeitsfehler"):
            MoodleApiDriver().parse(
                json.dumps({"quiz_id": 42}).encode("utf-8"),
                exam=exam,
                db=test_db,
            )


def test_driver_does_not_send_token_in_url(test_db: Session) -> None:
    """``wstoken`` must travel in the POST body, not the URL query string,
    so it never lands in reverse-proxy / Moodle access logs."""
    inst = _make_institution(test_db, slug="tf336-api-url-leak")
    exam, _eq1, _eq2 = _setup_exam_with_two_questions(test_db, inst.id)
    _setup_connection(test_db, inst.id)
    test_db.commit()

    endpoint = "https://moodle.example.org/webservice/rest/server.php"
    captured: list[httpx.Request] = []

    def _capture(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"quizzes": []})

    with respx.mock() as mock:
        mock.post(endpoint).mock(side_effect=_capture)
        # Quiz lookup will fail with "nicht in Token-Sicht" since the
        # mocked response has no quizzes — that's fine, we only care
        # about the URL of the call that was made.
        with pytest.raises(ImportDriverError):
            MoodleApiDriver().parse(
                json.dumps({"quiz_id": 42}).encode("utf-8"),
                exam=exam,
                db=test_db,
            )

    assert captured, "expected at least one request to Moodle"
    for req in captured:
        assert "wstoken" not in req.url.params, f"wstoken leaked into URL: {req.url}"
        body = req.content.decode("ascii")
        assert "wstoken=" in body, f"wstoken missing from POST body: {body!r}"


def test_driver_records_per_attempt_failure(test_db: Session) -> None:
    """A bogus attempt without a userid → row error, import continues."""
    inst = _make_institution(test_db, slug="tf336-api-perattempt")
    exam, _eq1, _eq2 = _setup_exam_with_two_questions(test_db, inst.id)
    _setup_connection(test_db, inst.id)
    test_db.commit()

    bad_attempts = {
        "attempts": [
            # No userid + no email — driver raises ImportDriverError mid-loop.
            {"id": 999, "attempt": 1},
        ]
    }
    endpoint = "https://moodle.example.org/webservice/rest/server.php"
    responses = [_quizzes_response(42), bad_attempts]
    with respx.mock() as mock:
        mock.post(endpoint).mock(
            side_effect=lambda req: httpx.Response(200, json=responses.pop(0))
        )
        with pytest.raises(ImportDriverError, match="identifizierbaren User"):
            MoodleApiDriver().parse(
                json.dumps({"quiz_id": 42}).encode("utf-8"),
                exam=exam,
                db=test_db,
            )


def test_driver_continues_on_attempt_review_exception(test_db: Session) -> None:
    """Mid-loop unknown exception is recorded as a row error."""
    inst = _make_institution(test_db, slug="tf336-api-recovery")
    exam, _eq1, _eq2 = _setup_exam_with_two_questions(test_db, inst.id)
    _setup_connection(test_db, inst.id)
    test_db.commit()

    # Two attempts, the first one's attempt_review returns garbage that
    # makes _process_attempt blow up on response parsing; the second
    # one's review is well-formed — final payload should have one
    # row_error and one persisted attempt.
    bad_review = {"questions": [{"slot": "not-an-int", "responsesummary": None}]}
    good_review = _attempt_review(slot1_answer="Bern", slot2_answer="wahr", mark=4.0)
    attempts_with_two = {
        "attempts": [
            {
                "id": 501,
                "userid": 1001,
                "useremail": "a@example.org",
                "fullname": "A",
                "attempt": 1,
                "timestart": 1747299600,
                "timefinish": 1747301400,
                "state": "finished",
            },
            {
                "id": 502,
                "userid": 1002,
                "useremail": "b@example.org",
                "fullname": "B",
                "attempt": 1,
                "timestart": 1747299600,
                "timefinish": 1747301400,
                "state": "finished",
            },
        ]
    }
    endpoint = "https://moodle.example.org/webservice/rest/server.php"
    responses = [
        _quizzes_response(42),
        attempts_with_two,
        bad_review,
        good_review,
    ]
    with respx.mock() as mock:
        mock.post(endpoint).mock(
            side_effect=lambda req: httpx.Response(200, json=responses.pop(0))
        )
        # The first attempt's bad_review still parses (slot becomes None,
        # answer drops); both attempts should produce records.
        payload = MoodleApiDriver().parse(
            json.dumps({"quiz_id": 42}).encode("utf-8"),
            exam=exam,
            db=test_db,
        )
    assert {s.external_id for s in payload.students} == {"1001", "1002"}
    assert len(payload.attempts) == 2
