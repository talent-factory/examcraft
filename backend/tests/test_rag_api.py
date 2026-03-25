"""
API Tests für RAG Endpoints

NOTE: These tests are skipped in CI because the RAG endpoints use importlib
dynamic loading, making mock patching unreliable. The endpoints are tested
via Premium integration tests instead.
"""

import pytest

from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from main import app
from services.document_service import document_service as actual_document_service
from models.document import Document, DocumentStatus
from utils.tenant_utils import TenantFilter


@pytest.fixture
def mock_user():
    """Mock authenticated user with create_questions permission"""
    mock_institution = Mock()
    mock_institution.id = 1
    mock_institution.name = "Test University"
    mock_institution.slug = "test-university"
    mock_institution.subscription_tier = "professional"
    mock_institution.max_users = 100
    mock_institution.max_documents = 1000
    mock_institution.max_questions_per_month = -1

    user = Mock()
    user.id = 42
    user.email = "dozent@example.com"
    user.first_name = "Test"
    user.last_name = "User"
    user.institution_id = 1
    user.institution = mock_institution
    user.has_permission = Mock(return_value=True)
    user.is_superuser = False
    user.roles = []
    return user


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = MagicMock()
    id_counter = [0]
    added_objects = []

    def mock_add(obj):
        added_objects.append(obj)

    def mock_flush():
        for obj in added_objects:
            if hasattr(obj, "id") and obj.id is None:
                id_counter[0] += 1
                obj.id = id_counter[0]

    db.add = mock_add
    db.flush = mock_flush
    db.commit = Mock()
    db.rollback = Mock()
    db._added_objects = added_objects
    return db


@pytest.fixture
def auth_client(mock_user, mock_db):
    """FastAPI Test Client with auth overrides"""
    from utils.auth_utils import get_current_user, get_current_active_user
    from database import get_db

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# Unauthenticated client for public endpoints
client = TestClient(app)


def _make_mock_rag_response():
    """Create a mock RAG response with the expected attributes"""
    context = Mock()
    context.query = "ExamCraft AI"
    context.retrieved_chunks = []
    context.total_similarity_score = 1.5
    context.source_documents = [{"id": 1, "filename": "test.txt", "chunks_used": 2}]
    context.context_length = 150

    q1 = Mock()
    q1.question_text = "Was ist ExamCraft AI?"
    q1.question_type = "multiple_choice"
    q1.options = ["A) CMS", "B) Prüfungssystem", "C) Browser", "D) Editor"]
    q1.correct_answer = "B"
    q1.explanation = "ExamCraft AI ist ein intelligentes Prüfungssystem"
    q1.difficulty = "medium"
    q1.source_chunks = ["chunk_1"]
    q1.source_documents = ["test.txt"]
    q1.confidence_score = 0.85

    q2 = Mock()
    q2.question_text = "Erläutern Sie die Funktionsweise von ExamCraft AI."
    q2.question_type = "open_ended"
    q2.options = None
    q2.correct_answer = "ExamCraft AI verwendet KI-Technologien..."
    q2.explanation = ["Verständnis", "Vollständigkeit"]
    q2.difficulty = "medium"
    q2.source_chunks = ["chunk_2"]
    q2.source_documents = ["test.txt"]
    q2.confidence_score = 0.78

    response = Mock()
    response.exam_id = "test_exam_123"
    response.topic = "ExamCraft AI"
    response.questions = [q1, q2]
    response.context_summary = context
    response.generation_time = 2.5
    response.quality_metrics = {
        "total_questions": 2,
        "average_confidence": 0.815,
        "source_coverage": 1.0,
        "question_type_distribution": {"multiple_choice": 1, "open_ended": 1},
    }

    return response


class TestRAGAPI:
    """Test Suite für RAG API Endpoints"""

    @pytest.fixture(autouse=True)
    def ensure_rag_router(self):
        """Ensure the RAG router is registered"""
        import api.rag_exams as rag_module

        route_paths = [r.path for r in app.routes]
        if "/api/v1/rag/generate-exam" not in route_paths:
            app.include_router(rag_module.router)

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
        doc.file_size = 1024
        doc.institution_id = 1
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
        mock_user.institution = MagicMock()

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            with (
                patch("api.rag_exams.document_service") as mock_doc_service,
                patch("api.rag_exams.generate_questions_task") as mock_task,
                patch("api.rag_exams.QuestionGenerationJob") as mock_job_cls,
                patch("utils.tenant_utils.SubscriptionLimits"),
            ):
                mock_doc_service.get_document_by_id.return_value = (
                    mock_processed_document
                )
                mock_task.apply_async.return_value = MagicMock()
                mock_job_cls.return_value = MagicMock()

                response = client.post("/api/v1/rag/generate-exam", json=request_data)
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "message" in data

    def test_generate_rag_exam_document_not_found(self, auth_client):
        """Test RAG Exam Generation mit nicht existierendem Dokument"""

        request_data = {
            "topic": "Test Topic",
            "document_ids": [999],  # Nicht existierende ID
            "question_count": 1,
        }

        with patch.object(
            actual_document_service,
            "get_document_by_id",
            return_value=None,
        ):
            response = auth_client.post("/api/v1/rag/generate-exam", json=request_data)

        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "nicht gefunden" in detail or "not found" in detail.lower()

    def test_generate_rag_exam_document_not_processed(
        self, auth_client, mock_processed_document
    ):
        """Test RAG Exam Generation mit nicht verarbeitetem Dokument"""

        # Setze Status auf nicht verarbeitet
        mock_processed_document.status = DocumentStatus.UPLOADED
        # institution_id already set in fixture

        request_data = {"topic": "Test Topic", "document_ids": [1], "question_count": 1}

        with patch.object(
            actual_document_service,
            "get_document_by_id",
            return_value=mock_processed_document,
        ):
            response = auth_client.post("/api/v1/rag/generate-exam", json=request_data)

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "nicht verarbeitet" in detail or "not processed" in detail.lower()

    def test_generate_rag_exam_invalid_question_type(self, auth_client):
        """Test RAG Exam Generation mit ungültigem Fragetyp"""

        request_data = {
            "topic": "Test Topic",
            "question_count": 1,
            "question_types": ["invalid_type"],
        }

        response = auth_client.post("/api/v1/rag/generate-exam", json=request_data)

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "Ungültiger" in detail or "Invalid" in detail

    def test_generate_rag_exam_validation_errors(self, auth_client):
        """Test RAG Exam Generation mit Validierungsfehlern"""

        # Leeres Topic
        response = auth_client.post(
            "/api/v1/rag/generate-exam",
            json={"topic": "", "question_count": 1},
        )
        assert response.status_code == 422

        # Zu viele Fragen
        response = auth_client.post(
            "/api/v1/rag/generate-exam",
            json={"topic": "Valid Topic", "question_count": 25},
        )
        assert response.status_code == 422

        # Negative Fragen
        response = auth_client.post(
            "/api/v1/rag/generate-exam",
            json={"topic": "Valid Topic", "question_count": -1},
        )
        assert response.status_code == 422

    def test_generate_exam_job_created_with_topic_and_count(
        self, mock_processed_document
    ):
        """QuestionGenerationJob must be created with topic and question_count populated"""
        from main import app
        from database import get_db
        from utils.auth_utils import get_current_user

        request_data = {
            "topic": "Heap Sort",
            "document_ids": [1],
            "question_count": 5,
            "question_types": ["multiple_choice"],
            "difficulty": "medium",
            "language": "de",
        }

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 99
        mock_user.has_permission.return_value = True
        mock_user.institution = MagicMock()

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user

        captured_jobs = []

        try:
            with (
                patch("api.rag_exams.document_service") as mock_doc_service,
                patch("api.rag_exams.generate_questions_task") as mock_task,
                patch("api.rag_exams.QuestionGenerationJob") as mock_job_cls,
                patch("utils.tenant_utils.SubscriptionLimits"),
            ):
                mock_doc_service.get_document_by_id.return_value = (
                    mock_processed_document
                )
                mock_task.apply_async.return_value = MagicMock()

                def capture_job(**kwargs):
                    job = MagicMock()
                    job.task_id = kwargs.get("task_id")
                    job.user_id = kwargs.get("user_id")
                    job.topic = kwargs.get("topic")
                    job.question_count = kwargs.get("question_count")
                    captured_jobs.append(job)
                    return job

                mock_job_cls.side_effect = capture_job

                response = client.post("/api/v1/rag/generate-exam", json=request_data)
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert len(captured_jobs) == 1
        job = captured_jobs[0]
        assert job.topic == "Heap Sort"
        assert job.question_count == 5
        assert job.user_id == mock_user.id

    def test_generate_rag_exam_broker_unavailable(self, mock_processed_document):
        """Test RAG Exam Generation wenn Celery Broker nicht erreichbar ist"""
        from main import app
        from database import get_db
        from utils.auth_utils import get_current_user

        request_data = {"topic": "Test Topic", "question_count": 1}

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.has_permission.return_value = True
        mock_user.institution = MagicMock()

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            with (
                patch("api.rag_exams.document_service") as mock_doc_service,
                patch("api.rag_exams.generate_questions_task") as mock_task,
                patch("api.rag_exams.QuestionGenerationJob") as mock_job_cls,
                patch("utils.tenant_utils.SubscriptionLimits"),
            ):
                mock_doc_service.get_document_by_id.return_value = (
                    mock_processed_document
                )
                mock_task.apply_async.side_effect = Exception("Broker unavailable")
                mock_job_cls.return_value = MagicMock()

                response = client.post("/api/v1/rag/generate-exam", json=request_data)
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 503
        detail = response.json()["detail"]
        assert "nicht verfügbar" in detail or "unavailable" in detail.lower()

    def test_retrieve_context_success(self, auth_client):
        """Test erfolgreiche Context Retrieval"""

        request_data = {
            "query": "ExamCraft AI",
            "document_ids": [1],
            "max_chunks": 5,
            "min_similarity": 0.3,
        }

        mock_context = Mock()
        mock_context.query = "ExamCraft AI"
        mock_context.retrieved_chunks = []
        mock_context.total_similarity_score = 2.1
        mock_context.source_documents = [
            {"id": 1, "filename": "test.txt", "chunks_used": 3}
        ]
        mock_context.context_length = 180

        # Document mock needs institution_id for tenant check
        mock_doc = Mock()
        mock_doc.institution_id = 1

        with (
            patch.object(
                actual_document_service,
                "get_document_by_id",
                return_value=mock_doc,
            ),
            patch("services.rag_service.rag_service") as mock_rag_service,
        ):
            mock_rag_service.retrieve_context = AsyncMock(return_value=mock_context)
            response = auth_client.post(
                "/api/v1/rag/retrieve-context", json=request_data
            )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "ExamCraft AI"
        assert data["total_chunks"] == 0
        assert data["total_similarity_score"] == 2.1
        assert len(data["source_documents"]) == 1
        assert data["context_length"] == 180

    def test_retrieve_context_validation_errors(self, auth_client):
        """Test Context Retrieval mit Validierungsfehlern"""

        response = auth_client.post("/api/v1/rag/retrieve-context", json={"query": ""})
        assert response.status_code == 422

        response = auth_client.post(
            "/api/v1/rag/retrieve-context",
            json={"query": "Valid Query", "max_chunks": -1},
        )
        assert response.status_code == 422

        response = auth_client.post(
            "/api/v1/rag/retrieve-context",
            json={"query": "Valid Query", "min_similarity": 1.5},
        )
        assert response.status_code == 422

    def test_get_available_documents_success(
        self, auth_client, mock_db, mock_processed_document
    ):
        """Test erfolgreiche Available Documents Abfrage"""

        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_processed_document]

        with patch.object(TenantFilter, "filter_by_tenant", return_value=mock_query):
            response = auth_client.get("/api/v1/rag/available-documents")

        assert response.status_code == 200
        data = response.json()
        assert data["total_documents"] == 1
        assert data["processed_documents"] == 1

    def test_get_supported_question_types(self):
        """Test Supported Question Types Endpoint (no auth required)"""

        response = client.get("/api/v1/rag/question-types")
        assert response.status_code == 200
        data = response.json()

        assert "supported_types" in data
        assert "difficulty_levels" in data
        assert "supported_languages" in data

        question_types = {qt["type"] for qt in data["supported_types"]}
        assert "multiple_choice" in question_types
        assert "open_ended" in question_types
        assert "true_false" in question_types

        difficulty_levels = {dl["level"] for dl in data["difficulty_levels"]}
        assert "easy" in difficulty_levels
        assert "medium" in difficulty_levels
        assert "hard" in difficulty_levels

        languages = {lang["code"] for lang in data["supported_languages"]}
        assert "de" in languages
        assert "en" in languages

    def test_rag_service_health_healthy(self):
        """Test RAG Service Health Check - Healthy (no auth required)"""

        mock_vector_stats = {"total_chunks": 10, "embedding_model": "mock-model"}

        with (
            patch("services.vector_service_factory.vector_service") as mock_vs,
            patch("services.rag_service.rag_service") as mock_rag,
        ):
            mock_vs.get_collection_stats.return_value = mock_vector_stats
            mock_rag.claude_service = Mock()
            mock_rag.question_templates = {
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

        with patch("services.vector_service_factory.vector_service") as mock_vs:
            mock_vs.get_collection_stats.side_effect = Exception("Vector Service Error")
            response = client.get("/api/v1/rag/health")

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["status"] == "unhealthy"
        assert data["detail"]["service"] == "RAG Service"

    def test_rag_service_health_claude_unavailable(self):
        """Test RAG Service Health Check - Claude Unavailable"""

        mock_vector_stats = {"total_chunks": 5, "embedding_model": "mock"}

        with (
            patch("services.vector_service_factory.vector_service") as mock_vs,
            patch("services.rag_service.rag_service") as mock_rag,
        ):
            mock_vs.get_collection_stats.return_value = mock_vector_stats
            mock_rag.claude_service = None
            mock_rag.question_templates = {"mc": "template"}

            response = client.get("/api/v1/rag/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["components"]["claude_service"]["status"] == "unavailable"
        assert data["components"]["claude_service"]["fallback_enabled"] is True


class TestRAGAPIIntegration:
    """Integration Tests für RAG API mit echten Services"""

    @pytest.fixture(autouse=True)
    def ensure_rag_router(self):
        """Ensure the RAG router is registered"""
        import api.rag_exams as rag_module

        route_paths = [r.path for r in app.routes]
        if "/api/v1/rag/generate-exam" not in route_paths:
            app.include_router(rag_module.router)

    def test_full_rag_workflow_mock(self, auth_client, mock_db):
        """Test vollständiger RAG Workflow mit Mocks"""

        mock_doc = Mock()
        mock_doc.id = 1
        mock_doc.original_filename = "integration_test.txt"
        mock_doc.status = DocumentStatus.PROCESSED
        mock_doc.vector_collection = "test"
        mock_doc.doc_metadata = {}
        mock_doc.created_at = None
        mock_doc.processed_at = None
        mock_doc.mime_type = "text/plain"
        mock_doc.institution_id = 1
        mock_doc.file_size = 2048

        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_doc]

        with patch.object(TenantFilter, "filter_by_tenant", return_value=mock_query):
            docs_response = auth_client.get("/api/v1/rag/available-documents")
            assert docs_response.status_code == 200
            assert docs_response.json()["total_documents"] == 1

        mock_context = Mock()
        mock_context.query = "Integration Test"
        mock_context.retrieved_chunks = []
        mock_context.total_similarity_score = 1.0
        mock_context.source_documents = [{"id": 1, "filename": "integration_test.txt"}]
        mock_context.context_length = 100

        with (
            patch.object(
                actual_document_service,
                "get_document_by_id",
                return_value=Mock(institution_id=1),
            ),
            patch("services.rag_service.rag_service") as mock_rag_service,
        ):
            mock_rag_service.retrieve_context = AsyncMock(return_value=mock_context)
            context_response = auth_client.post(
                "/api/v1/rag/retrieve-context",
                json={
                    "query": "Integration Test",
                    "document_ids": [1],
                    "max_chunks": 3,
                },
            )
            assert context_response.status_code == 200
            assert context_response.json()["query"] == "Integration Test"

        with (
            patch("api.rag_exams.document_service") as mock_doc_service,
            patch("api.rag_exams.generate_questions_task") as mock_task,
            patch("api.rag_exams.QuestionGenerationJob") as mock_job_cls,
            patch("utils.tenant_utils.SubscriptionLimits"),
        ):
            mock_doc_service.get_document_by_id.return_value = mock_doc
            mock_task.apply_async.return_value = MagicMock()
            mock_job_cls.return_value = MagicMock()

            exam_response = auth_client.post(
                "/api/v1/rag/generate-exam",
                json={"topic": "Test Topic", "document_ids": [1], "question_count": 1},
            )
            assert exam_response.status_code == 200
            exam_data = exam_response.json()
            assert "task_id" in exam_data
            assert "message" in exam_data

    def test_error_handling_chain(self, auth_client):
        """Test Error Handling in der gesamten Chain"""

        with patch.object(
            actual_document_service, "get_document_by_id", return_value=None
        ):
            response = auth_client.post(
                "/api/v1/rag/generate-exam",
                json={"topic": "Test", "document_ids": [999], "question_count": 1},
            )
            assert response.status_code == 404

    def test_concurrent_requests(self):
        """Test gleichzeitige RAG Requests (public endpoint)"""
        import threading

        results = []

        def make_request():
            response = client.get("/api/v1/rag/question-types")
            results.append(response.status_code)

        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert all(status == 200 for status in results)
        assert len(results) == 5


class TestRAGQuestionPersistence:
    """Tests for async question generation via Celery tasks"""

    @pytest.fixture(autouse=True)
    def ensure_rag_router(self):
        """Ensure the RAG router is registered"""
        import api.rag_exams as rag_module

        route_paths = [r.path for r in app.routes]
        if "/api/v1/rag/generate-exam" not in route_paths:
            app.include_router(rag_module.router)

    @pytest.fixture
    def sample_rag_response(self):
        context = Mock()
        context.query = "Test Topic"
        context.retrieved_chunks = []
        context.total_similarity_score = 1.5
        context.source_documents = [{"id": 1, "filename": "test.txt", "chunks_used": 2}]
        context.context_length = 150

        q1 = Mock()
        q1.question_text = "Was ist Unit Testing?"
        q1.question_type = "multiple_choice"
        q1.options = ["A) Spass", "B) Qualitaet", "C) Zeitverschwendung", "D) Kunst"]
        q1.correct_answer = "B"
        q1.explanation = "Unit Testing sichert Qualitaet"
        q1.difficulty = "medium"
        q1.source_chunks = ["chunk_1"]
        q1.source_documents = ["test.txt"]
        q1.confidence_score = 0.85

        q2 = Mock()
        q2.question_text = "Erklaeren Sie TDD."
        q2.question_type = "open_ended"
        q2.options = None
        q2.correct_answer = "TDD ist test-getriebene Entwicklung..."
        q2.explanation = "Vollstaendigkeit und Verstaendnis"
        q2.difficulty = "medium"
        q2.source_chunks = ["chunk_2"]
        q2.source_documents = ["test.txt"]
        q2.confidence_score = 0.78

        response = Mock()
        response.exam_id = "persist_test_exam_001"
        response.topic = "Test Topic"
        response.questions = [q1, q2]
        response.context_summary = context
        response.generation_time = 2.5
        response.quality_metrics = {"total_questions": 2, "average_confidence": 0.815}
        return response

    def test_generate_exam_returns_task_id(
        self, auth_client, mock_db, sample_rag_response
    ):
        """Generate-exam endpoint now returns task_id for async processing"""
        with (
            patch("api.rag_exams.document_service") as mock_doc_svc,
            patch("api.rag_exams.generate_questions_task") as mock_task,
            patch("api.rag_exams.QuestionGenerationJob") as mock_job_cls,
            patch("utils.tenant_utils.SubscriptionLimits"),
        ):
            mock_doc_svc.get_document_by_id.return_value = None
            mock_task.apply_async.return_value = MagicMock()
            mock_job_cls.return_value = MagicMock()

            response = auth_client.post(
                "/api/v1/rag/generate-exam",
                json={"topic": "Test Topic", "question_count": 2},
            )

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "message" in data

    def test_generate_exam_starts_async_task(
        self, mock_user, mock_db, sample_rag_response
    ):
        """Generate-exam endpoint starts a Celery task for async generation"""
        from utils.auth_utils import get_current_user, get_current_active_user
        from database import get_db

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_current_active_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            with (
                patch("api.rag_exams.document_service") as mock_doc_svc,
                patch("api.rag_exams.generate_questions_task") as mock_task,
                patch("api.rag_exams.QuestionGenerationJob") as mock_job_cls,
                patch("utils.tenant_utils.SubscriptionLimits"),
            ):
                mock_doc_svc.get_document_by_id.return_value = None
                mock_task.apply_async.return_value = MagicMock()
                mock_job_cls.return_value = MagicMock()

                test_client = TestClient(app)
                response = test_client.post(
                    "/api/v1/rag/generate-exam",
                    json={"topic": "Test Topic", "question_count": 2},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "message" in data
        mock_task.apply_async.assert_called_once()
