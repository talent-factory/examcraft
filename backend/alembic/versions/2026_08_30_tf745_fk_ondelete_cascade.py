"""Fix ON DELETE policy drift on two users.id FKs (TF-745 final-review fix).

`services.gdpr_deletion_service.delete_user_and_gdpr_data` does
``db.delete(user); db.commit()`` and relies entirely on FK ``ondelete``
policies to cascade/anonymize dependent rows. Two tables had NO policy at
all in the real database (``NO ACTION``), so deleting a user with rows in
either table raised ``IntegrityError``:

- ``wizard_sessions.user_id`` — the model (``premium/backend/models/wizard.py``)
  never declared ``ondelete`` either; personal working data belongs in the
  hard-delete category (same as Documents/Sessions/OAuth-Accounts), so this
  fixes both model and DB to ``CASCADE``.
- ``question_generation_jobs.user_id`` — model/migration drift: the model
  (``core/backend/models/question_generation_job.py``) already declared
  ``ondelete="CASCADE"``, but the migration that created the table
  (``2026_03_18_d74c69d53df6_add_question_generation_jobs.py``) never applied
  it, so every real database that ran that migration actually enforces
  ``NO ACTION``. This migration makes the DB match what the model always
  claimed.

Constraint names are discovered via introspection rather than hardcoded,
since Postgres's auto-generated FK constraint names for inline-defined FKs
are not 100% predictable without checking (see
``2026_05_01_tf335_grading_scheme_fk_restrict.py``'s ``_drop_fk_for_column``
for the same introspection-guarded pattern this migration follows — it
matches by ``referred_table``/``constrained_columns`` for the identical
reason).

Revision ID: tf745_fk_ondelete_cascade
Revises: tf740_impersonation_sessions
Create Date: 2026-08-30
"""

from typing import Optional, Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "tf745_fk_ondelete_cascade"
down_revision: Union[str, None] = "tf740_impersonation_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table_name, local column, referenced table)
_TARGETS = [
    ("wizard_sessions", "user_id", "users"),
    ("question_generation_jobs", "user_id", "users"),
]


def _find_user_fk(
    inspector: sa.engine.reflection.Inspector,
    table: str,
    column: str,
    referenced_table: str,
) -> Optional[dict]:
    """Find the FK constraint on ``table`` that references ``referenced_table``
    via ``column``. Returns the raw ``get_foreign_keys()`` dict, or None."""
    for fk in inspector.get_foreign_keys(table):
        if fk.get("referred_table") == referenced_table and fk.get(
            "constrained_columns"
        ) == [column]:
            return fk
    return None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    for table, column, referenced_table in _TARGETS:
        if table not in existing_tables:
            continue

        fk = _find_user_fk(inspector, table, column, referenced_table)
        if fk is None:
            # Nothing to fix (constraint missing entirely, or already
            # renamed away from what we expect) — skip defensively rather
            # than fail the migration.
            continue

        if fk.get("options", {}).get("ondelete") == "CASCADE":
            # Already fixed (re-run safety) — skip.
            continue

        constraint_name = fk["name"]
        op.drop_constraint(constraint_name, table, type_="foreignkey")
        op.create_foreign_key(
            constraint_name,
            table,
            referenced_table,
            [column],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    for table, column, referenced_table in _TARGETS:
        if table not in existing_tables:
            continue

        fk = _find_user_fk(inspector, table, column, referenced_table)
        if fk is None:
            continue

        if fk.get("options", {}).get("ondelete") != "CASCADE":
            # Already back to no policy (or never got the CASCADE fix) —
            # skip.
            continue

        constraint_name = fk["name"]
        op.drop_constraint(constraint_name, table, type_="foreignkey")
        op.create_foreign_key(
            constraint_name,
            table,
            referenced_table,
            [column],
            ["id"],
        )
