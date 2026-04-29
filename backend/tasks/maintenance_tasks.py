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
from models.question_generation_job import QuestionGenerationJob
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
