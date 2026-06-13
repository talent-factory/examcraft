"""Periodic maintenance tasks (TF-329 Watchdog).

`reconcile_stuck_jobs` läuft alle 5 Minuten via Celery Beat und gleicht
QuestionGenerationJob-Zeilen mit dem echten Celery-State aus dem Result-Backend
ab. Adressiert das Phantom-PENDING-Symptom aus dem Demo-Vorfall am 2026-04-28
auf einer dritten Verteidigungslinie nach TF-325 (Retry-Loop) und TF-326
(API-Endpoint-Reconcile).
"""

import logging
from datetime import datetime, timedelta, timezone

from celery.result import AsyncResult

from celery_app import celery_app
from database import SessionLocal
from enums import ImportJobStatus
from models.question_generation_job import QuestionGenerationJob
from models.submission import ImportJob
from tasks.question_tasks import _safe_update_job_status

logger = logging.getLogger(__name__)


# Stuck-Threshold: ein PENDING-Job, der älter ist als das, gilt als reconcile-bedürftig.
# Worst-case Retry-Chain in question_tasks.generate_questions_task:
#   max_retries=4, retry_backoff=30, retry_backoff_max=300, retry_jitter=True
# → kumulative Backoff-Summe bis zur letzten Ausführung erreicht ~20 Min.
# Plus task_soft_time_limit=3300 s greift erst bei langen Generations-Calls.
# 25 Min Schwelle räumt aktiv-retrygenden Tasks Luft, damit der Watchdog
# nicht prematur eine FAILURE setzt, die ein nachfolgender Retry mit SUCCESS
# überschreibt (Status-Flicker im UI).
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

# In-Progress-States, die der Watchdog NICHT anfasst — die Tasks laufen tatsächlich.
_IN_PROGRESS_STATES = frozenset({"PROGRESS", "STARTED", "RETRY"})

# Terminal-States, die der Watchdog 1:1 in die DB nachzieht.
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
    """Reconcile DB-Status für stuck PENDING-Jobs gegen Celerys Result-Backend.

    Returns:
        dict mit Counters:
        ``{reconciled, lost, skipped_in_progress, skipped_unexpected, errors}``.
        Counter-Semantik:
          - ``reconciled``: tatsächliche DB-Status-Updates, die persistiert wurden.
          - ``lost``: Untermenge von ``reconciled`` für broker-verlorene Jobs.
          - ``skipped_in_progress``: läuft noch, nichts zu tun.
          - ``skipped_unexpected``: Celery-State ausserhalb des bekannten Vokabulars
            (Tippfehler in einem custom State, kompatibilitätsbruch beim Upgrade,
            …) — nicht reconciled, aber sichtbar im Counter, damit Operatoren
            das Symptom in der Beat-Health-Metrik sehen.
          - ``errors``: AsyncResult-Read-Fehler ODER persistierungs-Fehler.
        Gut für Sentry-Metriken und Beat-Health-Checks — gibt operatorisch
        ehrliches Signal bei DB-Outages, statt grün zu bleiben.
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
                # Task ist im Broker verloren — kein Worker hat ihn jemals gesehen,
                # oder der Result-Backend-Eintrag ist abgelaufen. Markiere FAILURE
                # und spiegele den State ins Celery-Backend, damit der WebSocket
                # nicht 120 s auf den Pending-Timeout wartet.
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
                # Task läuft tatsächlich noch — nicht anfassen. Wenn der Job
                # älter als der Threshold ist und immer noch PROGRESS, dann ist
                # er langsam, aber nicht stuck. Operations-Visibility via Log.
                logger.debug(
                    "Watchdog: task %s still in_progress (celery=%s) — skipping",
                    job.task_id,
                    celery_state,
                )
                counters["skipped_in_progress"] += 1
            else:
                # Unbekannter State — defensiv loggen, nicht anfassen, aber
                # zählen. Ohne Counter wäre eine schleichende Drift (z. B.
                # Celery-Upgrade führt einen neuen State ein, custom State
                # mit Tippfehler) für Operatoren unsichtbar — der Summary-Log
                # unten würde nicht feuern und der Watchdog "grün" bleiben.
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
