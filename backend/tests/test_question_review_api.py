"""
API Integration Tests für Question Review Endpoints
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime

from main import app
from models.question_review import ReviewStatus


class TestQuestionReviewAPI:
    """Test Suite für Question Review API Endpoints"""

    @pytest.fixture(autouse=True)
    def ensure_question_review_router(self):
        """Routes are normally registered by main.py's lifespan; when tests
        run this file in isolation lifespan never fires, so register the
        router directly. Mirrors test_rag_api.ensure_rag_router."""
        import api.question_review as qr_module

        route_paths = [r.path for r in app.routes]
        if "/api/v1/questions/review" not in route_paths:
            app.include_router(qr_module.router)

    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user"""
        mock_institution = Mock()
        mock_institution.id = 1
        mock_institution.name = "Test University"
        mock_institution.slug = "test-university"
        mock_institution.subscription_tier = "professional"
        mock_institution.max_users = 100
        mock_institution.max_documents = 1000
        mock_institution.max_questions_per_month = -1

        user = Mock()
        user.id = 1
        user.email = "reviewer@example.com"
        user.first_name = "Test"
        user.last_name = "Reviewer"
        user.institution_id = 1
        user.institution = mock_institution
        user.has_permission = Mock(return_value=True)
        user.is_superuser = False
        user.roles = []
        return user

    @pytest.fixture
    def auth_client(self, mock_user):
        """FastAPI Test Client with auth overrides"""
        from utils.auth_utils import get_current_user, get_current_active_user
        from database import get_db

        mock_db = MagicMock()
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_current_active_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        client = TestClient(app)
        yield client, mock_db
        app.dependency_overrides.clear()

    @pytest.fixture
    def mock_question_review(self):
        """Mock QuestionReview Object"""
        mock = Mock()
        mock.id = 1
        mock.question_text = "What is a heap data structure?"
        mock.question_type = "multiple_choice"
        mock.options = [
            "A tree-based structure",
            "A linear structure",
            "A graph structure",
            "A hash table",
        ]
        mock.correct_answer = "A tree-based structure"
        mock.explanation = "A heap is a specialized tree-based data structure."
        mock.difficulty = "medium"
        mock.topic = "Data Structures"
        mock.language = "en"
        mock.source_chunks = ["Heap is a tree-based structure..."]
        mock.source_documents = ["algorithms_textbook.pdf"]
        mock.confidence_score = 0.85
        mock.bloom_level = 3
        mock.estimated_time_minutes = 5
        mock.quality_tier = "A"
        # TF-383: Provenance-Snapshot — muss gesetzt sein, sonst liefert der Mock
        # ein Mock-Attribut, das Pydantic nicht als Optional[Dict] validieren kann.
        mock.generation_metadata = {
            "prompt_id": "uuid-1",
            "prompt_name": "custom_mcq",
            "prompt_version": 2,
            "is_default_template": False,
            "variables": {"topic": "Data Structures"},
        }
        mock.review_status = ReviewStatus.PENDING.value
        mock.reviewed_by = None
        mock.reviewed_at = None
        mock.exam_id = "exam_123"
        mock.archived_at = None  # TF-396: Archiv-Achse
        mock.archived_by = None
        mock.archive_reason = None
        mock.created_at = datetime.now()
        mock.updated_at = datetime.now()
        mock.tags = []  # TF-320: route iterates q.tags — must be a real iterable
        return mock

    # ==================== GET /api/v1/questions/review ====================

    def test_get_review_queue_success(self, auth_client, mock_question_review):
        """Test erfolgreiche Review Queue Abfrage"""
        client, mock_db = auth_client

        # Mock Query Chain for main query
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = [mock_question_review]
        mock_query.count.return_value = 1

        mock_db.query.return_value = mock_query

        response = client.get("/api/v1/questions/review")

        assert response.status_code == 200

    def test_get_review_queue_requires_auth(self):
        """Test Review Queue requires authentication"""
        # Use client without auth overrides
        client = TestClient(app)
        response = client.get("/api/v1/questions/review")
        assert response.status_code == 401

    def test_get_review_queue_invalid_status(self):
        """Test Review Queue mit ungültigem Status"""
        client = TestClient(app)
        response = client.get(
            "/api/v1/questions/review", params={"status": "invalid_status"}
        )

        assert response.status_code in [401, 422]  # Auth or validation error

    # ==================== GET /api/v1/questions/{id}/review ====================

    def test_get_question_review_success(self, auth_client, mock_question_review):
        """Test erfolgreiche Question Review Details Abfrage"""
        client, mock_db = auth_client

        mock_question_review.comments = []
        mock_question_review.history = []

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_question_review
        mock_db.query.return_value = mock_query

        response = client.get("/api/v1/questions/1/review")

        assert response.status_code == 200
        # TF-383: Provenance-Snapshot wird durch die API-Serialisierung gereicht.
        body = response.json()
        assert body["generation_metadata"]["prompt_name"] == "custom_mcq"
        assert body["generation_metadata"]["prompt_version"] == 2
        assert body["generation_metadata"]["is_default_template"] is False

    def test_get_question_review_not_found(self, auth_client):
        """Test Question Review nicht gefunden"""
        client, mock_db = auth_client

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query

        response = client.get("/api/v1/questions/999/review")

        assert response.status_code == 404

    def test_get_question_review_denies_cross_tenant(self, auth_client, mock_user):
        """TF-383 review: the by-id detail endpoint is institution-scoped — a
        question outside the caller's tenant resolves to 404, so neither the
        question nor its generation_metadata leaks across institutions."""
        client, mock_db = auth_client

        # Simulate the tenant-scoped query finding nothing in the caller's scope.
        scoped_query = MagicMock()
        scoped_query.filter.return_value = scoped_query
        scoped_query.first.return_value = None

        with patch(
            "api.question_review.TenantFilter.filter_by_tenant",
            return_value=scoped_query,
        ) as tenant_spy:
            response = client.get("/api/v1/questions/999/review")

        assert response.status_code == 404
        # Assert the CALLER's tenant is what scopes the query (not merely that
        # *some* scoping ran) — catches a regression that passes the wrong
        # institution_id. filter_by_tenant(query, model, tenant_context).
        assert tenant_spy.called
        tenant_context = tenant_spy.call_args.args[2]
        assert tenant_context.institution_id == mock_user.institution_id

    # By-id endpoints that must all route through _get_scoped_question. Format:
    # (http_method, path, json_body_or_None, mutates_db).
    _BY_ID_ENDPOINTS = [
        ("get", "/api/v1/questions/777/review", None, False),
        ("put", "/api/v1/questions/777/edit", {"bloom_level": 3}, True),
        ("post", "/api/v1/questions/777/start-review", None, True),
        ("post", "/api/v1/questions/777/approve", {"reason": "ok"}, True),
        ("post", "/api/v1/questions/777/reject", {"reason": "no"}, True),
        ("post", "/api/v1/questions/777/comments", {"comment_text": "hi"}, True),
        ("get", "/api/v1/questions/777/comments", None, False),
        ("get", "/api/v1/questions/777/history", None, False),
        # TF-387: tag endpoints must also route through _get_scoped_question
        # (previously used a raw institution_id == filter without superuser bypass).
        ("post", "/api/v1/questions/777/tags", {"tag_ids": [1]}, True),
        ("delete", "/api/v1/questions/777/tags/5", None, True),
    ]

    @pytest.mark.parametrize("method,path,body,mutates", _BY_ID_ENDPOINTS)
    def test_by_id_endpoints_are_tenant_scoped(
        self, auth_client, method, path, body, mutates
    ):
        """TF-383 review: EVERY by-id endpoint must fetch via the institution-scoped
        path (TenantFilter.filter_by_tenant). When the scoped query finds nothing
        (question not visible in the caller's tenant), the endpoint answers 404 and
        performs no mutation. An endpoint reverted to an unscoped fetch would not
        call filter_by_tenant → `tenant_spy.called` fails."""
        client, mock_db = auth_client

        # Real _get_scoped_question runs; we stub the tenant filter to yield a
        # query that resolves to None (same seam as test_get_question_review_*).
        scoped_query = MagicMock()
        scoped_query.filter.return_value = scoped_query
        scoped_query.first.return_value = None

        with patch(
            "api.question_review.TenantFilter.filter_by_tenant",
            return_value=scoped_query,
        ) as tenant_spy:
            request = getattr(client, method)
            response = request(path, json=body) if body is not None else request(path)

        assert response.status_code == 404
        assert tenant_spy.called, (
            f"{method.upper()} {path} did not apply tenant scoping"
        )
        if mutates:
            mock_db.commit.assert_not_called()

    # ==================== POST /api/v1/questions/{id}/approve ====================

    def test_approve_question_requires_auth(self):
        """Test Question Approval requires auth"""
        client = TestClient(app)
        response = client.post(
            "/api/v1/questions/1/approve",
            json={"reason": "Meets all quality criteria"},
        )
        assert response.status_code == 401

    # ==================== POST /api/v1/questions/{id}/reject ====================

    def test_reject_question_requires_auth(self):
        """Test Question Rejection requires auth"""
        client = TestClient(app)
        response = client.post(
            "/api/v1/questions/1/reject",
            json={"reason": "Question is ambiguous"},
        )
        assert response.status_code == 401

    # ==================== GET /api/v1/questions/{id}/history ====================

    def test_get_review_history_success(self, auth_client):
        """Test erfolgreiche Review History Abfrage - history endpoint has no auth"""
        client, mock_db = auth_client

        mock_question = MagicMock()
        mock_question.id = 1

        mock_history = MagicMock()
        mock_history.id = 1
        mock_history.question_id = 1
        mock_history.action = "status_changed"
        mock_history.old_status = "pending"
        mock_history.new_status = "approved"
        mock_history.changed_fields = None
        mock_history.changed_by = "reviewer_1"
        mock_history.change_reason = "Meets all quality criteria"
        mock_history.changed_at = datetime.now()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_question
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_history]
        mock_db.query.return_value = mock_query

        response = client.get("/api/v1/questions/1/history")

        assert response.status_code == 200


class TestReviewQueueOptionsShape:
    """TF-330: ``ReviewQueueResponse`` must tolerate legacy dict-shaped options.

    Older generation paths persisted ``options`` as ``{'A': ..., 'B': ...}``;
    the schema expects ``List[str]``. A ``before`` field validator normalizes
    both shapes so the read path never 500s on a legacy row. We exercise the
    schema directly (instead of through TestClient) because the regression
    surfaced during Pydantic validation of the response body — that's the
    exact code path the validator guards.
    """

    @staticmethod
    def _question_payload(options):
        return {
            "id": 1,
            "question_text": "Welche Empfehlung gilt für E-Mails?",
            "question_type": "multiple_choice",
            "options": options,
            "correct_answer": "A",
            "explanation": "Aktive Sprache ist klarer.",
            "difficulty": "medium",
            "topic": "Kommunikation",
            "language": "de",
            "source_chunks": [],
            "source_documents": [],
            "confidence_score": 0.9,
            "bloom_level": 3,
            "estimated_time_minutes": 2,
            "quality_tier": "A",
            "review_status": ReviewStatus.PENDING.value,
            "reviewed_by": None,
            "reviewed_at": None,
            "exam_id": "exam_demo",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

    @staticmethod
    def _build_response(questions):
        # Imported locally to avoid pulling in api.question_review at module
        # collection time (tests in this file already do so via TestClient
        # paths above; keep parity).
        from api.question_review import ReviewQueueResponse

        return ReviewQueueResponse(
            total=len(questions),
            pending=len(questions),
            approved=0,
            rejected=0,
            in_review=0,
            questions=questions,
        )

    def test_dict_shaped_legacy_options_normalize_to_list_sorted_by_key(self):
        legacy = {
            "A": "Verwenden Sie aktive Sprache",
            "B": "Schreiben Sie passiv",
            "C": "Antworten Sie spät",
            "D": "Melden Sie sich bis Freitag",
        }

        response = self._build_response([self._question_payload(legacy)])

        assert response.questions[0].options == [
            "Verwenden Sie aktive Sprache",
            "Schreiben Sie passiv",
            "Antworten Sie spät",
            "Melden Sie sich bis Freitag",
        ]

    def test_list_shaped_options_round_trip_unchanged(self):
        list_options = ["alpha", "beta", "gamma", "delta"]

        response = self._build_response([self._question_payload(list_options)])

        assert response.questions[0].options == list_options

    def test_none_options_remain_none(self):
        response = self._build_response([self._question_payload(None)])

        assert response.questions[0].options is None
