"""tf320c: scope, usage_count, is_archived auf tags

Revision ID: tf320c3e4f5a6
Revises: tf320b2c3d4e5
Create Date: 2026-05-04
"""

from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = "tf320c3e4f5a6"
down_revision: Union[str, None] = "tf320b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tags",
        sa.Column("scope", sa.String(20), nullable=False, server_default="institution"),
    )
    op.add_column(
        "tags",
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "tags",
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
    )
    # institution_id darf nun NULL sein (für globale Tags)
    op.alter_column("tags", "institution_id", nullable=True)


def downgrade() -> None:
    op.alter_column("tags", "institution_id", nullable=False)
    op.drop_column("tags", "is_archived")
    op.drop_column("tags", "usage_count")
    op.drop_column("tags", "scope")
