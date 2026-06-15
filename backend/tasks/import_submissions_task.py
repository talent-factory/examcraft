"""Celery task that runs ``ImportService.commit`` off the request thread.

Since TF-412 this is the *only* execution path for result imports: the
HTTP endpoints (``/import/commit``, ``/import/api-commit``) validate the
upload synchronously, create a ``queued`` ImportJob, then dispatch this
task to persist attempts and — for open-ended questions — run serial LLM
grading in the background, so the request never blocks on grading. The
persisted output (``import_jobs``) is identical to the former inline
path, so the sync→async move needed no schema change.

Retry contract: the caller pre-creates the ``ImportJob`` row in
``queued`` status and passes its id. The task reuses that row across
retries so a transient-error retry does not produce duplicate jobs.
On retry exhaustion the task marks the job ``failed`` so the polling
client sees a terminal state instead of a permanently-``running`` row.
"""

from __future__ import annotations

import base64
import binascii
import logging
import traceback
from datetime import datetime, timezone
from typing import Any, NewType

from sqlalchemy.exc import DatabaseError, OperationalError

from celery_app import celery_app
from database import SessionLocal
from enums import ImportJobStatus
from models.exam import Exam
from models.submission import ImportJob
from services.import_service import ImportService


logger = logging.getLogger(__name__)

# Documents that this str is base64-encoded raw upload bytes, not arbitrary
# text — distinguishing the two at the type level the way ``secret_encryption``
# separates ciphertext from plaintext. NewType is erased at runtime; the real
# guard against a mis-encoded payload is ``b64decode(..., validate=True)`` below
# (Celery's JSON kwargs are untyped, so this can't be enforced across the wire).
Base64Str = NewType("Base64Str", str)


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
    # max_retries is set at task level *and* in retry_kwargs so the two agree:
    # autoretry reads retry_kwargs, but the manual exhaustion check below reads
    # ``self.max_retries`` (the task attribute, which otherwise defaults to 3).
    # If they diverge, ``retries >= self.max_retries`` never trips before
    # Celery aborts and the terminal-failure branch becomes dead code.
    max_retries=2,
    retry_kwargs={"max_retries": 2, "countdown": 30},
    acks_late=True,
    # TF-428: per-task cap well below the global 3600s. Free-text grading now
    # runs in parallel, so a healthy import finishes in minutes; if one runs
    # long enough to hit soft_time_limit a SoftTimeLimitExceeded is raised and
    # handled like any other failure (terminal FAILED, pollable), instead of a
    # genuine hang holding a worker slot for the full hour. 1500/1800s aligns
    # with the 30-min reap_stuck_import_jobs threshold.
    soft_time_limit=1500,
    time_limit=1800,
)
def import_submissions(  # type: ignore[no-untyped-def]
    self,
    *,
    exam_id: int,
    driver_name: str,
    source_b64: Base64Str,
    import_job_id: int,
    triggered_by: int | None = None,
    source_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Async variant of ``ImportService.commit``.

    Args:
        exam_id: institution-scoped — caller must have already checked
            multi-tenancy.
        driver_name: registered driver (e.g. ``moodle_csv``).
        source_b64: base64 of the *raw* upload bytes. Celery serialises args
            as JSON, so raw bytes cannot be passed directly; base64 round-trips
            them losslessly. The task decodes back to ``bytes`` and hands the
            driver the exact original bytes — keeping grading identical to the
            synchronous path and letting the CSV driver's own encoding
            detection run on the original bytes (its utf-8-sig → utf-8 →
            cp1252 → latin-1 cascade). Pre-decoding to ``str`` here would
            force one encoding before the driver sees the file and skip that
            detection. (``moodle_api`` accepts either bytes or str, so this
            matters for the ``moodle_csv`` path.)
        import_job_id: id of a pre-created ``import_jobs`` row in
            ``queued``/``running`` status. Reused across retries.
        triggered_by: user id for ``import_jobs.triggered_by``.
        source_metadata: optional extra metadata.

    Returns:
        Job summary with id/status/rows_processed/rows_failed.
    """
    try:
        source = base64.b64decode(source_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        # Malformed payload — permanent, do not retry. Mark the job failed so
        # the polling client sees a terminal state.
        db = SessionLocal()
        try:
            _mark_terminal_failure(db, import_job_id, exc, step="decode")
        finally:
            db.close()
        raise

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
            source=source,
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
        # Transient — Celery will retry. ``ImportService.commit`` has already
        # marked the row ``failed`` (its own except handler committed before
        # re-raising), and the next retry resets it to ``running`` in place
        # via ``import_job_id`` — so we only need to record a *terminal*
        # failure once retries are exhausted, to stop a transient blip from
        # masquerading as a permanent failure on every attempt.
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

    Best-effort: if the DB itself is the problem we cannot record it here.
    The periodic ``reap_stuck_import_jobs`` watchdog (Celery Beat, every
    5 min) age-fails any row left in ``queued``/``running``, so the job
    still converges on a terminal status even if this write is lost.
    """
    try:
        job = db.query(ImportJob).filter(ImportJob.id == import_job_id).one_or_none()
        if job is None:
            logger.error(
                "_mark_terminal_failure: ImportJob %s not found — "
                "failure cannot be persisted.",
                import_job_id,
            )
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
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            logger.warning("Rollback also failed for ImportJob %s", import_job_id)
