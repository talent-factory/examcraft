"""TagMergeLog Model für Audit-Trail von Tag-Zusammenführungen."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.sql import func
from database import Base


class TagMergeLog(Base):
    """Audit-Trail für Tag-Merges. Pro Merge ein Eintrag."""

    __tablename__ = "tag_merge_logs"

    id = Column(Integer, primary_key=True)
    source_tag_id = Column(
        Integer, ForeignKey("tags.id", ondelete="SET NULL"), nullable=True
    )
    target_tag_id = Column(
        Integer, ForeignKey("tags.id", ondelete="SET NULL"), nullable=True
    )
    merged_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    merged_at = Column(DateTime, server_default=func.now(), nullable=False)
    questions_migrated = Column(Integer, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<TagMergeLog(id={self.id}, "
            f"source={self.source_tag_id} -> target={self.target_tag_id})>"
        )
