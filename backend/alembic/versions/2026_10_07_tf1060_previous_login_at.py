"""add users.previous_login_at (TF-1060)

The profile showed "last login" from last_login_at, but every login stamps
that column before the frontend loads /auth/me — it is always the current
session. previous_login_at keeps the login before it.

Existing rows stay NULL: the previous login was never recorded, and the
profile hides the block until the next login fills the column.

Revision ID: tf1060_previous_login_at
Revises: tf972_job_created_at_tz
Create Date: 2026-10-07 10:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "tf1060_previous_login_at"
down_revision: Union[str, None] = "tf972_job_created_at_tz"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("previous_login_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "previous_login_at")
