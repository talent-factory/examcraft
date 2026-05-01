"""Celery wrapper for ``ImportService.commit``.

The synchronous API path runs ``ImportService.commit()`` directly. This
task exposes the same operation for asynchronous callers — backfills,
LLM-graded modes, or large classes that need to run in the background
without holding an HTTP connection open. Migrating an endpoint from
sync to async needs no schema change because the persisted output
(``import_jobs``) is identical either way.

Retry contract: the caller pre-creates the ``ImportJob`` row in
``queued`` status and passes its id. The task reuses that row across
retries so a transient-error retry does not produce duplicate jobs.
On retry exhaustion the task marks the job ``failed`` so the polling
client sees a terminal state instead of a permanently-``running`` row.
"""

from __future__ import annotations

import logging
import traceback
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import DatabaseError, OperationalError

from celery_app import celery_app
from database import SessionLocal
from enums import ImportJobStatus
from models.exam import Exam
from models.submission import ImportJob
from services.import_service import ImportService


logger = logging.getLogger(__name__)


# Retry only on truly transient errors — DB connection drops, deadlock
# retries, transient network blips. Permanent errors (validation,
# unknown driver, integrity violations from real conflicts) must not
# retry, otherwise the same broken CSV burns three retries before the
# operator sees the failure.
_TRANSIENT_ERRORS = (OperationalError, DatabaseError, ConnectionError)


@celery_app.task(
    bind=True,
    name="tasks.import_submissions_task.import_submissions",
    priority=5,
    autoretry_for=_TRANSIENT_ERRORS,
    retry_kwargs={"max_retries": 2, "countdown": 30},
    acks_late=True,
)
def import_submissions(  # type: ignore[no-untyped-def]
    self,
    *,
    exam_id: int,
    driver_name: str,
    source_text: str,
    import_job_id: int,
    triggered_by: int | None = None,
    source_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Async variant of ``ImportService.commit``.

    Args:
        exam_id: institution-scoped — caller must have already checked
            multi-tenancy.
        driver_name: registered driver (e.g. ``moodle_csv``).
        source_text: CSV as UTF-8 string. Bytes are not accepted because
            Celery serialises args as JSON.
        import_job_id: id of a pre-created ``import_jobs`` row in
            ``queued``/``running`` status. Reused across retries.
        triggered_by: user id for ``import_jobs.triggered_by``.
        source_metadata: optional extra metadata.

    Returns:
        Job summary with id/status/rows_processed/rows_failed.
    """
    db = SessionLocal()
    try:
        exam = db.query(Exam).filter(Exam.id == exam_id).one_or_none()
        if exam is None:
            _mark_terminal_failure(
                db,
                import_job_id,
                ValueError(f"Exam {exam_id} nicht gefunden"),
                step="lookup",
            )
            raise ValueError(f"Exam {exam_id} nicht gefunden")

        job = ImportService(db).commit(
            exam=exam,
            driver_name=driver_name,
            source=source_text,
            triggered_by=triggered_by,
            source_metadata=source_metadata or {},
            import_job_id=import_job_id,
        )

        return {
            "import_job_id": job.id,
            "status": job.status,
            "rows_processed": job.rows_processed,
            "rows_failed": job.rows_failed,
        }
    except _TRANSIENT_ERRORS as exc:
        # Transient — Celery will retry. Only mark terminal-failed when
        # we're out of retries; otherwise leave the row at ``running`` so
        # the next attempt resets it cleanly.
        if self.request.retries >= self.max_retries:
            logger.exception(
                "import_submissions_task exhausted retries for exam_id=%s job_id=%s",
                exam_id,
                import_job_id,
            )
            _mark_terminal_failure(db, import_job_id, exc, step="celery_retry")
        raise
    except Exception as exc:
        # Permanent — mark failed once and propagate.
        logger.exception(
            "import_submissions_task fehlgeschlagen für exam_id=%s job_id=%s",
            exam_id,
            import_job_id,
        )
        _mark_terminal_failure(db, import_job_id, exc, step="task")
        raise
    finally:
        db.close()


def _mark_terminal_failure(
    db, import_job_id: int, exc: Exception, *, step: str
) -> None:
    """Persist a terminal FAILED state on the job row.

    Best-effort: if the DB itself is the problem we cannot record it;
    the stuck-job reaper will clean up later.
    """
    try:
        job = db.query(ImportJob).filter(ImportJob.id == import_job_id).one_or_none()
        if job is None:
            return
        job.status = ImportJobStatus.FAILED.value
        job.finished_at = datetime.now(timezone.utc)
        existing = list(job.error_log or [])
        existing.append(
            {
                "row_index": 0,
                "reason": f"{type(exc).__name__}: {exc}",
                "step": step,
                "exception_type": type(exc).__name__,
                "traceback": "".join(
                    traceback.format_exception(type(exc), exc, exc.__traceback__)
                ),
            }
        )
        job.error_log = existing
        db.commit()
    except Exception:  # noqa: BLE001 — we are already in error path
        logger.exception(
            "Could not mark ImportJob %s as terminal-failed", import_job_id
        )
        db.rollback()
