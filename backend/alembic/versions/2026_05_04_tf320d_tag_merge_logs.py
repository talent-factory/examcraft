"""tf320d: tag_merge_logs Tabelle

Revision ID: tf320d4f5a6b7
Revises: tf320c3e4f5a6
Create Date: 2026-05-04
"""

from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = "tf320d4f5a6b7"
down_revision: Union[str, None] = "tf320c3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tag_merge_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_tag_id", sa.Integer(), nullable=True),
        sa.Column("target_tag_id", sa.Integer(), nullable=True),
        sa.Column("merged_by", sa.Integer(), nullable=True),
        sa.Column("merged_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("questions_migrated", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["merged_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_tag_id"], ["tags.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_tag_id"], ["tags.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("tag_merge_logs")
