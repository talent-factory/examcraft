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
# 10 Minuten ist großzügig genug, um kurze Generierungen (typisch 1-2 Minuten) und
# das normale 4-Versuche-Retry-Fenster (~17 s) nicht unnötig anzufassen, aber knapp
# genug, dass Phantom-PENDING-Jobs nicht stundenlang in der DB bleiben.
_STUCK_THRESHOLD = timedelta(minutes=10)

# In-Progress-States, die der Watchdog NICHT anfasst — die Tasks laufen tatsächlich.
_IN_PROGRESS_STATES = frozenset({"PROGRESS", "STARTED", "RETRY"})

# Terminal-States, die der Watchdog 1:1 in die DB nachzieht.
_TERMINAL_STATES = frozenset({"SUCCESS", "FAILURE", "REVOKED"})


@celery_app.task(name="tasks.maintenance_tasks.reconcile_stuck_jobs")
def reconcile_stuck_jobs() -> dict:
    """Reconcile DB-Status für stuck PENDING-Jobs gegen Celerys Result-Backend.

    Returns:
        dict mit Counters: ``{reconciled, lost, skipped_in_progress, errors}``.
        Gut für Sentry-Metriken und Beat-Health-Checks.
    """
    cutoff = datetime.now(timezone.utc) - _STUCK_THRESHOLD
    counters: dict = {"reconciled": 0, "lost": 0, "skipped_in_progress": 0}

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
                counters["errors"] = counters.get("errors", 0) + 1
                continue

            if celery_state in _TERMINAL_STATES:
                logger.info(
                    "Watchdog: reconciling task %s — DB=PENDING celery=%s",
                    job.task_id,
                    celery_state,
                )
                _safe_update_job_status(job.task_id, celery_state)
                counters["reconciled"] += 1
            elif celery_state == "PENDING":
                # Task ist im Broker verloren — kein Worker hat ihn jemals gesehen,
                # oder der Result-Backend-Eintrag ist abgelaufen. Markiere FAILURE.
                logger.warning(
                    "Watchdog: task %s lost from broker (celery=PENDING) — marking FAILURE",
                    job.task_id,
                )
                _safe_update_job_status(job.task_id, "FAILURE")
                counters["lost"] += 1
                counters["reconciled"] += 1
            elif celery_state in _IN_PROGRESS_STATES:
                # Task läuft tatsächlich noch — nicht anfassen. Wenn der Job
                # älter als 10 min ist und immer noch PROGRESS, dann ist er
                # langsam, aber nicht stuck. Operations-Visibility via Log.
                logger.debug(
                    "Watchdog: task %s still in_progress (celery=%s) — skipping",
                    job.task_id,
                    celery_state,
                )
                counters["skipped_in_progress"] += 1
            else:
                # Unbekannter State — defensiv loggen, nicht anfassen.
                logger.warning(
                    "Watchdog: task %s in unexpected celery state %r — skipping",
                    job.task_id,
                    celery_state,
                )

        if counters["reconciled"] or counters["lost"]:
            logger.info(
                "Watchdog summary: %s",
                counters,
            )
    finally:
        session.close()

    return counters
