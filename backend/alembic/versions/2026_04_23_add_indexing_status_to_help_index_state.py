"""add indexing_status and last_error to help_index_state

Revision ID: ab73e5f9c201
Revises: 39cd0f3c3bbf
Create Date: 2026-04-23 18:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "ab73e5f9c201"
down_revision: Union[str, None] = "39cd0f3c3bbf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # indexing_status: lifecycle tracker, backfilled to 'idle' for existing rows.
    op.add_column(
        "help_index_state",
        sa.Column(
            "indexing_status",
            sa.String(length=20),
            nullable=False,
            server_default="idle",
        ),
    )
    # last_error: most recent exception message when status='failed', else NULL.
    op.add_column(
        "help_index_state",
        sa.Column("last_error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("help_index_state", "last_error")
    op.drop_column("help_index_state", "indexing_status")
