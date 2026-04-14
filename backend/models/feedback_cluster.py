from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func
from database import Base


class FeedbackCluster(Base):
    __tablename__ = "feedback_clusters"

    id = Column(Integer, primary_key=True, index=True)
    topic_label = Column(String(100), nullable=False)
    vector_id = Column(String(36), nullable=True)
    positive_count = Column(Integer, default=0, nullable=False)
    negative_count = Column(Integer, default=0, nullable=False)
    total_count = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="aktiv", nullable=False)
    suggested_answer_de = Column(Text, nullable=True)
    suggested_answer_en = Column(Text, nullable=True)
    docs_gap = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self):
        return {
            "id": self.id,
            "topic_label": self.topic_label,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "total_count": self.total_count,
            "status": self.status,
            "suggested_answer_de": self.suggested_answer_de,
            "suggested_answer_en": self.suggested_answer_en,
            "docs_gap": self.docs_gap,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
