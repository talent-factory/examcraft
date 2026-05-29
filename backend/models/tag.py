"""Tag Models für ExamCraft AI."""

from sqlalchemy import (
    Column,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.sql import func
from database import Base


class Tag(Base):
    """Tags für Prüfungsfragen — scope='institution' (eigene Institution sichtbar),
    scope='global' (institution_id IS NULL, alle Institutionen), oder scope='user'
    (owner-only, application-validated, Eindeutigkeit case-insensitive per owner via
    ux_tags_user_name partial unique index).
    Eindeutigkeit case-insensitive per scope, durchgesetzt via partielle
    Unique-Indizes."""

    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    scope = Column(String(20), default="institution", nullable=False)
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    # Deprecated: usage_count wird nicht mehr beschrieben — live aus QuestionTag
    # berechnet. Spalte bleibt für Backwards-Compat des Schemas (keine Migration).
    usage_count = Column(Integer, default=0, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        # TF-355: case-insensitive uniqueness of user-scoped tag names per owner.
        # Partial unique index — only scope='user' rows. Declared here (not
        # migration-only) so Base.metadata.create_all() builds it for tests.
        Index(
            "ux_tags_user_name",
            "created_by",
            text("lower(name)"),
            unique=True,
            postgresql_where=text("scope = 'user'"),
        ),
    )

    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name={self.name!r}, scope={self.scope})>"


class QuestionTag(Base):
    __tablename__ = "question_tags"

    question_id = Column(
        Integer,
        ForeignKey("question_reviews.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id = Column(
        Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )


class DocumentTag(Base):
    """Link table between documents and tags (TF-355), mirrors QuestionTag."""

    __tablename__ = "document_tags"

    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id = Column(
        Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
