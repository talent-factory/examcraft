"""
QuestionGenerationJob — Ownership-Tracking für asynchrone Fragengenerierungs-Tasks.
Wird vor dem Celery-Task-Dispatch erstellt, damit der WebSocket-Ownership-Check
immer einen Eintrag findet.
"""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from database import Base


class QuestionGenerationJob(Base):
    __tablename__ = "question_generation_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
