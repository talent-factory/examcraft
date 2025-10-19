"""
Question Review Models für ExamCraft AI
Implementiert Review-Workflow für generierte Prüfungsfragen
"""

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey, JSON, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum
from datetime import datetime
from typing import Optional


class ReviewStatus(str, enum.Enum):
    """Status einer Question Review (Python Enum für Type-Safety)"""
    PENDING = "pending"  # Wartet auf Review
    APPROVED = "approved"  # Genehmigt
    REJECTED = "rejected"  # Abgelehnt
    EDITED = "edited"  # Bearbeitet (wartet auf erneute Genehmigung)
    IN_REVIEW = "in_review"  # Wird gerade überprüft


class QuestionReview(Base):
    """
    Haupttabelle für Question Reviews
    Speichert generierte Fragen mit Review-Status
    """
    __tablename__ = "question_reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Question Content
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False)  # multiple_choice, open_ended, true_false
    options = Column(JSON, nullable=True)  # Für Multiple Choice: ["A) ...", "B) ...", ...]
    correct_answer = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    
    # Metadata
    difficulty = Column(String(20), nullable=False)  # easy, medium, hard
    topic = Column(String(200), nullable=False)
    language = Column(String(10), default="de")
    
    # RAG-specific
    source_chunks = Column(JSON, nullable=True)  # List of chunk IDs
    source_documents = Column(JSON, nullable=True)  # List of document names
    confidence_score = Column(Float, default=0.0)
    
    # Quality Indicators
    bloom_level = Column(Integer, nullable=True)  # 1-6 (Bloom's Taxonomy)
    estimated_time_minutes = Column(Integer, nullable=True)
    quality_tier = Column(String(1), nullable=True)  # A, B, C
    
    # Review Status (String mit CHECK Constraint statt Enum)
    review_status = Column(
        String(20),
        default=ReviewStatus.PENDING.value,
        nullable=False,
        index=True
    )
    reviewed_by = Column(String(100), nullable=True)  # User ID
    reviewed_at = Column(DateTime, nullable=True)
    
    # Exam Association
    exam_id = Column(String(100), nullable=True, index=True)  # RAG Exam ID
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    comments = relationship("ReviewComment", back_populates="question", cascade="all, delete-orphan")
    history = relationship("ReviewHistory", back_populates="question", cascade="all, delete-orphan")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('pending', 'approved', 'rejected', 'edited', 'in_review')",
            name='check_review_status'
        ),
    )

    def __repr__(self):
        return f"<QuestionReview(id={self.id}, type={self.question_type}, status={self.review_status})>"


class ReviewComment(Base):
    """
    Kommentare zu Question Reviews
    Ermöglicht Feedback und Diskussion
    """
    __tablename__ = "review_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("question_reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Comment Content
    comment_text = Column(Text, nullable=False)
    comment_type = Column(String(50), default="general")  # general, suggestion, issue, approval_note
    
    # Author
    author = Column(String(100), nullable=False)  # User ID
    author_role = Column(String(50), nullable=True)  # reviewer, admin, system
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    question = relationship("QuestionReview", back_populates="comments")
    
    def __repr__(self):
        return f"<ReviewComment(id={self.id}, question_id={self.question_id}, author={self.author})>"


class ReviewHistory(Base):
    """
    Änderungshistorie für Question Reviews
    Audit Trail für alle Änderungen
    """
    __tablename__ = "review_history"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("question_reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Change Information
    action = Column(String(50), nullable=False)  # created, edited, approved, rejected, status_changed
    old_status = Column(String(20), nullable=True)  # ReviewStatus values
    new_status = Column(String(20), nullable=True)  # ReviewStatus values
    
    # Changed Fields
    changed_fields = Column(JSON, nullable=True)  # {"question_text": {"old": "...", "new": "..."}}
    
    # Actor
    changed_by = Column(String(100), nullable=False)  # User ID
    change_reason = Column(Text, nullable=True)
    
    # Timestamp
    changed_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    # Relationships
    question = relationship("QuestionReview", back_populates="history")
    
    def __repr__(self):
        return f"<ReviewHistory(id={self.id}, question_id={self.question_id}, action={self.action})>"

