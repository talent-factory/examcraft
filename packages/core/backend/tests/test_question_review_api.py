"""
API Integration Tests für Question Review Endpoints
"""

import pytest
from unittest.mock import Mock, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime

from main import app
from models.question_review import ReviewStatus


class TestQuestionReviewAPI:
    """Test Suite für Question Review API Endpoints"""

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
        mock.review_status = ReviewStatus.PENDING.value
        mock.reviewed_by = None
        mock.reviewed_at = None
        mock.exam_id = "exam_123"
        mock.created_at = datetime.now()
        mock.updated_at = datetime.now()
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

    def test_get_question_review_not_found(self, auth_client):
        """Test Question Review nicht gefunden"""
        client, mock_db = auth_client

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query

        response = client.get("/api/v1/questions/999/review")

        assert response.status_code == 404

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
