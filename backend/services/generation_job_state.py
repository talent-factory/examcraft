"""State of a Generation Job: the DB row, Celery's state, and how they reconcile.

A *Generation Job* is the ``QuestionGenerationJob`` row of a question-generation
Celery task. Its status column is the truth about the outcome: ``SUCCESS`` is
committed together with the questions and is never overwritten (TF-964). The
*Celery state* is volatile (``result_expires``) and may report ``FAILURE`` /
``REVOKED`` / ``PENDING`` for a job that is already ``SUCCESS`` in the DB.

This module owns the read side, the write side and the watchdog's reconcile
decision, so that invariant lives in one place:

- ``read_state``: one consistent ``JobState`` from Celery plus, where it
  matters, the DB row (the TF-964 rule, phantom detection).
- ``sync_phantom``: single-attempt mirror of Celery's terminal state into a
  row that is still not terminal.
- ``record_terminal``: write a terminal status; never overwrites ``SUCCESS``.
- ``reconcile_stuck``: decide what to do with a job stuck in ``PENDING``.
- ``CeleryStatePort``: the seam to Celery's result backend. Adapters:
  ``CeleryBackendAdapter`` (production) and ``InMemoryCelery`` in
  ``tests/generation_job_fakes.py``.

Only ``Generation Job`` rows are covered; document tasks have no job row.
"""

import enum
import logging
import time
from dataclasses import dataclass
from typing import Any, Literal, Protocol, get_args

from celery.result import AsyncResult
from sqlalchemy.exc import SQLAlchemyError

from models.question_generation_job import QuestionGenerationJob
from schemas.task import ProgressCode, progress_code_fields
from services.rag_errors import TASK_FAILED, user_facing_task_error

logger = logging.getLogger(__name__)

# Terminal job states (the implicit initial "PENDING" excluded). Single source:
# the Literal types the signatures, the frozenset is derived from it.
JobTerminalStatus = Literal["SUCCESS", "FAILURE", "REVOKED"]
TERMINAL_STATUSES = frozenset(get_args(JobTerminalStatus))
IN_PROGRESS_STATES = frozenset({"PROGRESS", "STARTED", "RETRY"})

# Backoffs (seconds) BETWEEN status-update attempts. Total attempts = len + 1 = 4.
# Covers the 5-15 s Postgres restart window observed during the 2026-04-28 incident
# (TF-325): the fourth attempt fires ~17 s after the first failure, comfortably past
# typical Fly.io managed PG restart durations.
_STATUS_WRITE_BACKOFFS: tuple[int, ...] = (2, 5, 10)


class JobStatusUpdateError(Exception):
    """Raised when a status write fails after exhausting all retry attempts.

    Indicates that QuestionGenerationJob.status could not be persisted to the DB
    despite retries. ``record_terminal`` turns it into ``WriteOutcome.FAILED``
    and logs CRITICAL so phantom PENDING jobs are visible to monitoring and the
    reconciliation watchdog (TF-329).

    Carries structured fields so Sentry / observability tooling can tag and
    aggregate by task_id, target status, and attempt count without parsing the
    formatted message string.
    """

    def __init__(
        self,
        task_id: str,
        status: str,
        attempts: int,
        last_err: Exception,
    ) -> None:
        super().__init__(
            f"Failed to update job status to {status} for task {task_id} "
            f"after {attempts} attempts: {last_err}"
        )
        self.task_id = task_id
        self.status = status
        self.attempts = attempts
        self.last_err = last_err


class JobNotFoundError(Exception):
    """Raised when no QuestionGenerationJob row exists for the given task_id.

    Distinct from JobStatusUpdateError: NOT retriable. Indicates a data-integrity
    issue (row deleted between dispatch and status update, or wrong task_id passed)
    rather than a transient DB failure.
    """

    def __init__(self, task_id: str, status: str) -> None:
        super().__init__(
            f"No QuestionGenerationJob found for task {task_id} "
            f"(attempted status: {status})"
        )
        self.task_id = task_id
        self.status = status


class WriteOutcome(enum.Enum):
    """Outcome of ``record_terminal``.

    KEPT_SUCCESS is not an error: the row already says SUCCESS and is left
    alone (TF-964). The watchdog must not count it as reconciled nor mirror
    a FAILURE into Celery's backend for it.
    """

    WRITTEN = "written"
    KEPT_SUCCESS = "kept_success"
    FAILED = "failed"


class Reconciliation(enum.Enum):
    """Outcome of ``reconcile_stuck`` for one job."""

    RECONCILED = "reconciled"  # Celery's terminal state written to the DB
    LOST = "lost"  # Celery PENDING: task lost from the broker, marked FAILURE
    IN_PROGRESS = "in_progress"  # still running, left alone
    KEPT_SUCCESS = "kept_success"  # task committed SUCCESS meanwhile (TF-964)
    UNEXPECTED = "unexpected"  # Celery state outside the known vocabulary
    READ_ERROR = "read_error"  # Celery result backend not readable
    WRITE_FAILED = "write_failed"  # DB write failed or the row vanished


# --- Seam: Celery's result backend -------------------------------------------


@dataclass(frozen=True)
class CeleryKnown:
    """Celery state was read.

    ``info`` is the progress meta for ``PROGRESS``, the worker meta for
    ``STARTED``, the exception for ``RETRY``/``FAILURE``/``REVOKED`` and the
    result for ``SUCCESS``. It is not read for ``PENDING``, where Celery has
    nothing to report.
    """

    state: str
    info: Any = None


@dataclass(frozen=True)
class CeleryUnknown:
    """Celery's result backend could not be read (Redis/broker down)."""

    cause: Exception


CeleryReading = CeleryKnown | CeleryUnknown


class CeleryStatePort(Protocol):
    """The seam to Celery's result backend."""

    def read(self, task_id: str) -> CeleryReading:
        """Read the task's state. Never raises: any failure, a backend error as
        well as an unavailable Celery app, is ``CeleryUnknown``."""
        ...

    def mark_failed(self, task_id: str, exc: BaseException) -> None:
        """Best effort: persist FAILURE into the result backend. Never raises."""
        ...


class WatchdogReconciliationFailure(RuntimeError):
    """Marker exception persisted to the Celery result backend when the
    watchdog forces a stuck job to FAILURE.

    Stored via ``mark_failed`` so subsequent ``AsyncResult.state`` reads return
    ``FAILURE``. Without this, the WebSocket progress endpoint (TF-328) would
    keep observing ``PENDING`` from Celery, even though the DB row already
    reads ``FAILURE``, and clients hang on the pending-timeout countdown.
    """


class CeleryBackendAdapter:
    """Production adapter: Celery's result backend via ``AsyncResult``."""

    def read(self, task_id: str) -> CeleryReading:
        try:
            # Lazy: importing celery_app pulls in the broker/Redis config, which
            # callers that only need the status constants must not pay for.
            from celery_app import celery_app

            result = AsyncResult(task_id, app=celery_app)
            state = result.state
            return CeleryKnown(
                state=state, info=None if state == "PENDING" else result.info
            )
        except Exception as err:
            return CeleryUnknown(cause=err)

    def mark_failed(self, task_id: str, exc: BaseException) -> None:
        try:
            from celery_app import celery_app  # lazy, see ``read``

            celery_app.backend.mark_as_failure(task_id, exc)
        except Exception:
            logger.error(
                "Failed to mirror FAILURE into Celery backend for task %s "
                "— UI may show pending-timeout instead of immediate failure",
                task_id,
                exc_info=True,
            )


# --- Write side --------------------------------------------------------------


def _write_once(task_id: str, status: JobTerminalStatus) -> bool:
    """Single-attempt status write.

    Opens a fresh SessionLocal so SQLAlchemy's pool_pre_ping (configured globally
    on the engine in database.py) validates the connection at checkout — this
    lets the retry loop recover from a stale pool entry without reusing a session
    whose internal transaction state may be poisoned by a prior exception.
    Raises JobNotFoundError if no matching row exists. Lets DB exceptions bubble;
    the retry loop decides whether to retry.

    A SUCCESS row is never changed (TF-964): SUCCESS is committed together
    with the questions, so it is the truth about the job. A later FAILURE
    write — the task raising after that commit on its last retry, or the
    watchdog / ``/active-tasks`` mirroring Celery's FAILURE after they
    loaded the row as PENDING and the task committed SUCCESS meanwhile —
    would show a finished job as failed and offer a retry that generates
    it twice.

    Returns True if the status was written, False if a SUCCESS row was
    kept.
    """
    from database import SessionLocal

    session = SessionLocal()
    try:
        # Locked like in the task's _save_generation: a writer that loaded the
        # row as PENDING waits for the task's SUCCESS commit and then sees it.
        job = (
            session.query(QuestionGenerationJob)
            .filter_by(task_id=task_id)
            .with_for_update()
            .first()
        )
        if job is None:
            raise JobNotFoundError(task_id, status)
        if job.status == "SUCCESS" and status != "SUCCESS":
            logger.warning(
                "Not overwriting SUCCESS with %s for task %s — the job's "
                "questions are already saved",
                status,
                task_id,
            )
            return False
        job.status = status
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _write_with_backoff(task_id: str, status: JobTerminalStatus) -> bool:
    """``_write_once`` with retries on transient DB errors.

    Calls ``_write_once`` up to ``len(_STATUS_WRITE_BACKOFFS) + 1`` times
    (currently 4). Backoffs are slept BETWEEN attempts; no sleep after the
    final attempt before the raise.

    Retries only ``(SQLAlchemyError, OSError)``. ``JobNotFoundError`` and any
    programmer-error exceptions (TypeError, AttributeError, ...) propagate
    immediately so they fail loudly instead of being silently retried.

    Raises ``JobStatusUpdateError`` on final failure.
    """
    attempts = len(_STATUS_WRITE_BACKOFFS) + 1
    last_err: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            written = _write_once(task_id, status)
            if attempt > 1:
                logger.info(
                    "Recovered job status update for task %s on attempt %d/%d",
                    task_id,
                    attempt,
                    attempts,
                )
            return written
        except (SQLAlchemyError, OSError) as err:
            last_err = err
            log = logger.error if attempt == attempts else logger.warning
            log(
                "Job status update attempt %d/%d failed for task %s: %s",
                attempt,
                attempts,
                task_id,
                err,
            )
            if attempt < attempts:
                time.sleep(_STATUS_WRITE_BACKOFFS[attempt - 1])
    raise JobStatusUpdateError(task_id, status, attempts, last_err) from last_err


def record_terminal(
    task_id: str, status: JobTerminalStatus, *, retry: bool = True
) -> WriteOutcome:
    """Best-effort status write for the Celery task body, the TF-329 watchdog
    and the ``/active-tasks`` phantom sync.

    Raises ``ValueError`` for a non-terminal ``status``: the callers pass
    Celery's state string, and a typo or a non-terminal value would otherwise
    land in the column as a job that stays "active" forever.

    A status-write failure must never override the actual task outcome (e.g.
    losing a successful generation because the DB write failed, or the row
    vanished), so expected failures are logged and returned, not raised:

    - ``retry=True`` (default): up to 4 attempts with backoff. A failure after
      retries or a missing row is logged CRITICAL and returns ``FAILED``.
    - ``retry=False``: one attempt, for request handlers that must never block
      on a retry loop (the watchdog reconciles persistent failures). A DB error
      or missing row is logged ERROR and returns ``FAILED``.

    Programmer errors (TypeError, AttributeError, ...) propagate in both modes.

    Returns ``WRITTEN`` if the row was updated, ``KEPT_SUCCESS`` if it already
    said SUCCESS and was left alone (TF-964), ``FAILED`` on any swallowed
    failure. The watchdog needs this signal to keep its counters honest.
    """
    if status not in TERMINAL_STATUSES:
        raise ValueError(
            f"record_terminal: non-terminal status {status!r} for task {task_id}"
        )

    if not retry:
        try:
            written = _write_once(task_id, status)
        except (JobNotFoundError, SQLAlchemyError, OSError) as err:
            logger.error(
                "Failed to sync DB status %s for job %s: %s",
                status,
                task_id,
                err,
                exc_info=True,
            )
            return WriteOutcome.FAILED
        return WriteOutcome.WRITTEN if written else WriteOutcome.KEPT_SUCCESS

    try:
        written = _write_with_backoff(task_id, status)
    except JobStatusUpdateError:
        logger.critical(
            "Could not persist %s status for task %s after retries — "
            "job will appear PENDING until reconciliation",
            status,
            task_id,
            exc_info=True,
        )
        return WriteOutcome.FAILED
    except JobNotFoundError:
        logger.critical(
            "Cannot update status to %s for task %s: no QuestionGenerationJob row "
            "found (data-integrity issue — possible row deletion or stale task_id)",
            status,
            task_id,
            exc_info=True,
        )
        return WriteOutcome.FAILED
    return WriteOutcome.WRITTEN if written else WriteOutcome.KEPT_SUCCESS


# --- Watchdog ----------------------------------------------------------------


def reconcile_stuck(
    task_id: str, *, celery: CeleryStatePort | None = None
) -> Reconciliation:
    """Decide and apply what to do with a job the DB still shows as PENDING.

    Precondition: the caller selected the job because its row is PENDING; this
    function does not re-check it.

    Compares the job against Celery's state: a terminal Celery state is
    mirrored into the DB, a Celery ``PENDING`` means the task was lost from the
    broker (marked FAILURE and mirrored into Celery's backend so the WebSocket
    doesn't wait for the pending timeout), a running task is left alone.
    ``record_terminal`` keeps a SUCCESS row that the task committed meanwhile.
    """
    celery = celery or CeleryBackendAdapter()

    reading = celery.read(task_id)
    if isinstance(reading, CeleryUnknown):
        logger.warning(
            "Watchdog: failed to read Celery state for task %s: %s",
            task_id,
            reading.cause,
        )
        return Reconciliation.READ_ERROR

    state = reading.state
    if state in TERMINAL_STATUSES:
        logger.info(
            "Watchdog: reconciling task %s — DB=PENDING celery=%s", task_id, state
        )
        write = record_terminal(task_id, state)
        if write is WriteOutcome.WRITTEN:
            return Reconciliation.RECONCILED
        if write is WriteOutcome.KEPT_SUCCESS:
            return Reconciliation.KEPT_SUCCESS
        return Reconciliation.WRITE_FAILED

    if state == "PENDING":
        # Task is lost from the broker — no worker ever saw it, or the
        # result-backend entry expired. Mark FAILURE and mirror the state
        # into the Celery backend.
        logger.warning(
            "Watchdog: task %s lost from broker (celery=PENDING) — marking FAILURE",
            task_id,
        )
        write = record_terminal(task_id, "FAILURE")
        if write is WriteOutcome.WRITTEN:
            celery.mark_failed(
                task_id,
                WatchdogReconciliationFailure(
                    f"Job {task_id} reconciled to FAILURE by watchdog "
                    "(stuck in PENDING beyond threshold)"
                ),
            )
            return Reconciliation.LOST
        if write is WriteOutcome.KEPT_SUCCESS:
            # Finished meanwhile: don't mirror a FAILURE into Celery.
            return Reconciliation.KEPT_SUCCESS
        return Reconciliation.WRITE_FAILED

    if state in IN_PROGRESS_STATES:
        # Task is actually still running. If the job is older than the
        # threshold and still PROGRESS, it's slow, but not stuck.
        logger.debug(
            "Watchdog: task %s still in_progress (celery=%s) — skipping",
            task_id,
            state,
        )
        return Reconciliation.IN_PROGRESS

    # Unknown state — leave it alone, but count it. Without the counter, a
    # gradual drift (a Celery upgrade introducing a new state, a custom state
    # with a typo) would be invisible to operators.
    logger.warning(
        "Watchdog: task %s in unexpected celery state %r — skipping", task_id, state
    )
    return Reconciliation.UNEXPECTED


# --- Read side ---------------------------------------------------------------


@dataclass(frozen=True)
class Progress:
    """What a running task reports. ``code``/``params`` are what the frontend
    translates (TF-736); ``message`` is the legacy text of document tasks."""

    percent: int
    message: str | None
    code: str | None
    params: dict | None


@dataclass(frozen=True)
class JobError:
    """The safe, user-facing reason a task failed (TF-358, TF-967)."""

    code: str
    message: str


@dataclass(frozen=True)
class JobState:
    """One consistent reading of a Generation Job: DB row and Celery state.

    ``status`` is the HTTP contract: a DB ``SUCCESS`` wins, otherwise a
    terminal Celery state, otherwise the DB column. It is ``PENDING`` without a
    row and whenever the DB was not consulted and Celery reports no terminal
    state, so a running task's state lives in ``celery_status`` and
    ``progress``.
    """

    task_id: str
    status: str
    db_status: str | None
    celery: CeleryReading
    celery_status: str | None
    progress: Progress | None
    result: Any | None
    error: JobError | None
    db_overrode_celery: bool  # TF-964: the row says SUCCESS, Celery does not report SUCCESS (also when unreadable)
    phantom: bool  # the row is not terminal, Celery is


def _percent_of(info: Any) -> int:
    """``progress`` as ``update_progress`` writes it, else derived from
    ``current``/``total`` (a PROGRESS meta from elsewhere may carry only those).

    Foreign or malformed meta never raises: a non-numeric value counts as 0 and
    the result is clamped to 0..100.
    """
    if not isinstance(info, dict):
        return 0

    def number(key: str, default: float) -> float:
        value = info.get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return value

    if "progress" in info:
        percent = number("progress", 0)
    else:
        percent = number("current", 0) / max(number("total", 1), 1) * 100
    return max(0, min(100, int(percent)))


def _progress_of(state: str, info: Any) -> Progress | None:
    if state not in ("PROGRESS", "STARTED", "RETRY"):
        return None
    percent = _percent_of(info)
    if state == "PROGRESS" and isinstance(info, dict):
        code, params = progress_code_fields(info)
        return Progress(percent, info.get("message") or None, code, params)
    if state == "STARTED":
        return Progress(percent, None, ProgressCode.TASK_STARTED.value, {})
    if state == "RETRY":
        return Progress(percent, None, ProgressCode.TASK_RETRYING.value, {})
    return None


def _load_job(db, task_id: str) -> QuestionGenerationJob | None:
    return (
        db.query(QuestionGenerationJob)
        .filter(QuestionGenerationJob.task_id == task_id)
        .first()
    )


def read_state(
    task_id: str,
    *,
    db=None,
    celery: CeleryStatePort | None = None,
    consult_db: bool = False,
    log_error: bool = True,
    job: QuestionGenerationJob | None = None,
) -> JobState:
    """Read a task's state from Celery and, where it matters, from the DB.

    The DB is consulted if ``db`` is given, if ``consult_db`` is set, or if
    Celery reports ``FAILURE``/``REVOKED``: only then can the row overrule
    Celery (TF-964). A caller polling a running task therefore opens no
    session. Never raises because of Celery (``CeleryUnknown``). With its own
    session (``db=None``) a DB read error is logged and swallowed, so the
    caller reports Celery's state; with ``db=`` it propagates.

    Ownership and 404 are the caller's business and happen before this call.
    ``log_error=False`` silences only the server-side ERROR log of a task
    failure, for a caller that reports it elsewhere (``/active-tasks`` is a
    read-only list). The TF-964 warning (Celery failed after the commit) is
    always logged. ``job`` is a row the caller has already loaded; it is used
    instead of querying again.
    """
    celery = celery or CeleryBackendAdapter()
    reading = celery.read(task_id)
    known = reading if isinstance(reading, CeleryKnown) else None
    celery_status = known.state if known else None
    info = known.info if known else None

    db_status: str | None = None
    job_result: Any = None
    if db is not None or consult_db or celery_status in ("FAILURE", "REVOKED"):
        db_status, job_result = _read_db_side(
            task_id, db, job=job, wants_result=celery_status != "SUCCESS"
        )

    overrode = db_status == "SUCCESS" and celery_status != "SUCCESS"
    if overrode:
        status = "SUCCESS"
        result = job_result
        if celery_status in ("FAILURE", "REVOKED"):
            # The user sees the saved result, but the error after the commit
            # must stay visible to ops — whatever ``log_error`` says.
            logger.warning(
                "Task %s: Celery=%s, DB=SUCCESS — reporting SUCCESS from the "
                "DB; Celery info: %r",
                task_id,
                celery_status,
                info,
            )
    else:
        status = (
            celery_status
            if celery_status in TERMINAL_STATUSES
            else (db_status or "PENDING")
        )
        result = info if celery_status == "SUCCESS" else None

    error = None
    if not overrode and celery_status in ("FAILURE", "REVOKED"):
        mapped = user_facing_task_error(info)
        error = JobError(mapped.code, mapped.message)
        if log_error:
            # Log the real error server-side (with traceback if available);
            # the user only gets the safe message (TF-358). Unmapped error
            # classes are flagged so new ones can be alerted on.
            logger.error(
                "Task %s failed (%s): %r",
                task_id,
                "unmapped error class"
                if mapped.code == TASK_FAILED
                else "mapped error",
                info,
                exc_info=info if isinstance(info, BaseException) else None,
            )

    return JobState(
        task_id=task_id,
        status=status,
        db_status=db_status,
        celery=reading,
        celery_status=celery_status,
        progress=_progress_of(celery_status, info) if celery_status else None,
        result=result,
        error=error,
        db_overrode_celery=overrode,
        phantom=(
            db_status is not None
            and db_status not in TERMINAL_STATUSES
            and celery_status in TERMINAL_STATUSES
        ),
    )


def _read_db_side(
    task_id: str,
    db,
    *,
    job: QuestionGenerationJob | None = None,
    wants_result: bool,
) -> tuple[str | None, Any]:
    """The job row's status and, for a SUCCESS row, its stored result."""
    from services.generation_job_result import build_job_result

    own = db is None
    if own:
        from database import SessionLocal

        db = SessionLocal()
    try:
        job = job or _load_job(db, task_id)
        if job is None:
            return None, None
        result = (
            build_job_result(db, job)
            if wants_result and job.status == "SUCCESS"
            else None
        )
        return job.status, result
    except SQLAlchemyError:
        if not own:
            raise
        logger.warning(
            "DB lookup of generation job for task %s failed — reporting Celery's state",
            task_id,
            exc_info=True,
        )
        return None, None
    finally:
        if own:
            db.close()


def sync_phantom(state: JobState) -> WriteOutcome:
    """Mirror Celery's terminal state into a job row that is still not terminal.

    Single attempt, no inline retry: the TF-329 watchdog reconciles persistent
    failures, so a request handler never blocks on the backoff. Programming
    errors propagate (the request path catches them itself). Raises
    ``ValueError`` if ``state`` is not a phantom job.
    """
    if not state.phantom or state.celery_status not in TERMINAL_STATUSES:
        raise ValueError(f"sync_phantom: task {state.task_id} is not a phantom job")
    logger.info(
        "Phantom job detected: task_id=%s db_status=%s celery_state=%s — syncing DB",
        state.task_id,
        state.db_status,
        state.celery_status,
    )
    return record_terminal(state.task_id, state.celery_status, retry=False)
