"""Idempotent system seed for platform-wide reference data.

Single source of truth for the system grading schemes (``grading_schemes``
with ``institution_id IS NULL``). Called from **both** paths:

* the Alembic migration ``tf333`` (regular prod/migration path), and
* the ``create_all`` bootstrap (``database.py`` fresh-DB branch as well as
  ``just repro-reset``), which *skips* migration bodies and would otherwise
  never receive the schemes (TF-433).

The seed is **idempotent per name**: calling it repeatedly never inserts
duplicates, so it can safely run on every bootstrap and heal existing DBs.

Deliberately only depends on ``sqlalchemy`` (no ORM model import) so the
migration can import it without coupling to drifting model definitions.
"""

from __future__ import annotations

import sqlalchemy as sa

# Platform-wide system grading schemes (institution_id = NULL). In a completely
# empty table the first entry gets id=1; but nothing relies on that exact value —
# the repro recipes collect schemes by their actual ID, not by id=1.
SYSTEM_GRADING_SCHEMES: list[dict] = [
    {
        "name": "Swiss 1.0–6.0",
        "display_format": "numeric",
        "config": {
            "type": "linear_segments",
            "round_to": 0.1,
            "pass_grade_label": "4.0",
            "segments": [
                {"from_pct": 0, "to_pct": 50, "from_grade": 1.0, "to_grade": 4.0},
                {"from_pct": 50, "to_pct": 100, "from_grade": 4.0, "to_grade": 6.0},
            ],
        },
    },
    {
        "name": "German 1.0–5.0",
        "display_format": "numeric",
        "config": {
            "type": "stepped",
            "steps": [
                {"min_pct": 92, "grade_label": "1.0", "is_passing": True},
                {"min_pct": 81, "grade_label": "2.0", "is_passing": True},
                {"min_pct": 67, "grade_label": "3.0", "is_passing": True},
                {"min_pct": 50, "grade_label": "4.0", "is_passing": True},
                {"min_pct": 0, "grade_label": "5.0", "is_passing": False},
            ],
        },
    },
    {
        "name": "Austrian 1–5",
        "display_format": "numeric",
        "config": {
            "type": "stepped",
            "steps": [
                {"min_pct": 90, "grade_label": "1", "is_passing": True},
                {"min_pct": 80, "grade_label": "2", "is_passing": True},
                {"min_pct": 65, "grade_label": "3", "is_passing": True},
                {"min_pct": 51, "grade_label": "4", "is_passing": True},
                {"min_pct": 0, "grade_label": "5", "is_passing": False},
            ],
        },
    },
    {
        "name": "French 0–20",
        "display_format": "numeric",
        "config": {
            "type": "linear",
            "min_pct": 0,
            "max_pct": 100,
            "min_grade": 0,
            "max_grade": 20,
            "round_to": 0.5,
            "pass_grade_label": "10",
        },
    },
    {
        "name": "Dutch 1–10",
        "display_format": "numeric",
        "config": {
            "type": "linear",
            "min_pct": 0,
            "max_pct": 100,
            "min_grade": 1,
            "max_grade": 10,
            "round_to": 0.1,
            "pass_grade_label": "5.5",
        },
    },
    {
        "name": "ECTS A–F",
        "display_format": "letter",
        "config": {
            "type": "stepped",
            "steps": [
                {"min_pct": 90, "grade_label": "A", "is_passing": True},
                {"min_pct": 80, "grade_label": "B", "is_passing": True},
                {"min_pct": 65, "grade_label": "C", "is_passing": True},
                {"min_pct": 55, "grade_label": "D", "is_passing": True},
                {"min_pct": 50, "grade_label": "E", "is_passing": True},
                {"min_pct": 0, "grade_label": "F", "is_passing": False},
            ],
        },
    },
    {
        "name": "Prozent",
        "display_format": "numeric",
        "config": {
            "type": "linear",
            "min_pct": 0,
            "max_pct": 100,
            "min_grade": 0,
            "max_grade": 100,
            "round_to": 0.1,
            "pass_grade_label": "50",
        },
    },
    {
        "name": "Pass/Fail",
        "display_format": "pass_fail",
        "config": {
            "type": "stepped",
            "steps": [
                {"min_pct": 50, "grade_label": "Pass", "is_passing": True},
                {"min_pct": 0, "grade_label": "Fail", "is_passing": False},
            ],
        },
    },
]

# Lightweight core Table projection (no ORM model import — see docstring).
_grading_schemes = sa.table(
    "grading_schemes",
    sa.column("institution_id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("display_format", sa.String),
    sa.column("config", sa.JSON),
    sa.column("is_default_for_institution", sa.Boolean),
)


def seed_system_grading_schemes(conn: sa.engine.Connection) -> int:
    """Inserts missing system grading schemes (``institution_id IS NULL``).

    Idempotent per ``name``: schemes that already exist are skipped.
    Expects an active ``Connection`` (e.g. ``op.get_bind()`` in the migration
    or ``engine.begin()`` in the bootstrap). Returns the number of rows
    inserted.
    """
    existing = set(
        conn.execute(
            sa.select(_grading_schemes.c.name).where(
                _grading_schemes.c.institution_id.is_(None)
            )
        ).scalars()
    )
    missing = [s for s in SYSTEM_GRADING_SCHEMES if s["name"] not in existing]
    if missing:
        conn.execute(
            _grading_schemes.insert(),
            [
                {
                    "institution_id": None,
                    "name": s["name"],
                    "display_format": s["display_format"],
                    "config": s["config"],
                    "is_default_for_institution": False,
                }
                for s in missing
            ],
        )
    return len(missing)
