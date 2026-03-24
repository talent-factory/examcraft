"""add_require_second_reviewer

Revision ID: a1b2c3d4e5f6
Revises: d715210cb3a3
Create Date: 2026-03-18

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "a1b2c3d4e5f6"  # pragma: allowlist secret
down_revision = "d715210cb3a3"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    """Check if a column already exists (idempotent migration support)."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c["name"] for c in inspector.get_columns(table)]
    return column in columns


def upgrade() -> None:
    if not _column_exists("institutions", "require_second_reviewer"):
        op.add_column(
            "institutions",
            sa.Column(
                "require_second_reviewer",
                sa.Boolean(),
                nullable=True,
                server_default=sa.text("false"),
            ),
        )


def downgrade() -> None:
    if _column_exists("institutions", "require_second_reviewer"):
        op.drop_column("institutions", "require_second_reviewer")
