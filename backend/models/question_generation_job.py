"""
QuestionGenerationJob — Ownership-Tracking für asynchrone Fragengenerierungs-Tasks.
Wird vor dem Celery-Task-Dispatch erstellt, damit der WebSocket-Ownership-Check
immer einen Eintrag findet.
"""

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    false,
)

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
    # TF-736: outcome of a SUCCESS run, so an under-filled generation (fewer
    # questions than `question_count`) stays explainable after the Celery
    # result has expired. NULL = not recorded (older rows, or the write failed).
    generated_question_count = Column(Integer, nullable=True)
    context_limited = Column(
        Boolean, default=False, server_default=false(), nullable=False
    )

    def __init__(self, **kwargs: object) -> None:
        kwargs.setdefault("status", "PENDING")
        super().__init__(**kwargs)
