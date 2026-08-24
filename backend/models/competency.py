"""Competency framework models for ExamCraft AI (TF-400).

CompetencyFramework = competency area (HKB / module), institution-
scoped like Document/Tag. `rendered_text` holds the full HKB text for
the later verbatim injection into the prompt variable {{ competencies }}.
Competency = a single competency (HK, e.g. "B3") with descriptors as
JSON (each including an LN level).
"""

import enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class CompetencyFrameworkVisibility(enum.Enum):
    """Who may browse/select a competency framework outside its creator, for
    question generation (TF-644).

    Applies to ``api.competency_frameworks.list_frameworks``/``get_framework``
    (browsing) AND additionally gates the reachability of EVERY mutation
    (update/archive/unarchive) via ``_get_for_write`` — visibility is checked
    there BEFORE the ``created_by``/``manage_settings`` check (see
    ``_get_for_write``'s docstring: "visibility is checked first, the
    owner-or-admin write gate only decides what an already-visible framework
    may do"). Only the ``competencies:read_all`` bypass itself stays
    disabled for mutations (``allow_read_all_bypass=False``, ADR-0004) — the
    private/team/institution rules themselves apply to both reading AND
    writing. Also applies to ``api.rag_exams.resolve_competencies_text``
    (question generation — TF-644 closes a pre-existing gap here: framework
    selection used to be purely institution-flat, ignoring visibility
    entirely). Mirrors ``DocumentVisibility`` (TF-354/TF-620),
    ``PromptVisibility`` (TF-410/TF-641), ``QuestionReviewVisibility``
    (TF-642) and ``ExamVisibility`` (TF-643).

    ``PRIVATE``: only the creator sees/uses the framework.
    ``TEAM``: members of the assigned Org-Unit see/use it,
    hierarchically (``services.org_unit_service.get_user_accessible_org_unit_ids``).
    ``INSTITUTION``: every member of the institution sees/uses it (default,
    status quo before TF-644).

    A user with ``competencies:read_all`` (institution-admin bypass,
    TF-639/``utils/resource_visibility.py``) sees every framework in
    their own institution regardless of visibility — analogous to Document/
    Prompt/Question/Exam.
    """

    PRIVATE = "private"
    TEAM = "team"
    INSTITUTION = "institution"


class CompetencyFramework(Base):
    """Competency area / module. visibility governs browsing/reuse
    (see ``CompetencyFrameworkVisibility``), not edit rights."""

    __tablename__ = "competency_frameworks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    module_code = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    # Full HKB text for the {{ competencies }} injection (verbatim).
    rendered_text = Column(Text, nullable=False)
    language = Column(String(10), default="de", nullable=False)

    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # TF-644: team visibility. No ON DELETE CASCADE/SET NULL — deleting
    # an Org-Unit that's still referenced is rejected at the DB level, mirrors
    # Document/TF-620, Prompt/TF-641, Question/TF-642, Exam/TF-643 (see
    # services.org_unit_service.delete_org_unit).
    org_unit_id = Column(
        Integer,
        ForeignKey("org_units.id"),
        nullable=True,
        index=True,
    )
    # TF-644: promoted from String(20)+CHECK (TF-400) to a native PG enum,
    # so CompetencyFramework carries a Python-side typed visibility like
    # Document/Prompt/Question/Exam (see the
    # CompetencyFrameworkVisibility docstring).
    visibility = Column(
        Enum(
            CompetencyFrameworkVisibility,
            name="competencyframeworkvisibility",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=CompetencyFrameworkVisibility.INSTITUTION,
        server_default=CompetencyFrameworkVisibility.INSTITUTION.value,
        index=True,
    )
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_archived = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    competencies = relationship(
        "Competency",
        back_populates="framework",
        cascade="all, delete-orphan",
        order_by="Competency.position",
    )

    __table_args__ = (
        # TF-644: mirrors Document/TF-354, Question/TF-642, Exam/TF-643.
        # Unlike Exam, institution_id IS nullable here, so this constraint
        # is real protection, not pure defense-in-depth.
        CheckConstraint(
            "visibility <> 'institution' OR institution_id IS NOT NULL",
            name="ck_competency_frameworks_inst_vis_requires_institution",
        ),
        # TF-644: mirrors Document/TF-620, Prompt/TF-641, Question/TF-642,
        # Exam/TF-643.
        CheckConstraint(
            "(visibility = 'team') = (org_unit_id IS NOT NULL)",
            name="ck_competency_frameworks_team_visibility_requires_org_unit",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<CompetencyFramework(id={self.id}, name={self.name!r}, "
            f"module_code={self.module_code!r})>"
        )


class Competency(Base):
    """A single competency (HK) within a framework."""

    __tablename__ = "competencies"

    id = Column(Integer, primary_key=True, index=True)
    framework_id = Column(
        Integer,
        ForeignKey("competency_frameworks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code = Column(String(10), nullable=False)
    title = Column(Text, nullable=False)
    # List of descriptors: [{"text": str, "ln_level": int}]
    descriptors = Column(JSON, nullable=True)
    position = Column(Integer, default=0, nullable=False)

    framework = relationship("CompetencyFramework", back_populates="competencies")

    __table_args__ = (
        UniqueConstraint("framework_id", "code", name="ux_competencies_framework_code"),
    )

    def __repr__(self) -> str:
        return f"<Competency(id={self.id}, code={self.code!r})>"
