"""Kompetenzrahmen-Modelle für ExamCraft AI (TF-400).

CompetencyFramework = Handlungskompetenzbereich (HKB / Modul), institutions-
skopiert wie Document/Tag. `rendered_text` hält den vollständigen HKB-Text für
die spätere verbatim-Injektion in die Prompt-Variable {{ competencies }}.
Competency = einzelne Handlungskompetenz (HK, z. B. "B3") mit Deskriptoren als
JSON (jeweils inkl. LN-Stufe).
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
    """Wer ein Kompetenz-Framework ausserhalb des Erstellers browsen/für die
    Fragengenerierung wählen darf (TF-644).

    Gilt für ``api.competency_frameworks.list_frameworks``/``get_framework``
    (Browsing) UND gatet zusätzlich die Erreichbarkeit JEDER Mutation
    (update/archive/unarchive) via ``_get_for_write`` — visibility wird dort
    VOR dem ``created_by``/``manage_settings``-Check geprüft (siehe
    ``_get_for_write``'s Docstring: "visibility is checked first, the
    owner-or-admin write gate only decides what an already-visible framework
    may do"). Nur der ``competencies:read_all``-Bypass selbst bleibt für
    Mutationen deaktiviert (``allow_read_all_bypass=False``, ADR-0004) — die
    private/team/institution-Regeln selbst gelten für Lesen UND Schreiben.
    Gilt ausserdem für ``api.rag_exams.resolve_competencies_text``
    (Fragengenerierung — TF-644 schliesst hier eine vorbestehende Lücke: die
    Framework-Auswahl war bislang rein institutionsflach, ignorierte
    visibility komplett). Mirrors ``DocumentVisibility`` (TF-354/TF-620),
    ``PromptVisibility`` (TF-410/TF-641), ``QuestionReviewVisibility``
    (TF-642) und ``ExamVisibility`` (TF-643).

    ``PRIVATE``: nur der Ersteller sieht/nutzt das Framework.
    ``TEAM``: Mitglieder der zugeordneten Org-Unit sehen/nutzen es,
    hierarchisch (``services.org_unit_service.get_user_accessible_org_unit_ids``).
    ``INSTITUTION``: jedes Mitglied der Institution sieht/nutzt es (Default,
    Status quo vor TF-644).

    Ein User mit ``competencies:read_all`` (Institutions-Admin-Bypass,
    TF-639/``utils/resource_visibility.py``) sieht jedes Framework der
    eigenen Institution unabhängig von visibility — analog zu Document/
    Prompt/Question/Exam.
    """

    PRIVATE = "private"
    TEAM = "team"
    INSTITUTION = "institution"


class CompetencyFramework(Base):
    """Handlungskompetenzbereich / Modul. visibility steuert Browsing/Reuse
    (siehe ``CompetencyFrameworkVisibility``), nicht Editierrechte."""

    __tablename__ = "competency_frameworks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    module_code = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    # Vollständiger HKB-Text für die {{ competencies }}-Injektion (verbatim).
    rendered_text = Column(Text, nullable=False)
    language = Column(String(10), default="de", nullable=False)

    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # TF-644: Team-Sichtbarkeit. Kein ON DELETE CASCADE/SET NULL — löschen
    # einer noch referenzierten Org-Unit wird DB-seitig abgelehnt, mirrors
    # Document/TF-620, Prompt/TF-641, Question/TF-642, Exam/TF-643 (siehe
    # services.org_unit_service.delete_org_unit).
    org_unit_id = Column(
        Integer,
        ForeignKey("org_units.id"),
        nullable=True,
        index=True,
    )
    # TF-644: von String(20)+CHECK (TF-400) auf natives PG-Enum promoviert,
    # damit CompetencyFramework wie Document/Prompt/Question/Exam eine
    # Python-seitig typisierte Visibility trägt (siehe
    # CompetencyFrameworkVisibility-Docstring).
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
    """Einzelne Handlungskompetenz (HK) innerhalb eines Frameworks."""

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
    # Liste von Deskriptoren: [{"text": str, "ln_level": int}]
    descriptors = Column(JSON, nullable=True)
    position = Column(Integer, default=0, nullable=False)

    framework = relationship("CompetencyFramework", back_populates="competencies")

    __table_args__ = (
        UniqueConstraint("framework_id", "code", name="ux_competencies_framework_code"),
    )

    def __repr__(self) -> str:
        return f"<Competency(id={self.id}, code={self.code!r})>"
