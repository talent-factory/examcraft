"""Grading scheme — percent → grade mapping.

System schemes (``institution_id IS NULL``) are seeded for Switzerland,
Germany, Austria, France, Netherlands, ECTS, percent, and pass/fail.
Custom per-institution schemes share the same table.

The ``config`` JSON is a discriminated union (``type`` field) with
three variants — ``linear_segments``, ``linear``, ``stepped`` —
validated at write time by ``_validate_config``. A typo'd ``type``
raises immediately rather than round-tripping to disk and surfacing
as a wrong grade weeks later.
"""

from typing import Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    UniqueConstraint,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from typing_extensions import Annotated

from database import Base


class _BaseConfig(BaseModel):
    # ``extra='allow'`` so future optional fields don't break old rows;
    # the discriminator + required fields below still catch typos.
    model_config = ConfigDict(extra="allow")


class _LinearSegment(BaseModel):
    model_config = ConfigDict(extra="allow")

    from_pct: float
    to_pct: float
    from_grade: float
    to_grade: float


class _LinearSegmentsConfig(_BaseConfig):
    type: Literal["linear_segments"]
    segments: list[_LinearSegment]


class _LinearConfig(_BaseConfig):
    type: Literal["linear"]
    min_pct: float
    max_pct: float
    min_grade: float
    max_grade: float


class _Step(BaseModel):
    model_config = ConfigDict(extra="allow")

    min_pct: float
    grade_label: str
    is_passing: bool


class _SteppedConfig(_BaseConfig):
    type: Literal["stepped"]
    steps: list[_Step]


GradingSchemeConfig = Annotated[
    Union[_LinearSegmentsConfig, _LinearConfig, _SteppedConfig],
    Field(discriminator="type"),
]
_CONFIG_ADAPTER = TypeAdapter(GradingSchemeConfig)


class GradingScheme(Base):
    __tablename__ = "grading_schemes"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name = Column(String(200), nullable=False)
    display_format = Column(String(20), nullable=False)
    config = Column(JSON, nullable=False)
    is_default_for_institution = Column(Boolean, default=False, nullable=False)

    institution = relationship(
        "Institution",
        back_populates="grading_schemes",
        foreign_keys=[institution_id],
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
        UniqueConstraint(
            "institution_id", "name", name="uq_grading_schemes_institution_name"
        ),
        CheckConstraint(
            "display_format IN ('numeric', 'letter', 'pass_fail')",
            name="check_grading_scheme_display_format",
        ),
        # At most one default per institution. ``institution_id IS NOT
        # NULL`` excludes system schemes from the uniqueness check so
        # multiple system defaults can coexist during seeding.
        Index(
            "uq_grading_schemes_default_per_institution",
            "institution_id",
            unique=True,
            postgresql_where=(
                "is_default_for_institution = true AND institution_id IS NOT NULL"
            ),
        ),
    )

    @validates("config")
    def _validate_config(self, _key: str, value: dict) -> dict:
        """Reject illegal ``config`` shapes at write time.

        See module docstring: a typo'd ``type`` (or a missing required
        field) currently round-trips to disk and only surfaces during
        grade calculation. Validation here turns it into an immediate
        ``ValueError`` from the ORM.
        """
        if value is None:
            raise ValueError("GradingScheme.config darf nicht None sein")
        if not isinstance(value, dict):
            raise ValueError("GradingScheme.config muss ein dict sein")
        try:
            _CONFIG_ADAPTER.validate_python(value)
        except ValidationError as exc:
            raise ValueError(f"GradingScheme.config invalid: {exc}") from exc
        return value

    def __repr__(self):
        scope = (
            f"institution_id={self.institution_id}"
            if self.institution_id is not None
            else "system"
        )
        return f"<GradingScheme(id={self.id}, name='{self.name}', {scope})>"
