"""TF-335: switch grading_scheme FKs from SET NULL to RESTRICT

Revision ID: tf335_fk_restrict
Revises: tf333_phase1
Create Date: 2026-05-01

Why
---

The original phase-1 migration set ``ON DELETE SET NULL`` on both
``exams.grading_scheme_id`` and ``institutions.default_grading_scheme_id``.
That made delete look safe at the DB level but silently corrupted exams
and institution defaults — the API tried to compensate with a pre-flight
in-use guard, but it was racy (TOCTOU between the SELECT and the DELETE
COMMIT).

RESTRICT pushes the invariant down to Postgres. The API still does a
friendly pre-check so the user sees a 409 with a useful message; if
that pre-check loses the race, the constraint surfaces an
``IntegrityError`` and the API translates it into the same 409.

Constraint-name discovery
-------------------------

Fresh databases bootstrapped by ``database._run_migrations_or_create_all``
get their schema from ``Base.metadata.create_all`` and are then stamped
to the alembic head — the FKs end up with Postgres' default
``<table>_<column>_fkey`` shape rather than the explicit names from the
phase-1 migration (``fk_exams_grading_scheme``,
``fk_institutions_default_grading_scheme``). Both shapes exist in the
wild, so we discover the actual constraint name via the inspector
instead of hard-coding it.

Side effect: after this migration the FK is always named with the
explicit phase-1 form, regardless of which shape the DB started in.
``downgrade`` keeps the explicit name too — round-trip restores the
``ON DELETE`` semantics but normalizes the name. This is intentional.

Run-mode requirements
---------------------

This migration must run online — it inspects the live schema to
discover the existing FK name. Offline ``alembic upgrade --sql`` is
explicitly refused with an actionable error rather than silently
producing broken SQL.

The whole migration runs inside Postgres' default per-migration
transaction (transactional DDL), so a mid-way failure rolls back
cleanly and the migration can be retried.
"""

from typing import Sequence, Union

from alembic import context, op
from sqlalchemy import inspect


revision: str = "tf335_fk_restrict"
down_revision: Union[str, None] = "tf333_phase1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TARGET_FK_NAME = {
    ("exams", "grading_scheme_id"): "fk_exams_grading_scheme",
    ("institutions", "default_grading_scheme_id"): (
        "fk_institutions_default_grading_scheme"
    ),
}

_REFERRED_TABLE = "grading_schemes"


def _drop_fk_for_column(table: str, column: str) -> None:
    """Drop the single-column FK on ``table.column`` referencing
    ``grading_schemes``, regardless of constraint name.

    Refuses to run in offline mode (no live schema to inspect). Refuses
    to guess if the column has zero or multiple matching FKs, or if the
    matching FK has no name in the inspector output. Composite FKs that
    include this column are not matched.
    """
    if context.is_offline_mode():
        raise RuntimeError(
            "tf335_fk_restrict cannot run in offline (--sql) mode: it "
            "must introspect the live schema to discover the existing "
            "FK name (Postgres-default vs. explicit phase-1 form). "
            "Run `alembic upgrade tf335_fk_restrict` online against "
            "the target database instead."
        )

    inspector = inspect(op.get_bind())
    all_fks = inspector.get_foreign_keys(table)
    matches = [
        fk
        for fk in all_fks
        if fk["constrained_columns"] == [column]
        and fk["referred_table"] == _REFERRED_TABLE
    ]

    if len(matches) == 0:
        existing = [
            (fk["name"], fk["constrained_columns"], fk["referred_table"])
            for fk in all_fks
        ]
        raise RuntimeError(
            f"tf335_fk_restrict expected exactly one FK on "
            f"{table}.{column} referencing {_REFERRED_TABLE}.id, found "
            f"none. FKs currently on {table}: {existing}. Likely "
            "causes: (a) the DB was bootstrapped from "
            "Base.metadata.create_all but never had phase-1 "
            "(tf333_phase1) applied — re-run from there; (b) a previous "
            "tf335 attempt half-succeeded — the per-migration "
            "transaction should have rolled it back, so verify the "
            "alembic_version row and restore the SET NULL FK from the "
            "phase-1 definition before retrying; (c) the FK was "
            "hand-removed in this environment — restore it first."
        )

    if len(matches) > 1:
        names = sorted(str(fk["name"]) for fk in matches)
        raise RuntimeError(
            f"tf335_fk_restrict found multiple FKs on {table}.{column} "
            f"referencing {_REFERRED_TABLE}: {names}. Refusing to guess "
            "which one to swap. Drop the stray constraint manually and "
            "re-run."
        )

    fk_name = matches[0]["name"]
    if fk_name is None:
        raise RuntimeError(
            f"tf335_fk_restrict found an unnamed FK on {table}.{column}; "
            "cannot drop by name. Query "
            "information_schema.table_constraints to identify it and "
            "drop it manually before re-running."
        )

    op.drop_constraint(fk_name, table, type_="foreignkey")


def _swap_fk(table: str, column: str, ondelete: str) -> None:
    _drop_fk_for_column(table, column)
    op.create_foreign_key(
        _TARGET_FK_NAME[(table, column)],
        table,
        _REFERRED_TABLE,
        [column],
        ["id"],
        ondelete=ondelete,
    )


def upgrade() -> None:
    _swap_fk("exams", "grading_scheme_id", "RESTRICT")
    _swap_fk("institutions", "default_grading_scheme_id", "RESTRICT")


def downgrade() -> None:
    _swap_fk("exams", "grading_scheme_id", "SET NULL")
    _swap_fk("institutions", "default_grading_scheme_id", "SET NULL")
