"""
Tests for GET /api/v1/rag/tasks/{task_id}/result (TF-608).

The WebSocket only delivers the generation result to a live connection. If
the page is changed or reloaded while the task finishes, there is no way
back to the result view without this pull endpoint.

Covers:
1. Result is delivered to the owner
2. Error cases (FAILURE/REVOKED) return the error message instead of a result
3. An expired Celery result does not downgrade a finished job back to PENDING
4. Broker outage does not lead to 5xx
5. Ownership: foreign jobs are rejected, superusers get an audit log entry
"""

import logging

import pytest
from unittest.mock import MagicMock, Mock, patch

from fastapi.testclient import TestClient

from main import app
from services.rag_errors import GENERIC_TASK_ERROR, NoContextError

# main.py loads core API modules via importlib.spec_from_file_location under
# special names (avoids the api ↔ premium.api conflict in full deployment;
# core_api_rag_exams for rag_exams.py, see main.py). A plain
# `import api.rag_exams` in THIS file would create a completely separate,
# independent module instance — with a different `logger` object than the
# one actually used by the app running via `from main import app`.
# logging.getLogger(name), by contrast, is a global registry lookup: for
# the same name it always returns the same singleton, regardless of which
# module instance called `logging.getLogger(__name__)`.
_rag_exams_logger = logging.getLogger("core_api_rag_exams")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_user():
    user = Mock()
    user.id = 7
    user.email = "tester@example.com"
    user.is_superuser = False
    user.institution_id = 1
    return user


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def auth_client(mock_user, mock_db):
    from utils.auth_utils import get_current_active_user
    from database import get_db

    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_job(task_id: str = "task-1", status: str = "SUCCESS", user_id: int = 7):
    job = Mock()
    job.id = 1
    job.task_id = task_id
    job.status = status
    job.user_id = user_id
    # QuestionGenerationJob has no institution_id column; without this `del`
    # the mock would invent one, and enforce_resource_access' tenant check
    # would test against a value that doesn't exist in production.
    del job.institution_id
    return job


def _wire_job(mock_db, job):
    mock_db.query.return_value.filter.return_value.first.return_value = job


EXAM_RESULT = {
    "exam_id": "exam-42",
    "topic": "Heapsort",
    "questions": [{"question_text": "Was ist ein Heap?"}],
    "generation_time": 12.5,
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetTaskResult:
    def test_returns_result_for_successful_task(self, auth_client, mock_db):
        """The owner gets the full generation result."""
        _wire_job(mock_db, _make_job(status="SUCCESS"))

        with patch("celery.result.AsyncResult") as mock_ar_cls:
            mock_result = Mock()
            mock_result.state = "SUCCESS"
            mock_result.result = EXAM_RESULT
            mock_ar_cls.return_value = mock_result

            response = auth_client.get("/api/v1/rag/tasks/task-1/result")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task-1"
        assert data["status"] == "SUCCESS"
        assert data["result"] == EXAM_RESULT
        assert data["error"] is None

    @pytest.mark.parametrize("state", ["FAILURE", "REVOKED"])
    def test_returns_error_for_failed_task(self, auth_client, mock_db, state):
        """Failed tasks return a safe, generic error message, no result —
        NOT the raw exception message (TF-358). The same mapper as the
        WebSocket recovery path (api/v1/websocket.py) prevents internal
        details/PII from leaking to the client via the Celery exception."""
        _wire_job(mock_db, _make_job(status=state))

        # Module logger method patched instead of caplog/patch("...logger") —
        # unreliable in the full suite (propagation/module-instance quirks,
        # see test_rag_competency_wiring.py for the same pattern).
        with (
            patch("celery.result.AsyncResult") as mock_ar_cls,
            patch.object(_rag_exams_logger, "error") as mock_error,
        ):
            mock_result = Mock()
            mock_result.state = state
            mock_result.result = RuntimeError(
                "Claude timeout: connection to internal-db-host:5432 refused"
            )
            mock_ar_cls.return_value = mock_result

            response = auth_client.get("/api/v1/rag/tasks/task-1/result")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == state
        assert data["result"] is None
        assert data["error"] == GENERIC_TASK_ERROR
        assert "Claude timeout" not in data["error"]
        assert "internal-db-host" not in data["error"]

        # The real error stays visible server-side (alerting), even though
        # the client only sees the generic message.
        mock_error.assert_called_once()
        logged_task_id, logged_kind = mock_error.call_args[0][1:3]
        assert logged_task_id == "task-1"
        assert logged_kind == "unmapped error class"

    @pytest.mark.parametrize("state", ["FAILURE", "REVOKED"])
    def test_returns_mapped_message_for_known_error_code(
        self, auth_client, mock_db, state
    ):
        """A known RAG error code (TF-358, `services.rag_errors`) returns
        the specific, localized message instead of the generic fallback —
        a parity test against the same mapping in the WebSocket recovery path."""
        _wire_job(mock_db, _make_job(status=state))

        with patch("celery.result.AsyncResult") as mock_ar_cls:
            mock_result = Mock()
            mock_result.state = state
            mock_result.result = NoContextError("no context available for topic")
            mock_ar_cls.return_value = mock_result

            response = auth_client.get("/api/v1/rag/tasks/task-1/result")

        assert response.status_code == 200
        data = response.json()
        assert data["error"] != GENERIC_TASK_ERROR
        assert "durchsuchbaren" in data["error"]

    def test_expired_celery_result_keeps_db_status(self, auth_client, mock_db):
        """An expired result backend must not downgrade a finished job back
        to PENDING — otherwise the UI would show a long-completed task as
        running again and wait forever for progress."""
        _wire_job(mock_db, _make_job(status="SUCCESS"))

        with patch("celery.result.AsyncResult") as mock_ar_cls:
            mock_result = Mock()
            mock_result.state = "PENDING"  # Result entry already discarded
            mock_result.result = None
            mock_ar_cls.return_value = mock_result

            response = auth_client.get("/api/v1/rag/tasks/task-1/result")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SUCCESS"
        assert data["result"] is None

    def test_broker_failure_does_not_break_endpoint(self, auth_client, mock_db):
        """Broker outage: 200 with DB status instead of 5xx, so the progress
        bar can keep showing the task."""
        _wire_job(mock_db, _make_job(status="SUCCESS"))

        with patch(
            "celery.result.AsyncResult", side_effect=Exception("Broker unreachable")
        ):
            response = auth_client.get("/api/v1/rag/tasks/task-1/result")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SUCCESS"
        assert data["result"] is None

    def test_unknown_task_returns_404(self, auth_client, mock_db):
        """Unknown task_id → 404."""
        _wire_job(mock_db, None)

        response = auth_client.get("/api/v1/rag/tasks/does-not-exist/result")

        assert response.status_code == 404

    def test_foreign_job_is_denied(self, auth_client, mock_db):
        """Foreign jobs are rejected (not a superuser)."""
        _wire_job(mock_db, _make_job(user_id=42))

        with patch("celery.result.AsyncResult"):
            response = auth_client.get("/api/v1/rag/tasks/task-1/result")

        assert response.status_code == 403

    def test_requires_authentication(self):
        unauthenticated_client = TestClient(app)
        response = unauthenticated_client.get("/api/v1/rag/tasks/task-1/result")
        assert response.status_code in (401, 403)


class TestGetTaskResultSuperuser:
    @pytest.fixture
    def super_user(self):
        u = Mock()
        u.id = 99
        u.email = "admin@s.ch"
        u.is_superuser = True
        u.institution_id = 1
        return u

    @pytest.fixture
    def super_client(self, super_user, mock_db):
        from utils.auth_utils import get_current_active_user
        from database import get_db

        app.dependency_overrides[get_current_active_user] = lambda: super_user
        app.dependency_overrides[get_db] = lambda: mock_db
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()

    def test_superuser_access_to_foreign_job_is_audited(self, super_client, mock_db):
        """A superuser may read foreign results — with a GDPR audit trail."""
        _wire_job(mock_db, _make_job(user_id=42))

        with (
            patch("celery.result.AsyncResult") as mock_ar_cls,
            patch("services.audit_service.AuditService") as mock_audit,
        ):
            mock_result = Mock()
            mock_result.state = "SUCCESS"
            mock_result.result = EXAM_RESULT
            mock_ar_cls.return_value = mock_result

            response = super_client.get("/api/v1/rag/tasks/task-1/result")

        assert response.status_code == 200
        assert response.json()["result"] == EXAM_RESULT
        mock_audit.log_superuser_bypass.assert_called_once()
        kwargs = mock_audit.log_superuser_bypass.call_args.kwargs
        assert kwargs["resource_type"] == "question_generation_job"
        assert kwargs["action"] == "read_result"
        assert kwargs["owner_user_id"] == 42
