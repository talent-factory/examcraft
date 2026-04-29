"""Tests für tasks.maintenance_tasks.reconcile_stuck_jobs (TF-329 Watchdog).

Der Watchdog läuft periodisch, sucht stuck PENDING-Jobs in der DB und reconciled
ihren Status mit dem echten Celery-State aus dem Result-Backend (Redis).
"""

import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

# Mock system-level dependencies (matches test_question_tasks.py pattern)
if "magic" not in sys.modules:
    sys.modules["magic"] = MagicMock()


def _make_job(
    task_id: str, status: str = "PENDING", age_minutes: int = 15
) -> MagicMock:
    """Helper to build a mock QuestionGenerationJob."""
    job = MagicMock()
    job.task_id = task_id
    job.status = status
    job.created_at = datetime.now(timezone.utc) - timedelta(minutes=age_minutes)
    return job


def _setup_db_query(mock_session: MagicMock, jobs: list[MagicMock]) -> None:
    """Wire SessionLocal().query(...).filter(...).all() to return `jobs`."""
    query = mock_session.query.return_value
    query.filter.return_value = query
    query.all.return_value = jobs


def test_reconcile_stuck_jobs_importable():
    """Task is importable and registered with Celery."""
    from tasks.maintenance_tasks import reconcile_stuck_jobs

    assert reconcile_stuck_jobs is not None
    assert reconcile_stuck_jobs.name == "tasks.maintenance_tasks.reconcile_stuck_jobs"


def test_reconcile_syncs_success_state_to_db():
    """Celery state SUCCESS → _safe_update_job_status('SUCCESS') called."""
    job = _make_job("task-1")

    mock_session = MagicMock()
    _setup_db_query(mock_session, [job])

    mock_async_result = MagicMock()
    mock_async_result.state = "SUCCESS"

    with (
        patch("tasks.maintenance_tasks.SessionLocal", return_value=mock_session),
        patch("tasks.maintenance_tasks.AsyncResult", return_value=mock_async_result),
        patch(
            "tasks.maintenance_tasks._safe_update_job_status", return_value=True
        ) as mock_safe,
    ):
        from tasks.maintenance_tasks import reconcile_stuck_jobs

        result = reconcile_stuck_jobs.run()

    mock_safe.assert_called_once_with("task-1", "SUCCESS")
    assert result["reconciled"] == 1
    assert result["lost"] == 0


def test_reconcile_syncs_failure_state_to_db():
    """Celery state FAILURE → _safe_update_job_status('FAILURE') called."""
    job = _make_job("task-1")
    mock_session = MagicMock()
    _setup_db_query(mock_session, [job])

    mock_async_result = MagicMock()
    mock_async_result.state = "FAILURE"

    with (
        patch("tasks.maintenance_tasks.SessionLocal", return_value=mock_session),
        patch("tasks.maintenance_tasks.AsyncResult", return_value=mock_async_result),
        patch(
            "tasks.maintenance_tasks._safe_update_job_status", return_value=True
        ) as mock_safe,
    ):
        from tasks.maintenance_tasks import reconcile_stuck_jobs

        result = reconcile_stuck_jobs.run()

    mock_safe.assert_called_once_with("task-1", "FAILURE")
    assert result["reconciled"] == 1


def test_reconcile_syncs_revoked_state_to_db():
    """Celery state REVOKED → _safe_update_job_status('REVOKED') called."""
    job = _make_job("task-1")
    mock_session = MagicMock()
    _setup_db_query(mock_session, [job])

    mock_async_result = MagicMock()
    mock_async_result.state = "REVOKED"

    with (
        patch("tasks.maintenance_tasks.SessionLocal", return_value=mock_session),
        patch("tasks.maintenance_tasks.AsyncResult", return_value=mock_async_result),
        patch(
            "tasks.maintenance_tasks._safe_update_job_status", return_value=True
        ) as mock_safe,
    ):
        from tasks.maintenance_tasks import reconcile_stuck_jobs

        result = reconcile_stuck_jobs.run()

    mock_safe.assert_called_once_with("task-1", "REVOKED")
    assert result["reconciled"] == 1


def test_reconcile_marks_pending_with_no_celery_state_as_failure():
    """Celery state PENDING (task lost in broker) → DB FAILURE + lost counter
    + Celery backend mark_as_failure mirror so the WebSocket sees terminal state."""
    job = _make_job("task-1")
    mock_session = MagicMock()
    _setup_db_query(mock_session, [job])

    # Celery returns PENDING for unknown task IDs — the broker lost it.
    mock_async_result = MagicMock()
    mock_async_result.state = "PENDING"

    with (
        patch("tasks.maintenance_tasks.SessionLocal", return_value=mock_session),
        patch("tasks.maintenance_tasks.AsyncResult", return_value=mock_async_result),
        patch(
            "tasks.maintenance_tasks._safe_update_job_status", return_value=True
        ) as mock_safe,
        patch("tasks.maintenance_tasks._notify_celery_backend_failure") as mock_notify,
    ):
        from tasks.maintenance_tasks import reconcile_stuck_jobs

        result = reconcile_stuck_jobs.run()

    mock_safe.assert_called_once_with("task-1", "FAILURE")
    mock_notify.assert_called_once_with("task-1")
    assert result["lost"] == 1
    assert result["reconciled"] == 1
    assert result["errors"] == 0


def test_reconcile_skips_jobs_still_in_progress():
    """Celery state PROGRESS / STARTED / RETRY → no DB change, no count."""
    job = _make_job("task-1")
    mock_session = MagicMock()
    _setup_db_query(mock_session, [job])

    mock_async_result = MagicMock()
    mock_async_result.state = "PROGRESS"

    with (
        patch("tasks.maintenance_tasks.SessionLocal", return_value=mock_session),
        patch("tasks.maintenance_tasks.AsyncResult", return_value=mock_async_result),
        patch("tasks.maintenance_tasks._safe_update_job_status") as mock_safe,
    ):
        from tasks.maintenance_tasks import reconcile_stuck_jobs

        result = reconcile_stuck_jobs.run()

    mock_safe.assert_not_called()
    assert result["reconciled"] == 0
    assert result["skipped_in_progress"] == 1


def test_reconcile_returns_zero_counts_when_no_stuck_jobs():
    """Empty stuck-job query → result counts all zero, no _safe_update_job_status call."""
    mock_session = MagicMock()
    _setup_db_query(mock_session, [])

    with (
        patch("tasks.maintenance_tasks.SessionLocal", return_value=mock_session),
        patch("tasks.maintenance_tasks._safe_update_job_status") as mock_safe,
    ):
        from tasks.maintenance_tasks import reconcile_stuck_jobs

        result = reconcile_stuck_jobs.run()

    mock_safe.assert_not_called()
    assert result == {
        "reconciled": 0,
        "lost": 0,
        "skipped_in_progress": 0,
        "errors": 0,
    }


def test_reconcile_continues_after_individual_job_error():
    """If processing one job raises, the loop logs and continues with the next."""
    job1 = _make_job("task-1")
    job2 = _make_job("task-2")
    mock_session = MagicMock()
    _setup_db_query(mock_session, [job1, job2])

    # First AsyncResult raises, second is healthy.
    healthy_result = MagicMock()
    healthy_result.state = "SUCCESS"

    def async_result_side_effect(task_id):
        if task_id == "task-1":
            raise RuntimeError("simulated celery backend hiccup")
        return healthy_result

    with (
        patch("tasks.maintenance_tasks.SessionLocal", return_value=mock_session),
        patch(
            "tasks.maintenance_tasks.AsyncResult", side_effect=async_result_side_effect
        ),
        patch(
            "tasks.maintenance_tasks._safe_update_job_status", return_value=True
        ) as mock_safe,
    ):
        from tasks.maintenance_tasks import reconcile_stuck_jobs

        result = reconcile_stuck_jobs.run()

    # task-1 errored → not reconciled. task-2 succeeded → reconciled.
    mock_safe.assert_called_once_with("task-2", "SUCCESS")
    assert result["reconciled"] == 1
    assert result["errors"] == 1


def test_reconcile_counts_db_write_failure_as_error_not_reconciled():
    """When _safe_update_job_status returns False (DB write failed) the
    watchdog must NOT increment reconciled — counters have to reflect reality
    so beat-health checks alarm during a real DB outage instead of staying
    green."""
    job = _make_job("task-1")
    mock_session = MagicMock()
    _setup_db_query(mock_session, [job])

    mock_async_result = MagicMock()
    mock_async_result.state = "SUCCESS"

    with (
        patch("tasks.maintenance_tasks.SessionLocal", return_value=mock_session),
        patch("tasks.maintenance_tasks.AsyncResult", return_value=mock_async_result),
        patch(
            "tasks.maintenance_tasks._safe_update_job_status", return_value=False
        ) as mock_safe,
    ):
        from tasks.maintenance_tasks import reconcile_stuck_jobs

        result = reconcile_stuck_jobs.run()

    mock_safe.assert_called_once_with("task-1", "SUCCESS")
    assert result["reconciled"] == 0
    assert result["errors"] == 1


def test_reconcile_skips_celery_backend_notify_when_db_write_fails():
    """Phantom-PENDING with failing DB write must NOT mirror FAILURE into
    Celery backend — that would double-misrepresent the state (Celery says
    FAILURE while DB still says PENDING)."""
    job = _make_job("task-1")
    mock_session = MagicMock()
    _setup_db_query(mock_session, [job])

    mock_async_result = MagicMock()
    mock_async_result.state = "PENDING"  # broker-lost

    with (
        patch("tasks.maintenance_tasks.SessionLocal", return_value=mock_session),
        patch("tasks.maintenance_tasks.AsyncResult", return_value=mock_async_result),
        patch("tasks.maintenance_tasks._safe_update_job_status", return_value=False),
        patch("tasks.maintenance_tasks._notify_celery_backend_failure") as mock_notify,
    ):
        from tasks.maintenance_tasks import reconcile_stuck_jobs

        result = reconcile_stuck_jobs.run()

    mock_notify.assert_not_called()
    assert result["lost"] == 0
    assert result["reconciled"] == 0
    assert result["errors"] == 1


def test_notify_celery_backend_failure_marks_async_result():
    """The notify helper writes a terminal FAILURE into the Celery backend so
    AsyncResult.state stops returning PENDING after watchdog reconciliation."""
    from tasks.maintenance_tasks import (
        WatchdogReconciliationFailure,
        _notify_celery_backend_failure,
    )

    fake_backend = MagicMock()
    with patch("tasks.maintenance_tasks.celery_app") as mock_celery:
        mock_celery.backend = fake_backend
        _notify_celery_backend_failure("task-1")

    fake_backend.mark_as_failure.assert_called_once()
    args, _ = fake_backend.mark_as_failure.call_args
    assert args[0] == "task-1"
    assert isinstance(args[1], WatchdogReconciliationFailure)


def test_notify_celery_backend_failure_swallows_backend_errors():
    """Backend write failure must not abort the watchdog — log and continue."""
    from tasks.maintenance_tasks import _notify_celery_backend_failure

    with patch("tasks.maintenance_tasks.celery_app") as mock_celery:
        mock_celery.backend.mark_as_failure.side_effect = RuntimeError("redis down")
        # Must not raise:
        _notify_celery_backend_failure("task-1")


def test_reconcile_stuck_threshold_at_least_25_min():
    """Threshold must exceed worst-case retry chain
    (max_retries=4 × retry_backoff_max=300s ≈ 20 min) so an actively-retrying
    task isn't reaped by the watchdog before its scheduled retry runs."""
    from datetime import timedelta

    from tasks.maintenance_tasks import _STUCK_THRESHOLD

    assert _STUCK_THRESHOLD >= timedelta(minutes=25)


def test_reconcile_stuck_jobs_registered_in_beat_schedule():
    """Beat-Schedule includes the watchdog task — typo in the task name would
    silently disable production reconciliation."""
    from celery_app import celery_app

    schedule = celery_app.conf.beat_schedule
    task_names = [entry["task"] for entry in schedule.values()]
    assert "tasks.maintenance_tasks.reconcile_stuck_jobs" in task_names
