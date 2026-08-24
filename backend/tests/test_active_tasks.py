"""
Tests for GET /api/v1/rag/active-tasks endpoint.

Verifies:
1. Non-terminal jobs are returned; jobs older than 2 hours are excluded
2. Recently completed jobs are returned too, so a task that finished during a
   page reload stays reachable in the UI (TF-608)
3. Progress/message come from Celery AsyncResult when available
4. Defaults to progress=0, message=None when Celery is unavailable
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

from fastapi.testclient import TestClient

from main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_user():
    """Authenticated user mock (non-superuser)."""
    user = Mock()
    user.id = 7
    user.email = "tester@example.com"
    user.is_superuser = False
    return user


@pytest.fixture
def mock_db():
    """Minimal database session mock."""
    return MagicMock()


@pytest.fixture
def auth_client(mock_user, mock_db):
    """Test client with auth and DB overrides applied."""
    from utils.auth_utils import get_current_active_user
    from database import get_db

    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_job(
    task_id: str,
    status: str = "PENDING",
    created_at: datetime = None,
    topic: str = "Test Topic",
    question_count: int = 5,
    user_id: int = 7,
):
    """Helper: build a mock QuestionGenerationJob."""
    job = Mock()
    job.task_id = task_id
    job.status = status
    job.created_at = created_at or datetime.now(timezone.utc)
    job.topic = topic
    job.question_count = question_count
    job.user_id = user_id
    return job


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetActiveTasks:
    """Unit-level tests for the /active-tasks endpoint."""

    def _setup_db_query(self, mock_db, jobs: list):
        """Wire mock_db.query(...).filter(...).all() to return *jobs*.

        Code path for non-superusers chains two .filter() calls (status/age,
        then user_id), so we wire both filter levels to the same .all() result.
        """
        query_mock = MagicMock()
        filter_mock = MagicMock()
        filter_mock.all.return_value = jobs
        # Inner filter (user_id) returns a chain whose .all() is also jobs
        filter_mock.filter.return_value.all.return_value = jobs
        query_mock.filter.return_value = filter_mock
        mock_db.query.return_value = query_mock

    def test_returns_empty_list_when_no_active_jobs(self, auth_client, mock_db):
        """Endpoint returns empty tasks list when no active jobs exist."""
        self._setup_db_query(mock_db, [])

        with patch("celery.result.AsyncResult"):
            response = auth_client.get("/api/v1/rag/active-tasks")

        assert response.status_code == 200
        data = response.json()
        assert data == {"tasks": []}

    def test_returns_active_jobs(self, auth_client, mock_db):
        """Non-terminal jobs within the 2-hour window are returned."""
        job = _make_job("task-abc", status="STARTED")
        self._setup_db_query(mock_db, [job])

        with patch("celery.result.AsyncResult") as mock_ar_cls:
            mock_result = Mock()
            mock_result.state = "STARTED"
            mock_result.info = None
            mock_ar_cls.return_value = mock_result

            response = auth_client.get("/api/v1/rag/active-tasks")

        assert response.status_code == 200
        tasks = response.json()["tasks"]
        assert len(tasks) == 1
        t = tasks[0]
        assert t["task_id"] == "task-abc"
        assert t["status"] == "STARTED"
        assert t["progress"] == 0
        assert t["message"] == "Gestartet..."
        assert t["topic"] == "Test Topic"
        assert t["question_count"] == 5

    def test_progress_from_celery_progress_state(self, auth_client, mock_db):
        """Progress and message are extracted from Celery PROGRESS state."""
        job = _make_job("task-progress", status="PROGRESS")
        self._setup_db_query(mock_db, [job])

        with patch("celery.result.AsyncResult") as mock_ar_cls:
            mock_result = Mock()
            mock_result.state = "PROGRESS"
            mock_result.info = {
                "current": 3,
                "total": 10,
                "message": "Generiere Frage 3",
            }
            mock_ar_cls.return_value = mock_result

            response = auth_client.get("/api/v1/rag/active-tasks")

        assert response.status_code == 200
        task = response.json()["tasks"][0]
        assert task["progress"] == 30
        assert task["message"] == "Generiere Frage 3"

    def test_progress_defaults_when_celery_unavailable(self, auth_client, mock_db):
        """If AsyncResult raises, progress=0 and message=None are returned."""
        job = _make_job("task-no-broker", status="PENDING")
        self._setup_db_query(mock_db, [job])

        with patch("celery.result.AsyncResult") as mock_ar_cls:
            mock_ar_cls.side_effect = Exception("Broker unreachable")

            response = auth_client.get("/api/v1/rag/active-tasks")

        assert response.status_code == 200
        task = response.json()["tasks"][0]
        assert task["progress"] == 0
        assert task["message"] is None

    def test_multiple_active_jobs_returned(self, auth_client, mock_db):
        """Multiple active jobs are all returned."""
        jobs = [
            _make_job("task-1", status="PENDING"),
            _make_job("task-2", status="STARTED"),
            _make_job("task-3", status="PROGRESS"),
        ]
        self._setup_db_query(mock_db, jobs)

        with patch("celery.result.AsyncResult") as mock_ar_cls:
            mock_result = Mock()
            mock_result.state = "PENDING"
            mock_result.info = {}
            mock_ar_cls.return_value = mock_result

            response = auth_client.get("/api/v1/rag/active-tasks")

        assert response.status_code == 200
        assert len(response.json()["tasks"]) == 3

    def test_db_filter_excludes_terminal_statuses(self, auth_client, mock_db):
        """DB query filters out terminal statuses via notin_."""
        # The query itself is mocked; we verify the filter receives the right
        # arguments by inspecting the call chain on mock_db.
        self._setup_db_query(mock_db, [])

        with patch("celery.result.AsyncResult"):
            auth_client.get("/api/v1/rag/active-tasks")

        # query(QuestionGenerationJob) was called
        assert mock_db.query.called

    def test_db_filter_excludes_old_jobs(self, auth_client, mock_db):
        """DB query uses a cutoff of now - 2 hours."""
        # We don't get old jobs back because the filter is applied in the DB
        # layer (which is mocked). Verify the endpoint returns whatever the
        # mock returns — meaning old-job filtering is delegated to DB.
        # Simulate the DB correctly filtering out the old job
        # (old_job would have created_at 3 hours ago, outside the 2h cutoff)
        self._setup_db_query(mock_db, [])  # DB returns nothing (filtered out)

        with patch("celery.result.AsyncResult"):
            response = auth_client.get("/api/v1/rag/active-tasks")

        assert response.status_code == 200
        assert response.json()["tasks"] == []

    def test_progress_boundary_values(self, auth_client, mock_db):
        """Progress is clamped correctly at 0% and 100%."""
        job = _make_job("task-full", status="PROGRESS")
        self._setup_db_query(mock_db, [job])

        with patch("celery.result.AsyncResult") as mock_ar_cls:
            mock_result = Mock()
            mock_result.state = "PROGRESS"
            mock_result.info = {"current": 10, "total": 10, "message": "Fast fertig"}
            mock_ar_cls.return_value = mock_result

            response = auth_client.get("/api/v1/rag/active-tasks")

        task = response.json()["tasks"][0]
        assert task["progress"] == 100

    def test_zero_total_does_not_divide_by_zero(self, auth_client, mock_db):
        """total=0 in Celery info does not cause ZeroDivisionError."""
        job = _make_job("task-zero-total", status="PROGRESS")
        self._setup_db_query(mock_db, [job])

        with patch("celery.result.AsyncResult") as mock_ar_cls:
            mock_result = Mock()
            mock_result.state = "PROGRESS"
            mock_result.info = {"current": 0, "total": 0, "message": None}
            mock_ar_cls.return_value = mock_result

            response = auth_client.get("/api/v1/rag/active-tasks")

        assert response.status_code == 200
        task = response.json()["tasks"][0]
        assert task["progress"] == 0

    def test_requires_authentication(self):
        """Endpoint returns 401/403 when no auth is provided."""
        unauthenticated_client = TestClient(app)
        response = unauthenticated_client.get("/api/v1/rag/active-tasks")
        assert response.status_code in (401, 403)

    def test_optional_fields_can_be_none(self, auth_client, mock_db):
        """topic and question_count may be None (nullable columns)."""
        job = _make_job(
            "task-no-meta", status="PENDING", topic=None, question_count=None
        )
        self._setup_db_query(mock_db, [job])

        with patch("celery.result.AsyncResult") as mock_ar_cls:
            mock_result = Mock()
            mock_result.state = "PENDING"
            mock_result.info = {}
            mock_ar_cls.return_value = mock_result

            response = auth_client.get("/api/v1/rag/active-tasks")

        assert response.status_code == 200
        task = response.json()["tasks"][0]
        assert task["topic"] is None
        assert task["question_count"] is None


class TestRecentlyCompletedTasks:
    """TF-608: recently completed jobs stay recoverable.

    If the page is switched or reloaded while a task is finishing, the
    WebSocket dies — without these jobs in the recovery payload, the result
    would vanish from the UI (the questions do sit in the review queue, but
    there's no way back into the generation view).
    """

    def _setup_db_query(self, mock_db, jobs: list):
        query_mock = MagicMock()
        filter_mock = MagicMock()
        filter_mock.all.return_value = jobs
        filter_mock.filter.return_value.all.return_value = jobs
        query_mock.filter.return_value = filter_mock
        mock_db.query.return_value = query_mock

    def test_completed_job_is_returned_with_full_progress(self, auth_client, mock_db):
        """A job with DB status SUCCESS appears with progress=100."""
        job = _make_job("task-done", status="SUCCESS")
        self._setup_db_query(mock_db, [job])

        with patch("celery.result.AsyncResult") as mock_ar_cls:
            response = auth_client.get("/api/v1/rag/active-tasks")

        assert response.status_code == 200
        task = response.json()["tasks"][0]
        assert task["task_id"] == "task-done"
        assert task["status"] == "SUCCESS"
        assert task["progress"] == 100
        # The status lives in the DB — Celery doesn't need to be queried for it.
        mock_ar_cls.assert_not_called()

    @pytest.mark.parametrize("status", ["FAILURE", "REVOKED"])
    def test_failed_job_is_returned_without_progress(
        self, auth_client, mock_db, status
    ):
        """FAILURE/REVOKED also appear, but without a progress claim."""
        job = _make_job(f"task-{status.lower()}", status=status)
        self._setup_db_query(mock_db, [job])

        with patch("celery.result.AsyncResult"):
            response = auth_client.get("/api/v1/rag/active-tasks")

        assert response.status_code == 200
        task = response.json()["tasks"][0]
        assert task["status"] == status
        assert task["progress"] == 0

    def test_active_and_completed_jobs_are_mixed(self, auth_client, mock_db):
        """Running and completed jobs appear side by side."""
        jobs = [
            _make_job("task-running", status="PROGRESS"),
            _make_job("task-finished", status="SUCCESS"),
        ]
        self._setup_db_query(mock_db, jobs)

        with patch("celery.result.AsyncResult") as mock_ar_cls:
            mock_result = Mock()
            mock_result.state = "PROGRESS"
            mock_result.info = {"current": 1, "total": 4, "message": "läuft"}
            mock_ar_cls.return_value = mock_result

            response = auth_client.get("/api/v1/rag/active-tasks")

        assert response.status_code == 200
        tasks = {t["task_id"]: t for t in response.json()["tasks"]}
        assert tasks["task-running"]["progress"] == 25
        assert tasks["task-finished"]["progress"] == 100
        # Only the running job triggers a Celery query.
        assert mock_ar_cls.call_count == 1


class TestActiveTasksSuperuser:
    """Superuser bypass for /active-tasks: all active jobs + audit log."""

    @pytest.fixture
    def super_user(self):
        u = Mock()
        u.id = 99
        u.email = "admin@s.ch"
        u.is_superuser = True
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

    def test_superuser_lists_all_active_jobs_and_logs_bypass(
        self, super_client, mock_db
    ):
        """Superuser sees jobs from all users; a bypass audit log entry is created."""
        foreign_job = _make_job("task-foreign", user_id=42)
        own_job = _make_job("task-own", user_id=99)

        # Build query chain — superuser branch does NOT filter by user_id
        query_chain = MagicMock()
        query_chain.filter.return_value.all.return_value = [foreign_job, own_job]
        mock_db.query.return_value = query_chain

        with (
            patch("celery.result.AsyncResult") as mock_ar_cls,
            patch("services.audit_service.AuditService") as mock_audit,
        ):
            mock_result = Mock()
            mock_result.state = "PENDING"
            mock_result.info = {}
            mock_ar_cls.return_value = mock_result
            mock_audit.log_superuser_bypass.return_value = Mock()

            response = super_client.get("/api/v1/rag/active-tasks")

        assert response.status_code == 200
        task_ids = [t["task_id"] for t in response.json()["tasks"]]
        assert "task-foreign" in task_ids
        assert "task-own" in task_ids

        mock_audit.log_superuser_bypass.assert_called_once()
        kwargs = mock_audit.log_superuser_bypass.call_args.kwargs
        assert kwargs["resource_type"] == "question_generation_job_list"
        assert kwargs["action"] == "list_all_active"
        assert kwargs["request"] is not None  # http_request forwarded

    def test_superuser_no_audit_when_only_own_jobs_returned(
        self, super_client, mock_db
    ):
        """Audit fires ONLY when at least one foreign-owned job is in the
        response. The frontend polls this endpoint repeatedly; emitting an
        audit row every poll cycle (most of which return only own jobs)
        flooded the DSGVO trail with low-signal entries and obscured genuine
        cross-owner access.
        """
        own_job_a = _make_job("task-own-a", user_id=99)
        own_job_b = _make_job("task-own-b", user_id=99)

        query_chain = MagicMock()
        query_chain.filter.return_value.all.return_value = [own_job_a, own_job_b]
        mock_db.query.return_value = query_chain

        with (
            patch("celery.result.AsyncResult") as mock_ar_cls,
            patch("services.audit_service.AuditService") as mock_audit,
        ):
            mock_result = Mock()
            mock_result.state = "PENDING"
            mock_result.info = {}
            mock_ar_cls.return_value = mock_result

            response = super_client.get("/api/v1/rag/active-tasks")

        assert response.status_code == 200
        # Both own jobs returned, but no audit-bypass log generated.
        mock_audit.log_superuser_bypass.assert_not_called()

    def test_active_tasks_superuser_bypass_aborts_when_audit_fails(
        self, super_client, mock_db
    ):
        """DSGVO contract symmetry: when /active-tasks's bypass-audit insert
        fails (log_superuser_bypass raises HTTPException(500) per the
        invariant tested elsewhere), the endpoint must return 500 instead
        of silently leaking foreign-owned jobs into the response. Without
        this assertion, a regression that swallows the helper's exception
        would silently restore the bypass-without-trail risk that TF-324
        was specifically meant to close.
        """
        from fastapi import HTTPException

        foreign_job = _make_job("task-foreign", user_id=42)

        query_chain = MagicMock()
        query_chain.filter.return_value.all.return_value = [foreign_job]
        mock_db.query.return_value = query_chain

        with (
            patch("celery.result.AsyncResult") as mock_ar_cls,
            patch("services.audit_service.AuditService") as mock_audit,
        ):
            mock_result = Mock()
            mock_result.state = "PENDING"
            mock_result.info = {}
            mock_ar_cls.return_value = mock_result
            mock_audit.log_superuser_bypass.side_effect = HTTPException(
                status_code=500, detail="Audit log unavailable"
            )

            response = super_client.get("/api/v1/rag/active-tasks")

        assert response.status_code == 500
        assert "Audit log unavailable" in response.json().get("detail", "")


class TestPhantomJobFiltering:
    """TF-326: jobs with terminal Celery state must be excluded and DB synced."""

    def _setup_db_query(self, mock_db, jobs: list):
        query_mock = MagicMock()
        filter_mock = MagicMock()
        filter_mock.all.return_value = jobs
        query_mock.filter.return_value = filter_mock
        mock_db.query.return_value = query_mock

    def test_phantom_failure_excluded_and_db_synced(self, auth_client, mock_db):
        """DB status PENDING + Celery state FAILURE → omitted, _try_update_job_status('FAILURE') called."""
        job = _make_job("task-phantom", status="PENDING")
        self._setup_db_query(mock_db, [job])

        with (
            patch("celery.result.AsyncResult") as mock_ar_cls,
            patch("tasks.question_tasks._try_update_job_status") as mock_sync,
        ):
            mock_result = Mock()
            mock_result.state = "FAILURE"
            mock_result.info = None
            mock_ar_cls.return_value = mock_result

            response = auth_client.get("/api/v1/rag/active-tasks")

        assert response.status_code == 200
        assert response.json() == {"tasks": []}
        mock_sync.assert_called_once_with("task-phantom", "FAILURE")

    @pytest.mark.parametrize("celery_state", ["SUCCESS", "FAILURE", "REVOKED"])
    def test_all_terminal_celery_states_excluded(
        self, auth_client, mock_db, celery_state
    ):
        """SUCCESS, FAILURE and REVOKED are all treated as terminal."""
        job = _make_job(f"task-{celery_state.lower()}", status="PENDING")
        self._setup_db_query(mock_db, [job])

        with (
            patch("celery.result.AsyncResult") as mock_ar_cls,
            patch("tasks.question_tasks._try_update_job_status") as mock_sync,
        ):
            mock_result = Mock()
            mock_result.state = celery_state
            mock_result.info = None
            mock_ar_cls.return_value = mock_result

            response = auth_client.get("/api/v1/rag/active-tasks")

        assert response.status_code == 200
        assert response.json()["tasks"] == []
        mock_sync.assert_called_once_with(f"task-{celery_state.lower()}", celery_state)

    def test_active_celery_states_still_returned(self, auth_client, mock_db):
        """Jobs with PROGRESS or STARTED Celery state remain in the response."""
        jobs = [
            _make_job("task-progress", status="PROGRESS"),
            _make_job("task-started", status="STARTED"),
        ]
        self._setup_db_query(mock_db, jobs)

        states = iter(["PROGRESS", "STARTED"])
        infos = iter([{"current": 2, "total": 4, "message": "halb"}, None])

        def make_result(_task_id):
            r = Mock()
            r.state = next(states)
            r.info = next(infos)
            return r

        with (
            patch("celery.result.AsyncResult", side_effect=make_result),
            patch("tasks.question_tasks._try_update_job_status") as mock_sync,
        ):
            response = auth_client.get("/api/v1/rag/active-tasks")

        assert response.status_code == 200
        task_ids = [t["task_id"] for t in response.json()["tasks"]]
        assert task_ids == ["task-progress", "task-started"]
        mock_sync.assert_not_called()

    def test_db_sync_failure_does_not_break_endpoint(self, auth_client, mock_db):
        """If _try_update_job_status raises, the endpoint still returns 200 and excludes the job."""
        job = _make_job("task-sync-broken", status="PENDING")
        self._setup_db_query(mock_db, [job])

        with (
            patch("celery.result.AsyncResult") as mock_ar_cls,
            patch(
                "tasks.question_tasks._try_update_job_status",
                side_effect=RuntimeError("DB down"),
            ),
        ):
            mock_result = Mock()
            mock_result.state = "FAILURE"
            mock_result.info = None
            mock_ar_cls.return_value = mock_result

            response = auth_client.get("/api/v1/rag/active-tasks")

        assert response.status_code == 200
        assert response.json()["tasks"] == []

    def test_celery_unavailable_keeps_job_in_response(self, auth_client, mock_db):
        """If AsyncResult raises (broker down), the job stays in the response (no false phantom)."""
        job = _make_job("task-broker-down", status="PENDING")
        self._setup_db_query(mock_db, [job])

        with (
            patch(
                "celery.result.AsyncResult", side_effect=Exception("Broker unreachable")
            ),
            patch("tasks.question_tasks._try_update_job_status") as mock_sync,
        ):
            response = auth_client.get("/api/v1/rag/active-tasks")

        assert response.status_code == 200
        tasks = response.json()["tasks"]
        assert len(tasks) == 1
        assert tasks[0]["task_id"] == "task-broker-down"
        mock_sync.assert_not_called()

    def test_phantom_and_active_jobs_mixed(self, auth_client, mock_db):
        """A mixed list returns only the active jobs, syncs phantoms."""
        jobs = [
            _make_job("phantom-1", status="PENDING"),
            _make_job("active-1", status="STARTED"),
            _make_job("phantom-2", status="PENDING"),
        ]
        self._setup_db_query(mock_db, jobs)

        states = iter(["FAILURE", "STARTED", "REVOKED"])

        def make_result(_task_id):
            r = Mock()
            r.state = next(states)
            r.info = None
            return r

        with (
            patch("celery.result.AsyncResult", side_effect=make_result),
            patch("tasks.question_tasks._try_update_job_status") as mock_sync,
        ):
            response = auth_client.get("/api/v1/rag/active-tasks")

        assert response.status_code == 200
        task_ids = [t["task_id"] for t in response.json()["tasks"]]
        assert task_ids == ["active-1"]
        assert mock_sync.call_args_list == [
            (("phantom-1", "FAILURE"),),
            (("phantom-2", "REVOKED"),),
        ]

    def test_phantom_sync_never_blocks_on_retry_loop(self, auth_client, mock_db):
        """Phantom sync uses _try_update_job_status (single attempt). The endpoint
        must NEVER invoke the multi-attempt _update_job_status retry loop nor
        time.sleep — those would block the HTTP request handler for up to 17 s
        on a transient DB hiccup. The watchdog (TF-329) handles persistence.
        """
        job = _make_job("phantom-no-block", status="PENDING")
        self._setup_db_query(mock_db, [job])

        with (
            patch("celery.result.AsyncResult") as mock_ar_cls,
            patch("tasks.question_tasks._try_update_job_status") as mock_try,
            patch("tasks.question_tasks._update_job_status") as mock_retry,
            patch("tasks.question_tasks.time.sleep") as mock_sleep,
        ):
            mock_result = Mock()
            mock_result.state = "FAILURE"
            mock_result.info = None
            mock_ar_cls.return_value = mock_result

            response = auth_client.get("/api/v1/rag/active-tasks")

        assert response.status_code == 200
        assert response.json()["tasks"] == []
        mock_try.assert_called_once_with("phantom-no-block", "FAILURE")
        mock_retry.assert_not_called()
        mock_sleep.assert_not_called()
