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


class DocumentProcessingTask(Task):
    """Base Task with retry logic and error handling"""

    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 60}
    retry_backoff = True
    retry_jitter = True


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
    base=DocumentProcessingTask,
    name="tasks.document_tasks.process_document",
    priority=5,
)
def process_document(self, document_id: str, user_id: str) -> Dict[str, Any]:
    """
    Asynchronous document processing with Docling and Vector embedding.

    Args:
        document_id: ID of the document
        user_id: ID of the user

    Returns:
        Dict with processing status and metadata
    """
    db = SessionLocal()
    document = None

    try:
        # 1. Load document from DB
        document = db.query(Document).filter(Document.id == int(document_id)).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        logger.info(
            f"Starting document processing for {document.filename} "
            f"(file_path: {document.file_path}, S3: {document_service.use_s3})"
        )

        # 2. Process document with vectors using document_service
        # This handles: Docling processing + Vector embedding creation
        result = run_async(
            document_service.process_document_with_vectors(int(document_id), db)
        )

        if result is None:
            raise ValueError(f"Document processing failed for {document_id}")

        # Refresh document to get updated values
        db.refresh(document)

        logger.info(f"Successfully processed document {document_id}")

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
        logger.error(f"Error processing document {document_id}: {str(e)}")

        # Set status to "error"
        if document:
            document.status = DocumentStatus.ERROR
            document.error_message = str(e)
            db.commit()

        # Retry on temporary errors
        raise self.retry(exc=e, countdown=60)

    finally:
        db.close()


# Note: create_embeddings task removed - vector embedding is now handled
# directly in document_service.process_document_with_vectors()
