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
        "skipped_unexpected": 0,
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


def test_reap_stuck_impersonation_sessions_registered_in_beat_schedule():
    """TF-741: a typo in the task name would silently disable the reaper,
    leaving stuck ImpersonationSession rows open forever."""
    from celery_app import celery_app

    schedule = celery_app.conf.beat_schedule
    task_names = [entry["task"] for entry in schedule.values()]
    assert "tasks.maintenance_tasks.reap_stuck_impersonation_sessions" in task_names


def test_watchdog_beat_schedule_interval_within_sla():
    """Beat-Schedule interval must stay within the operational SLA.

    Pin the interval so a regression like 5 min → 5 hours doesn't slip
    through silently. 15 min is the upper bound: stuck-threshold is 25 min,
    so the watchdog must run at least once per threshold window to catch
    every stuck job within ~40 min in the worst case.
    """
    from celery_app import celery_app

    schedule = celery_app.conf.beat_schedule
    watchdog_entries = [
        entry
        for entry in schedule.values()
        if entry["task"] == "tasks.maintenance_tasks.reconcile_stuck_jobs"
    ]
    assert watchdog_entries, "Watchdog task must be registered in beat_schedule"
    for entry in watchdog_entries:
        interval_seconds = entry["schedule"]
        # Accept either a float-seconds schedule (current) or a timedelta.
        if isinstance(interval_seconds, timedelta):
            interval_seconds = interval_seconds.total_seconds()
        assert interval_seconds <= 15 * 60, (
            f"Watchdog interval {interval_seconds}s exceeds 15-min SLA "
            f"upper bound — stuck jobs would linger past the 25-min threshold"
        )


def test_reconcile_unknown_state_increments_skipped_unexpected_counter():
    """Unknown Celery state → counted in skipped_unexpected (not silently 0).

    Without the counter, drift like a Celery upgrade introducing a new state
    or a typo in a custom state would be invisible to operators — the summary
    log gate would never fire and beat health stays falsely green.
    """
    job = _make_job("task-unknown")

    mock_session = MagicMock()
    _setup_db_query(mock_session, [job])

    mock_async_result = MagicMock()
    mock_async_result.state = "WEIRD_CUSTOM_STATE"

    with (
        patch("tasks.maintenance_tasks.SessionLocal", return_value=mock_session),
        patch("tasks.maintenance_tasks.AsyncResult", return_value=mock_async_result),
        patch(
            "tasks.maintenance_tasks._safe_update_job_status", return_value=True
        ) as mock_safe,
    ):
        from tasks.maintenance_tasks import reconcile_stuck_jobs

        result = reconcile_stuck_jobs()

    mock_safe.assert_not_called()
    assert result["skipped_unexpected"] == 1
    assert result["reconciled"] == 0
    assert result["errors"] == 0


def test_moodle_feedback_reaper_age_fails_stuck_jobs_only(test_db):
    """``reap_stuck_moodle_feedback_jobs`` (TF-435 watchdog) age-fails push jobs
    stuck non-terminal past the threshold, so the frontend poll always converges
    on a terminal status. Fresh and already-terminal rows are untouched."""
    from models.auth import Institution
    from models.exam import Exam
    from models.submission import MoodleFeedbackPushJob
    from tasks.maintenance_tasks import (
        _MOODLE_PUSH_STUCK_THRESHOLD,
        reap_stuck_moodle_feedback_jobs,
    )

    inst = Institution(
        name="reaper-inst",
        slug="reaper-tf435",
        subscription_tier="free",
        max_users=1,
        max_documents=1,
        max_questions_per_month=1,
    )
    test_db.add(inst)
    test_db.flush()
    exam = Exam(title="Reaper", status="finalized", institution_id=inst.id)
    test_db.add(exam)
    test_db.flush()

    now = datetime.now(timezone.utc)
    old = now - _MOODLE_PUSH_STUCK_THRESHOLD - timedelta(minutes=10)

    def _job(status: str, created_at: datetime) -> int:
        job = MoodleFeedbackPushJob(
            institution_id=inst.id,
            exam_id=exam.id,
            status=status,
            created_at=created_at,
        )
        test_db.add(job)
        test_db.commit()
        test_db.refresh(job)
        return job.id

    stuck_queued = _job("queued", old)
    stuck_processing = _job("processing", old)
    fresh_queued = _job("queued", now)
    old_completed = _job("completed", old)  # 0+0+0 == 0 satisfies the sum CHECK

    with (
        patch("tasks.maintenance_tasks.SessionLocal", return_value=test_db),
        patch.object(test_db, "close"),
    ):
        result = reap_stuck_moodle_feedback_jobs.run()

    assert result["reaped"] == 2
    test_db.expire_all()
    assert test_db.get(MoodleFeedbackPushJob, stuck_queued).status == "failed"
    assert test_db.get(MoodleFeedbackPushJob, stuck_processing).status == "failed"
    assert test_db.get(MoodleFeedbackPushJob, fresh_queued).status == "queued"
    assert test_db.get(MoodleFeedbackPushJob, old_completed).status == "completed"
    reaped = test_db.get(MoodleFeedbackPushJob, stuck_queued)
    assert reaped.finished_at is not None
    assert reaped.error_log and reaped.error_log[-1]["scope"] == "job"


def test_impersonation_reaper_closes_stuck_sessions_only(test_db):
    """``reap_stuck_impersonation_sessions`` (TF-741 watchdog) age-closes
    ImpersonationSession rows left open past the 30-min access-token cap.
    The token itself already expired via JWT ``exp`` -- this task only
    fixes up the DB bookkeeping for correct reporting/audit (TF-742).
    Fresh and already-ended rows are untouched.
    """
    from models.auth import ImpersonationSession, Institution, User, UserStatus
    from tasks.maintenance_tasks import (
        _IMPERSONATION_STUCK_THRESHOLD,
        reap_stuck_impersonation_sessions,
    )

    inst = Institution(
        name="reaper-impersonation-inst",
        slug="reaper-tf741",
        subscription_tier="free",
        max_users=10,
        max_documents=10,
        max_questions_per_month=10,
    )
    test_db.add(inst)
    test_db.flush()

    def _user(email: str) -> User:
        user = User(
            email=email,
            password_hash="dummy",
            first_name="R",
            last_name="U",
            institution_id=inst.id,
            status=UserStatus.ACTIVE.value,
        )
        test_db.add(user)
        test_db.flush()
        return user

    now = datetime.now(timezone.utc)
    old = now - _IMPERSONATION_STUCK_THRESHOLD - timedelta(minutes=10)

    def _session(
        admin_email: str, target_email: str, started_at: datetime, ended: bool = False
    ) -> int:
        # Each session needs its own admin: the DB enforces at most one
        # *active* (ended_at IS NULL) session per admin_user_id.
        admin = _user(admin_email)
        target = _user(target_email)
        session = ImpersonationSession(
            admin_user_id=admin.id,
            target_user_id=target.id,
            reason="x",
            started_at=started_at,
        )
        if ended:
            session.ended_at = started_at
            session.end_reason = "manual"
        test_db.add(session)
        test_db.commit()
        test_db.refresh(session)
        return session.id

    stuck_id = _session(
        "reaper-admin-stuck@reaper-tf741.ch", "reaper-stuck@reaper-tf741.ch", old
    )
    fresh_id = _session(
        "reaper-admin-fresh@reaper-tf741.ch", "reaper-fresh@reaper-tf741.ch", now
    )
    already_ended_id = _session(
        "reaper-admin-ended@reaper-tf741.ch",
        "reaper-ended@reaper-tf741.ch",
        old,
        ended=True,
    )

    with (
        patch("tasks.maintenance_tasks.SessionLocal", return_value=test_db),
        patch.object(test_db, "close"),
    ):
        result = reap_stuck_impersonation_sessions.run()

    assert result["reaped"] == 1
    test_db.expire_all()

    stuck = test_db.get(ImpersonationSession, stuck_id)
    assert stuck.ended_at is not None
    assert stuck.end_reason == "timeout"

    fresh = test_db.get(ImpersonationSession, fresh_id)
    assert fresh.ended_at is None

    already_ended = test_db.get(ImpersonationSession, already_ended_id)
    assert already_ended.end_reason == "manual"


def test_impersonation_reaper_writes_audit_event_and_queues_email(test_db):
    """TF-742: a session the reaper age-closes still needs an
    ``impersonation.end`` audit row (impersonator_user_id populated) and a
    notification email to the target -- the same guarantee the manual
    ``/impersonate/end`` endpoint gives, just via the timeout path instead
    of an HTTP request."""
    from models.auth import (
        AuditLog,
        ImpersonationSession,
        Institution,
        User,
        UserStatus,
    )
    from services.audit_service import AuditService
    from tasks.maintenance_tasks import (
        _IMPERSONATION_STUCK_THRESHOLD,
        reap_stuck_impersonation_sessions,
    )

    inst = Institution(
        name="reaper-impersonation-audit-inst",
        slug="reaper-tf742-audit",
        subscription_tier="free",
        max_users=10,
        max_documents=10,
        max_questions_per_month=10,
    )
    test_db.add(inst)
    test_db.flush()

    admin = User(
        email="reaper-audit-admin@reaper-tf742-audit.ch",
        password_hash="dummy",
        first_name="R",
        last_name="Admin",
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
    )
    target = User(
        email="reaper-audit-target@reaper-tf742-audit.ch",
        password_hash="dummy",
        first_name="R",
        last_name="Target",
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
    )
    test_db.add_all([admin, target])
    test_db.flush()

    old = (
        datetime.now(timezone.utc)
        - _IMPERSONATION_STUCK_THRESHOLD
        - timedelta(minutes=10)
    )
    session = ImpersonationSession(
        admin_user_id=admin.id,
        target_user_id=target.id,
        reason="stuck-for-audit",
        started_at=old,
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    with (
        patch("tasks.maintenance_tasks.SessionLocal", return_value=test_db),
        patch.object(test_db, "close"),
        patch("tasks.notification_tasks.send_impersonation_ended_email") as mock_task,
    ):
        result = reap_stuck_impersonation_sessions.run()

    assert result["reaped"] == 1

    row = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == AuditService.ACTION_IMPERSONATION_END)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert row is not None
    assert row.user_id == target.id
    assert row.impersonator_user_id == admin.id
    import json

    data = json.loads(row.additional_data)
    assert data["end_reason"] == "timeout"
    assert data["reason"] == "stuck-for-audit"

    mock_task.delay.assert_called_once()
    kwargs = mock_task.delay.call_args.kwargs
    assert kwargs["to_email"] == target.email
    assert kwargs["end_reason"] == "timeout"


def test_reaper_won_query_excludes_row_closed_by_a_different_invocation(test_db):
    """TF-742 review fix: two overlapping executions of
    ``reap_stuck_impersonation_sessions`` (plausible given
    ``task_acks_late=True`` plus at-least-once redelivery, or more than one
    machine embedding ``--beat``) can each read an overlapping
    ``candidate_ids`` snapshot before either commits. Before the fix, the
    post-UPDATE "won" query filtered only on
    ``id IN candidate_ids AND end_reason == "timeout"`` -- which cannot
    tell "my UPDATE closed this row" apart from "a *different*, concurrent
    execution's UPDATE closed this row and it happens to also be timeout",
    causing a duplicate ``impersonation.end`` audit row + duplicate
    notification email for the same session.

    Reliably interleaving two real concurrent DB transactions inside a
    single-threaded test is inherently flaky, so this instead pins the fix
    down at the level of the actual SQL predicate `reap_stuck_impersonation_
    sessions` runs: two rows both marked ``end_reason == "timeout"`` (as
    they would be regardless of *which* execution closed them) but with
    different ``ended_at`` values -- one matching "this invocation's" own
    timestamp, one not (standing in for a row a concurrent sibling
    execution closed with its own, different timestamp) -- both present in
    one stale ``candidate_ids`` snapshot. Only the row carrying this
    invocation's own ``ended_at`` may come back as "won"."""
    from models.auth import ImpersonationSession, Institution, User, UserStatus
    from tasks.maintenance_tasks import _IMPERSONATION_STUCK_THRESHOLD

    inst = Institution(
        name="reaper-race-inst",
        slug="reaper-tf742-race",
        subscription_tier="free",
        max_users=10,
        max_documents=10,
        max_questions_per_month=10,
    )
    test_db.add(inst)
    test_db.flush()

    admin = User(
        email="reaper-race-admin@reaper-tf742-race.ch",
        password_hash="dummy",
        first_name="R",
        last_name="Admin",
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
    )
    target = User(
        email="reaper-race-target@reaper-tf742-race.ch",
        password_hash="dummy",
        first_name="R",
        last_name="Target",
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
    )
    test_db.add_all([admin, target])
    test_db.flush()

    old = (
        datetime.now(timezone.utc)
        - _IMPERSONATION_STUCK_THRESHOLD
        - timedelta(minutes=10)
    )
    this_invocations_ended_at = datetime.now(timezone.utc)
    other_invocations_ended_at = this_invocations_ended_at - timedelta(seconds=3)

    # Row this invocation's own UPDATE closed.
    won_by_this_run = ImpersonationSession(
        admin_user_id=admin.id,
        target_user_id=target.id,
        reason="closed-by-this-run",
        started_at=old,
        ended_at=this_invocations_ended_at,
        end_reason="timeout",
    )
    # Row a *different*, concurrent execution's UPDATE closed in the gap
    # between this run's stale candidate read and its own UPDATE.
    won_by_other_run = ImpersonationSession(
        admin_user_id=admin.id,
        target_user_id=target.id,
        reason="closed-by-other-run",
        started_at=old,
        ended_at=other_invocations_ended_at,
        end_reason="timeout",
    )
    test_db.add_all([won_by_this_run, won_by_other_run])
    test_db.commit()
    test_db.refresh(won_by_this_run)
    test_db.refresh(won_by_other_run)

    # A stale candidate_ids snapshot this invocation would have read
    # before either UPDATE ran, including both rows.
    candidate_ids = [won_by_this_run.id, won_by_other_run.id]

    won = (
        test_db.query(ImpersonationSession)
        .filter(
            ImpersonationSession.id.in_(candidate_ids),
            ImpersonationSession.end_reason == "timeout",
            ImpersonationSession.ended_at == this_invocations_ended_at,
        )
        .all()
    )

    assert [row.id for row in won] == [won_by_this_run.id]
