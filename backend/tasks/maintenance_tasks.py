"""Periodic maintenance tasks (TF-329 Watchdog).

`reconcile_stuck_jobs` runs every 5 minutes via Celery Beat and
reconciles QuestionGenerationJob rows against the real Celery state from
the result backend. Addresses the phantom-PENDING symptom from the demo
incident on 2026-04-28 as a third line of defense after TF-325
(retry loop) and TF-326 (API endpoint reconcile).
"""

import logging
from datetime import datetime, timedelta, timezone

from celery.result import AsyncResult

from celery_app import celery_app
from database import SessionLocal
from enums import ImportJobStatus, MoodleFeedbackPushStatus
from models.auth import ImpersonationSession
from models.question_generation_job import QuestionGenerationJob
from models.submission import ImportJob, MoodleFeedbackPushJob
from services.auth_service import IMPERSONATION_TOKEN_EXPIRE_MINUTES
from tasks.question_tasks import _safe_update_job_status

logger = logging.getLogger(__name__)


# Stuck threshold: a PENDING job older than this is considered in need
# of reconciliation.
# Worst-case retry chain in question_tasks.generate_questions_task:
#   max_retries=4, retry_backoff=30, retry_backoff_max=300, retry_jitter=True
# → cumulative backoff sum up to the last execution reaches ~20 min.
# Plus task_soft_time_limit=3300s only kicks in for long generation calls.
# A 25 min threshold gives actively retrying tasks room, so the
# watchdog doesn't prematurely set a FAILURE that a subsequent retry
# then overwrites with SUCCESS (status flicker in the UI).
_STUCK_THRESHOLD = timedelta(minutes=25)

# TF-412: ImportJob rows are pre-created in ``queued`` and flipped to
# ``running`` by the Celery worker. If the message is lost (broker blip,
# misrouted queue, worker OOM before any DB write) the row never reaches a
# terminal status and the polling client hangs until its own 5-min timeout.
# Unlike question jobs there is no Celery result_backend lookup here — an
# ImportJob carries no ``task_id`` — so this reaper is purely age-based on
# ``created_at`` (``queued`` rows have ``started_at = NULL``, so filtering on
# ``started_at`` would miss them). 30 min comfortably clears the slowest
# legitimate LLM-graded large-class import while still bounding the stuck row.
_IMPORT_STUCK_THRESHOLD = timedelta(minutes=30)
_IMPORT_NON_TERMINAL_STATUSES = (
    ImportJobStatus.QUEUED.value,
    ImportJobStatus.RUNNING.value,
)

# TF-435: same age-fail watchdog for the outbound feedback-push jobs. A push
# job is pre-created ``queued`` and flipped ``processing`` by the worker; a
# lost message / OOM before the terminal write would leave it non-terminal
# forever, and the frontend poll (~2 min cap) would then silently show nothing.
# Same created_at age basis as ImportJob (``queued`` rows have started_at = NULL).
_MOODLE_PUSH_STUCK_THRESHOLD = timedelta(minutes=30)
_MOODLE_PUSH_NON_TERMINAL_STATUSES = (
    MoodleFeedbackPushStatus.QUEUED.value,
    MoodleFeedbackPushStatus.PROCESSING.value,
)

# In-progress states the watchdog does NOT touch — these tasks are actually running.
_IN_PROGRESS_STATES = frozenset({"PROGRESS", "STARTED", "RETRY"})

# Terminal states the watchdog mirrors 1:1 into the DB.
_TERMINAL_STATES = frozenset({"SUCCESS", "FAILURE", "REVOKED"})


class WatchdogReconciliationFailure(RuntimeError):
    """Marker exception persisted to the Celery result backend when the
    watchdog forces a stuck job to FAILURE.

    Stored via ``celery_app.backend.mark_as_failure`` so subsequent
    ``AsyncResult.state`` reads return ``FAILURE``. Without this, the WebSocket
    progress endpoint (TF-328) would keep observing ``PENDING`` from Celery —
    even though the DB row already reads ``FAILURE`` — and clients hang on
    the pending-timeout countdown until the 120 s ceiling.
    """


def _notify_celery_backend_failure(task_id: str) -> None:
    """Mirror the watchdog's DB-FAILURE write into Celery's result backend so
    AsyncResult.state reflects the terminal state. Best-effort: a failure here
    only delays UI signaling, not data integrity, so we log and move on.
    """
    try:
        celery_app.backend.mark_as_failure(
            task_id,
            WatchdogReconciliationFailure(
                f"Job {task_id} reconciled to FAILURE by watchdog "
                "(stuck in PENDING beyond threshold)"
            ),
        )
    except Exception:
        logger.error(
            "Watchdog: failed to mirror FAILURE into Celery backend for task %s "
            "— UI may show pending-timeout instead of immediate failure",
            task_id,
            exc_info=True,
        )


@celery_app.task(name="tasks.maintenance_tasks.reconcile_stuck_jobs")
def reconcile_stuck_jobs() -> dict:
    """Reconcile the DB status of stuck PENDING jobs against Celery's result backend.

    Returns:
        dict with counters:
        ``{reconciled, lost, skipped_in_progress, skipped_unexpected, errors}``.
        Counter semantics:
          - ``reconciled``: actual DB status updates that were persisted.
          - ``lost``: subset of ``reconciled`` for broker-lost jobs.
          - ``skipped_in_progress``: still running, nothing to do.
          - ``skipped_unexpected``: Celery state outside the known
            vocabulary (a typo in a custom state, a compatibility break
            on upgrade, …) — not reconciled, but visible in the counter
            so operators see the symptom in the Beat health metric.
          - ``errors``: AsyncResult read errors OR persistence errors.
        Good for Sentry metrics and Beat health checks — gives an
        operationally honest signal during DB outages, instead of
        staying green.
    """
    cutoff = datetime.now(timezone.utc) - _STUCK_THRESHOLD
    counters: dict = {
        "reconciled": 0,
        "lost": 0,
        "skipped_in_progress": 0,
        "skipped_unexpected": 0,
        "errors": 0,
    }

    session = SessionLocal()
    try:
        stuck = (
            session.query(QuestionGenerationJob)
            .filter(
                QuestionGenerationJob.status == "PENDING",
                QuestionGenerationJob.created_at < cutoff,
            )
            .all()
        )

        for job in stuck:
            try:
                celery_state = AsyncResult(job.task_id).state
            except Exception as err:
                logger.warning(
                    "Watchdog: failed to read Celery state for task %s: %s",
                    job.task_id,
                    err,
                )
                counters["errors"] += 1
                continue

            if celery_state in _TERMINAL_STATES:
                logger.info(
                    "Watchdog: reconciling task %s — DB=PENDING celery=%s",
                    job.task_id,
                    celery_state,
                )
                if _safe_update_job_status(job.task_id, celery_state):
                    counters["reconciled"] += 1
                else:
                    counters["errors"] += 1
            elif celery_state == "PENDING":
                # Task is lost from the broker — no worker ever saw it,
                # or the result-backend entry expired. Mark FAILURE and
                # mirror the state into the Celery backend, so the
                # WebSocket doesn't wait 120s for the pending timeout.
                logger.warning(
                    "Watchdog: task %s lost from broker (celery=PENDING) — marking FAILURE",
                    job.task_id,
                )
                if _safe_update_job_status(job.task_id, "FAILURE"):
                    _notify_celery_backend_failure(job.task_id)
                    counters["lost"] += 1
                    counters["reconciled"] += 1
                else:
                    counters["errors"] += 1
            elif celery_state in _IN_PROGRESS_STATES:
                # Task is actually still running — leave it alone. If the
                # job is older than the threshold and still PROGRESS,
                # it's slow, but not stuck. Operational visibility via log.
                logger.debug(
                    "Watchdog: task %s still in_progress (celery=%s) — skipping",
                    job.task_id,
                    celery_state,
                )
                counters["skipped_in_progress"] += 1
            else:
                # Unknown state — log defensively, leave it alone, but
                # count it. Without the counter, a gradual drift (e.g. a
                # Celery upgrade introduces a new state, a custom state
                # with a typo) would be invisible to operators — the
                # summary log below wouldn't fire and the watchdog would
                # stay "green".
                logger.warning(
                    "Watchdog: task %s in unexpected celery state %r — skipping",
                    job.task_id,
                    celery_state,
                )
                counters["skipped_unexpected"] += 1

        if (
            counters["reconciled"]
            or counters["lost"]
            or counters["errors"]
            or counters["skipped_unexpected"]
        ):
            logger.info(
                "Watchdog summary: %s",
                counters,
            )
    finally:
        session.close()

    return counters


@celery_app.task(name="tasks.maintenance_tasks.reap_stuck_import_jobs")
def reap_stuck_import_jobs() -> dict[str, int]:
    """Mark ImportJob rows stuck in a non-terminal state as ``failed`` (TF-412).

    The async import endpoint pre-creates a ``queued`` row, enqueues the
    grading task, and returns 202; the polling client waits for a terminal
    status. If the task message is lost (broker blip, misrouted queue, worker
    killed before any DB write), the row would sit ``queued``/``running``
    forever and the client would only ever see its own 5-min poll timeout —
    the DB row itself would never reach a terminal status. This watchdog
    closes that gap by age-failing such rows so the job detail eventually
    shows ``failed`` instead of a perpetual spinner on re-open.

    Age-based on ``created_at`` (not ``started_at``, which is NULL for
    ``queued`` rows). Idempotent: only non-terminal rows past the threshold
    are touched.
    """
    cutoff = datetime.now(timezone.utc) - _IMPORT_STUCK_THRESHOLD
    reaped = 0

    session = SessionLocal()
    try:
        stuck = (
            session.query(ImportJob)
            .filter(
                ImportJob.status.in_(_IMPORT_NON_TERMINAL_STATUSES),
                ImportJob.created_at < cutoff,
            )
            .all()
        )

        for job in stuck:
            prior_status = job.status
            job.status = ImportJobStatus.FAILED.value
            job.finished_at = datetime.now(timezone.utc)
            existing = list(job.error_log or [])
            existing.append(
                {
                    "row_index": 0,
                    "reason": (
                        "Import-Job in nicht-terminalem Status "
                        f"({prior_status!r}) seit über "
                        f"{int(_IMPORT_STUCK_THRESHOLD.total_seconds() // 60)} "
                        "Minuten — vom Watchdog als fehlgeschlagen markiert. "
                        "Mögliche Ursache: verlorene Broker-Nachricht oder "
                        "abgestürzter Worker."
                    ),
                    "step": "reaper",
                }
            )
            job.error_log = existing
            reaped += 1

        if reaped:
            session.commit()
            logger.warning("Reaped %s stuck import_jobs (age-failed)", reaped)
    except Exception:
        logger.exception("reap_stuck_import_jobs failed")
        session.rollback()
    finally:
        session.close()

    return {"reaped": reaped}


@celery_app.task(name="tasks.maintenance_tasks.reap_stuck_moodle_feedback_jobs")
def reap_stuck_moodle_feedback_jobs() -> dict[str, int]:
    """Age-fail MoodleFeedbackPushJob rows stuck non-terminal (TF-435).

    Mirror of ``reap_stuck_import_jobs`` for the outbound feedback push. A push
    job is pre-created ``queued`` and flipped ``processing`` by the worker; if
    the task message is lost or the worker dies before the terminal write, the
    row sits non-terminal forever and the frontend poll (~2 min cap) silently
    shows nothing. Age-based on ``created_at``; idempotent.
    """
    cutoff = datetime.now(timezone.utc) - _MOODLE_PUSH_STUCK_THRESHOLD
    threshold_min = int(_MOODLE_PUSH_STUCK_THRESHOLD.total_seconds() // 60)
    reaped = 0

    session = SessionLocal()
    try:
        stuck = (
            session.query(MoodleFeedbackPushJob)
            .filter(
                MoodleFeedbackPushJob.status.in_(_MOODLE_PUSH_NON_TERMINAL_STATUSES),
                MoodleFeedbackPushJob.created_at < cutoff,
            )
            .all()
        )

        for job in stuck:
            prior_status = job.status
            job.status = MoodleFeedbackPushStatus.FAILED.value
            job.finished_at = datetime.now(timezone.utc)
            error_log = list(job.error_log or [])
            error_log.append(
                {
                    "scope": "job",
                    "reason": (
                        f"Feedback-Push seit über {threshold_min} Minuten in "
                        f"Status {prior_status!r} — vom Watchdog als "
                        "fehlgeschlagen markiert (verlorene Broker-Nachricht "
                        "oder abgestürzter Worker)."
                    ),
                }
            )
            job.error_log = error_log
            reaped += 1

        if reaped:
            session.commit()
            logger.warning(
                "Reaped %s stuck moodle_feedback_push_jobs (age-failed)", reaped
            )
    except Exception:
        logger.exception("reap_stuck_moodle_feedback_jobs failed")
        session.rollback()
    finally:
        session.close()

    return {"reaped": reaped}


# TF-741: matches the hard 30-minute cap on impersonation access tokens.
# Derived from AuthService.IMPERSONATION_TOKEN_EXPIRE_MINUTES rather than
# restated as an independent literal, so the two can't drift apart (review
# fix: they used to be two separately-hardcoded 30s that nothing enforced
# were equal -- a future change to one without the other would make this
# reaper close still-valid sessions early, or leave expired ones open too
# long, either way corrupting the audit picture this task exists to keep
# accurate). The token itself is already unusable once expired (normal 401
# path) -- this is pure DB bookkeeping cleanup for open ImpersonationSession
# rows nobody ended manually, so reporting/audit (TF-742) sees an accurate
# picture.
_IMPERSONATION_STUCK_THRESHOLD = timedelta(minutes=IMPERSONATION_TOKEN_EXPIRE_MINUTES)


@celery_app.task(name="tasks.maintenance_tasks.reap_stuck_impersonation_sessions")
def reap_stuck_impersonation_sessions() -> dict[str, int]:
    """Close ImpersonationSession rows left open past the token's lifetime.

    The impersonation token already stopped working via JWT ``exp`` — this
    task never invalidates anything, it only sets ``ended_at``/
    ``end_reason="timeout"`` on rows nobody called
    ``POST /impersonate/end`` for.

    Uses a single conditional bulk UPDATE (``WHERE ended_at IS NULL``,
    re-evaluated by the DB at write time) rather than SELECT-then-mutate-
    then-commit: a manual ``POST /impersonate/end`` that commits in the gap
    between this task's query and its own commit would otherwise get its
    ``end_reason="manual"`` silently clobbered back to ``"timeout"``
    (TF-741 review fix) -- the bulk UPDATE's WHERE clause excludes any row
    a concurrent commit already closed, so whichever write lands first wins
    cleanly instead of the second blindly overwriting the first.
    """
    cutoff = datetime.now(timezone.utc) - _IMPERSONATION_STUCK_THRESHOLD
    reaped = 0

    session = SessionLocal()
    try:
        reaped = (
            session.query(ImpersonationSession)
            .filter(
                ImpersonationSession.ended_at.is_(None),
                ImpersonationSession.started_at < cutoff,
            )
            .update(
                {
                    "ended_at": datetime.now(timezone.utc),
                    "end_reason": "timeout",
                },
                synchronize_session=False,
            )
        )

        if reaped:
            session.commit()
            logger.warning("Reaped %s stuck impersonation_sessions (timeout)", reaped)
    except Exception:
        logger.exception("reap_stuck_impersonation_sessions failed")
        session.rollback()
        # Nothing was actually persisted on this path -- report 0, not the
        # in-progress count, so a caller/dashboard reading the task result
        # can't mistake a rolled-back attempt for a successful reap
        # (TF-741 review fix).
        reaped = 0
    finally:
        session.close()

    return {"reaped": reaped}
