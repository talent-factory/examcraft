"""
Tests for Celery async task processing
"""

import pytest
from unittest.mock import patch, MagicMock
from tasks.document_tasks import process_document
from tasks.rag_tasks import create_embeddings
from models.document import Document, DocumentStatus


class TestDocumentProcessingTask:
    """Test async document processing with Celery"""

    def test_process_document_task_success(self):
        """Test successful document processing"""
        # Mock the database and services
        with (
            patch("tasks.document_tasks.SessionLocal") as mock_session_local,
            patch("tasks.document_tasks.DoclingService") as mock_docling,
            patch("tasks.document_tasks.RAGService") as mock_rag,
        ):
            # Setup mocks
            mock_db = MagicMock()
            mock_session_local.return_value = mock_db

            mock_document = MagicMock(spec=Document)
            mock_document.id = "test-doc-id"
            mock_document.filename = "test.pdf"
            mock_document.file_path = "/path/to/test.pdf"

            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_document
            )

            # Mock Docling service
            mock_docling_instance = MagicMock()
            mock_docling.return_value = mock_docling_instance
            mock_docling_instance.process_document.return_value = {
                "title": "Test Document",
                "metadata": {"pages": 10},
                "content": "Test content",
                "page_count": 10,
            }

            # Mock RAG service
            mock_rag_instance = MagicMock()
            mock_rag.return_value = mock_rag_instance
            mock_rag_instance.chunk_document.return_value = ["chunk1", "chunk2"]

            # Mock Celery task
            with patch("tasks.document_tasks.create_embeddings") as mock_embedding_task:
                mock_embedding_task.apply_async.return_value = MagicMock(id="task-123")

                # Execute task
                result = process_document(
                    document_id="test-doc-id", user_id="test-user-id"
                )

            # Verify results
            assert result["success"] is True
            assert result["document_id"] == "test-doc-id"
            assert result["title"] == "Test Document"
            assert result["chunks"] == 2

            # Verify document status was updated
            assert mock_document.status == DocumentStatus.COMPLETED

    def test_process_document_task_not_found(self):
        """Test processing when document doesn't exist"""
        with patch("tasks.document_tasks.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_session_local.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None

            # Should raise ValueError
            with pytest.raises(ValueError, match="Document .* not found"):
                process_document(document_id="nonexistent-id", user_id="test-user-id")

    def test_create_embeddings_task_success(self):
        """Test successful embedding creation"""
        with (
            patch("tasks.rag_tasks.SessionLocal") as mock_session_local,
            patch("tasks.rag_tasks.RAGService") as mock_rag,
        ):
            mock_db = MagicMock()
            mock_session_local.return_value = mock_db

            mock_document = MagicMock(spec=Document)
            mock_document.id = "test-doc-id"

            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_document
            )

            mock_rag_instance = MagicMock()
            mock_rag.return_value = mock_rag_instance

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
