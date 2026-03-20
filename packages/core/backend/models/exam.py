"""
Exam Composer Models for ExamCraft AI
Implements exam assembly from approved questions with M:N relationship.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Date,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class ExamStatus(str, enum.Enum):
    DRAFT = "draft"
    FINALIZED = "finalized"
    EXPORTED = "exported"


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    course = Column(String(200), nullable=True)
    exam_date = Column(Date, nullable=True)
    time_limit_minutes = Column(Integer, nullable=True)
    allowed_aids = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)
    passing_percentage = Column(Float, default=50.0, nullable=False)
    total_points = Column(Float, default=0.0, nullable=False)
    status = Column(
        String(20), default=ExamStatus.DRAFT.value, nullable=False, index=True
    )
    language = Column(String(10), default="de", nullable=False)

    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    questions = relationship(
        "ExamQuestion",
        back_populates="exam",
        cascade="all, delete-orphan",
        order_by="ExamQuestion.position",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'finalized', 'exported')", name="check_exam_status"
        ),
    )

    def recalculate_total_points(self):
        self.total_points = sum(eq.points for eq in self.questions)

    def __repr__(self):
        return f"<Exam(id={self.id}, title='{self.title}', status={self.status})>"


class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(
        Integer,
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = Column(
        Integer,
        ForeignKey("question_reviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    position = Column(Integer, nullable=False)
    points = Column(Float, nullable=False)
    section = Column(String(100), nullable=True)

    exam = relationship("Exam", back_populates="questions")
    question = relationship("QuestionReview")

    __table_args__ = (
        UniqueConstraint("exam_id", "question_id", name="uq_exam_question"),
        UniqueConstraint("exam_id", "position", name="uq_exam_position"),
    )

    def __repr__(self):
        return f"<ExamQuestion(exam_id={self.exam_id}, question_id={self.question_id}, pos={self.position})>"
