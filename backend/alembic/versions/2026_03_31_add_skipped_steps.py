"""add skipped_steps to help_onboarding_progress

Revision ID: 2026_03_31_skipped
Revises: 2026_03_26_help
Create Date: 2026-03-31 10:00:00.000000
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "2026_03_31_skipped"
down_revision: Union[str, None] = "2026_03_26_help"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "help_onboarding_progress",
        sa.Column(
            "skipped_steps",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("help_onboarding_progress", "skipped_steps")
