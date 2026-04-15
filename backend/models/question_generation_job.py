"""
QuestionGenerationJob — Ownership-Tracking für asynchrone Fragengenerierungs-Tasks.
Wird vor dem Celery-Task-Dispatch erstellt, damit der WebSocket-Ownership-Check
immer einen Eintrag findet.
"""

from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String

from database import Base


class QuestionGenerationJob(Base):
    __tablename__ = "question_generation_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    topic = Column(String, nullable=True)
    question_count = Column(Integer, nullable=True)
    status = Column(String, default="PENDING", server_default="PENDING", nullable=False)
    request_data = Column(JSON, nullable=True)

    def __init__(self, **kwargs: object) -> None:
        kwargs.setdefault("status", "PENDING")
        super().__init__(**kwargs)
