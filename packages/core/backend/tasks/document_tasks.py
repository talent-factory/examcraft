"""
Celery Tasks for Asynchronous Document Processing
Handles document extraction, RAG embedding, and metadata extraction
"""

from celery import Task
from celery_app import celery_app
from services.docling_service import DoclingService
from services.rag_service import RAGService
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


@celery_app.task(
    bind=True,
    base=DocumentProcessingTask,
    name="tasks.document_tasks.process_document",
    priority=5,
)
def process_document(self, document_id: str, user_id: str) -> Dict[str, Any]:
    """
    Asynchronous document processing with Docling and RAG embedding.

    Args:
        document_id: UUID of the document
        user_id: UUID of the user

    Returns:
        Dict with processing status and metadata
    """
    db = SessionLocal()

    try:
        # 1. Load document from DB
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        # Set status to "processing"
        document.status = DocumentStatus.PROCESSING
        db.commit()

        logger.info(f"Starting Docling processing for {document.filename}")

        # 2. Docling Processing
        docling_service = DoclingService()
        processing_result = docling_service.process_document(
            file_path=document.file_path, filename=document.filename
        )

        # 3. Save metadata
        document.title = processing_result.get("title", document.filename)
        document.metadata = processing_result.get("metadata", {})
        document.content = processing_result.get("content", "")
        document.page_count = processing_result.get("page_count", 0)

        logger.info(f"Docling processing completed for {document_id}")

        # 4. Create RAG embeddings (as sub-task)
        logger.info(f"Creating RAG embeddings for {document_id}")
        rag_service = RAGService()
        chunks = rag_service.chunk_document(
            content=document.content, document_id=document_id
        )

        # Dispatch embedding task
        embedding_task = create_embeddings.apply_async(
            args=[document_id, chunks],
            countdown=5,  # 5 seconds delay
        )

        # 5. Set status to "completed"
        document.status = DocumentStatus.COMPLETED
        document.processing_info = {
            "chunks_created": len(chunks),
            "embedding_task_id": embedding_task.id,
        }
        db.commit()

        logger.info(f"Successfully processed document {document_id}")

        return {
            "success": True,
            "document_id": document_id,
            "title": document.title,
            "chunks": len(chunks),
            "embedding_task_id": embedding_task.id,
        }

    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")

        # Set status to "failed"
        if document:
            document.status = DocumentStatus.FAILED
            document.error_message = str(e)
            db.commit()

        # Retry on temporary errors
        raise self.retry(exc=e, countdown=60)

    finally:
        db.close()


@celery_app.task(name="tasks.rag_tasks.create_embeddings", priority=3)
def create_embeddings(document_id: str, chunks: list) -> Dict[str, Any]:
    """
    Create RAG embeddings for document chunks.

    Args:
        document_id: UUID of the document
        chunks: List of text chunks

    Returns:
        Dict with embedding status
    """
    try:
        rag_service = RAGService()
        rag_service.add_document_chunks(document_id=document_id, chunks=chunks)

        logger.info(f"Successfully created embeddings for {document_id}")

        return {
            "success": True,
            "document_id": document_id,
            "chunks_embedded": len(chunks),
        }

    except Exception as e:
        logger.error(f"Error creating embeddings for {document_id}: {str(e)}")
        raise
