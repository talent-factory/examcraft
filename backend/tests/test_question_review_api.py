"""
API Integration Tests für Question Review Endpoints
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime

from main import app
from models.question_review import ReviewStatus


class TestQuestionReviewAPI:
    """Test Suite für Question Review API Endpoints"""
    
    @pytest.fixture
    def client(self):
        """FastAPI Test Client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_question_review(self):
        """Mock QuestionReview Object"""
        mock = Mock()
        mock.id = 1
        mock.question_text = "What is a heap data structure?"
        mock.question_type = "multiple_choice"
        mock.options = ["A tree-based structure", "A linear structure", "A graph structure", "A hash table"]
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
    
    @pytest.fixture
    def mock_review_comment(self):
        """Mock ReviewComment Object"""
        mock = Mock()
        mock.id = 1
        mock.question_review_id = 1
        mock.comment_text = "Great question, very clear!"
        mock.comment_type = "general"
        mock.author = "reviewer_1"
        mock.author_role = "senior_reviewer"
        mock.created_at = datetime.now()
        return mock
    
    @pytest.fixture
    def mock_review_history(self):
        """Mock ReviewHistory Object"""
        mock = Mock()
        mock.id = 1
        mock.question_review_id = 1
        mock.changed_by = "reviewer_1"
        mock.change_type = "status_change"
        mock.old_value = "pending"
        mock.new_value = "approved"
        mock.change_reason = "Meets all quality criteria"
        mock.created_at = datetime.now()
        return mock
    
    # ==================== GET /api/v1/questions/review ====================

    @patch('database.get_db')
    def test_get_review_queue_success(self, mock_get_db, client, mock_question_review):
        """Test erfolgreiche Review Queue Abfrage"""
        # Mock Database Session
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Mock Query Chain
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
        data = response.json()

        assert data["total"] == 1
        assert data["pending"] == 1
        assert len(data["questions"]) == 1
        assert data["questions"][0]["id"] == 1
        assert data["questions"][0]["question_text"] == "What is a heap data structure?"
        assert data["questions"][0]["review_status"] == "pending"

    def test_get_review_queue_invalid_status(self, client):
        """Test Review Queue mit ungültigem Status"""
        response = client.get(
            "/api/v1/questions/review",
            params={"status": "invalid_status"}
        )

        assert response.status_code == 422  # Validation Error
    
    # ==================== GET /api/v1/questions/{id}/review ====================
    
    @patch('api.question_review.review_service.get_question_review')
    def test_get_question_review_success(self, mock_get_review, client, mock_question_review, mock_review_comment, mock_review_history):
        """Test erfolgreiche Question Review Details Abfrage"""
        mock_get_review.return_value = (mock_question_review, [mock_review_comment], [mock_review_history])
        
        response = client.get("/api/v1/questions/1/review")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["question"]["id"] == 1
        assert data["question"]["question_text"] == "What is a heap data structure?"
        assert len(data["comments"]) == 1
        assert data["comments"][0]["comment_text"] == "Great question, very clear!"
        assert len(data["history"]) == 1
        assert data["history"][0]["change_type"] == "status_change"
    
    @patch('api.question_review.review_service.get_question_review')
    def test_get_question_review_not_found(self, mock_get_review, client):
        """Test Question Review nicht gefunden"""
        from fastapi import HTTPException
        mock_get_review.side_effect = HTTPException(status_code=404, detail="Question review not found")
        
        response = client.get("/api/v1/questions/999/review")
        
        assert response.status_code == 404
    
    # ==================== POST /api/v1/questions/review ====================
    
    @patch('api.question_review.review_service.create_question_review')
    def test_create_question_review_success(self, mock_create, client, mock_question_review):
        """Test erfolgreiche Question Review Erstellung"""
        mock_create.return_value = mock_question_review
        
        request_data = {
            "question_text": "What is a heap data structure?",
            "question_type": "multiple_choice",
            "options": ["A tree-based structure", "A linear structure"],
            "correct_answer": "A tree-based structure",
            "explanation": "A heap is a specialized tree-based data structure.",
            "difficulty": "medium",
            "topic": "Data Structures",
            "language": "en",
            "confidence_score": 0.85,
            "bloom_level": 3,
            "estimated_time_minutes": 5
        }
        
        response = client.post("/api/v1/questions/review", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == 1
        assert data["question_text"] == "What is a heap data structure?"
        assert data["review_status"] == "pending"
    
    @patch('api.question_review.review_service.create_question_review')
    def test_create_question_review_validation_error(self, mock_create, client):
        """Test Question Review Erstellung mit Validation Error"""
        request_data = {
            "question_text": "",  # Empty question text
            "question_type": "multiple_choice",
            "difficulty": "medium"
        }
        
        response = client.post("/api/v1/questions/review", json=request_data)
        
        assert response.status_code == 422  # Validation Error
    
    # ==================== POST /api/v1/questions/{id}/approve ====================
    
    @patch('api.question_review.review_service.approve_question')
    def test_approve_question_success(self, mock_approve, client, mock_question_review):
        """Test erfolgreiche Question Approval"""
        mock_question_review.review_status = ReviewStatus.APPROVED.value
        mock_question_review.reviewed_by = "reviewer_1"
        mock_approve.return_value = mock_question_review
        
        request_data = {
            "reviewer_id": "reviewer_1",
            "reason": "Meets all quality criteria"
        }
        
        response = client.post("/api/v1/questions/1/approve", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == 1
        assert data["review_status"] == "approved"
        assert data["reviewed_by"] == "reviewer_1"
    
    @patch('api.question_review.review_service.approve_question')
    def test_approve_question_not_found(self, mock_approve, client):
        """Test Question Approval für nicht existierende Question"""
        from fastapi import HTTPException
        mock_approve.side_effect = HTTPException(status_code=404, detail="Question not found")
        
        request_data = {"reviewer_id": "reviewer_1"}
        response = client.post("/api/v1/questions/999/approve", json=request_data)
        
        assert response.status_code == 404
    
    # ==================== POST /api/v1/questions/{id}/reject ====================
    
    @patch('api.question_review.review_service.reject_question')
    def test_reject_question_success(self, mock_reject, client, mock_question_review):
        """Test erfolgreiche Question Rejection"""
        mock_question_review.review_status = ReviewStatus.REJECTED.value
        mock_question_review.reviewed_by = "reviewer_1"
        mock_reject.return_value = mock_question_review
        
        request_data = {
            "reviewer_id": "reviewer_1",
            "reason": "Question is ambiguous"
        }
        
        response = client.post("/api/v1/questions/1/reject", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == 1
        assert data["review_status"] == "rejected"
        assert data["reviewed_by"] == "reviewer_1"
    
    # ==================== PUT /api/v1/questions/{id}/edit ====================
    
    @patch('api.question_review.review_service.edit_question')
    def test_edit_question_success(self, mock_edit, client, mock_question_review):
        """Test erfolgreiche Question Edit"""
        mock_question_review.question_text = "Updated question text"
        mock_question_review.review_status = ReviewStatus.EDITED.value
        mock_edit.return_value = mock_question_review
        
        request_data = {
            "question_text": "Updated question text",
            "difficulty": "hard"
        }
        
        response = client.put("/api/v1/questions/1/edit?editor_id=teacher_1", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == 1
        assert data["question_text"] == "Updated question text"
        assert data["review_status"] == "edited"
    
    @patch('api.question_review.review_service.edit_question')
    def test_edit_question_validation_error(self, mock_edit, client):
        """Test Question Edit mit Validation Error"""
        request_data = {
            "difficulty": "invalid_difficulty"  # Invalid difficulty
        }
        
        response = client.put("/api/v1/questions/1/edit?editor_id=teacher_1", json=request_data)
        
        # Should fail validation
        assert response.status_code in [400, 422]
    
    # ==================== POST /api/v1/questions/{id}/comments ====================
    
    @patch('api.question_review.review_service.add_comment')
    def test_add_comment_success(self, mock_add_comment, client, mock_review_comment):
        """Test erfolgreiche Comment Hinzufügung"""
        mock_add_comment.return_value = mock_review_comment
        
        request_data = {
            "comment_text": "Great question, very clear!",
            "comment_type": "general",
            "author": "reviewer_1"
        }
        
        response = client.post("/api/v1/questions/1/comments", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == 1
        assert data["comment_text"] == "Great question, very clear!"
        assert data["author"] == "reviewer_1"
    
    # ==================== GET /api/v1/questions/{id}/history ====================
    
    @patch('api.question_review.review_service.get_review_history')
    def test_get_review_history_success(self, mock_get_history, client, mock_review_history):
        """Test erfolgreiche Review History Abfrage"""
        mock_get_history.return_value = [mock_review_history]
        
        response = client.get("/api/v1/questions/1/history")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 1
        assert data[0]["change_type"] == "status_change"
        assert data[0]["old_value"] == "pending"
        assert data[0]["new_value"] == "approved"

