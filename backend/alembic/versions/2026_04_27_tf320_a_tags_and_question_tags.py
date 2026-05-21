"""tf320: tags and question_tags tables

Revision ID: tf320a1b2c3d4
Revises: ab73e5f9c201
Create Date: 2026-04-27
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "tf320a1b2c3d4"
down_revision: Union[str, None] = "ab73e5f9c201"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "institution_id", name="uq_tag_name_institution"),
    )
    op.create_index("ix_tags_id", "tags", ["id"])
    op.create_index("ix_tags_institution_id", "tags", ["institution_id"])

    op.create_table(
        "question_tags",
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["question_id"], ["question_reviews.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("question_id", "tag_id"),
    )


def downgrade() -> None:
    op.drop_table("question_tags")
    op.drop_index("ix_tags_institution_id", table_name="tags")
    op.drop_index("ix_tags_id", table_name="tags")
    op.drop_table("tags")
