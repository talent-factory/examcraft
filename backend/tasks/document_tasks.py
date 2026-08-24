"""
Celery Tasks for Asynchronous Document Processing
Handles document extraction, RAG embedding, and metadata extraction
"""

import asyncio
import logging
from typing import Any, Dict

from celery import Task
from celery.exceptions import Ignore, Reject
from sqlalchemy.exc import IntegrityError, ProgrammingError

from celery_app import celery_app
from database import SessionLocal
from models.document import Document, DocumentStatus
from services.document_service import document_service
from services.document_processors.processor_factory import (
    create_ocr_processor,
    is_ocr_available,
)
from services.quality_assessor import EscalationState
from services.vector_service_factory import get_vector_service
from sqlalchemy.orm.attributes import flag_modified

logger = logging.getLogger(__name__)


class ProgressTask(Task):
    """Base task with progress tracking via Celery update_state"""

    abstract = True

    def update_progress(self, current: int, total: int, message: str = "") -> None:
        """
        Sends a progress update to the Redis result backend.

        Args:
            current: Current step (0-based)
            total: Total number of steps (must be > 0)
            message: Progress message (German)
        """
        if total <= 0:
            logger.error(
                f"update_progress aufgerufen mit total={total} (muss > 0 sein)"
            )
            total = 1
        current = max(0, min(current, total))
        self.update_state(
            state="PROGRESS",
            meta={
                "current": current,
                "total": total,
                "progress": int((current / total) * 100),
                "message": message,
            },
        )


def run_async(coro):
    """Runs an async coroutine inside the synchronous Celery worker.

    Creates a fresh event loop for every call and closes it in the
    finally block. Celery prefork workers are long-lived processes in
    which a reused loop can be left in a half-closed state after a
    raised coroutine and silently hang follow-up tasks (TF-351 symptom).
    Fresh loops eliminate this shared state between tasks and retries.
    """
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def _detect_vector_failure(document, document_id, result):
    """Detects a failed vectorization in the result envelope.

    ``process_document_with_vectors`` marks the document as ERROR on
    vector failures and returns a dict (not None) with
    ``vector_embeddings.error`` — the tasks' ``result is None`` guard
    then does NOT catch it. Without this shared check, the code would
    fall through the quality/escalation branch and report
    ``success=True`` despite ``status="error"`` (TF-364). Kept as a
    helper so ``process_document`` and ``reprocess_document_ocr`` use
    the same detection and don't drift apart.

    Returns:
        ``(error_code, error_message)`` on vector failure, else ``None``.
    """
    vector_error = (
        result.get("vector_embeddings", {}).get("error")
        if isinstance(result, dict)
        else None
    )
    if document.status != DocumentStatus.ERROR and not vector_error:
        return None

    metadata = document.doc_metadata or {}
    error_code = metadata.get("error_code")
    if error_code is None:
        # process_document_with_vectors otherwise always persists a
        # classified code; if it's missing, the ERROR marking came from
        # a different source -> surface that instead of silently
        # defaulting to vectorization_failed.
        error_code = "vectorization_failed"
        logger.warning(
            f"Kein error_code in doc_metadata für {document_id}; "
            f"Default '{error_code}'."
        )
    # Error message as specific as possible: vector error from the
    # result, else error_message, else the cause persisted in
    # doc_metadata — never an empty (None) error envelope.
    error_message = (
        vector_error
        or document.error_message
        or metadata.get("vector_embedding_error")
        or metadata.get("error")
    )
    return error_code, error_message


@celery_app.task(
    bind=True,
    base=ProgressTask,
    name="tasks.document_tasks.process_document",
    priority=5,
    autoretry_for=(Exception,),
    dont_autoretry_for=(
        Ignore,
        Reject,
        ValueError,  # e.g. "Document X not found" — a retry won't find it either
        TypeError,  # programming error
        ImportError,  # deployment problem
        ProgrammingError,  # psycopg2 adapter/DDL error
        IntegrityError,  # FK violation
    ),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    retry_backoff=True,
    retry_jitter=True,
)
def process_document(self, document_id: str, user_id: str) -> Dict[str, Any]:
    """
    Asynchronous document processing with Docling and vector embedding.
    Sends granular progress updates (0-100%) to Redis.

    Args:
        document_id: ID of the document
        user_id: ID of the user

    Returns:
        Dict with processing status and metadata
    """
    db = SessionLocal()
    document = None

    try:
        self.update_progress(0, 10, "Starte Verarbeitung...")

        # 1. Load document from DB
        self.update_progress(1, 10, "Dokument wird geladen...")
        document = db.query(Document).filter(Document.id == int(document_id)).first()
        if not document:
            raise ValueError(f"Dokument {document_id} nicht gefunden")

        logger.info(
            f"Starte Dokumentverarbeitung für {document.original_filename} "
            f"(file_path: {document.file_path}, S3: {document_service.use_s3})"
        )

        self.update_progress(2, 10, "Text wird extrahiert...")
        self.update_progress(3, 10, "Docling-Verarbeitung läuft...")

        # 2. Process document (Docling + vectors)
        self.update_progress(4, 10, "Vektoren werden erstellt...")
        result = run_async(
            document_service.process_document_with_vectors(int(document_id), db)
        )

        if result is None:
            raise ValueError(f"Dokumentverarbeitung fehlgeschlagen für {document_id}")

        self.update_progress(8, 10, "Vektoren werden erstellt...")

        # 3. Reload document from DB
        db.refresh(document)

        # TF-364: vectorization failed -> process_document_with_vectors
        # marked the document as ERROR and returned a dict (not None)
        # with vector_embeddings.error. The None guard above therefore
        # didn't catch it. Return a consistent error envelope instead of
        # falling through the escalation branch (otherwise
        # success=True despite status="error").
        vector_failure = _detect_vector_failure(document, document_id, result)
        if vector_failure is not None:
            error_code, error_message = vector_failure
            logger.error(
                f"Vektorisierung fehlgeschlagen für {document_id} "
                f"(error_code={error_code}); melde success=False."
            )
            return {
                "success": False,
                "document_id": document_id,
                "title": document.original_filename,
                "status": document.status.value,
                "error_code": error_code,
                "error": error_message,
                "extraction": result.get("extraction", {}),
                "vector_embeddings": result.get("vector_embeddings", {}),
            }

        # Quality escalation (TF-360): on a negative verdict, possibly
        # enqueue a separate OCR reprocess job. reprocess_document_ocr
        # itself never escalates further -> structural loop protection.
        info = dict(document.processing_info or {})
        has_verdict = isinstance(result, dict) and "quality" in result
        quality = result.get("quality", {}) if isinstance(result, dict) else {}
        if not has_verdict:
            # No quality verdict (e.g. vectorization failed) -> no
            # escalation, clear marking instead of silently defaulting
            # to 'not_needed'.
            info["escalation"] = "no_verdict"
            logger.warning(
                f"Kein Qualitäts-Verdict für {document_id}; Eskalation übersprungen."
            )
        elif not quality.get("ok", True):
            if is_ocr_available() and not info.get("ocr_attempted"):
                reprocess_document_ocr.apply_async(args=[document_id, user_id])
                info["escalation"] = "queued"
                logger.info(
                    f"OCR-Eskalation eingereiht für {document_id} "
                    f"(reason={quality.get('reason')})"
                )
            elif not is_ocr_available():
                info["escalation"] = "unavailable"
                logger.info(
                    f"OCR-Eskalation nötig, aber OCR nicht verfügbar für {document_id}"
                )
            else:
                # OCR already attempted, quality still insufficient — no
                # further escalation (loop protection). Preserve the
                # existing state (e.g. 'exhausted'/'failed').
                info.setdefault("escalation", "exhausted")
                logger.warning(
                    f"Qualität weiterhin ungenügend nach OCR für {document_id} "
                    f"(reason={quality.get('reason')}); keine weitere Eskalation."
                )
        else:
            info["escalation"] = "not_needed"
        document.processing_info = info
        flag_modified(document, "processing_info")

        # 4. Persist to database
        self.update_progress(9, 10, "In Datenbank speichern...")
        db.commit()

        self.update_progress(10, 10, "Abgeschlossen!")
        logger.info(f"Dokumentverarbeitung erfolgreich: {document_id}")

        return {
            "success": True,
            "document_id": document_id,
            "title": document.original_filename,
            "status": document.status.value,
            "has_vectors": document.has_vectors,
            "extraction": result.get("extraction", {}),
            "vector_embeddings": result.get("vector_embeddings", {}),
        }

    except Exception as e:
        logger.error(
            f"Fehler bei Dokumentverarbeitung {document_id}: {str(e)}", exc_info=True
        )

        if document:
            try:
                document.status = DocumentStatus.ERROR
                document.error_message = str(e)
                db.commit()
            except Exception as db_err:
                logger.error(
                    f"DB-Commit beim Fehler-Status fehlgeschlagen für {document_id}: {db_err}"
                )
                try:
                    db.rollback()
                except Exception as rb_err:
                    logger.error(
                        f"DB-Rollback fehlgeschlagen für {document_id}: {rb_err}"
                    )

        raise  # autoretry_for=(Exception,) on the decorator handles the retry logic

    finally:
        db.close()


# Exceptions the OCR reprocess does NOT auto-retry (terminal on first
# occurrence). Kept as a constant because the except block needs the
# same set to decide whether an error is final and may be persisted as
# escalation='failed'/ERROR — otherwise the decorator and handler would
# drift apart.
_REPROCESS_NON_RETRYABLE = (
    Ignore,
    Reject,
    ValueError,
    TypeError,
    ImportError,
    NotImplementedError,  # core-tier placeholder vector service
    ProgrammingError,
    IntegrityError,
)
REPROCESS_MAX_RETRIES = 2


@celery_app.task(
    bind=True,
    base=ProgressTask,
    name="tasks.document_tasks.reprocess_document_ocr",
    priority=4,
    autoretry_for=(Exception,),
    dont_autoretry_for=_REPROCESS_NON_RETRYABLE,
    retry_kwargs={"max_retries": REPROCESS_MAX_RETRIES, "countdown": 120},
    retry_backoff=True,
    retry_jitter=True,
)
def reprocess_document_ocr(self, document_id: str, user_id: str) -> Dict[str, Any]:
    """Reprocessing with PyMuPDF + Tesseract OCR after a negative quality verdict.

    Enqueued by ``process_document`` when the initial extraction was
    insufficient and OCR is available. Deletes old vectors idempotently,
    reprocesses with OCR, and sets loop-protection flags. Does NOT
    escalate any further itself (exactly one attempt).
    """
    db = SessionLocal()
    document = None

    try:
        self.update_progress(0, 10, "Starte OCR-Neuverarbeitung...")
        document = db.query(Document).filter(Document.id == int(document_id)).first()
        if not document:
            raise ValueError(f"Dokument {document_id} nicht gefunden")

        # 1. Remove old vectors (idempotent) — otherwise stale points with
        #    higher chunk_index values are left behind in Qdrant.
        self.update_progress(2, 10, "Alte Vektoren werden gelöscht...")
        vector_service = get_vector_service()
        try:
            run_async(vector_service.delete_document_chunks(int(document_id)))
        except Exception as delete_err:
            # Distinct context so a vector-deletion error (e.g. Qdrant
            # unreachable) doesn't look like an OCR error in the log.
            logger.error(
                f"Alte Vektoren konnten nicht gelöscht werden für {document_id}: "
                f"{delete_err}. OCR-Neuverarbeitung wird abgebrochen.",
                exc_info=True,
            )
            raise

        # 2. Reprocess with OCR
        self.update_progress(3, 10, "OCR-Verarbeitung läuft...")
        ocr_processor = create_ocr_processor()
        result = run_async(
            document_service.process_document_with_vectors(
                int(document_id), db, processor=ocr_processor
            )
        )
        if result is None:
            raise ValueError(f"OCR-Neuverarbeitung fehlgeschlagen für {document_id}")

        # 3. Set loop-protection and status flags
        db.refresh(document)

        # TF-364 (review): identical vector-error check as in
        # process_document. process_document_with_vectors returns a dict
        # (not None) with vector_embeddings.error on vectorization
        # failures and marks the document as ERROR — the None guard
        # above then doesn't catch it. Without this check, the OCR
        # reprocess would fall into the 'exhausted' quality branch and
        # report success=True despite status="error" (the same bug
        # TF-364 fixed in process_document). Terminal error: no further
        # reprocess (ocr_attempted) and visible in the UI as 'failed'.
        # As in process_document, the vector error is NOT retried again
        # (process_document_with_vectors has already classified it).
        vector_failure = _detect_vector_failure(document, document_id, result)
        if vector_failure is not None:
            error_code, error_message = vector_failure
            info = dict(document.processing_info or {})
            info["ocr_attempted"] = True
            info["processed_with_ocr"] = True
            info["escalation"] = "failed"
            document.processing_info = info
            flag_modified(document, "processing_info")
            db.commit()
            logger.error(
                f"Vektorisierung bei OCR-Neuverarbeitung fehlgeschlagen für "
                f"{document_id} (error_code={error_code}); melde success=False."
            )
            return {
                "success": False,
                "document_id": document_id,
                "status": document.status.value,
                "error_code": error_code,
                "error": error_message,
                "escalation": "failed",
                "quality": result.get("quality", {}),
            }

        quality = result.get("quality", {})
        info = dict(document.processing_info or {})
        info["ocr_attempted"] = True
        info["processed_with_ocr"] = True
        escalation: EscalationState = "completed" if quality.get("ok") else "exhausted"
        info["escalation"] = escalation
        document.processing_info = info
        flag_modified(document, "processing_info")

        self.update_progress(9, 10, "In Datenbank speichern...")
        db.commit()
        self.update_progress(10, 10, "Abgeschlossen!")
        logger.info(f"OCR-Neuverarbeitung erfolgreich: {document_id}")

        return {
            "success": True,
            "document_id": document_id,
            "escalation": info["escalation"],
            "quality": quality,
        }

    except Exception as e:
        logger.error(
            f"Fehler bei OCR-Neuverarbeitung {document_id}: {str(e)}", exc_info=True
        )
        # TF-365 (review): only persist as escalation='failed'/ERROR on a
        # terminal error (no further retry follows). Otherwise the user
        # would see the red 'failed' chip during the retry window
        # (~120s) even though the retry could still succeed. Terminal =
        # not auto-retried OR retries exhausted. On a transient error,
        # the queued/PROCESSING state remains and the reprocessing
        # indicator stays visible.
        terminal = isinstance(e, _REPROCESS_NON_RETRYABLE) or (
            self.request.retries >= REPROCESS_MAX_RETRIES
        )
        if document and terminal:
            try:
                info = dict(document.processing_info or {})
                info["ocr_attempted"] = True
                info["escalation"] = "failed"
                document.processing_info = info
                flag_modified(document, "processing_info")
                document.status = DocumentStatus.ERROR
                document.error_message = str(e)
                db.commit()
            except Exception as db_err:
                logger.error(
                    f"DB-Commit beim Fehler-Status fehlgeschlagen für {document_id}: {db_err}"
                )
                try:
                    db.rollback()
                except Exception as rb_err:
                    logger.error(
                        f"DB-Rollback fehlgeschlagen für {document_id}: {rb_err}"
                    )
        elif document:
            logger.info(
                f"OCR-Neuverarbeitung für {document_id} fehlgeschlagen "
                f"(Versuch {self.request.retries + 1}/{REPROCESS_MAX_RETRIES + 1}); "
                f"Retry folgt, Status/Eskalation bleiben unverändert."
            )
        raise

    finally:
        db.close()
