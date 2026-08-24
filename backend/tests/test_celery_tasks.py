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
            patch("tasks.document_tasks.flag_modified"),
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
                "extraction": {"pages": 10},
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

    def test_process_document_vectorization_failure_reports_failure(self):
        """TF-364: on a vectorization error, process_document_with_vectors
        returns a dict (not None) with vector_embeddings.error and no quality key.

        The None guard doesn't trigger; previously execution fell into the
        escalation branch and returned ``success: True`` alongside
        ``status: "error"``. The envelope ``success`` and the embedded
        ``status`` must be consistent: for an ERROR document, ``success=False``
        with error_code.
        """
        with (
            patch("tasks.document_tasks.SessionLocal") as mock_session_local,
            patch("tasks.document_tasks.document_service"),
            patch("tasks.document_tasks.run_async") as mock_run_async,
            patch("tasks.document_tasks.flag_modified"),
        ):
            mock_db = MagicMock()
            mock_session_local.return_value = mock_db

            mock_document = MagicMock(spec=Document)
            mock_document.id = 1
            mock_document.original_filename = "broken.pdf"
            mock_document.file_path = "/path/to/broken.pdf"
            # Vectorization has already marked the document as ERROR
            # (process_document_with_vectors, except branch).
            mock_document.status = DocumentStatus.ERROR
            mock_document.has_vectors = False
            mock_document.error_message = "Qdrant unreachable"
            mock_document.doc_metadata = {
                "error_code": "vectorization_failed",
                "vector_embedding_error": "Qdrant unreachable",
            }
            mock_document.processing_info = {}

            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_document
            )

            # dict WITHOUT a quality key, WITH vector_embeddings.error
            mock_run_async.return_value = {
                "document_id": 1,
                "extraction": {"total_chunks": 3},
                "vector_embeddings": {"error": "Qdrant unreachable"},
            }

            with patch.object(process_document, "update_state"):
                result = process_document.__wrapped__(
                    document_id="1", user_id="test-user-id"
                )

            # Envelope success and embedded status are consistent
            assert result["success"] is False
            assert result["status"] == DocumentStatus.ERROR.value
            assert result["error_code"] == "vectorization_failed"
            # The specific vector error is passed through, not swallowed.
            assert result["error"] == "Qdrant unreachable"

    def test_process_document_failure_reads_metadata_fallbacks(self):
        """TF-364 (review): error_code is read from doc_metadata (not hard-
        defaulted), and the error message falls back to the cause persisted
        in doc_metadata when neither result nor error_message provide one —
        the envelope is never left without an error message."""
        with (
            patch("tasks.document_tasks.SessionLocal") as mock_session_local,
            patch("tasks.document_tasks.document_service"),
            patch("tasks.document_tasks.run_async") as mock_run_async,
            patch("tasks.document_tasks.flag_modified"),
        ):
            mock_db = MagicMock()
            mock_session_local.return_value = mock_db

            mock_document = MagicMock(spec=Document)
            mock_document.id = 1
            mock_document.original_filename = "empty.pdf"
            mock_document.file_path = "/path/to/empty.pdf"
            mock_document.status = DocumentStatus.ERROR
            mock_document.has_vectors = False
            mock_document.error_message = None
            mock_document.doc_metadata = {
                "error_code": "empty_document",
                "vector_embedding_error": "no chunks extracted",
            }
            mock_document.processing_info = {}

            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_document
            )

            # Branch triggers via status==ERROR; vector_embeddings without 'error'.
            mock_run_async.return_value = {
                "document_id": 1,
                "extraction": {"error": "processing_failed_before_vectorization"},
                "vector_embeddings": {},
            }

            with patch.object(process_document, "update_state"):
                result = process_document.__wrapped__(
                    document_id="1", user_id="test-user-id"
                )

            assert result["success"] is False
            # error_code comes from doc_metadata, not from the default.
            assert result["error_code"] == "empty_document"
            # Error message falls back to the persisted cause (not None).
            assert result["error"] == "no chunks extracted"

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
