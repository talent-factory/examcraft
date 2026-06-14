"""Domain enums — single source of truth for status fields.

These mirror the DB CHECK constraints. SQLAlchemy columns keep
``String`` + CHECK for defence-in-depth; service code uses these enums
so a typo at the call site fails type-check time, not insert time.
FastAPI Pydantic models annotate fields with these so OpenAPI emits
proper enum schemas, which the frontend consumes via openapi-typescript.
"""

from __future__ import annotations

from enum import StrEnum


class ImportJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"


class ScoringStrategy(StrEnum):
    LATEST = "latest"
    BEST = "best"
    FIRST = "first"


class GradeStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    MANUAL_OVERRIDE = "manual_override"


class SubmissionGradeStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    PARTIALLY_REVIEWED = "partially_reviewed"
    FULLY_REVIEWED = "fully_reviewed"
    # Import-time grading raised; submission has total_points_max set
    # but no per-answer grades. UI must surface this distinctly so
    # operators don't read it as "0 / N points awarded".
    IMPORT_GRADING_FAILED = "import_grading_failed"


class DriverName(StrEnum):
    # This enum doubles as the *display* type for stored import_jobs
    # (``ImportJobOut.driver_name`` deserialises every historical row), so
    # MOODLE_CSV must stay for backward-compat: the CSV file-import driver was
    # removed (TF-423, superseded by the JSON driver) but old rows still carry
    # the value. Creating a NEW csv import is rejected elsewhere — no driver is
    # registered for it (ImportService.DRIVERS) and it's absent from every
    # tier's allowlist (auswertung_quotas) — not by this enum, since the create
    # endpoints validate ``driver_name`` as a plain str, not against DriverName.
    MOODLE_CSV = "moodle_csv"
    MOODLE_API = "moodle_api"
    MOODLE_JSON = "moodle_json"


class AttemptSource(StrEnum):
    """Mirrors DriverName — separate enum so future divergence is type-safe."""

    # MOODLE_CSV retained for historical attempts.source values (TF-423).
    MOODLE_CSV = "moodle_csv"
    MOODLE_API = "moodle_api"
    MOODLE_JSON = "moodle_json"
