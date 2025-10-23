"""
Tests for Subscription Limits and Quota Enforcement
Tests unlimited quotas (-1) handling and quota exceeded scenarios
"""

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from models.auth import Institution, User, UserStatus
from models.document import Document, DocumentStatus
from models.question_review import QuestionReview, ReviewStatus
from utils.tenant_utils import SubscriptionLimits


class TestSubscriptionLimits:
    """Test suite for SubscriptionLimits quota enforcement"""

    # ==================== User Limit Tests ====================

    def test_check_user_limit_unlimited(self, test_db: Session, test_institution: Institution):
        """Test that unlimited user quota (-1) allows any number of users"""
        # Arrange: Set unlimited quota
        test_institution.max_users = -1
        test_db.commit()

        # Create 100 active users (way over any normal limit)
        for i in range(100):
            user = User(
                email=f"user{i}@test.com",
                username=f"user{i}",
                hashed_password="dummy",
                institution_id=test_institution.id,
                status=UserStatus.ACTIVE.value,
            )
            test_db.add(user)
        test_db.commit()

        # Act & Assert: Should not raise exception
        try:
            SubscriptionLimits.check_user_limit(test_institution, test_db)
        except HTTPException:
            pytest.fail("check_user_limit raised HTTPException for unlimited quota")

    def test_check_user_limit_exceeded(self, test_db: Session, test_institution: Institution):
        """Test that user limit is enforced when quota is set"""
        # Arrange: Set limit to 3 users
        test_institution.max_users = 3
        test_db.commit()

        # Create 3 active users (at limit)
        for i in range(3):
            user = User(
                email=f"user{i}@test.com",
                username=f"user{i}",
                hashed_password="dummy",
                institution_id=test_institution.id,
                status=UserStatus.ACTIVE.value,
            )
            test_db.add(user)
        test_db.commit()

        # Act & Assert: Should raise exception
        with pytest.raises(HTTPException) as exc_info:
            SubscriptionLimits.check_user_limit(test_institution, test_db)

        assert exc_info.value.status_code == 403
        assert "User limit reached" in exc_info.value.detail
        assert "3 users" in exc_info.value.detail

    def test_check_user_limit_not_exceeded(self, test_db: Session, test_institution: Institution):
        """Test that user limit allows creation when under quota"""
        # Arrange: Set limit to 5 users
        test_institution.max_users = 5
        test_db.commit()

        # Create 2 active users (under limit)
        for i in range(2):
            user = User(
                email=f"user{i}@test.com",
                username=f"user{i}",
                hashed_password="dummy",
                institution_id=test_institution.id,
                status=UserStatus.ACTIVE.value,
            )
            test_db.add(user)
        test_db.commit()

        # Act & Assert: Should not raise exception
        try:
            SubscriptionLimits.check_user_limit(test_institution, test_db)
        except HTTPException:
            pytest.fail("check_user_limit raised HTTPException when under quota")

    def test_check_user_limit_ignores_inactive_users(
        self, test_db: Session, test_institution: Institution
    ):
        """Test that inactive users don't count towards quota"""
        # Arrange: Set limit to 2 users
        test_institution.max_users = 2
        test_db.commit()

        # Create 1 active user
        active_user = User(
            email="active@test.com",
            username="active",
            hashed_password="dummy",
            institution_id=test_institution.id,
            status=UserStatus.ACTIVE.value,
        )
        test_db.add(active_user)

        # Create 5 inactive users
        for i in range(5):
            inactive_user = User(
                email=f"inactive{i}@test.com",
                username=f"inactive{i}",
                hashed_password="dummy",
                institution_id=test_institution.id,
                status=UserStatus.INACTIVE.value,
            )
            test_db.add(inactive_user)
        test_db.commit()

        # Act & Assert: Should not raise exception (only 1 active user)
        try:
            SubscriptionLimits.check_user_limit(test_institution, test_db)
        except HTTPException:
            pytest.fail("check_user_limit counted inactive users towards quota")

    # ==================== Document Limit Tests ====================

    def test_check_document_limit_unlimited(
        self, test_db: Session, test_institution: Institution
    ):
        """Test that unlimited document quota (-1) allows any number of documents"""
        # Arrange: Set unlimited quota
        test_institution.max_documents = -1
        test_db.commit()

        # Create 100 documents (way over any normal limit)
        for i in range(100):
            doc = Document(
                filename=f"doc{i}.pdf",
                file_path=f"/uploads/doc{i}.pdf",
                file_size=1024,
                mime_type="application/pdf",
                status=DocumentStatus.READY.value,
                institution_id=test_institution.id,
                uploaded_by=1,
            )
            test_db.add(doc)
        test_db.commit()

        # Act & Assert: Should not raise exception
        try:
            SubscriptionLimits.check_document_limit(test_institution, test_db)
        except HTTPException:
            pytest.fail("check_document_limit raised HTTPException for unlimited quota")

    def test_check_document_limit_exceeded(
        self, test_db: Session, test_institution: Institution
    ):
        """Test that document limit is enforced when quota is set"""
        # Arrange: Set limit to 5 documents
        test_institution.max_documents = 5
        test_db.commit()

        # Create 5 documents (at limit)
        for i in range(5):
            doc = Document(
                filename=f"doc{i}.pdf",
                file_path=f"/uploads/doc{i}.pdf",
                file_size=1024,
                mime_type="application/pdf",
                status=DocumentStatus.READY.value,
                institution_id=test_institution.id,
                uploaded_by=1,
            )
            test_db.add(doc)
        test_db.commit()

        # Act & Assert: Should raise exception
        with pytest.raises(HTTPException) as exc_info:
            SubscriptionLimits.check_document_limit(test_institution, test_db)

        assert exc_info.value.status_code == 403
        assert "Document limit reached" in exc_info.value.detail
        assert "5 documents" in exc_info.value.detail

    def test_check_document_limit_not_exceeded(
        self, test_db: Session, test_institution: Institution
    ):
        """Test that document limit allows upload when under quota"""
        # Arrange: Set limit to 10 documents
        test_institution.max_documents = 10
        test_db.commit()

        # Create 3 documents (under limit)
        for i in range(3):
            doc = Document(
                filename=f"doc{i}.pdf",
                file_path=f"/uploads/doc{i}.pdf",
                file_size=1024,
                mime_type="application/pdf",
                status=DocumentStatus.READY.value,
                institution_id=test_institution.id,
                uploaded_by=1,
            )
            test_db.add(doc)
        test_db.commit()

        # Act & Assert: Should not raise exception
        try:
            SubscriptionLimits.check_document_limit(test_institution, test_db)
        except HTTPException:
            pytest.fail("check_document_limit raised HTTPException when under quota")

    # ==================== Question Limit Tests ====================

    def test_check_question_limit_unlimited(
        self, test_db: Session, test_institution: Institution
    ):
        """Test that unlimited question quota (-1) allows any number of questions"""
        # Arrange: Set unlimited quota
        test_institution.max_questions_per_month = -1
        test_db.commit()

        # Create 1000 questions this month (way over any normal limit)
        for i in range(1000):
            question = QuestionReview(
                question_text=f"Question {i}?",
                question_type="multiple_choice",
                difficulty="medium",
                bloom_level="understand",
                status=ReviewStatus.PENDING.value,
                institution_id=test_institution.id,
                created_by=1,
                created_at=datetime.now(timezone.utc),
            )
            test_db.add(question)
        test_db.commit()

        # Act & Assert: Should not raise exception
        try:
            SubscriptionLimits.check_question_limit(test_institution, test_db)
        except HTTPException:
            pytest.fail("check_question_limit raised HTTPException for unlimited quota")

    def test_check_question_limit_exceeded(
        self, test_db: Session, test_institution: Institution
    ):
        """Test that question limit is enforced when quota is set"""
        # Arrange: Set limit to 20 questions/month
        test_institution.max_questions_per_month = 20
        test_db.commit()

        # Create 20 questions this month (at limit)
        for i in range(20):
            question = QuestionReview(
                question_text=f"Question {i}?",
                question_type="multiple_choice",
                difficulty="medium",
                bloom_level="understand",
                status=ReviewStatus.PENDING.value,
                institution_id=test_institution.id,
                created_by=1,
                created_at=datetime.now(timezone.utc),
            )
            test_db.add(question)
        test_db.commit()

        # Act & Assert: Should raise exception
        with pytest.raises(HTTPException) as exc_info:
            SubscriptionLimits.check_question_limit(test_institution, test_db)

        assert exc_info.value.status_code == 403
        assert "Monthly question limit reached" in exc_info.value.detail
        assert "20 questions" in exc_info.value.detail

    def test_check_question_limit_not_exceeded(
        self, test_db: Session, test_institution: Institution
    ):
        """Test that question limit allows generation when under quota"""
        # Arrange: Set limit to 100 questions/month
        test_institution.max_questions_per_month = 100
        test_db.commit()

        # Create 30 questions this month (under limit)
        for i in range(30):
            question = QuestionReview(
                question_text=f"Question {i}?",
                question_type="multiple_choice",
                difficulty="medium",
                bloom_level="understand",
                status=ReviewStatus.PENDING.value,
                institution_id=test_institution.id,
                created_by=1,
                created_at=datetime.now(timezone.utc),
            )
            test_db.add(question)
        test_db.commit()

        # Act & Assert: Should not raise exception
        try:
            SubscriptionLimits.check_question_limit(test_institution, test_db)
        except HTTPException:
            pytest.fail("check_question_limit raised HTTPException when under quota")


