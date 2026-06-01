"""
Celery Tasks for RAG (Retrieval-Augmented Generation) Operations
Handles vector embedding and semantic search indexing
"""

from __future__ import annotations

from celery_app import celery_app
from database import SessionLocal
from models.document import Document
from typing import Dict, Any, List, Literal
import logging

logger = logging.getLogger(__name__)

# Geschlossene Wertemenge für das ``status``-Feld des reindex-Result-Envelopes
# (TF-370). Als Literal getypt, damit Tippfehler an Schreib-/Lesestellen
# statisch auffallen statt erst im Consumer zu einem stillen Mismatch zu werden.
ReindexStatus = Literal["reindexed", "deferred", "not_found"]


@celery_app.task(name="tasks.rag_tasks.create_embeddings", priority=3, max_retries=3)
def create_embeddings(document_id: str, chunks: List[str]) -> Dict[str, Any]:
    """
    Create RAG embeddings for document chunks.

    This task is called after document processing to create vector embeddings
    for semantic search and RAG retrieval.

    Args:
        document_id: UUID of the document
        chunks: List of text chunks to embed

    Returns:
        Dict with embedding status and statistics
    """
    db = SessionLocal()
    # Vor dem try binden: schlägt die Query unten fehl (z. B. DB nicht
    # erreichbar), referenziert der except-Block `document` sonst ungebunden
    # (UnboundLocalError) und verdeckt den eigentlichen Fehler.
    document = None

    try:
        # Verify document exists
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        logger.info(
            f"Starting RAG embedding for {document_id} with {len(chunks)} chunks"
        )

        # Create embeddings
        from services.rag_service import RAGService

        rag_service = RAGService()
        rag_service.add_document_chunks(document_id=document_id, chunks=chunks)

        # Update document with embedding info
        document.embedding_status = "completed"
        document.chunks_count = len(chunks)
        db.commit()

        logger.info(f"Successfully created embeddings for {document_id}")

        return {
            "success": True,
            "document_id": document_id,
            "chunks_embedded": len(chunks),
            "status": "completed",
        }

    except Exception as e:
        logger.error(f"Error creating embeddings for {document_id}: {str(e)}")

        # Persist the failure status, but guard the commit: the original
        # exception may have poisoned the transaction (common for
        # SQLAlchemyError). An unguarded commit here would raise a *second*
        # exception that replaces the real one in the traceback and hides the
        # root cause in Sentry. Roll back first, then write + commit the status
        # in its own try (same pattern as document_service vector-error path).
        if document is not None:
            try:
                db.rollback()
                document.embedding_status = "failed"
                document.embedding_error = str(e)
                db.commit()
            except Exception as commit_err:
                db.rollback()
                logger.error(
                    "Failed to persist embedding-failure status for %s: %s",
                    document_id,
                    commit_err,
                )

        raise

    finally:
        db.close()


@celery_app.task(name="tasks.rag_tasks.update_embeddings", priority=2, max_retries=2)
def update_embeddings(document_id: str) -> Dict[str, Any]:
    """
    Update existing embeddings for a document.

    Used when document content is modified and embeddings need to be refreshed.

    Args:
        document_id: UUID of the document

    Returns:
        Dict with update status
    """
    db = SessionLocal()

    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        logger.info(f"Updating embeddings for {document_id}")

        # Delete old embeddings
        from services.rag_service import RAGService

        rag_service = RAGService()
        rag_service.delete_document_embeddings(document_id)

        # Create new embeddings
        chunks = rag_service.chunk_document(
            content=document.content, document_id=document_id
        )

        rag_service.add_document_chunks(document_id=document_id, chunks=chunks)

        document.embedding_status = "updated"
        db.commit()

        logger.info(f"Successfully updated embeddings for {document_id}")

        return {
            "success": True,
            "document_id": document_id,
            "chunks_updated": len(chunks),
        }

    except Exception as e:
        logger.error(f"Error updating embeddings for {document_id}: {str(e)}")
        raise

    finally:
        db.close()


@celery_app.task(name="tasks.rag_tasks.delete_embeddings", priority=1)
def delete_embeddings(document_id: str) -> Dict[str, Any]:
    """
    Delete embeddings for a document.

    Called when a document is deleted.

    Args:
        document_id: UUID of the document

    Returns:
        Dict with deletion status
    """
    try:
        logger.info(f"Deleting embeddings for {document_id}")

        from services.rag_service import RAGService

        rag_service = RAGService()
        rag_service.delete_document_embeddings(document_id)

        logger.info(f"Successfully deleted embeddings for {document_id}")

        return {"success": True, "document_id": document_id, "status": "deleted"}

    except Exception as e:
        logger.error(f"Error deleting embeddings for {document_id}: {str(e)}")
        raise


def _reindex_document_payload(document: "Document") -> bool:
    """Re-upload the document's vector payload to Qdrant with the current
    institution_id.

    STUB (TF-352): not yet implemented. The real upsert needs the RAG team
    to confirm the correct API and payload shape (see services/rag_service.py
    add_document_chunks and services/docs_indexer_service.py for existing
    upsert patterns). Until then, this raises NotImplementedError so the
    caller (`reindex_document_to_institution`) can leave `pending_reindex=True`
    as a truthful marker rather than falsely claim Qdrant was updated.
    """
    raise NotImplementedError(
        f"Qdrant re-index not yet implemented for document {document.id} "
        f"(institution_id={document.institution_id}); pending_reindex remains True. "
        f"See TF-352 follow-up."
    )


@celery_app.task(
    name="tasks.rag_tasks.reindex_document_to_institution",
    priority=3,
    max_retries=3,
    default_retry_delay=30,
)
def reindex_document_to_institution(document_id: int) -> "dict[str, object]":
    """Re-index a document in Qdrant with its current institution_id (TF-352).

    Triggered after a SuperAdmin transfers a user with documents. On success,
    clears `documents.pending_reindex`.

    Returns a structured result whose ``status`` field disambiguates the
    three non-raising outcomes (TF-370) — previously two of them returned a
    bare ``None``, so a caller could not tell "reindex still deferred" from
    "document no longer exists":

    * ``{"status": "reindexed", "document_id": ..., "institution_id": ...}``
      — payload re-indexed and ``pending_reindex`` cleared.
    * ``{"status": "deferred", "document_id": ...}`` — the Qdrant upsert stub
      raised ``NotImplementedError``; ``pending_reindex`` stays True so a
      future implementation / operator tool can pick the document up.
    * ``{"status": "not_found", "document_id": ...}`` — the document is gone
      (e.g. the transfer was rolled back after dispatch).

    On any other exception, rolls back and re-raises so Celery's retry
    handles transient failures (Qdrant outage, broker hiccup) per the
    decorator's max_retries.
    """
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc is None:
            logger.warning(
                "reindex_document_to_institution: document %s not found "
                "(transfer rolled back?)",
                document_id,
            )
            return {"document_id": document_id, "status": "not_found"}

        try:
            _reindex_document_payload(doc)
        except NotImplementedError as exc:
            # Stub is still in place — document remains marked for reindex.
            # Logged at ERROR (not WARNING) so the Sentry logging integration
            # captures it and on-call is actually alerted: a deferred reindex
            # leaves the document's Qdrant payload pointing at the *old*
            # institution_id (cross-tenant search-visibility gap) until a manual
            # reindex runs. There is no automatic sweeper today (TF-352 follow-up).
            logger.error(
                "Document %s pending_reindex stays True — Qdrant upsert stub "
                "still active. %s",
                document_id,
                exc,
            )
            return {"document_id": document_id, "status": "deferred"}

        doc.pending_reindex = False
        db.commit()

        logger.info(
            "Document %s re-indexed to institution %s",
            document_id,
            doc.institution_id,
        )
        return {
            "document_id": document_id,
            "institution_id": doc.institution_id,
            "status": "reindexed",
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
