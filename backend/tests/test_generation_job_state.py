"""Tests for services.generation_job_state, through its interface.

The Celery state is the seam: ``InMemoryCelery`` stands in for the result
backend. The DB side runs against the real test Postgres (savepoint isolation
from ``conftest.test_db``). That isolation shares one connection, so most tests
pin the check-then-write decision (SUCCESS is never overwritten, TF-964). The
row lock itself is exercised by one test on separate, really committing
connections (``test_a_waiting_writer_sees_the_success_the_task_commits``).
"""

import threading
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
    Progress,
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
    read_state,
    reconcile_stuck,
    record_terminal,
    sync_phantom,
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
    """Cheap complement to the real lock test below: the SELECT asks for
    FOR UPDATE."""
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


def test_a_waiting_writer_sees_the_success_the_task_commits(test_engine, monkeypatch):
    """The row lock for real (TF-964): a writer that wants FAILURE blocks while
    the task holds the row, then finds the SUCCESS the task commits and keeps
    it. Needs separate, really committing connections, so it cleans up after
    itself instead of using the savepoint isolation of ``test_db``."""
    factory = sessionmaker(bind=test_engine)
    suffix = uuid.uuid4().hex[:8]
    task_id = f"lock-{suffix}"
    setup = factory()
    institution = Institution(
        name=f"Lock {suffix}",
        slug=f"lock-{suffix}",
        subscription_tier="free",
        max_users=10,
        max_documents=50,
        max_questions_per_month=100,
    )
    setup.add(institution)
    setup.flush()
    user = User(
        email=f"lock-{suffix}@example.ch",
        first_name="L",
        last_name="K",
        institution_id=institution.id,
        status="active",
    )
    setup.add(user)
    setup.flush()
    setup.add(QuestionGenerationJob(task_id=task_id, user_id=user.id, status="PENDING"))
    setup.commit()
    ids = (user.id, institution.id)
    setup.close()

    writer = None
    task = factory()
    try:
        # The task holds the row, like _save_generation before its commit.
        task.query(QuestionGenerationJob).filter_by(
            task_id=task_id
        ).with_for_update().one()
        monkeypatch.setattr("database.SessionLocal", factory)
        outcome: dict = {}

        def _write():
            try:
                outcome["value"] = record_terminal(task_id, "FAILURE", retry=False)
            except BaseException as exc:  # surfaced by the assertion below
                outcome["error"] = exc

        writer = threading.Thread(target=_write)
        writer.start()
        writer.join(timeout=1)
        assert writer.is_alive(), "the writer must wait for the row lock"

        task.query(QuestionGenerationJob).filter_by(task_id=task_id).update(
            {"status": "SUCCESS"}
        )
        task.commit()
        writer.join(timeout=10)

        assert not writer.is_alive()
        assert "error" not in outcome, outcome.get("error")
        assert outcome["value"] is WriteOutcome.KEPT_SUCCESS
        check = factory()
        try:
            stored = check.query(QuestionGenerationJob).filter_by(task_id=task_id)
            assert stored.one().status == "SUCCESS"
        finally:
            check.close()
    finally:
        task.close()
        if writer is not None:
            writer.join(timeout=10)
        cleanup = factory()
        cleanup.query(QuestionGenerationJob).filter_by(task_id=task_id).delete()
        cleanup.query(User).filter_by(id=ids[0]).delete()
        cleanup.query(Institution).filter_by(id=ids[1]).delete()
        cleanup.commit()
        cleanup.close()


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


def test_adapter_reads_state_and_info():
    result = MagicMock(state="PROGRESS", info={"progress": 40})

    with patch("services.generation_job_state.AsyncResult", return_value=result):
        reading = CeleryBackendAdapter().read("task-1")

    assert reading == CeleryKnown(state="PROGRESS", info={"progress": 40})


def test_adapter_does_not_read_info_for_pending():
    """PENDING has nothing to report; skip the second backend round trip."""
    result = MagicMock(state="PENDING")
    type(result).info = property(lambda self: pytest.fail("info read"))

    with patch("services.generation_job_state.AsyncResult", return_value=result):
        reading = CeleryBackendAdapter().read("task-1")

    assert reading == CeleryKnown(state="PENDING")


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


# --- read_state ----------------------------------------------------------------


def test_read_state_running_task_opens_no_session(mocker):
    """A WebSocket tick on a running task must not touch the DB."""
    celery = InMemoryCelery()
    celery.set("t1", "PROGRESS", {"current": 1, "total": 4, "progress": 25})
    session = mocker.patch("database.SessionLocal", side_effect=AssertionError)

    state = read_state("t1", celery=celery)

    session.assert_not_called()
    assert state.status == "PENDING"
    assert state.celery_status == "PROGRESS"
    assert state.progress == Progress(25, None, None, None)
    assert state.db_status is None


def test_read_state_progress_carries_code_and_params():
    celery = InMemoryCelery()
    info = {"progress": 50, "message": "", "code": "x", "params": {"n": 2}}
    celery.set("t1", "PROGRESS", info)

    progress = read_state("t1", celery=celery).progress

    assert progress == Progress(50, None, "x", {"n": 2})


@pytest.mark.parametrize(
    ("celery_state", "code"),
    [("STARTED", "task_started"), ("RETRY", "task_retrying")],
)
def test_read_state_started_and_retry_report_a_progress_code(celery_state, code):
    celery = InMemoryCelery()
    celery.set("t1", celery_state, {"pid": 7})

    state = read_state("t1", celery=celery)

    assert state.progress == Progress(0, None, code, {})


def test_read_state_celery_success_carries_the_celery_result():
    celery = InMemoryCelery()
    celery.set("t1", "SUCCESS", {"questions": [1]})

    state = read_state("t1", celery=celery)

    assert state.status == "SUCCESS"
    assert state.result == {"questions": [1]}
    assert state.error is None


def test_read_state_unreadable_celery_is_unknown_not_an_error():
    celery = InMemoryCelery()
    celery.break_backend()

    state = read_state("t1", celery=celery)

    assert isinstance(state.celery, CeleryUnknown)
    assert state.celery_status is None
    assert state.status == "PENDING"


def test_read_state_failure_maps_to_a_safe_user_error(bound, make_job, mocker):
    task_id = make_job("PENDING")
    celery = InMemoryCelery()
    celery.set(task_id, "FAILURE", RuntimeError("secret internals"))
    log = mocker.patch("services.generation_job_state.logger")

    state = read_state(task_id, celery=celery)

    assert state.status == "FAILURE"
    assert state.error is not None
    assert "secret internals" not in state.error.message
    log.error.assert_called_once()


def test_read_state_failure_log_can_be_silenced(bound, make_job, mocker):
    task_id = make_job("PENDING")
    celery = InMemoryCelery()
    celery.set(task_id, "FAILURE", RuntimeError("boom"))
    log = mocker.patch("services.generation_job_state.logger")

    read_state(task_id, celery=celery, log_error=False)

    log.error.assert_not_called()


@pytest.mark.parametrize("celery_state", ["FAILURE", "REVOKED"])
def test_read_state_db_success_wins_over_celery_failure(
    bound, make_job, mocker, celery_state
):
    """TF-964: the worker was lost after the commit; the row is the truth."""
    task_id = make_job("SUCCESS")
    celery = InMemoryCelery()
    celery.set(task_id, celery_state, RuntimeError("late"))
    mocker.patch(
        "services.generation_job_result.build_job_result", return_value={"q": 1}
    )
    log = mocker.patch("services.generation_job_state.logger")

    state = read_state(task_id, celery=celery)

    assert state.status == "SUCCESS"
    assert state.db_overrode_celery is True
    assert state.result == {"q": 1}
    assert state.error is None
    log.warning.assert_called_once()
    log.error.assert_not_called()


def test_read_state_db_success_wins_over_an_expired_celery_entry(
    bound, make_job, mocker
):
    task_id = make_job("SUCCESS")
    mocker.patch(
        "services.generation_job_result.build_job_result", return_value={"q": 1}
    )

    state = read_state(task_id, celery=InMemoryCelery(), consult_db=True)

    assert state.celery_status == "PENDING"
    assert state.status == "SUCCESS"
    assert state.db_overrode_celery is True


def test_read_state_pending_without_consult_does_not_ask_the_db(bound, make_job):
    """The WebSocket asks the DB for a PENDING task only after its timeout."""
    task_id = make_job("SUCCESS")

    state = read_state(task_id, celery=InMemoryCelery())

    assert state.db_status is None
    assert state.db_overrode_celery is False


def test_read_state_with_a_session_reads_the_row_for_any_celery_state(bound, make_job):
    task_id = make_job("PENDING")
    celery = InMemoryCelery()
    celery.set(task_id, "PROGRESS", {"progress": 10})
    db = bound()
    try:
        state = read_state(task_id, db=db, celery=celery)
    finally:
        db.close()

    assert state.db_status == "PENDING"
    assert state.status == "PENDING"
    assert state.phantom is False


def test_read_state_missing_row_leaves_celery_in_charge(bound):
    celery = InMemoryCelery()
    celery.set("doc-task", "FAILURE", RuntimeError("x"))

    state = read_state("doc-task", celery=celery)

    assert state.db_status is None
    assert state.status == "FAILURE"
    assert state.phantom is False


def test_read_state_failing_to_open_the_session_bubbles(bound, mocker):
    celery = InMemoryCelery()
    celery.set("t1", "FAILURE", RuntimeError("x"))
    mocker.patch("database.SessionLocal", side_effect=_DB_DOWN)

    with pytest.raises(OperationalError):
        # Opening the session itself failing is not a read error: it bubbles.
        read_state("t1", celery=celery)


def test_read_state_own_session_query_error_reports_celery(bound, mocker):
    celery = InMemoryCelery()
    celery.set("t1", "FAILURE", RuntimeError("x"))
    broken = MagicMock()
    broken.query.side_effect = _DB_DOWN
    mocker.patch("database.SessionLocal", return_value=broken)

    state = read_state("t1", celery=celery)

    assert state.status == "FAILURE"
    assert state.db_status is None
    broken.close.assert_called_once()


def test_read_state_given_session_propagates_a_db_error():
    broken = MagicMock()
    broken.query.side_effect = _DB_DOWN

    with pytest.raises(OperationalError):
        read_state("t1", db=broken, celery=InMemoryCelery())


@pytest.mark.parametrize("celery_state", ["SUCCESS", "FAILURE", "REVOKED"])
def test_read_state_flags_a_phantom_job(bound, make_job, celery_state):
    task_id = make_job("PENDING")
    celery = InMemoryCelery()
    celery.set(task_id, celery_state, None)
    db = bound()
    try:
        state = read_state(task_id, db=db, celery=celery, log_error=False)
    finally:
        db.close()

    assert state.phantom is True
    assert state.status == celery_state


def test_sync_phantom_makes_a_single_attempt_when_the_write_fails(bound, make_job):
    task_id = make_job("PENDING")
    celery = InMemoryCelery()
    celery.set(task_id, "FAILURE", None)
    db = bound()
    try:
        state = read_state(task_id, db=db, celery=celery, log_error=False)
    finally:
        db.close()
    flaky = _flaky(bound, 99, _DB_DOWN)

    with (
        patch("database.SessionLocal", flaky),
        patch("services.generation_job_state.time.sleep") as sleep,
    ):
        outcome = sync_phantom(state)

    assert outcome is WriteOutcome.FAILED
    assert flaky.calls["n"] == 1
    sleep.assert_not_called()


@pytest.mark.parametrize(
    ("info", "expected"),
    [
        ({"progress": 40}, 40),
        ({"current": 1, "total": 4}, 25),
        ({"current": 5, "total": 0}, 100),
        ({"progress": 250}, 100),
        ({"progress": -5}, 0),
        ({"progress": None}, 0),
        ({"progress": "half"}, 0),
        ({"current": None, "total": 3}, 0),
        ({"current": 2, "total": None}, 100),
        (RuntimeError("retry"), 0),
        (None, 0),
    ],
)
def test_progress_percent_never_raises_on_foreign_meta(info, expected):
    from services.generation_job_state import _percent_of

    assert _percent_of(info) == expected


@pytest.mark.parametrize("celery_state", ["SUCCESS", "FAILURE", "REVOKED", "PENDING"])
def test_read_state_ignores_the_info_of_non_running_states_for_progress(celery_state):
    celery = InMemoryCelery()
    celery.set("t1", celery_state, {"progress": 99, "total": "x"})

    state = read_state("t1", celery=celery, log_error=False)

    assert state.progress is None


def test_read_state_override_warning_survives_log_error_false(bound, make_job, mocker):
    """Silencing the task-error log must not hide a failure after the commit."""
    task_id = make_job("SUCCESS")
    celery = InMemoryCelery()
    celery.set(task_id, "FAILURE", RuntimeError("late"))
    mocker.patch(
        "services.generation_job_result.build_job_result", return_value={"q": 1}
    )
    log = mocker.patch("services.generation_job_state.logger")

    state = read_state(task_id, celery=celery, log_error=False)

    assert state.db_overrode_celery is True
    log.warning.assert_called_once()
    log.error.assert_not_called()


@pytest.mark.parametrize("celery_state", ["SUCCESS", "FAILURE", "REVOKED"])
def test_read_state_terminal_row_is_not_a_phantom(bound, make_job, celery_state):
    task_id = make_job("FAILURE")
    celery = InMemoryCelery()
    celery.set(task_id, celery_state, None)
    db = bound()
    try:
        state = read_state(task_id, db=db, celery=celery, log_error=False)
    finally:
        db.close()

    assert state.phantom is False


def test_read_state_unreadable_celery_with_a_success_row_reports_success(
    bound, make_job, mocker
):
    task_id = make_job("SUCCESS")
    mocker.patch(
        "services.generation_job_result.build_job_result", return_value={"q": 1}
    )
    celery = MagicMock()
    celery.read.return_value = CeleryUnknown(ConnectionError("redis down"))
    db = bound()
    try:
        state = read_state(task_id, db=db, celery=celery)
    finally:
        db.close()

    assert state.status == "SUCCESS"
    assert state.db_overrode_celery is True
    assert state.celery_status is None


def test_read_state_uses_a_given_job_without_querying_again():
    job = MagicMock()
    job.status = "PENDING"
    db = MagicMock()
    celery = InMemoryCelery()
    celery.set("t1", "FAILURE", None)

    state = read_state("t1", db=db, celery=celery, job=job, log_error=False)

    db.query.assert_not_called()
    assert state.db_status == "PENDING"
    assert state.phantom is True


def test_sync_phantom_mirrors_the_terminal_state(bound, make_job):
    task_id = make_job("PENDING")
    celery = InMemoryCelery()
    celery.set(task_id, "REVOKED", None)
    db = bound()
    try:
        state = read_state(task_id, db=db, celery=celery, log_error=False)
    finally:
        db.close()

    assert sync_phantom(state) is WriteOutcome.WRITTEN
    assert _status(bound, task_id) == "REVOKED"


def test_sync_phantom_rejects_a_job_that_is_not_a_phantom():
    celery = InMemoryCelery()
    celery.set("t1", "PROGRESS", {})
    state = read_state("t1", celery=celery)

    with pytest.raises(ValueError):
        sync_phantom(state)
