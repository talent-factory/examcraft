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

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    model_validator,
)
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


_STRICT = ConfigDict(extra="forbid")


class _LinearSegment(BaseModel):
    """One piece of a piecewise-linear scheme.

    ``from_pct < to_pct`` is enforced — descending or zero-width
    segments produce a divide-by-zero in the evaluator.
    """

    model_config = _STRICT

    from_pct: float = Field(ge=0, le=100)
    to_pct: float = Field(ge=0, le=100)
    from_grade: float
    to_grade: float

    @model_validator(mode="after")
    def _check_pct_order(self) -> "_LinearSegment":
        if self.from_pct >= self.to_pct:
            raise ValueError(
                f"linear segment: from_pct ({self.from_pct}) "
                f"muss kleiner to_pct ({self.to_pct}) sein"
            )
        return self


class _LinearSegmentsConfig(BaseModel):
    """Piecewise-linear scheme — segments must cover [0, 100] continuously."""

    model_config = _STRICT

    type: Literal["linear_segments"]
    segments: list[_LinearSegment] = Field(min_length=1)
    round_to: float | None = Field(default=None, gt=0)
    pass_grade_label: str | None = None  # UI hint only; not a threshold.

    @model_validator(mode="after")
    def _check_coverage(self) -> "_LinearSegmentsConfig":
        ordered = sorted(self.segments, key=lambda s: s.from_pct)
        if ordered[0].from_pct != 0:
            raise ValueError(
                f"linear_segments: erstes Segment muss bei 0 % beginnen "
                f"(bekam {ordered[0].from_pct})"
            )
        if ordered[-1].to_pct != 100:
            raise ValueError(
                f"linear_segments: letztes Segment muss bei 100 % enden "
                f"(bekam {ordered[-1].to_pct})"
            )
        for prev, curr in zip(ordered, ordered[1:]):
            if prev.to_pct != curr.from_pct:
                raise ValueError(
                    f"linear_segments: Lücke oder Überlappung "
                    f"(prev.to_pct={prev.to_pct}, curr.from_pct={curr.from_pct})"
                )
        return self


class _LinearConfig(BaseModel):
    """Single linear scale across [min_pct, max_pct]."""

    model_config = _STRICT

    type: Literal["linear"]
    min_pct: float = Field(ge=0, le=100)
    max_pct: float = Field(ge=0, le=100)
    min_grade: float
    max_grade: float
    round_to: float | None = Field(default=None, gt=0)
    pass_grade_label: str | None = None  # UI hint only; not a threshold.

    @model_validator(mode="after")
    def _check_pct_order(self) -> "_LinearConfig":
        if self.min_pct >= self.max_pct:
            raise ValueError(
                f"linear: min_pct ({self.min_pct}) muss kleiner "
                f"max_pct ({self.max_pct}) sein"
            )
        return self


class _Step(BaseModel):
    model_config = _STRICT

    min_pct: float = Field(ge=0, le=100)
    grade_label: str
    is_passing: bool


class _SteppedConfig(BaseModel):
    """Discrete-buckets scheme — must include a step covering 0 % and ≥1 passing step."""

    model_config = _STRICT

    type: Literal["stepped"]
    steps: list[_Step] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_steps(self) -> "_SteppedConfig":
        seen: set[float] = set()
        for s in self.steps:
            if s.min_pct in seen:
                raise ValueError(f"stepped: dupliziertes min_pct {s.min_pct}")
            seen.add(s.min_pct)
        if not any(s.is_passing for s in self.steps):
            raise ValueError("stepped: mindestens ein Step muss is_passing=True haben")
        ordered = sorted(self.steps, key=lambda s: s.min_pct)
        if ordered[0].min_pct != 0:
            raise ValueError(
                f"stepped: niedrigster Step muss bei 0 % beginnen "
                f"(bekam {ordered[0].min_pct})"
            )
        return self


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
