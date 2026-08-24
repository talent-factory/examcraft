"""Tag models for ExamCraft AI."""

from typing import Literal

from sqlalchemy import (
    CheckConstraint,
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

# TF-397: single source of truth for the tag-kind value set. The DB CHECK below
# is built from ``TAG_KINDS`` and the API layer imports ``TagKind`` from here
# instead of redeclaring the literal — so model, constraint and API can't drift.
TagKind = Literal["content", "prompt"]
TAG_KINDS: tuple[str, ...] = ("content", "prompt")


class Tag(Base):
    """Tags for exam questions — scope='institution' (visible within own institution),
    scope='global' (institution_id IS NULL, all institutions), or scope='user'
    (owner-only, application-validated, uniqueness case-insensitive per owner via
    ux_tags_user_name partial unique index).
    Uniqueness is case-insensitive per scope, enforced via partial
    unique indexes."""

    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    # Closed value set — enforced via DB CHECK (see __table_args__),
    # not merely by convention at the write sites (TF-372).
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
    # Deprecated: usage_count is no longer written — computed live from
    # QuestionTag. Column stays for schema backwards-compat (no migration).
    usage_count = Column(Integer, default=0, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    # TF-397: namespace dimension. 'content' tags classify questions/documents,
    # 'prompt' tags classify prompt templates. Kept separate so prompt
    # classification tags (e.g. 'single_choice', 'default') never pollute the
    # question/document tag selection. Closed value set — enforced by DB CHECK.
    kind = Column(String(20), default="content", nullable=False)

    __table_args__ = (
        # TF-355: case-insensitive uniqueness of user-scoped tag names per owner.
        # Partial unique index — only scope='user' rows. Declared here (not
        # migration-only) so Base.metadata.create_all() builds it for tests.
        # TF-397: kind folded into the uniqueness key so a 'prompt'-kind tag may
        # coexist with a 'content'-kind tag of the same name in the same scope.
        Index(
            "ux_tags_user_name",
            "created_by",
            "kind",
            text("lower(name)"),
            unique=True,
            postgresql_where=text("scope = 'user'"),
        ),
        # TF-372: case-insensitive uniqueness of institution-scoped tag names
        # per institution, and of global-scoped tag names. Without these the
        # get-or-create endpoint's 409-on-duplicate branch was dead for those
        # scopes (the pre-check is a TOCTOU race with no DB backstop). Declared
        # here so create_all() builds them for tests; mirrored in the migration.
        Index(
            "ux_tags_institution_name",
            "institution_id",
            "kind",
            text("lower(name)"),
            unique=True,
            postgresql_where=text("scope = 'institution'"),
        ),
        Index(
            "ux_tags_global_name",
            "kind",
            text("lower(name)"),
            unique=True,
            postgresql_where=text("scope = 'global'"),
        ),
        # TF-372: the scope value set is closed — enforce it at the DB, not just
        # by convention at the (scattered) write sites.
        CheckConstraint(
            "scope IN ('user', 'institution', 'global')",
            name="ck_tags_scope_valid",
        ),
        # TF-397: the kind value set is closed too — built from TAG_KINDS so the
        # constraint and the TagKind literal stay in lockstep.
        CheckConstraint(
            f"kind IN ({', '.join(repr(k) for k in TAG_KINDS)})",
            name="ck_tags_kind_valid",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Tag(id={self.id}, name={self.name!r}, "
            f"scope={self.scope}, kind={self.kind})>"
        )


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


class DocumentPersonalTag(Base):
    """Per-user (personal) document↔tag assignment (TF-399).

    Unlike ``DocumentTag`` — which is shared institution state visible to every
    member who can see the document — a personal assignment is visible **only**
    to the user who made it (``user_id`` is part of the primary key). This lets a
    user group *any* document they can see, including foreign
    ``institution``-visible documents, with their own ``user``-scope tags without
    changing what anyone else sees. Shared (``institution``/``global``) tag
    assignments stay in ``document_tags``.
    """

    __tablename__ = "document_personal_tags"

    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id = Column(
        Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Filter/read path always scopes by ``user_id`` ("my personal tags on these
    # documents"); a dedicated index keeps that lookup cheap.
    __table_args__ = (Index("ix_document_personal_tags_user_id", "user_id"),)
