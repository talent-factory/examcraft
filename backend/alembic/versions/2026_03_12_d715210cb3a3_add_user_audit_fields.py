"""add_user_audit_fields

Revision ID: d715210cb3a3
Revises:
Create Date: 2026-03-12

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "d715210cb3a3"  # pragma: allowlist secret
down_revision = None
branch_labels = None
depends_on = None


def _table_exists(table: str) -> bool:
    """Check if a table exists."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return inspector.has_table(table)


def _column_exists(table: str, column: str) -> bool:
    """Check if a column already exists (idempotent migration support)."""
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(table):
        return False
    columns = [c["name"] for c in inspector.get_columns(table)]
    return column in columns


def upgrade() -> None:
    # Skip if table doesn't exist yet — create_all() will create it with these columns
    if not _table_exists("users"):
        return
    if not _column_exists("users", "email_verified_at"):
        op.add_column(
            "users",
            sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not _column_exists("users", "password_changed_at"):
        op.add_column(
            "users",
            sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not _column_exists("users", "registration_method"):
        op.add_column(
            "users", sa.Column("registration_method", sa.String(20), nullable=True)
        )


def downgrade() -> None:
    if _column_exists("users", "registration_method"):
        op.drop_column("users", "registration_method")
    if _column_exists("users", "password_changed_at"):
        op.drop_column("users", "password_changed_at")
    if _column_exists("users", "email_verified_at"):
        op.drop_column("users", "email_verified_at")
