import enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.sql import func

from database import Base


class OnboardingRole(str, enum.Enum):
    TEACHER = "teacher"
    ADMIN = "admin"


class FeedbackRating(str, enum.Enum):
    UP = "up"
    DOWN = "down"


class FeedbackStatus(str, enum.Enum):
    OPEN = "offen"
    IN_PROGRESS = "in_bearbeitung"
    DOCUMENTED = "dokumentiert"


class HelpOnboardingProgress(Base):
    __tablename__ = "help_onboarding_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )
    role = Column(String(20), nullable=False)
    current_step = Column(Integer, default=0, nullable=False)
    completed_steps = Column(JSON, default=list, nullable=False)
    skipped_steps = Column(JSON, default=list, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    # TF-625: progress of the optional deep-dive tracks, separate from the
    # linear core-tour progress above. Keyed by track id (from
    # help-onboarding-steps.json), value per track:
    #   {"current_step": int, "completed_steps": [int], "skipped_steps": [int],
    #    "completed_at": iso8601 | None}
    # Deliberately its own column rather than a number-range convention inside
    # `completed_steps`: the track id stays stable when steps are renumbered or
    # inserted, so stored progress does not silently point at different content.
    # MutableDict.as_mutable, not plain JSON: without it, an in-place write
    # like `progress.track_progress[track_id]["current_step"] += 1` would not
    # be seen as a dirty attribute and would silently fail to persist — the
    # route handler works around this today by rebuilding the dict and
    # reassigning it wholesale, but that convention is only as strong as the
    # next contributor remembering it. This makes the safe form the only one
    # that works, structurally, instead of a rule to keep in mind.
    track_progress = Column(
        MutableDict.as_mutable(JSON), default=dict, nullable=False, server_default="{}"
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

    __table_args__ = (
        CheckConstraint("role IN ('teacher', 'admin')", name="ck_onboarding_role"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role": self.role,
            "current_step": self.current_step,
            "completed_steps": self.completed_steps,
            "skipped_steps": self.skipped_steps or [],
            "track_progress": self.track_progress or {},
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }


class HelpConversation(Base):
    __tablename__ = "help_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    messages = Column(JSON, default=list, nullable=False)
    route = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "messages": self.messages,
            "route": self.route,
            "created_at": (self.created_at.isoformat() if self.created_at else None),
        }


class HelpFeedback(Base):
    __tablename__ = "help_feedback"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    rating = Column(String(10), nullable=True)
    user_role = Column(String(20), nullable=True)
    user_tier = Column(String(30), nullable=True)
    route = Column(String(255), nullable=True)
    language = Column(String(10), nullable=True)
    cluster_id = Column(Integer, nullable=True, index=True)
    status = Column(String(20), default="offen", nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("rating IN ('up', 'down')", name="ck_feedback_rating"),
        CheckConstraint(
            "status IN ('offen', 'in_bearbeitung', 'dokumentiert')",
            name="ck_feedback_status",
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
            "confidence": self.confidence,
            "rating": self.rating,
            "user_role": self.user_role,
            "user_tier": self.user_tier,
            "route": self.route,
            "language": self.language,
            "cluster_id": self.cluster_id,
            "status": self.status,
            "created_at": (self.created_at.isoformat() if self.created_at else None),
        }


class HelpContextHint(Base):
    __tablename__ = "help_context_hints"

    id = Column(Integer, primary_key=True, index=True)
    route_pattern = Column(String(255), nullable=False)
    role = Column(String(20), nullable=True)
    tier = Column(String(30), nullable=True)
    # The text itself lives in the frontend's translation.json under this key.
    # It used to sit here as hint_text_de/en, which made this the only help
    # surface whose language the server decided — and therefore the only one
    # that did not follow the language switcher without a reload.
    i18n_key = Column(String(255), nullable=False)
    priority = Column(Integer, default=0, nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    def to_dict(self):
        """Structure only. The client resolves `i18n_key` in its own locale."""
        return {
            "id": self.id,
            "route_pattern": self.route_pattern,
            "i18n_key": self.i18n_key,
            "priority": self.priority,
        }


class HelpFaqCache(Base):
    __tablename__ = "help_faq_cache"

    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(Text, nullable=False)
    answer_de = Column(Text, nullable=False)
    answer_en = Column(Text, nullable=False)
    docs_links = Column(JSON, default=list, nullable=False)
    source_files = Column(JSON, default=list, nullable=False)
    hit_count = Column(Integer, default=0, nullable=False)
    last_used = Column(DateTime(timezone=True), nullable=True)
    stale = Column(Boolean, default=False, nullable=False)
    approved_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    cluster_id = Column(
        Integer,
        ForeignKey("feedback_clusters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    faq_status = Column(String(20), default="vorgeschlagen", nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "question_text": self.question_text,
            "answer_de": self.answer_de,
            "answer_en": self.answer_en,
            "docs_links": self.docs_links,
            "hit_count": self.hit_count,
            "stale": self.stale,
            "faq_status": self.faq_status,
            "cluster_id": self.cluster_id,
            "approved_by": self.approved_by,
        }


class HelpDismissedHint(Base):
    __tablename__ = "help_dismissed_hints"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hint_id = Column(
        Integer,
        ForeignKey("help_context_hints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "hint_id", name="uq_dismissed_user_hint"),
    )


class HelpIndexState(Base):
    __tablename__ = "help_index_state"

    id = Column(Integer, primary_key=True, index=True)
    last_indexed_sha = Column(String(40), nullable=True)
    last_indexed_at = Column(DateTime(timezone=True), nullable=True)
    files_indexed = Column(Integer, default=0, nullable=False)
    files_deleted = Column(Integer, default=0, nullable=False)
    # Lifecycle state persisted across restarts. Complements the transient
    # Redis SETNX lock ("is running right now?") with durable visibility
    # of the last completed or failed run.
    # Values: 'idle' | 'in_progress' | 'completed' | 'failed'
    indexing_status = Column(
        String(20), nullable=False, server_default="idle", default="idle"
    )
    last_error = Column(Text, nullable=True)
