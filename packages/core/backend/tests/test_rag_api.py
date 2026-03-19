"""
API Tests für RAG Endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from main import app
from services.rag_service import RAGExamResponse, RAGQuestion, RAGContext
from models.document import Document, DocumentStatus


client = TestClient(app)


class TestRAGAPI:
    """Test Suite für RAG API Endpoints"""

    @pytest.fixture
    def sample_rag_response(self):
        """Sample RAG Response für Tests"""
        context = RAGContext(
            query="ExamCraft AI",
            retrieved_chunks=[],
            total_similarity_score=1.5,
            source_documents=[{"id": 1, "filename": "test.txt", "chunks_used": 2}],
            context_length=150,
        )

        questions = [
            RAGQuestion(
                question_text="Was ist ExamCraft AI?",
                question_type="multiple_choice",
                options=["A) CMS", "B) Prüfungssystem", "C) Browser", "D) Editor"],
                correct_answer="B",
                explanation="ExamCraft AI ist ein intelligentes Prüfungssystem",
                difficulty="medium",
                source_chunks=["chunk_1"],
                source_documents=["test.txt"],
                confidence_score=0.85,
            ),
            RAGQuestion(
                question_text="Erläutern Sie die Funktionsweise von ExamCraft AI.",
                question_type="open_ended",
                correct_answer="ExamCraft AI verwendet KI-Technologien...",
                explanation=["Verständnis", "Vollständigkeit"],
                difficulty="medium",
                source_chunks=["chunk_2"],
                source_documents=["test.txt"],
                confidence_score=0.78,
            ),
        ]

        return RAGExamResponse(
            exam_id="test_exam_123",
            topic="ExamCraft AI",
            questions=questions,
            context_summary=context,
            generation_time=2.5,
            quality_metrics={
                "total_questions": 2,
                "average_confidence": 0.815,
                "source_coverage": 1.0,
                "question_type_distribution": {"multiple_choice": 1, "open_ended": 1},
            },
        )

    @pytest.fixture
    def mock_processed_document(self):
        """Mock verarbeitetes Dokument"""
        doc = Mock(spec=Document)
        doc.id = 1
        doc.original_filename = "test_document.txt"
        doc.mime_type = "text/plain"
        doc.status = DocumentStatus.PROCESSED
        doc.vector_collection = "test_collection"
        doc.doc_metadata = {
            "total_chunks": 5,
            "embedding_model": "mock-model",
            "processing_time": 1.2,
        }
        doc.created_at = None
        doc.processed_at = None
        return doc

    def test_generate_rag_exam_success(self, mock_processed_document):
        """Test erfolgreiche RAG Exam Generation — gibt jetzt task_id zurück"""
        from main import app
        from database import get_db
        from utils.auth_utils import get_current_user

        request_data = {
            "topic": "ExamCraft AI",
            "document_ids": [1],
            "question_count": 2,
            "question_types": ["multiple_choice", "open_ended"],
            "difficulty": "medium",
            "language": "de",
            "context_chunks_per_question": 3,
        }

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.has_permission.return_value = True

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            with (
                patch("api.rag_exams.document_service") as mock_doc_service,
                patch("api.rag_exams.generate_questions_task") as mock_task,
                patch("api.rag_exams.QuestionGenerationJob") as mock_job_cls,
            ):
                # Mock Document Service
                mock_doc_service.get_document_by_id.return_value = (
                    mock_processed_document
                )

                # Mock Celery Task und Job
                mock_task.apply_async.return_value = MagicMock()
                mock_job_cls.return_value = MagicMock()

                response = client.post("/api/v1/rag/generate-exam", json=request_data)
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()

        assert "task_id" in data
        assert "message" in data

    def test_generate_rag_exam_document_not_found(self):
        """Test RAG Exam Generation mit nicht existierendem Dokument"""

        request_data = {
            "topic": "Test Topic",
            "document_ids": [999],  # Nicht existierende ID
            "question_count": 1,
        }

        with patch("api.rag_exams.document_service") as mock_doc_service:
            mock_doc_service.get_document_by_id.return_value = None

            response = client.post("/api/v1/rag/generate-exam", json=request_data)

        assert response.status_code == 404
        assert "Document with ID 999 not found" in response.json()["detail"]

    def test_generate_rag_exam_document_not_processed(self, mock_processed_document):
        """Test RAG Exam Generation mit nicht verarbeitetem Dokument"""

        # Setze Status auf nicht verarbeitet
        mock_processed_document.status = DocumentStatus.UPLOADED

        request_data = {"topic": "Test Topic", "document_ids": [1], "question_count": 1}

        with patch("api.rag_exams.document_service") as mock_doc_service:
            mock_doc_service.get_document_by_id.return_value = mock_processed_document

            response = client.post("/api/v1/rag/generate-exam", json=request_data)

        assert response.status_code == 400
        assert "is not processed yet" in response.json()["detail"]

    def test_generate_rag_exam_invalid_question_type(self):
        """Test RAG Exam Generation mit ungültigem Fragetyp"""

        request_data = {
            "topic": "Test Topic",
            "question_count": 1,
            "question_types": ["invalid_type"],
        }

        response = client.post("/api/v1/rag/generate-exam", json=request_data)

        assert response.status_code == 400
        assert "Invalid question type: invalid_type" in response.json()["detail"]

    def test_generate_rag_exam_validation_errors(self):
        """Test RAG Exam Generation mit Validierungsfehlern"""

        # Leeres Topic
        response = client.post(
            "/api/v1/rag/generate-exam",
            json={
                "topic": "",  # Zu kurz
                "question_count": 1,
            },
        )
        assert response.status_code == 422

        # Zu viele Fragen
        response = client.post(
            "/api/v1/rag/generate-exam",
            json={
                "topic": "Valid Topic",
                "question_count": 25,  # Über Limit (20)
            },
        )
        assert response.status_code == 422

        # Negative Fragen
        response = client.post(
            "/api/v1/rag/generate-exam",
            json={"topic": "Valid Topic", "question_count": -1},
        )
        assert response.status_code == 422

    def test_generate_rag_exam_broker_unavailable(self, mock_processed_document):
        """Test RAG Exam Generation wenn Celery Broker nicht erreichbar ist"""

        request_data = {"topic": "Test Topic", "question_count": 1}

        with (
            patch("api.rag_exams.document_service") as mock_doc_service,
            patch("api.rag_exams.generate_questions_task") as mock_task,
            patch("api.rag_exams.QuestionGenerationJob") as mock_job_cls,
            patch("api.rag_exams.get_db"),
        ):
            mock_doc_service.get_document_by_id.return_value = mock_processed_document
            mock_task.apply_async.side_effect = Exception("Broker unavailable")
            mock_job_cls.return_value = MagicMock()

            response = client.post("/api/v1/rag/generate-exam", json=request_data)

        assert response.status_code == 503
        assert "Task-Queue nicht verfügbar" in response.json()["detail"]

    def test_retrieve_context_success(self):
        """Test erfolgreiche Context Retrieval"""

        request_data = {
            "query": "ExamCraft AI",
            "document_ids": [1],
            "max_chunks": 5,
            "min_similarity": 0.3,
        }

        mock_context = RAGContext(
            query="ExamCraft AI",
            retrieved_chunks=[],
            total_similarity_score=2.1,
            source_documents=[{"id": 1, "filename": "test.txt", "chunks_used": 3}],
            context_length=180,
        )

        with (
            patch("api.rag_exams.document_service") as mock_doc_service,
            patch("api.rag_exams.rag_service") as mock_rag_service,
        ):
            mock_doc_service.get_document_by_id.return_value = Mock()
            mock_rag_service.retrieve_context = AsyncMock(return_value=mock_context)

            response = client.post("/api/v1/rag/retrieve-context", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["query"] == "ExamCraft AI"
        assert data["total_chunks"] == 0
        assert data["total_similarity_score"] == 2.1
        assert len(data["source_documents"]) == 1
        assert data["context_length"] == 180

    def test_retrieve_context_validation_errors(self):
        """Test Context Retrieval mit Validierungsfehlern"""

        # Leere Query
        response = client.post(
            "/api/v1/rag/retrieve-context",
            json={
                "query": ""  # Zu kurz
            },
        )
        assert response.status_code == 422

        # Negative max_chunks
        response = client.post(
            "/api/v1/rag/retrieve-context",
            json={"query": "Valid Query", "max_chunks": -1},
        )
        assert response.status_code == 422

        # Ungültige min_similarity
        response = client.post(
            "/api/v1/rag/retrieve-context",
            json={
                "query": "Valid Query",
                "min_similarity": 1.5,  # Über 1.0
            },
        )
        assert response.status_code == 422

    def test_get_available_documents_success(self, mock_processed_document):
        """Test erfolgreiche Available Documents Abfrage"""

        documents = [mock_processed_document]

        with patch("api.rag_exams.document_service") as mock_doc_service:
            mock_doc_service.get_documents_by_user.return_value = documents

            response = client.get("/api/v1/rag/available-documents")

        assert response.status_code == 200
        data = response.json()

        assert data["total_documents"] == 1
        assert data["processed_documents"] == 1
        assert data["documents_with_vectors"] == 1
        assert len(data["documents"]) == 1

        doc_data = data["documents"][0]
        assert doc_data["id"] == 1
        assert doc_data["filename"] == "test_document.txt"
        assert doc_data["status"] == "processed"
        assert doc_data["has_vectors"] is True

    def test_get_available_documents_processed_only(self, mock_processed_document):
        """Test Available Documents nur verarbeitete"""

        # Erstelle gemischte Dokumente
        unprocessed_doc = Mock(spec=Document)
        unprocessed_doc.status = DocumentStatus.UPLOADED

        documents = [mock_processed_document, unprocessed_doc]

        with patch("api.rag_exams.document_service") as mock_doc_service:
            mock_doc_service.get_documents_by_user.return_value = documents

            response = client.get("/api/v1/rag/available-documents?processed_only=true")

        assert response.status_code == 200
        data = response.json()

        # Nur verarbeitete Dokumente sollten zurückgegeben werden
        assert data["total_documents"] == 1
        assert data["processed_documents"] == 1

    def test_get_available_documents_all(self, mock_processed_document):
        """Test Available Documents alle anzeigen"""

        unprocessed_doc = Mock(spec=Document)
        unprocessed_doc.id = 2
        unprocessed_doc.original_filename = "unprocessed.txt"
        unprocessed_doc.mime_type = "text/plain"
        unprocessed_doc.status = DocumentStatus.UPLOADED
        unprocessed_doc.vector_collection = None
        unprocessed_doc.doc_metadata = None
        unprocessed_doc.created_at = None
        unprocessed_doc.processed_at = None

        documents = [mock_processed_document, unprocessed_doc]

        with patch("api.rag_exams.document_service") as mock_doc_service:
            mock_doc_service.get_documents_by_user.return_value = documents

            response = client.get(
                "/api/v1/rag/available-documents?processed_only=false"
            )

        assert response.status_code == 200
        data = response.json()

        assert data["total_documents"] == 2
        assert data["processed_documents"] == 1
        assert data["documents_with_vectors"] == 1

    def test_get_supported_question_types(self):
        """Test Supported Question Types Endpoint"""

        response = client.get("/api/v1/rag/question-types")

        assert response.status_code == 200
        data = response.json()

        assert "supported_types" in data
        assert "difficulty_levels" in data
        assert "supported_languages" in data

        # Prüfe Question Types
        question_types = {qt["type"] for qt in data["supported_types"]}
        assert "multiple_choice" in question_types
        assert "open_ended" in question_types
        assert "true_false" in question_types

        # Prüfe Difficulty Levels
        difficulty_levels = {dl["level"] for dl in data["difficulty_levels"]}
        assert "easy" in difficulty_levels
        assert "medium" in difficulty_levels
        assert "hard" in difficulty_levels

        # Prüfe Languages
        languages = {lang["code"] for lang in data["supported_languages"]}
        assert "de" in languages
        assert "en" in languages

    def test_rag_service_health_healthy(self):
        """Test RAG Service Health Check - Healthy"""

        mock_vector_stats = {"total_chunks": 10, "embedding_model": "mock-model"}

        with (
            patch("api.rag_exams.vector_service") as mock_vector_service,
            patch("api.rag_exams.rag_service") as mock_rag_service,
        ):
            mock_vector_service.get_collection_stats.return_value = mock_vector_stats
            mock_rag_service.claude_service = Mock()  # Claude Service verfügbar
            mock_rag_service.question_templates = {
                "mc": "template",
                "oe": "template",
                "tf": "template",
            }

            response = client.get("/api/v1/rag/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["service"] == "RAG Service"
        assert "components" in data
        assert data["components"]["vector_service"]["status"] == "available"
        assert data["components"]["claude_service"]["status"] == "available"
        assert data["components"]["rag_templates"]["template_count"] == 3
        assert "supported_features" in data

    def test_rag_service_health_unhealthy(self):
        """Test RAG Service Health Check - Unhealthy"""

        with patch("api.rag_exams.vector_service") as mock_vector_service:
            mock_vector_service.get_collection_stats.side_effect = Exception(
                "Vector Service Error"
            )

            response = client.get("/api/v1/rag/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "unhealthy"
        assert data["service"] == "RAG Service"
        assert "error" in data

    def test_rag_service_health_claude_unavailable(self):
        """Test RAG Service Health Check - Claude Unavailable"""

        mock_vector_stats = {"total_chunks": 5, "embedding_model": "mock"}

        with (
            patch("api.rag_exams.vector_service") as mock_vector_service,
            patch("api.rag_exams.rag_service") as mock_rag_service,
        ):
            mock_vector_service.get_collection_stats.return_value = mock_vector_stats
            mock_rag_service.claude_service = None  # Claude Service nicht verfügbar
            mock_rag_service.question_templates = {"mc": "template"}

            response = client.get("/api/v1/rag/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["components"]["claude_service"]["status"] == "unavailable"
        assert data["components"]["claude_service"]["fallback_enabled"] is True


class TestRAGAPIIntegration:
    """Integration Tests für RAG API mit echten Services"""

    def test_full_rag_workflow_mock(self):
        """Test vollständiger RAG Workflow mit Mocks"""

        # 1. Prüfe verfügbare Dokumente
        with patch("api.rag_exams.document_service") as mock_doc_service:
            mock_doc = Mock()
            mock_doc.id = 1
            mock_doc.original_filename = "integration_test.txt"
            mock_doc.status = DocumentStatus.PROCESSED
            mock_doc.vector_collection = "test"
            mock_doc.doc_metadata = {}
            mock_doc.created_at = None
            mock_doc.processed_at = None

            mock_doc_service.get_documents_by_user.return_value = [mock_doc]

            docs_response = client.get("/api/v1/rag/available-documents")
            assert docs_response.status_code == 200
            assert docs_response.json()["total_documents"] == 1

        # 2. Teste Context Retrieval
        mock_context = RAGContext(
            query="Integration Test",
            retrieved_chunks=[],
            total_similarity_score=1.0,
            source_documents=[{"id": 1, "filename": "integration_test.txt"}],
            context_length=100,
        )

        with patch("api.rag_exams.rag_service") as mock_rag_service:
            mock_rag_service.retrieve_context = AsyncMock(return_value=mock_context)

            context_response = client.post(
                "/api/v1/rag/retrieve-context",
                json={
                    "query": "Integration Test",
                    "document_ids": [1],
                    "max_chunks": 3,
                },
            )

            assert context_response.status_code == 200
            assert context_response.json()["query"] == "Integration Test"

        # 3. Teste RAG Exam Generation — gibt jetzt task_id zurück
        with (
            patch("api.rag_exams.document_service") as mock_doc_service,
            patch("api.rag_exams.generate_questions_task") as mock_task,
            patch("api.rag_exams.QuestionGenerationJob") as mock_job_cls,
            patch("api.rag_exams.get_db"),
        ):
            mock_doc_service.get_document_by_id.return_value = mock_doc
            mock_task.apply_async.return_value = MagicMock()
            mock_job_cls.return_value = MagicMock()

            exam_response = client.post(
                "/api/v1/rag/generate-exam",
                json={
                    "topic": "Integration Test",
                    "document_ids": [1],
                    "question_count": 1,
                    "question_types": ["multiple_choice"],
                },
            )

            assert exam_response.status_code == 200
            exam_data = exam_response.json()
            assert "task_id" in exam_data
            assert "message" in exam_data

    def test_error_handling_chain(self):
        """Test Error Handling in der gesamten Chain"""

        # Test Document Not Found -> Context Retrieval Error -> Exam Generation Error
        with patch("api.rag_exams.document_service") as mock_doc_service:
            mock_doc_service.get_document_by_id.return_value = None

            # Document Not Found sollte früh abbrechen
            response = client.post(
                "/api/v1/rag/generate-exam",
                json={"topic": "Test", "document_ids": [999], "question_count": 1},
            )

            assert response.status_code == 404

    def test_concurrent_requests(self):
        """Test gleichzeitige RAG Requests"""
        import threading

        results = []

        def make_request():
            response = client.get("/api/v1/rag/question-types")
            results.append(response.status_code)

        # Starte mehrere gleichzeitige Requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Warte auf alle Threads
        for thread in threads:
            thread.join()

        # Alle Requests sollten erfolgreich sein
        assert all(status == 200 for status in results)
        assert len(results) == 5
