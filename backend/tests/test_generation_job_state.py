"""Tests for services.generation_job_state, through its interface.

The Celery state is the seam: ``InMemoryCelery`` stands in for the result
backend. The DB side runs against the real test Postgres (savepoint isolation
from ``conftest.test_db``). That isolation shares one connection, so the row
lock itself is not exercised here; the tests pin the check-then-write
decision (SUCCESS is never overwritten, TF-964), not the locking.
"""

import uuid
from typing import get_args
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from models.auth import Institution, User
from models.question_generation_job import QuestionGenerationJob
from services.generation_job_state import (
    IN_PROGRESS_STATES,
    TERMINAL_STATUSES,
    CeleryBackendAdapter,
    CeleryKnown,
    CeleryUnknown,
    JobNotFoundError,
    JobTerminalStatus,
    JobStatusUpdateError,
    Reconciliation,
    WatchdogReconciliationFailure,
    WriteOutcome,
    reconcile_stuck,
    record_terminal,
)
from tests.generation_job_fakes import InMemoryCelery


@pytest.fixture
def bound(test_db, monkeypatch):
    """Sessionmaker on the test connection; the module opens its own sessions."""
    factory = sessionmaker(
        bind=test_db.get_bind(), join_transaction_mode="create_savepoint"
    )
    monkeypatch.setattr("database.SessionLocal", factory)
    return factory


@pytest.fixture
def make_job(test_db, bound):
    """Create a Generation Job row; returns its task_id."""

    def _make(status: str = "PENDING") -> str:
        suffix = uuid.uuid4().hex[:8]
        institution = Institution(
            name=f"GJS {suffix}",
            slug=f"gjs-{suffix}",
            subscription_tier="free",
            max_users=10,
            max_documents=50,
            max_questions_per_month=100,
        )
        test_db.add(institution)
        test_db.flush()
        user = User(
            email=f"gjs-{suffix}@example.ch",
            first_name="G",
            last_name="S",
            institution_id=institution.id,
            status="active",
        )
        test_db.add(user)
        test_db.flush()
        task_id = f"gjs-{suffix}"
        test_db.add(
            QuestionGenerationJob(task_id=task_id, user_id=user.id, status=status)
        )
        test_db.commit()
        return task_id

    return _make


def _status(bound, task_id: str) -> str:
    """Read the stored status through a separate session."""
    db = bound()
    try:
        return db.query(QuestionGenerationJob).filter_by(task_id=task_id).one().status
    finally:
        db.close()


def _set_status(bound, task_id: str, status: str) -> None:
    """Simulate another writer (the task itself) committing a status."""
    db = bound()
    db.query(QuestionGenerationJob).filter_by(task_id=task_id).update(
        {"status": status}
    )
    db.commit()
    db.close()


def _flaky(real, fail_times: int, exc: Exception):
    """Session factory whose first ``fail_times`` calls raise ``exc``."""
    calls = {"n": 0}

    def factory():
        calls["n"] += 1
        if calls["n"] <= fail_times:
            raise exc
        return real()

    factory.calls = calls
    return factory


_DB_DOWN = OperationalError("SELECT 1", {}, Exception("db down"))


def test_status_sets_match_the_celery_vocabulary():
    assert TERMINAL_STATUSES == {"SUCCESS", "FAILURE", "REVOKED"}
    assert IN_PROGRESS_STATES == {"PROGRESS", "STARTED", "RETRY"}


def test_core_api_shares_the_terminal_statuses():
    """api.rag_exams re-uses the module's TERMINAL_STATUSES, not its own copy."""
    from api import rag_exams

    assert rag_exams.TERMINAL_STATUSES is TERMINAL_STATUSES


# --- record_terminal -----------------------------------------------------------


@pytest.mark.parametrize("status", ["SUCCESS", "FAILURE", "REVOKED"])
def test_record_terminal_writes_status(bound, make_job, status):
    task_id = make_job("PENDING")

    assert record_terminal(task_id, status) is WriteOutcome.WRITTEN
    assert _status(bound, task_id) == status


@pytest.mark.parametrize("status", ["FAILURE", "REVOKED"])
def test_record_terminal_never_downgrades_success(bound, make_job, status):
    """Every status writer (task body, watchdog, /active-tasks phantom sync)
    goes through record_terminal; a SUCCESS row stays SUCCESS (TF-964)."""
    task_id = make_job("SUCCESS")

    assert record_terminal(task_id, status) is WriteOutcome.KEPT_SUCCESS
    assert _status(bound, task_id) == "SUCCESS"


@pytest.mark.parametrize("status", ["PENDING", "PROGRESS", "SUKZESS", ""])
def test_record_terminal_rejects_non_terminal_status(bound, make_job, status):
    """A typo or non-terminal value must not land in the column: such a job
    would stay "active" forever and the watchdog only looks at PENDING."""
    task_id = make_job("PENDING")

    with pytest.raises(ValueError):
        record_terminal(task_id, status)
    with pytest.raises(ValueError):
        record_terminal(task_id, status, retry=False)
    assert _status(bound, task_id) == "PENDING"


def test_terminal_statuses_derive_from_the_literal():
    assert TERMINAL_STATUSES == frozenset(get_args(JobTerminalStatus))


def test_record_terminal_missing_row_fails_loudly_without_raising(bound, mocker):
    log = mocker.patch("services.generation_job_state.logger")

    assert record_terminal("ghost", "SUCCESS") is WriteOutcome.FAILED
    log.critical.assert_called_once()


def test_record_terminal_recovers_from_transient_db_errors(bound, make_job):
    task_id = make_job("PENDING")
    flaky = _flaky(bound, 2, _DB_DOWN)

    with (
        patch("database.SessionLocal", flaky),
        patch("services.generation_job_state.time.sleep") as sleep,
    ):
        outcome = record_terminal(task_id, "FAILURE")

    assert outcome is WriteOutcome.WRITTEN
    assert [c.args[0] for c in sleep.call_args_list] == [2, 5]
    assert _status(bound, task_id) == "FAILURE"


def test_record_terminal_succeeds_on_the_fourth_attempt(bound, make_job):
    """Pins the off-by-one of the backoff list: 3 failures, 4th attempt wins."""
    task_id = make_job("PENDING")
    flaky = _flaky(bound, 3, _DB_DOWN)

    with (
        patch("database.SessionLocal", flaky),
        patch("services.generation_job_state.time.sleep") as sleep,
    ):
        outcome = record_terminal(task_id, "FAILURE")

    assert outcome is WriteOutcome.WRITTEN
    assert flaky.calls["n"] == 4
    assert [c.args[0] for c in sleep.call_args_list] == [2, 5, 10]


def test_write_locks_the_job_row(bound, make_job):
    """The row lock is what makes "watchdog loaded PENDING, task committed
    SUCCESS meanwhile" safe (TF-964). The shared test connection cannot show
    a real lock wait, so pin that the SELECT asks for FOR UPDATE."""
    task_id = make_job("PENDING")
    statements: list[str] = []

    def capture(conn, cursor, statement, *args):
        statements.append(statement)

    engine = bound.kw["bind"]
    event.listen(engine, "before_cursor_execute", capture)
    try:
        record_terminal(task_id, "FAILURE")
    finally:
        event.remove(engine, "before_cursor_execute", capture)

    selects = [s for s in statements if s.lstrip().upper().startswith("SELECT")]
    assert any("FOR UPDATE" in s.upper() for s in selects)


def test_record_terminal_gives_up_after_four_attempts(bound, make_job, mocker):
    task_id = make_job("PENDING")
    flaky = _flaky(bound, 99, _DB_DOWN)
    log = mocker.patch("services.generation_job_state.logger")

    with (
        patch("database.SessionLocal", flaky),
        patch("services.generation_job_state.time.sleep") as sleep,
    ):
        outcome = record_terminal(task_id, "FAILURE")

    assert outcome is WriteOutcome.FAILED
    assert flaky.calls["n"] == 4
    assert [c.args[0] for c in sleep.call_args_list] == [2, 5, 10]
    log.critical.assert_called_once()
    assert _status(bound, task_id) == "PENDING"


def test_record_terminal_missing_row_is_not_retried(bound):
    flaky = _flaky(bound, 0, _DB_DOWN)

    with (
        patch("database.SessionLocal", flaky),
        patch("services.generation_job_state.time.sleep") as sleep,
    ):
        outcome = record_terminal("ghost", "FAILURE")

    assert outcome is WriteOutcome.FAILED
    assert flaky.calls["n"] == 1
    sleep.assert_not_called()


def test_commit_failure_rolls_back_closes_and_retries(bound, make_job):
    """A failure after the session exists must leave no open session behind
    (TF-325) and the retry must still persist the status."""
    task_id = make_job("PENDING")
    sessions = []

    def factory():
        session = bound()
        if not sessions:
            session.commit = MagicMock(side_effect=_DB_DOWN)
        session.rollback = MagicMock(wraps=session.rollback)
        session.close = MagicMock(wraps=session.close)
        sessions.append(session)
        return session

    with (
        patch("database.SessionLocal", factory),
        patch("services.generation_job_state.time.sleep"),
    ):
        outcome = record_terminal(task_id, "FAILURE")

    assert outcome is WriteOutcome.WRITTEN
    assert len(sessions) == 2
    sessions[0].rollback.assert_called_once()
    for session in sessions:
        session.close.assert_called_once()
    assert _status(bound, task_id) == "FAILURE"


def test_record_terminal_does_not_retry_programmer_errors(bound, make_job):
    task_id = make_job("PENDING")
    flaky = _flaky(bound, 99, TypeError("bug"))

    with (
        patch("database.SessionLocal", flaky),
        patch("services.generation_job_state.time.sleep") as sleep,
        pytest.raises(TypeError),
    ):
        record_terminal(task_id, "FAILURE")

    assert flaky.calls["n"] == 1
    sleep.assert_not_called()


def test_single_attempt_does_not_retry_or_sleep(bound, make_job, mocker):
    """The /active-tasks handler must never block on the retry loop."""
    task_id = make_job("PENDING")
    flaky = _flaky(bound, 99, _DB_DOWN)
    log = mocker.patch("services.generation_job_state.logger")

    with (
        patch("database.SessionLocal", flaky),
        patch("services.generation_job_state.time.sleep") as sleep,
    ):
        outcome = record_terminal(task_id, "FAILURE", retry=False)

    assert outcome is WriteOutcome.FAILED
    assert flaky.calls["n"] == 1
    sleep.assert_not_called()
    log.error.assert_called_once()  # ERROR, not WARNING: surfaces a real DB outage


def test_single_attempt_writes_and_keeps_success(bound, make_job):
    pending = make_job("PENDING")
    done = make_job("SUCCESS")

    assert record_terminal(pending, "FAILURE", retry=False) is WriteOutcome.WRITTEN
    assert record_terminal(done, "FAILURE", retry=False) is WriteOutcome.KEPT_SUCCESS
    assert _status(bound, pending) == "FAILURE"
    assert _status(bound, done) == "SUCCESS"


def test_single_attempt_missing_row_fails_without_raising(bound):
    assert record_terminal("ghost", "FAILURE", retry=False) is WriteOutcome.FAILED


def test_error_types_expose_structured_fields():
    cause = RuntimeError("cause")
    update_err = JobStatusUpdateError("task-1", "FAILURE", 4, cause)
    assert (update_err.task_id, update_err.status, update_err.attempts) == (
        "task-1",
        "FAILURE",
        4,
    )
    assert update_err.last_err is cause

    missing = JobNotFoundError("ghost", "SUCCESS")
    assert (missing.task_id, missing.status) == ("ghost", "SUCCESS")


# --- reconcile_stuck -----------------------------------------------------------


@pytest.mark.parametrize("state", ["SUCCESS", "FAILURE", "REVOKED"])
def test_reconcile_mirrors_terminal_celery_state(bound, make_job, state):
    task_id = make_job("PENDING")
    celery = InMemoryCelery()
    celery.set(task_id, state)

    assert reconcile_stuck(task_id, celery=celery) is Reconciliation.RECONCILED
    assert _status(bound, task_id) == state
    assert celery.failed == []


def test_reconcile_marks_broker_lost_task_failed_and_mirrors_into_celery(
    bound, make_job
):
    """Celery PENDING = lost from the broker: DB FAILURE, plus FAILURE into
    Celery's backend so the WebSocket doesn't wait for the pending timeout."""
    task_id = make_job("PENDING")
    celery = InMemoryCelery()  # unknown task reads as PENDING

    assert reconcile_stuck(task_id, celery=celery) is Reconciliation.LOST
    assert _status(bound, task_id) == "FAILURE"
    assert [t for t, _ in celery.failed] == [task_id]
    assert isinstance(celery.failed[0][1], WatchdogReconciliationFailure)


@pytest.mark.parametrize("state", sorted(IN_PROGRESS_STATES))
def test_reconcile_leaves_running_tasks_alone(bound, make_job, state):
    task_id = make_job("PENDING")
    celery = InMemoryCelery()
    celery.set(task_id, state)

    assert reconcile_stuck(task_id, celery=celery) is Reconciliation.IN_PROGRESS
    assert _status(bound, task_id) == "PENDING"
    assert celery.failed == []


def test_reconcile_counts_unknown_celery_state_as_unexpected(bound, make_job):
    task_id = make_job("PENDING")
    celery = InMemoryCelery()
    celery.set(task_id, "SUCESS")  # typo in a custom state

    assert reconcile_stuck(task_id, celery=celery) is Reconciliation.UNEXPECTED
    assert _status(bound, task_id) == "PENDING"


def test_reconcile_reports_unreadable_celery_backend(bound, make_job):
    task_id = make_job("PENDING")
    celery = InMemoryCelery()
    celery.break_backend()

    assert reconcile_stuck(task_id, celery=celery) is Reconciliation.READ_ERROR
    assert _status(bound, task_id) == "PENDING"


def test_reconcile_reports_vanished_row_as_write_failure(bound):
    celery = InMemoryCelery()
    celery.set("ghost", "FAILURE")

    assert reconcile_stuck("ghost", celery=celery) is Reconciliation.WRITE_FAILED


def test_reconcile_does_not_mirror_failure_when_db_write_fails(bound, make_job):
    """A lost task whose DB write fails must not get a FAILURE in Celery's
    backend: Celery would say FAILURE while the DB still says PENDING."""
    task_id = make_job("PENDING")
    celery = InMemoryCelery()
    flaky = _flaky(bound, 99, _DB_DOWN)

    with (
        patch("database.SessionLocal", flaky),
        patch("services.generation_job_state.time.sleep"),
    ):
        outcome = reconcile_stuck(task_id, celery=celery)

    assert outcome is Reconciliation.WRITE_FAILED
    assert celery.failed == []


@pytest.mark.parametrize("celery_state", ["FAILURE", "REVOKED", "PENDING"])
def test_reconcile_keeps_success_the_task_committed_meanwhile(
    bound, make_job, celery_state
):
    """Race: the watchdog loaded the row as PENDING, then the task commits
    SUCCESS before the watchdog writes. Celery says FAILURE (worker lost
    after the commit) or PENDING (entry expired). The write keeps SUCCESS and
    no FAILURE is mirrored into Celery."""
    task_id = make_job("PENDING")
    celery = InMemoryCelery()
    celery.set(task_id, celery_state)
    celery.before_read = lambda tid: _set_status(bound, tid, "SUCCESS")

    assert reconcile_stuck(task_id, celery=celery) is Reconciliation.KEPT_SUCCESS
    assert _status(bound, task_id) == "SUCCESS"
    assert celery.failed == []


# --- Celery adapter ------------------------------------------------------------


def test_adapter_reads_the_state_only():
    result = MagicMock(state="PROGRESS")

    with patch("services.generation_job_state.AsyncResult", return_value=result):
        reading = CeleryBackendAdapter().read("task-1")

    assert reading == CeleryKnown(state="PROGRESS")


def test_adapter_turns_backend_errors_into_unknown():
    boom = ConnectionError("redis down")

    with patch("services.generation_job_state.AsyncResult", side_effect=boom):
        reading = CeleryBackendAdapter().read("task-1")

    assert reading == CeleryUnknown(cause=boom)


def test_adapter_turns_an_unavailable_celery_app_into_unknown():
    """The port promises "never raises": a failing celery_app import is a read
    error for the watchdog, not an abort of its whole run."""
    with patch.dict("sys.modules", {"celery_app": None}):
        reading = CeleryBackendAdapter().read("task-1")

    assert isinstance(reading, CeleryUnknown)


def test_adapter_mirrors_failure_into_the_result_backend():
    exc = WatchdogReconciliationFailure("lost")

    with patch("celery_app.celery_app") as celery_app:
        CeleryBackendAdapter().mark_failed("task-1", exc)

    celery_app.backend.mark_as_failure.assert_called_once_with("task-1", exc)


def test_adapter_swallows_mirror_errors():
    with patch("celery_app.celery_app") as celery_app:
        celery_app.backend.mark_as_failure.side_effect = RuntimeError("redis down")
        CeleryBackendAdapter().mark_failed("task-1", RuntimeError("x"))  # no raise
