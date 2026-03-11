"""Add billing_owner_id to subscriptions

Revision ID: 968de2a40e04
Revises: 4d90a37a3aac
Create Date: 2026-02-03 19:35:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "968de2a40e04"
down_revision: Union[str, None] = "4d90a37a3aac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add billing_owner_id column to subscriptions table.

    This column tracks which user purchased the subscription.
    Only the billing owner can view invoices, payment methods, and manage the subscription.
    """
    op.add_column(
        "subscriptions",
        sa.Column(
            "billing_owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    # Create index for billing_owner_id lookups
    op.create_index(
        "ix_subscriptions_billing_owner_id",
        "subscriptions",
        ["billing_owner_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove billing_owner_id column from subscriptions table."""
    op.drop_index("ix_subscriptions_billing_owner_id", table_name="subscriptions")
    op.drop_column("subscriptions", "billing_owner_id")
