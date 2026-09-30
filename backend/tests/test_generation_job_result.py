"""TF-964: a job that is SUCCESS in the DB is shown as successful everywhere.

A worker lost after the questions were committed leaves Celery on FAILURE
(or its entry expires) while the job row says SUCCESS. The row and the
questions linked to it are the lasting record, so ``/tasks/{id}/result``,
``/active-tasks`` and the WebSocket report «successful» and deliver the saved
questions, rebuilt by ``services.generation_job_result.build_job_result``.

Real rows in the test transaction; only Celery (``AsyncResult``) and the
WebSocket token check are mocked.
"""

import dataclasses
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from models.auth import Institution, User, UserStatus
from models.question_generation_job import QuestionGenerationJob

TASK_ID = "tf964-display"

# The keys generate_questions_task returns and the frontend's
# RAGExamResponse / RAGQuestion read (core/frontend/src/types/document.ts).
RESULT_KEYS = {
    "exam_id",
    "topic",
    "questions",
    "context_summary",
    "generation_time",
    "quality_metrics",
    "review_question_ids",
}
QUESTION_KEYS = {
    "question_text",
    "question_type",
    "options",
    "correct_answer",
    "explanation",
    "difficulty",
    "source_chunks",
    "source_documents",
    "confidence_score",
    "bloom_level",
    "estimated_time_minutes",
}


@dataclasses.dataclass
class _Question:
    question_text: str
    question_type: str = "single_choice"
    options: list = dataclasses.field(default_factory=lambda: ["a", "b", "c"])
    correct_answer: str = "a"
    explanation: str = "weil"
    difficulty: str = "medium"
    source_chunks: list = dataclasses.field(default_factory=lambda: ["c1"])
    source_documents: list = dataclasses.field(default_factory=list)
    confidence_score: float = 0.5


@pytest.fixture
def finished_job(test_db):
    """A SUCCESS job with two linked questions, saved the way
    ``_save_generation`` saves them."""
    from tasks.question_tasks import _persist_questions

    inst = Institution(
        name="TF-964 Display",
        slug="tf964-display",
        subscription_tier="free",
        max_users=10,
        max_documents=50,
        max_questions_per_month=100,
    )
    test_db.add(inst)
    test_db.flush()
    user = User(
        email="display@tf964.ch",
        first_name="D",
        last_name="S",
        password_hash="x",  # pragma: allowlist secret
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    test_db.add(user)
    test_db.flush()
    job = QuestionGenerationJob(
        task_id=TASK_ID,
        user_id=user.id,
        topic="Anzeige",
        question_count=5,
        status="SUCCESS",
        generated_question_count=2,
        context_limited=True,
    )
    test_db.add(job)
    test_db.flush()
    review_ids = _persist_questions(
        questions=[_Question("Erste?", confidence_score=0.4), _Question("Zweite?")],
        exam_id="rag_exam_display",
        topic="Anzeige",
        language="de",
        user_id=user.id,
        institution_id=inst.id,
        db=test_db,
        generation_job_id=job.id,
    )
    test_db.commit()
    return SimpleNamespace(user=user, job=job, review_ids=review_ids)


def _celery(state, result=None):
    async_result = MagicMock()
    async_result.state = state
    async_result.result = result
    async_result.info = result
    return async_result


class TestBuildJobResult:
    def test_rebuilds_the_task_result_shape(self, test_db, finished_job):
        from services.generation_job_result import build_job_result

        result = build_job_result(test_db, finished_job.job)

        assert set(result) == RESULT_KEYS
        assert result["exam_id"] == "rag_exam_display"
        assert result["review_question_ids"] == finished_job.review_ids
        assert [q["question_text"] for q in result["questions"]] == [
            "Erste?",
            "Zweite?",
        ]
        assert QUESTION_KEYS <= set(result["questions"][0])
        assert result["questions"][0]["options"] == ["a", "b", "c"]
        metrics = result["quality_metrics"]
        assert metrics["average_confidence"] == 0.45
        assert metrics["generated_question_count"] == 2
        assert metrics["requested_question_count"] == 5
        assert metrics["context_limited"] is True
        assert result["context_summary"]["source_documents"] == []

    def test_none_without_linked_questions(self, test_db, finished_job):
        """Jobs from before TF-964 have no link — callers keep their
        previous behaviour (no detail view) instead of an empty exam."""
        from services.generation_job_result import build_job_result

        legacy = QuestionGenerationJob(
            task_id="tf964-legacy", user_id=finished_job.user.id, status="SUCCESS"
        )
        test_db.add(legacy)
        test_db.commit()

        assert build_job_result(test_db, legacy) is None


@pytest.fixture
def api_client(test_db, finished_job):
    from database import get_db
    from main import app
    from utils.auth_utils import get_current_active_user

    app.dependency_overrides[get_current_active_user] = lambda: finished_job.user
    app.dependency_overrides[get_db] = lambda: test_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


class TestResultEndpoint:
    @pytest.mark.parametrize("celery_state", ["FAILURE", "REVOKED", "PENDING"])
    def test_db_success_wins_over_celery(self, api_client, finished_job, celery_state):
        """Acceptance «Anzeige»: DB SUCCESS + Celery FAILURE/REVOKED, or an
        expired Celery entry (PENDING) → «successful» with the saved
        questions, no error."""
        celery_info = (
            RuntimeError("WorkerLostError") if celery_state != "PENDING" else None
        )
        with patch(
            "celery.result.AsyncResult", return_value=_celery(celery_state, celery_info)
        ):
            response = api_client.get(f"/api/v1/rag/tasks/{TASK_ID}/result")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "SUCCESS"
        assert body["error"] is None
        assert set(body["result"]) == RESULT_KEYS
        assert body["result"]["review_question_ids"] == finished_job.review_ids
        assert body["generated_question_count"] == 2
        assert body["context_limited"] is True

    def test_live_celery_result_is_still_preferred(self, api_client):
        """While Celery still has the result, it is the fresher source."""
        live = {"exam_id": "live", "questions": []}
        with patch("celery.result.AsyncResult", return_value=_celery("SUCCESS", live)):
            body = api_client.get(f"/api/v1/rag/tasks/{TASK_ID}/result").json()

        assert body["result"] == live


class TestActiveTasks:
    def test_db_success_is_listed_as_success(self, api_client):
        """/active-tasks takes terminal rows from the DB without asking
        Celery, so Celery's FAILURE can't turn the entry red."""
        with patch(
            "celery.result.AsyncResult", return_value=_celery("FAILURE")
        ) as async_result:
            body = api_client.get("/api/v1/rag/active-tasks").json()

        [task] = [t for t in body["tasks"] if t["task_id"] == TASK_ID]
        assert task["status"] == "SUCCESS"
        assert task["progress"] == 100
        async_result.assert_not_called()


class TestWebSocket:
    def test_db_success_wins_over_celery_failure(self, test_db, finished_job):
        """The WebSocket reports SUCCESS with the saved questions instead of
        relaying Celery's FAILURE."""
        from sqlalchemy.orm import sessionmaker

        from api.v1 import websocket as ws_module

        app = FastAPI()
        app.include_router(ws_module.router)
        bound = sessionmaker(
            bind=test_db.get_bind(), join_transaction_mode="create_savepoint"
        )
        with (
            patch("api.v1.websocket.SessionLocal", bound),
            patch("api.v1.websocket.AuthService") as auth,
            patch(
                "api.v1.websocket.AsyncResult",
                return_value=_celery("FAILURE", RuntimeError("WorkerLostError")),
            ),
        ):
            auth.decode_token.return_value = {"sub": str(finished_job.user.id)}
            with TestClient(app).websocket_connect(f"/ws/tasks/{TASK_ID}") as ws:
                ws.send_json({"token": "t"})
                message = ws.receive_json()

        assert message["status"] == "SUCCESS"
        assert message["progress"] == 100
        assert message["error"] is None
        assert message["result"]["review_question_ids"] == finished_job.review_ids

    def test_db_lookup_error_reports_the_task_error(self, test_db, finished_job):
        """A failing DB lookup must not turn Celery's FAILURE into an
        internal WebSocket error: the user still gets the task's mapped
        error, as before TF-964."""
        from sqlalchemy.exc import OperationalError
        from sqlalchemy.orm import sessionmaker

        from api.v1 import websocket as ws_module
        from services.rag_errors import user_facing_task_error

        app = FastAPI()
        app.include_router(ws_module.router)
        bound = sessionmaker(
            bind=test_db.get_bind(), join_transaction_mode="create_savepoint"
        )
        task_error = RuntimeError("WorkerLostError")
        with (
            patch("api.v1.websocket.SessionLocal", bound),
            patch("api.v1.websocket.AuthService") as auth,
            patch(
                "api.v1.websocket.AsyncResult",
                return_value=_celery("FAILURE", task_error),
            ),
            patch(
                "api.v1.websocket._stored_success_result",
                side_effect=OperationalError("stmt", {}, Exception("db down")),
            ),
        ):
            auth.decode_token.return_value = {"sub": str(finished_job.user.id)}
            with TestClient(app).websocket_connect(f"/ws/tasks/{TASK_ID}") as ws:
                ws.send_json({"token": "t"})
                message = ws.receive_json()

        assert message["status"] == "FAILURE"
        assert message["error_code"] == user_facing_task_error(task_error).code

    def test_celery_failure_without_db_success_stays_failure(self, test_db):
        """No job row in SUCCESS (here: none at all) → the old FAILURE path."""
        from sqlalchemy.orm import sessionmaker

        from api.v1.websocket import _stored_success_result

        bound = sessionmaker(
            bind=test_db.get_bind(), join_transaction_mode="create_savepoint"
        )
        with patch("api.v1.websocket.SessionLocal", bound):
            assert _stored_success_result("no-such-task") == (False, None)
