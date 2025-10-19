"""
Unit Tests für Review Service
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from sqlalchemy.orm import Session

from services.review_service import ReviewService
from models.question_review import QuestionReview, ReviewComment, ReviewHistory, ReviewStatus


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
    
    # ==================== get_pending_reviews ====================
    
    def test_get_pending_reviews_success(self, mock_db, mock_question_review):
        """Test erfolgreiche Abfrage von pending reviews"""
        # Mock Query Chain
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_question_review]
        mock_query.count.return_value = 1
        
        mock_db.query.return_value = mock_query
        
        # Execute
        questions, total, pending, approved, rejected, in_review = ReviewService.get_pending_reviews(
            db=mock_db,
            status=None,
            limit=50,
            offset=0
        )
        
        # Assert
        assert len(questions) == 1
        assert questions[0].id == 1
        assert total == 1
        assert pending == 1
    
    def test_get_pending_reviews_with_filters(self, mock_db, mock_question_review):
        """Test Abfrage mit Filtern"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_question_review]
        mock_query.count.return_value = 1
        
        mock_db.query.return_value = mock_query
        
        questions, total, pending, approved, rejected, in_review = ReviewService.get_pending_reviews(
            db=mock_db,
            status=ReviewStatus.PENDING.value,
            difficulty="medium",
            question_type="multiple_choice",
            limit=10,
            offset=0
        )
        
        assert len(questions) == 1
        assert total == 1
    
    # ==================== approve_question ====================
    
    def test_approve_question_success(self, mock_db, mock_question_review):
        """Test erfolgreiche Question Approval"""
        # Mock Query
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_question_review
        mock_db.query.return_value = mock_query
        
        # Execute
        result = ReviewService.approve_question(
            db=mock_db,
            question_id=1,
            reviewer_id="reviewer_1",
            reason="Meets criteria"
        )
        
        # Assert
        assert result.review_status == ReviewStatus.APPROVED.value
        assert result.reviewed_by == "reviewer_1"
        assert result.reviewed_at is not None
        mock_db.commit.assert_called_once()
    
    def test_approve_question_not_found(self, mock_db):
        """Test Approval für nicht existierende Question"""
        from fastapi import HTTPException
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        with pytest.raises(HTTPException) as exc_info:
            ReviewService.approve_question(
                db=mock_db,
                question_id=999,
                reviewer_id="reviewer_1"
            )
        
        assert exc_info.value.status_code == 404
    
    # ==================== reject_question ====================
    
    def test_reject_question_success(self, mock_db, mock_question_review):
        """Test erfolgreiche Question Rejection"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_question_review
        mock_db.query.return_value = mock_query
        
        result = ReviewService.reject_question(
            db=mock_db,
            question_id=1,
            reviewer_id="reviewer_1",
            reason="Ambiguous question"
        )
        
        assert result.review_status == ReviewStatus.REJECTED.value
        assert result.reviewed_by == "reviewer_1"
        mock_db.commit.assert_called_once()
    
    # ==================== edit_question ====================
    
    def test_edit_question_success(self, mock_db, mock_question_review):
        """Test erfolgreiche Question Edit"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_question_review
        mock_db.query.return_value = mock_query
        
        updates = {
            "question_text": "Updated question",
            "difficulty": "hard"
        }
        
        result = ReviewService.edit_question(
            db=mock_db,
            question_id=1,
            updates=updates,
            editor_id="teacher_1"
        )
        
        assert result.question_text == "Updated question"
        assert result.difficulty == "hard"
        assert result.review_status == ReviewStatus.EDITED.value
        mock_db.commit.assert_called_once()
    
    def test_edit_question_no_changes(self, mock_db, mock_question_review):
        """Test Edit ohne Änderungen"""
        from fastapi import HTTPException
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_question_review
        mock_db.query.return_value = mock_query
        
        with pytest.raises(HTTPException) as exc_info:
            ReviewService.edit_question(
                db=mock_db,
                question_id=1,
                updates={},
                editor_id="teacher_1"
            )
        
        assert exc_info.value.status_code == 400
        assert "No changes provided" in str(exc_info.value.detail)
    
    # ==================== add_comment ====================
    
    def test_add_comment_success(self, mock_db, mock_question_review):
        """Test erfolgreiche Comment Hinzufügung"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_question_review
        mock_db.query.return_value = mock_query
        
        result = ReviewService.add_comment(
            db=mock_db,
            question_id=1,
            comment_text="Great question!",
            comment_type="general",
            author="reviewer_1",
            author_role="senior_reviewer"
        )
        
        assert result.comment_text == "Great question!"
        assert result.author == "reviewer_1"
        assert result.question_review_id == 1
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_add_comment_question_not_found(self, mock_db):
        """Test Comment für nicht existierende Question"""
        from fastapi import HTTPException
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        with pytest.raises(HTTPException) as exc_info:
            ReviewService.add_comment(
                db=mock_db,
                question_id=999,
                comment_text="Comment",
                comment_type="general",
                author="reviewer_1"
            )
        
        assert exc_info.value.status_code == 404
    
    # ==================== get_review_history ====================
    
    def test_get_review_history_success(self, mock_db):
        """Test erfolgreiche History Abfrage"""
        mock_history = Mock(spec=ReviewHistory)
        mock_history.id = 1
        mock_history.question_review_id = 1
        mock_history.changed_by = "reviewer_1"
        mock_history.change_type = "status_change"
        mock_history.old_value = "pending"
        mock_history.new_value = "approved"
        mock_history.created_at = datetime.now()
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_history]
        mock_db.query.return_value = mock_query
        
        result = ReviewService.get_review_history(db=mock_db, question_id=1)
        
        assert len(result) == 1
        assert result[0].change_type == "status_change"
        assert result[0].old_value == "pending"
        assert result[0].new_value == "approved"
    
    # ==================== get_question_review ====================
    
    def test_get_question_review_success(self, mock_db, mock_question_review):
        """Test erfolgreiche Question Review Details Abfrage"""
        mock_comment = Mock(spec=ReviewComment)
        mock_comment.id = 1
        mock_comment.comment_text = "Good question"
        
        mock_history = Mock(spec=ReviewHistory)
        mock_history.id = 1
        mock_history.change_type = "status_change"
        
        # Mock Queries
        mock_question_query = MagicMock()
        mock_question_query.filter.return_value = mock_question_query
        mock_question_query.first.return_value = mock_question_review
        
        mock_comment_query = MagicMock()
        mock_comment_query.filter.return_value = mock_comment_query
        mock_comment_query.order_by.return_value = mock_comment_query
        mock_comment_query.all.return_value = [mock_comment]
        
        mock_history_query = MagicMock()
        mock_history_query.filter.return_value = mock_history_query
        mock_history_query.order_by.return_value = mock_history_query
        mock_history_query.all.return_value = [mock_history]
        
        # Setup query return based on model type
        def query_side_effect(model):
            if model == QuestionReview:
                return mock_question_query
            elif model == ReviewComment:
                return mock_comment_query
            elif model == ReviewHistory:
                return mock_history_query
        
        mock_db.query.side_effect = query_side_effect
        
        question, comments, history = ReviewService.get_question_review(
            db=mock_db,
            question_id=1
        )
        
        assert question.id == 1
        assert len(comments) == 1
        assert len(history) == 1
    
    def test_get_question_review_not_found(self, mock_db):
        """Test Question Review nicht gefunden"""
        from fastapi import HTTPException
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        with pytest.raises(HTTPException) as exc_info:
            ReviewService.get_question_review(db=mock_db, question_id=999)
        
        assert exc_info.value.status_code == 404

