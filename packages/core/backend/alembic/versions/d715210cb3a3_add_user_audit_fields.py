"""add_user_audit_fields

Revision ID: d715210cb3a3
Revises:
Create Date: 2026-03-12

"""

from alembic import op
import sqlalchemy as sa

revision = "d715210cb3a3"  # pragma: allowlist secret
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users", sa.Column("registration_method", sa.String(20), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "registration_method")
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "email_verified_at")
