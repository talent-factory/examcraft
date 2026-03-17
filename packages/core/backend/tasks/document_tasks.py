"""
Celery Tasks for Asynchronous Document Processing
Handles document extraction, RAG embedding, and metadata extraction
"""

import asyncio
from celery import Task
from celery_app import celery_app
from services.document_service import document_service
from models.document import Document, DocumentStatus
from database import SessionLocal
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class ProgressTask(Task):
    """Base Task mit Progress-Tracking via Celery update_state"""

    abstract = True

    def update_progress(self, current: int, total: int, message: str = "") -> None:
        """
        Sendet Progress-Update an Redis Result Backend.

        Args:
            current: Aktueller Schritt (0-based)
            total: Gesamtanzahl Schritte
            message: Deutsche Fortschrittsmessage
        """
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
    """Helper to run async code in sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(
    bind=True,
    base=ProgressTask,
    name="tasks.document_tasks.process_document",
    priority=5,
    autoretry_for=(Exception,),
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
            "docling_processing": result.get("docling_processing", {}),
            "vector_embeddings": result.get("vector_embeddings", {}),
        }

    except Exception as e:
        logger.error(f"Fehler bei Dokumentverarbeitung {document_id}: {str(e)}")

        if document:
            document.status = DocumentStatus.ERROR
            document.error_message = str(e)
            db.commit()

        raise self.retry(exc=e, countdown=60)

    finally:
        db.close()


# Hinweis: create_embeddings wurde entfernt — Vector Embedding wird direkt
# in document_service.process_document_with_vectors() behandelt
