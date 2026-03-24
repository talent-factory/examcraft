"""
Review Service für ExamCraft AI
Business Logic für Question Review Workflow
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from models.question_review import (
    QuestionReview,
    ReviewComment,
    ReviewHistory,
    ReviewStatus,
)

logger = logging.getLogger(__name__)


class ReviewService:
    """Service für Question Review Operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_pending_reviews(
        self,
        limit: int = 50,
        offset: int = 0,
        difficulty: Optional[str] = None,
        question_type: Optional[str] = None,
        exam_id: Optional[str] = None,
    ) -> List[QuestionReview]:
        """
        Hole alle Questions mit Status PENDING

        Args:
            limit: Maximale Anzahl Ergebnisse
            offset: Offset für Pagination
            difficulty: Filter nach Schwierigkeitsgrad
            question_type: Filter nach Fragetyp
            exam_id: Filter nach Exam ID

        Returns:
            Liste von QuestionReview Objekten
        """
        query = self.db.query(QuestionReview).filter(
            QuestionReview.review_status == ReviewStatus.PENDING.value
        )

        if difficulty:
            query = query.filter(QuestionReview.difficulty == difficulty)
        if question_type:
            query = query.filter(QuestionReview.question_type == question_type)
        if exam_id:
            query = query.filter(QuestionReview.exam_id == exam_id)

        return (
            query.order_by(QuestionReview.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def approve_question(
        self,
        question_id: int,
        reviewer_id: str,
        comment: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> QuestionReview:
        """
        Genehmige eine Question

        Args:
            question_id: ID der Question
            reviewer_id: ID des Reviewers
            comment: Optional comment
            reason: Optional reason

        Returns:
            Aktualisierte QuestionReview

        Raises:
            ValueError: Wenn Question nicht gefunden
        """
        question = (
            self.db.query(QuestionReview)
            .filter(QuestionReview.id == question_id)
            .first()
        )

        if not question:
            raise ValueError(f"Question {question_id} not found")

        old_status = question.review_status

        # Update Question
        question.review_status = ReviewStatus.APPROVED.value
        question.reviewed_by = reviewer_id
        question.reviewed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(question)

        # Create History Entry
        self._create_history_entry(
            question_id=question_id,
            action="approved",
            old_status=old_status,
            new_status=ReviewStatus.APPROVED.value,
            changed_by=reviewer_id,
            change_reason=reason or "Question approved",
        )

        # Add Comment if provided
        if comment:
            self._add_comment(
                question_id=question_id,
                comment_text=comment,
                comment_type="approval_note",
                author=reviewer_id,
                author_role="reviewer",
            )

        logger.info(f"Approved question {question_id} by {reviewer_id}")
        return question

    def reject_question(
        self,
        question_id: int,
        reviewer_id: str,
        comment: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> QuestionReview:
        """
        Lehne eine Question ab

        Args:
            question_id: ID der Question
            reviewer_id: ID des Reviewers
            comment: Optional comment
            reason: Optional reason

        Returns:
            Aktualisierte QuestionReview

        Raises:
            ValueError: Wenn Question nicht gefunden
        """
        question = (
            self.db.query(QuestionReview)
            .filter(QuestionReview.id == question_id)
            .first()
        )

        if not question:
            raise ValueError(f"Question {question_id} not found")

        old_status = question.review_status

        # Update Question
        question.review_status = ReviewStatus.REJECTED.value
        question.reviewed_by = reviewer_id
        question.reviewed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(question)

        # Create History Entry
        self._create_history_entry(
            question_id=question_id,
            action="rejected",
            old_status=old_status,
            new_status=ReviewStatus.REJECTED.value,
            changed_by=reviewer_id,
            change_reason=reason or "Question rejected",
        )

        # Add Comment if provided
        if comment:
            self._add_comment(
                question_id=question_id,
                comment_text=comment,
                comment_type="issue",
                author=reviewer_id,
                author_role="reviewer",
            )

        logger.info(f"Rejected question {question_id} by {reviewer_id}")
        return question

    def edit_question(
        self, question_id: int, updates: Dict[str, Any], editor_id: str
    ) -> QuestionReview:
        """
        Bearbeite eine Question

        Args:
            question_id: ID der Question
            updates: Dictionary mit Updates
            editor_id: ID des Editors

        Returns:
            Aktualisierte QuestionReview

        Raises:
            ValueError: Wenn Question nicht gefunden
        """
        question = (
            self.db.query(QuestionReview)
            .filter(QuestionReview.id == question_id)
            .first()
        )

        if not question:
            raise ValueError(f"Question {question_id} not found")

        old_status = question.review_status
        changed_fields = {}

        # Track and apply changes
        for field, new_value in updates.items():
            if hasattr(question, field):
                old_value = getattr(question, field)
                if old_value != new_value:
                    changed_fields[field] = {"old": old_value, "new": new_value}
                    setattr(question, field, new_value)

        # Set status to EDITED if changes were made
        if changed_fields:
            question.review_status = ReviewStatus.EDITED.value

        self.db.commit()
        self.db.refresh(question)

        # Create History Entry
        if changed_fields:
            self._create_history_entry(
                question_id=question_id,
                action="edited",
                old_status=old_status,
                new_status=question.review_status,
                changed_by=editor_id,
                change_reason="Question edited",
                changed_fields=changed_fields,
            )

        logger.info(f"Edited question {question_id} by {editor_id}")
        return question

    def add_comment(
        self,
        question_id: int,
        comment_text: str,
        author: str,
        comment_type: str = "general",
        author_role: Optional[str] = None,
    ) -> ReviewComment:
        """
        Füge Comment zu Question hinzu

        Args:
            question_id: ID der Question
            comment_text: Text des Comments
            author: Autor des Comments
            comment_type: Typ des Comments
            author_role: Rolle des Autors

        Returns:
            Erstellter ReviewComment

        Raises:
            ValueError: Wenn Question nicht gefunden
        """
        # Check if question exists
        question = (
            self.db.query(QuestionReview)
            .filter(QuestionReview.id == question_id)
            .first()
        )

        if not question:
            raise ValueError(f"Question {question_id} not found")

        return self._add_comment(
            question_id, comment_text, comment_type, author, author_role
        )

    def get_review_history(self, question_id: int) -> List[ReviewHistory]:
        """
        Hole Review History für Question

        Args:
            question_id: ID der Question

        Returns:
            Liste von ReviewHistory Objekten

        Raises:
            ValueError: Wenn Question nicht gefunden
        """
        # Check if question exists
        question = (
            self.db.query(QuestionReview)
            .filter(QuestionReview.id == question_id)
            .first()
        )

        if not question:
            raise ValueError(f"Question {question_id} not found")

        return (
            self.db.query(ReviewHistory)
            .filter(ReviewHistory.question_id == question_id)
            .order_by(ReviewHistory.changed_at.desc())
            .all()
        )

    def get_review_statistics(self) -> Dict[str, int]:
        """
        Hole Review Statistiken

        Returns:
            Dictionary mit Statistiken
        """
        total = self.db.query(QuestionReview).count()
        pending = (
            self.db.query(QuestionReview)
            .filter(QuestionReview.review_status == ReviewStatus.PENDING.value)
            .count()
        )
        approved = (
            self.db.query(QuestionReview)
            .filter(QuestionReview.review_status == ReviewStatus.APPROVED.value)
            .count()
        )
        rejected = (
            self.db.query(QuestionReview)
            .filter(QuestionReview.review_status == ReviewStatus.REJECTED.value)
            .count()
        )
        edited = (
            self.db.query(QuestionReview)
            .filter(QuestionReview.review_status == ReviewStatus.EDITED.value)
            .count()
        )
        in_review = (
            self.db.query(QuestionReview)
            .filter(QuestionReview.review_status == ReviewStatus.IN_REVIEW.value)
            .count()
        )

        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "edited": edited,
            "in_review": in_review,
        }

    # Private Helper Methods

    def _create_history_entry(
        self,
        question_id: int,
        action: str,
        changed_by: str,
        old_status: Optional[str] = None,
        new_status: Optional[str] = None,
        change_reason: Optional[str] = None,
        changed_fields: Optional[Dict[str, Any]] = None,
    ) -> ReviewHistory:
        """Erstelle History Entry"""
        history = ReviewHistory(
            question_id=question_id,
            action=action,
            old_status=old_status,
            new_status=new_status,
            changed_fields=changed_fields,
            changed_by=changed_by,
            change_reason=change_reason,
        )

        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)

        return history

    def _add_comment(
        self,
        question_id: int,
        comment_text: str,
        comment_type: str,
        author: str,
        author_role: Optional[str] = None,
    ) -> ReviewComment:
        """Füge Comment hinzu"""
        comment = ReviewComment(
            question_id=question_id,
            comment_text=comment_text,
            comment_type=comment_type,
            author=author,
            author_role=author_role,
        )

        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)

        return comment
