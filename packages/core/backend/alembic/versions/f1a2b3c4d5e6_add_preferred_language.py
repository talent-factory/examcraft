"""add_preferred_language

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
Create Date: 2026-03-22 10:00:00.000000

Add preferred_language column to users table for i18n Phase 1.
NULL means "use browser locale / Accept-Language header".
Valid values: de, en, fr, it (enforced by CHECK constraint).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"  # pragma: allowlist secret
down_revision: Union[str, None] = "e1f2a3b4c5d6"  # pragma: allowlist secret
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    """Check if a column already exists (idempotent migration support)."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c["name"] for c in inspector.get_columns(table)]
    return column in columns


def _constraint_exists(table: str, constraint_name: str) -> bool:
    """Check if a check constraint already exists (idempotent migration support)."""
    bind = op.get_bind()
    inspector = inspect(bind)
    constraints = [c["name"] for c in inspector.get_check_constraints(table)]
    return constraint_name in constraints


def upgrade() -> None:
    if not _column_exists("users", "preferred_language"):
        op.add_column(
            "users",
            sa.Column("preferred_language", sa.String(5), nullable=True),
        )
    if not _constraint_exists("users", "ck_user_preferred_language"):
        op.create_check_constraint(
            "ck_user_preferred_language",
            "users",
            "preferred_language IN ('de', 'en', 'fr', 'it') OR preferred_language IS NULL",
        )


def downgrade() -> None:
    if _constraint_exists("users", "ck_user_preferred_language"):
        op.drop_constraint("ck_user_preferred_language", "users", type_="check")
    if _column_exists("users", "preferred_language"):
        op.drop_column("users", "preferred_language")
