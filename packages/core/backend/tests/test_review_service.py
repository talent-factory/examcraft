"""
Unit Tests für Review Service
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from sqlalchemy.orm import Session

from services.review_service import ReviewService
from models.question_review import (
    QuestionReview,
    ReviewHistory,
    ReviewStatus,
)


class TestReviewService:
    """Test Suite für ReviewService"""

    @pytest.fixture
    def mock_db(self):
        """Mock Database Session"""
        return MagicMock(spec=Session)

    @pytest.fixture
    def mock_question_review(self):
        """Mock QuestionReview Object"""
        mock = Mock(spec=QuestionReview)
        mock.id = 1
        mock.question_text = "What is a heap?"
        mock.question_type = "multiple_choice"
        mock.options = ["Tree", "Array", "Graph"]
        mock.correct_answer = "Tree"
        mock.explanation = "A heap is a tree-based structure"
        mock.difficulty = "medium"
        mock.topic = "Data Structures"
        mock.language = "en"
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

    @pytest.fixture
    def service(self, mock_db):
        """ReviewService instance with mock DB"""
        return ReviewService(mock_db)

    # ==================== get_pending_reviews ====================

    def test_get_pending_reviews_success(self, service, mock_db, mock_question_review):
        """Test erfolgreiche Abfrage von pending reviews"""
        # Mock Query Chain
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_question_review]

        mock_db.query.return_value = mock_query

        # Execute
        questions = service.get_pending_reviews(limit=50, offset=0)

        # Assert
        assert len(questions) == 1
        assert questions[0].id == 1

    def test_get_pending_reviews_with_filters(
        self, service, mock_db, mock_question_review
    ):
        """Test Abfrage mit Filtern"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_question_review]

        mock_db.query.return_value = mock_query

        questions = service.get_pending_reviews(
            difficulty="medium",
            question_type="multiple_choice",
            limit=10,
            offset=0,
        )

        assert len(questions) == 1

    # ==================== approve_question ====================

    def test_approve_question_success(self, service, mock_db, mock_question_review):
        """Test erfolgreiche Question Approval"""
        # Mock Query
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_question_review
        mock_db.query.return_value = mock_query

        # Execute
        result = service.approve_question(
            question_id=1, reviewer_id="reviewer_1", reason="Meets criteria"
        )

        # Assert
        assert result.review_status == ReviewStatus.APPROVED.value
        assert result.reviewed_by == "reviewer_1"
        assert result.reviewed_at is not None

    def test_approve_question_not_found(self, service, mock_db):
        """Test Approval für nicht existierende Question"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query

        with pytest.raises(ValueError) as exc_info:
            service.approve_question(question_id=999, reviewer_id="reviewer_1")

        assert "not found" in str(exc_info.value)

    # ==================== reject_question ====================

    def test_reject_question_success(self, service, mock_db, mock_question_review):
        """Test erfolgreiche Question Rejection"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_question_review
        mock_db.query.return_value = mock_query

        result = service.reject_question(
            question_id=1,
            reviewer_id="reviewer_1",
            reason="Ambiguous question",
        )

        assert result.review_status == ReviewStatus.REJECTED.value
        assert result.reviewed_by == "reviewer_1"

    # ==================== edit_question ====================

    def test_edit_question_success(self, service, mock_db, mock_question_review):
        """Test erfolgreiche Question Edit"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_question_review
        mock_db.query.return_value = mock_query

        updates = {"question_text": "Updated question", "difficulty": "hard"}

        result = service.edit_question(
            question_id=1, updates=updates, editor_id="teacher_1"
        )

        assert result.question_text == "Updated question"
        assert result.difficulty == "hard"
        assert result.review_status == ReviewStatus.EDITED.value

    def test_edit_question_no_changes(self, service, mock_db, mock_question_review):
        """Test Edit ohne Änderungen"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_question_review
        mock_db.query.return_value = mock_query

        # Pass empty updates - the service still returns the question
        # but does not set status to EDITED
        result = service.edit_question(question_id=1, updates={}, editor_id="teacher_1")

        # With empty updates, no fields change, so status stays as-is
        assert result.review_status == ReviewStatus.PENDING.value

    # ==================== add_comment ====================

    def test_add_comment_success(self, service, mock_db, mock_question_review):
        """Test erfolgreiche Comment Hinzufügung"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_question_review
        mock_db.query.return_value = mock_query

        service.add_comment(
            question_id=1,
            comment_text="Great question!",
            comment_type="general",
            author="reviewer_1",
            author_role="senior_reviewer",
        )

        # The service creates a ReviewComment and adds it to the DB
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()

    def test_add_comment_question_not_found(self, service, mock_db):
        """Test Comment für nicht existierende Question"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query

        with pytest.raises(ValueError) as exc_info:
            service.add_comment(
                question_id=999,
                comment_text="Comment",
                comment_type="general",
                author="reviewer_1",
            )

        assert "not found" in str(exc_info.value)

    # ==================== get_review_history ====================

    def test_get_review_history_success(self, mock_db):
        """Test erfolgreiche History Abfrage"""
        service = ReviewService(mock_db)

        mock_question = Mock(spec=QuestionReview)
        mock_question.id = 1

        mock_history = Mock(spec=ReviewHistory)
        mock_history.id = 1
        mock_history.question_id = 1
        mock_history.changed_by = "reviewer_1"
        mock_history.action = "approved"
        mock_history.old_status = "pending"
        mock_history.new_status = "approved"
        mock_history.changed_at = datetime.now()

        # First query returns question (exists check), second returns history
        mock_question_query = MagicMock()
        mock_question_query.filter.return_value = mock_question_query
        mock_question_query.first.return_value = mock_question

        mock_history_query = MagicMock()
        mock_history_query.filter.return_value = mock_history_query
        mock_history_query.order_by.return_value = mock_history_query
        mock_history_query.all.return_value = [mock_history]

        def query_side_effect(model):
            if model == QuestionReview:
                return mock_question_query
            elif model == ReviewHistory:
                return mock_history_query

        mock_db.query.side_effect = query_side_effect

        result = service.get_review_history(question_id=1)

        assert len(result) == 1
        assert result[0].action == "approved"

    # ==================== get_review_statistics ====================

    def test_get_review_statistics_success(self, mock_db):
        """Test erfolgreiche Statistik Abfrage"""
        service = ReviewService(mock_db)

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_db.query.return_value = mock_query

        result = service.get_review_statistics()

        assert "total" in result
        assert "pending" in result
        assert "approved" in result
        assert "rejected" in result
