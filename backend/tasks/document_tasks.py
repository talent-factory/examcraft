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
    """Base Task mit Progress-Tracking via Celery update_state"""

    abstract = True

    def update_progress(self, current: int, total: int, message: str = "") -> None:
        """
        Sendet Progress-Update an Redis Result Backend.

        Args:
            current: Aktueller Schritt (0-based)
            total: Gesamtanzahl Schritte (muss > 0 sein)
            message: Deutsche Fortschrittsmessage
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
    """Führt eine async Coroutine im synchronen Celery Worker aus.

    Erstellt für jeden Aufruf einen frischen Event-Loop und schliesst ihn
    im finally-Block. Celery prefork-Worker sind langlebige Prozesse, in
    denen ein wiederverwendeter Loop nach einer geworfenen Coroutine in
    einem halb-geschlossenen Zustand zurückbleiben und Folge-Tasks
    silently hängen lassen kann (TF-351-Symptom). Frische Loops eliminieren
    diesen geteilten Zustand zwischen Tasks und Retries.
    """
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


@celery_app.task(
    bind=True,
    base=ProgressTask,
    name="tasks.document_tasks.process_document",
    priority=5,
    autoretry_for=(Exception,),
    dont_autoretry_for=(
        Ignore,
        Reject,
        ValueError,  # z. B. "Dokument X nicht gefunden" — Retry findet es auch nicht
        TypeError,  # Programmierfehler
        ImportError,  # Deployment-Problem
        ProgrammingError,  # psycopg2-Adapter-/DDL-Fehler
        IntegrityError,  # FK-Verletzung
    ),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    retry_backoff=True,
    retry_jitter=True,
)
def process_document(self, document_id: str, user_id: str) -> Dict[str, Any]:
    """
    Asynchrone Dokumentverarbeitung mit Docling und Vector Embedding.
    Sendet granulare Progress-Updates (0-100%) an Redis.

    Args:
        document_id: ID des Dokuments
        user_id: ID des Users

    Returns:
        Dict mit Verarbeitungsstatus und Metadaten
    """
    db = SessionLocal()
    document = None

    try:
        self.update_progress(0, 10, "Starte Verarbeitung...")

        # 1. Dokument aus DB laden
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

        # 2. Dokument verarbeiten (Docling + Vektoren)
        self.update_progress(4, 10, "Vektoren werden erstellt...")
        result = run_async(
            document_service.process_document_with_vectors(int(document_id), db)
        )

        if result is None:
            raise ValueError(f"Dokumentverarbeitung fehlgeschlagen für {document_id}")

        self.update_progress(8, 10, "Vektoren werden erstellt...")

        # 3. Dokument aus DB neu laden
        db.refresh(document)

        # TF-364: Vektorisierung fehlgeschlagen -> process_document_with_vectors
        # hat das Dokument als ERROR markiert und ein dict (kein None) mit
        # vector_embeddings.error zurückgegeben. Der None-Guard oben griff daher
        # nicht. Konsistentes Fehler-Envelope zurückgeben statt durch den
        # Eskalations-Zweig zu fallen (sonst success=True bei status="error").
        vector_error = (
            result.get("vector_embeddings", {}).get("error")
            if isinstance(result, dict)
            else None
        )
        if document.status == DocumentStatus.ERROR or vector_error:
            metadata = document.doc_metadata or {}
            error_code = metadata.get("error_code")
            if error_code is None:
                # process_document_with_vectors persistiert sonst immer einen
                # klassifizierten Code; fehlt er, stammt die ERROR-Markierung aus
                # einer anderen Quelle -> sichtbar machen statt still als
                # vectorization_failed zu defaulten.
                error_code = "vectorization_failed"
                logger.warning(
                    f"Kein error_code in doc_metadata für {document_id}; "
                    f"Default '{error_code}'."
                )
            # Fehlermeldung möglichst spezifisch: Vektor-Fehler aus dem Result,
            # sonst error_message, sonst die in doc_metadata persistierte Ursache —
            # nie ein leeres (None) Fehler-Envelope.
            error_message = (
                vector_error
                or document.error_message
                or metadata.get("vector_embedding_error")
                or metadata.get("error")
            )
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

        # Qualitäts-Eskalation (TF-360): bei negativem Verdict ggf. einen
        # separaten OCR-Reprocess-Job einreihen. reprocess_document_ocr selbst
        # eskaliert nie weiter -> struktureller Loop-Schutz.
        info = dict(document.processing_info or {})
        has_verdict = isinstance(result, dict) and "quality" in result
        quality = result.get("quality", {}) if isinstance(result, dict) else {}
        if not has_verdict:
            # Kein Qualitäts-Verdict (z. B. Vektorisierung fehlgeschlagen) ->
            # keine Eskalation, klare Markierung statt stillem 'not_needed'.
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
                # OCR bereits versucht, Qualität weiterhin ungenügend — keine
                # weitere Eskalation (Loop-Schutz). Bestehenden Zustand
                # (z. B. 'exhausted'/'failed') bewahren.
                info.setdefault("escalation", "exhausted")
                logger.warning(
                    f"Qualität weiterhin ungenügend nach OCR für {document_id} "
                    f"(reason={quality.get('reason')}); keine weitere Eskalation."
                )
        else:
            info["escalation"] = "not_needed"
        document.processing_info = info
        flag_modified(document, "processing_info")

        # 4. In Datenbank speichern
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

        raise  # autoretry_for=(Exception,) auf dem Decorator übernimmt die Retry-Logik

    finally:
        db.close()


# Exceptions, die der OCR-Reprocess NICHT auto-retried (terminal beim ersten
# Auftreten). Als Konstante geführt, weil der except-Block dieselbe Menge braucht,
# um zu entscheiden, ob ein Fehler endgültig ist und als escalation='failed'/ERROR
# persistiert werden darf — sonst driften Decorator und Handler auseinander.
_REPROCESS_NON_RETRYABLE = (
    Ignore,
    Reject,
    ValueError,
    TypeError,
    ImportError,
    NotImplementedError,  # Core-Tier-Placeholder-Vektorservice
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
    """Neuverarbeitung mit PyMuPDF + Tesseract-OCR nach negativem Qualitäts-Verdict.

    Eingereiht durch ``process_document``, wenn die Erst-Extraktion ungenügend
    war und OCR verfügbar ist. Löscht alte Vektoren idempotent, verarbeitet mit
    OCR neu und setzt Loop-Schutz-Flags. Eskaliert selbst NICHT weiter (genau ein
    Versuch).
    """
    db = SessionLocal()
    document = None

    try:
        self.update_progress(0, 10, "Starte OCR-Neuverarbeitung...")
        document = db.query(Document).filter(Document.id == int(document_id)).first()
        if not document:
            raise ValueError(f"Dokument {document_id} nicht gefunden")

        # 1. Alte Vektoren entfernen (idempotent) — sonst bleiben stale Points
        #    mit höheren chunk_index-Werten in Qdrant zurück.
        self.update_progress(2, 10, "Alte Vektoren werden gelöscht...")
        vector_service = get_vector_service()
        try:
            run_async(vector_service.delete_document_chunks(int(document_id)))
        except Exception as delete_err:
            # Distinkter Kontext, damit ein Vektor-Lösch-Fehler (z. B. Qdrant
            # nicht erreichbar) im Log nicht wie ein OCR-Fehler aussieht.
            logger.error(
                f"Alte Vektoren konnten nicht gelöscht werden für {document_id}: "
                f"{delete_err}. OCR-Neuverarbeitung wird abgebrochen.",
                exc_info=True,
            )
            raise

        # 2. Mit OCR neu verarbeiten
        self.update_progress(3, 10, "OCR-Verarbeitung läuft...")
        ocr_processor = create_ocr_processor()
        result = run_async(
            document_service.process_document_with_vectors(
                int(document_id), db, processor=ocr_processor
            )
        )
        if result is None:
            raise ValueError(f"OCR-Neuverarbeitung fehlgeschlagen für {document_id}")

        # 3. Loop-Schutz- und Status-Flags setzen
        db.refresh(document)
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
        # TF-365 (Review): Nur bei terminalem Fehler (kein weiterer Retry folgt) als
        # escalation='failed'/ERROR persistieren. Sonst sähe der Nutzer im
        # Retry-Fenster (~120 s) den roten 'failed'-Chip, obwohl der Retry noch
        # erfolgreich werden kann. Terminal = nicht auto-retried ODER Retries
        # erschöpft. Bei transientem Fehler bleibt der queued/PROCESSING-Zustand
        # bestehen und der Reprocessing-Hinweis weiter sichtbar.
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
