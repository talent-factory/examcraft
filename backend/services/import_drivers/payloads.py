"""DTOs for the results import pipeline (Spec 5.1).

Driver output is always an ``ImportPayload``. ``ImportService`` consumes
it and persists with no further source-specific logic.

Pydantic v2. ``extra='forbid'`` rejects unknown fields, so a future
driver that produces a typo'd attribute fails loudly at parse time
rather than silently dropping data.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


_STRICT = ConfigDict(extra="forbid", str_strip_whitespace=True)


class StudentRef(BaseModel):
    """A student — pseudonym-first."""

    model_config = _STRICT

    external_id: str
    display_name: str | None = None
    # Driver-supplied class hint for class auto-association in later
    # phases. Drivers without class info simply leave it None.
    class_hint: str | None = None


class AnswerRecord(BaseModel):
    """A single answer (1:1 with ``attempt_answers`` in the DB)."""

    model_config = _STRICT

    exam_question_id: int
    given_answer: str | None = None
    moodle_points_awarded: float | None = Field(default=None, ge=0)


class AttemptRecord(BaseModel):
    """A single attempt by one student."""

    model_config = _STRICT

    student_external_id: str
    attempt_number: int = Field(default=1, ge=1)
    started_at: datetime | None = None
    submitted_at: datetime | None = None
    # Idempotency key — re-importing the same CSV must produce the same
    # value so a duplicate import is skipped.
    source_attempt_id: str | None = None
    answers: list[AnswerRecord] = Field(default_factory=list)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class ImportRowError(BaseModel):
    """Per-row tolerance: a malformed row doesn't block the import."""

    model_config = _STRICT

    row_index: int
    reason: str


class ImportPayload(BaseModel):
    """Driver output: everything ``ImportService`` needs to persist."""

    model_config = _STRICT

    exam_id: int
    driver_name: str
    students: list[StudentRef] = Field(default_factory=list)
    attempts: list[AttemptRecord] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[ImportRowError] = Field(default_factory=list)
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    # Service-side counters set by ``ImportService._persist_attempts``.
    # Drivers don't populate these; they default to None so legacy
    # callers and unit tests that build payloads by hand continue to
    # work unchanged.
    attempts_persisted: int | None = None
    attempts_skipped_idempotent: int | None = None
