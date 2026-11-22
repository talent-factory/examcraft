"""store the profile picture in the users table (EXAMCRAFT-168)

Adds ``avatar_data``, ``avatar_content_type``, ``avatar_source`` and
``avatar_updated_at``. Additive and nullable: no existing row changes, the
legacy proxy keeps serving ``avatar_url`` until the next login syncs it.

Revision ID: ec168_user_avatar_storage
Revises: ec127_mcp_use_role
Create Date: 2026-11-19 17:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "ec168_user_avatar_storage"
down_revision: Union[str, None] = "ec127_mcp_use_role"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_data", sa.LargeBinary(), nullable=True))
    op.add_column(
        "users", sa.Column("avatar_content_type", sa.String(50), nullable=True)
    )
    op.add_column("users", sa.Column("avatar_source", sa.String(10), nullable=True))
    op.add_column(
        "users",
        sa.Column("avatar_updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "avatar_updated_at")
    op.drop_column("users", "avatar_source")
    op.drop_column("users", "avatar_content_type")
    op.drop_column("users", "avatar_data")
