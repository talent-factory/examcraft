"""
Tests for Celery async task processing
"""

import sys
from unittest.mock import MagicMock

# Mock system-level dependencies before any project imports
if "magic" not in sys.modules:
    sys.modules["magic"] = MagicMock()

import pytest
from unittest.mock import patch, MagicMock
from tasks.document_tasks import process_document
from tasks.rag_tasks import create_embeddings
from models.document import Document, DocumentStatus


class TestDocumentProcessingTask:
    """Test async document processing with Celery"""

    def test_process_document_task_success(self):
        """Test successful document processing"""
        with (
            patch("tasks.document_tasks.SessionLocal") as mock_session_local,
            patch("tasks.document_tasks.document_service"),
            patch("tasks.document_tasks.run_async") as mock_run_async,
        ):
            # Setup mocks
            mock_db = MagicMock()
            mock_session_local.return_value = mock_db

            mock_document = MagicMock(spec=Document)
            mock_document.id = 1
            mock_document.original_filename = "test.pdf"
            mock_document.file_path = "/path/to/test.pdf"
            mock_document.status = DocumentStatus.PROCESSING
            mock_document.has_vectors = True

            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_document
            )

            # Mock document_service.process_document_with_vectors
            mock_run_async.return_value = {
                "docling_processing": {"pages": 10},
                "vector_embeddings": {"count": 2},
            }

            # Mock the update_state method to avoid Celery backend interaction
            with patch.object(process_document, "update_state"):
                result = process_document.__wrapped__(
                    document_id="1", user_id="test-user-id"
                )

            # Verify results
            assert result["success"] is True
            assert result["document_id"] == "1"
            assert result["title"] == "test.pdf"
            assert result["status"] == mock_document.status.value
            assert result["has_vectors"] is True

    def test_process_document_task_not_found(self):
        """Test processing when document doesn't exist"""
        with patch("tasks.document_tasks.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_session_local.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None

            # Mock the update_state method to avoid Celery backend interaction
            with patch.object(process_document, "update_state"):
                with pytest.raises(ValueError, match="Dokument .* nicht gefunden"):
                    process_document.__wrapped__(
                        document_id="999", user_id="test-user-id"
                    )

    def test_create_embeddings_task_success(self):
        """Test successful embedding creation"""
        with (
            patch("tasks.rag_tasks.SessionLocal") as mock_session_local,
            patch("services.rag_service.RAGService", create=True) as mock_rag_cls,
        ):
            mock_db = MagicMock()
            mock_session_local.return_value = mock_db

            mock_document = MagicMock(spec=Document)
            mock_document.id = "test-doc-id"

            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_document
            )

            mock_rag_instance = MagicMock()
            mock_rag_cls.return_value = mock_rag_instance

            # Execute task
            result = create_embeddings(
                document_id="test-doc-id", chunks=["chunk1", "chunk2", "chunk3"]
            )

            # Verify results
            assert result["success"] is True
            assert result["document_id"] == "test-doc-id"
            assert result["chunks_embedded"] == 3

            # Verify RAG service was called
            mock_rag_instance.add_document_chunks.assert_called_once()


class TestCeleryConfiguration:
    """Test Celery app configuration"""

    def test_celery_app_initialization(self):
        """Test that Celery app is properly initialized"""
        from celery_app import celery_app

        assert celery_app is not None
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.timezone == "Europe/Zurich"

    def test_celery_queues_configured(self):
        """Test that Celery queues are properly configured"""
        from celery_app import celery_app

        queues = celery_app.conf.task_queues
        queue_names = [q.name for q in queues]

        assert "document_processing" in queue_names
        assert "rag_embedding" in queue_names
        assert "question_generation" in queue_names

    def test_celery_task_routes_configured(self):
        """Test that Celery task routes are properly configured"""
        from celery_app import celery_app

        routes = celery_app.conf.task_routes

        assert "tasks.document_tasks.process_document" in routes
        assert "tasks.rag_tasks.create_embeddings" in routes

        # Verify routing
        assert (
            routes["tasks.document_tasks.process_document"]["queue"]
            == "document_processing"
        )
        assert routes["tasks.rag_tasks.create_embeddings"]["queue"] == "rag_embedding"
