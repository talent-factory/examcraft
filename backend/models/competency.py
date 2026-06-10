"""Kompetenzrahmen-Modelle für ExamCraft AI (TF-400).

CompetencyFramework = Handlungskompetenzbereich (HKB / Modul), institutions-
skopiert wie Document/Tag. `rendered_text` hält den vollständigen HKB-Text für
die spätere verbatim-Injektion in die Prompt-Variable {{ competencies }}.
Competency = einzelne Handlungskompetenz (HK, z. B. "B3") mit Deskriptoren als
JSON (jeweils inkl. LN-Stufe).
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
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


class CompetencyFramework(Base):
    """Handlungskompetenzbereich / Modul. visibility='private' (owner-only) oder
    'institution' (institutionsweit). Geschlossene Wertemenge per DB-CHECK."""

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
    visibility = Column(String(20), default="institution", nullable=False)
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
        CheckConstraint(
            "visibility IN ('private', 'institution')",
            name="ck_competency_frameworks_visibility_valid",
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
