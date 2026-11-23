"""
Question version model (EXAMCRAFT-192, Resolution von EXAMCRAFT-174).

``question_reviews`` stays the *question* (the stable identity: institution,
owner, visibility, org unit, archive, job link, tags, source documents).
``question_versions`` holds one content snapshot per row with exactly one
review status. Versions are numbered per question (1, 2, 3 ...), never
renumbered and never deleted individually, only together with their question.

Transition note: this issue adds the schema and the backfill only. The legacy
content/status columns on ``question_reviews`` stay in place until the
read/write paths are switched over (grading, statistics, exports:
EXAMCRAFT-175; review workflow: EXAMCRAFT-189). Until then ``question_reviews``
remains the source of truth for the running application and version 1 is a
copy.
"""

import enum

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class QuestionVersionStatus(str, enum.Enum):
    """Review status of a single version (``edited`` no longer exists)."""

    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


# Statuses of an *open* (still editable) version; at most one per question.
OPEN_VERSION_STATUSES = (
    QuestionVersionStatus.PENDING.value,
    QuestionVersionStatus.IN_REVIEW.value,
)


class QuestionVersion(Base):
    """One content snapshot of a question with its own review status."""

    __tablename__ = "question_versions"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(
        Integer,
        ForeignKey(
            "question_reviews.id",
            ondelete="CASCADE",
            name="fk_question_versions_question_id",
        ),
        nullable=False,
        index=True,
    )
    version_number = Column(Integer, nullable=False)

    # Content
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False)
    options = Column(JSON, nullable=True)
    correct_answer = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)

    # Metadata
    difficulty = Column(String(20), nullable=False)
    topic = Column(String(200), nullable=False)
    language = Column(String(10), default="de")
    bloom_level = Column(Integer, nullable=True)
    ln_level = Column(Integer, nullable=True)
    estimated_time_minutes = Column(Integer, nullable=True)
    quality_tier = Column(String(1), nullable=True)
    confidence_score = Column(Float, default=0.0)
    competency_id = Column(
        Integer,
        ForeignKey(
            "competencies.id",
            ondelete="SET NULL",
            name="fk_question_versions_competency_id_competencies",
        ),
        nullable=True,
        index=True,
    )

    # Provenance
    source_chunks = Column(JSON, nullable=True)
    source_documents = Column(JSON, nullable=True)
    generation_metadata = Column(JSON, nullable=True)
    exam_id = Column(String(100), nullable=True, index=True)  # RAG exam id

    # Author and review. Both user references are SET NULL: a GDPR deletion
    # anonymises the version, it never removes it (exam positions may pin it).
    created_by = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
            name="fk_question_versions_created_by_users",
        ),
        nullable=True,
    )
    review_status = Column(
        String(20),
        default=QuestionVersionStatus.PENDING.value,
        server_default=QuestionVersionStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    reviewed_by = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
            name="fk_question_versions_reviewed_by_users",
        ),
        nullable=True,
    )
    reviewed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    question = relationship(
        "QuestionReview",
        back_populates="versions",
        foreign_keys=[question_id],
    )

    __table_args__ = (
        UniqueConstraint(
            "question_id", "version_number", name="uq_question_versions_number"
        ),
        CheckConstraint(
            "review_status IN ("
            + ", ".join(f"'{s.value}'" for s in QuestionVersionStatus)
            + ")",
            name="ck_question_versions_review_status",
        ),
        CheckConstraint(
            "ln_level IS NULL OR (ln_level >= 1 AND ln_level <= 4)",
            name="ck_question_versions_ln_level_range",
        ),
        CheckConstraint(
            "version_number >= 1", name="ck_question_versions_number_positive"
        ),
        # At most one open version per question.
        Index(
            "uq_question_versions_one_open",
            question_id,
            unique=True,
            postgresql_where=text(
                "review_status IN ("
                + ", ".join(f"'{v}'" for v in OPEN_VERSION_STATUSES)
                + ")"
            ),
        ),
    )

    def __repr__(self):
        return (
            f"<QuestionVersion(id={self.id}, question_id={self.question_id}, "
            f"v={self.version_number}, status={self.review_status})>"
        )
