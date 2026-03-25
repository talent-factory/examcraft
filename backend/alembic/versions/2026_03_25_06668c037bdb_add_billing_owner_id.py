"""add billing_owner_id to subscriptions

Revision ID: 06668c037bdb
Revises: f1a2b3c4d5e6
Create Date: 2026-03-25

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "06668c037bdb"  # pragma: allowlist secret
down_revision: Union[str, None] = "f1a2b3c4d5e6"  # pragma: allowlist secret
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = [c["name"] for c in inspector.get_columns("subscriptions")]
    if "billing_owner_id" not in cols:
        op.add_column(
            "subscriptions",
            sa.Column("billing_owner_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            op.f("subscriptions_billing_owner_id_fkey"),
            "subscriptions",
            "users",
            ["billing_owner_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(
            op.f("ix_subscriptions_billing_owner_id"),
            "subscriptions",
            ["billing_owner_id"],
            unique=False,
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = [c["name"] for c in inspector.get_columns("subscriptions")]
    if "billing_owner_id" in cols:
        indexes = [idx["name"] for idx in inspector.get_indexes("subscriptions")]
        if "ix_subscriptions_billing_owner_id" in indexes:
            op.drop_index(
                op.f("ix_subscriptions_billing_owner_id"),
                table_name="subscriptions",
            )
        fks = [fk["name"] for fk in inspector.get_foreign_keys("subscriptions")]
        if "subscriptions_billing_owner_id_fkey" in fks:
            op.drop_constraint(
                op.f("subscriptions_billing_owner_id_fkey"),
                "subscriptions",
                type_="foreignkey",
            )
        op.drop_column("subscriptions", "billing_owner_id")
