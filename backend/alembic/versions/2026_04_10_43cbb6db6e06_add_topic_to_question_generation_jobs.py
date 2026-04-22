"""add_topic_to_question_generation_jobs

Revision ID: 43cbb6db6e06
Revises: 06668c037bdb
Create Date: 2026-04-10 11:12:34.811682

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "43cbb6db6e06"
down_revision: Union[str, None] = "06668c037bdb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "question_generation_jobs", sa.Column("topic", sa.String(), nullable=True)
    )
    op.add_column(
        "question_generation_jobs",
        sa.Column("question_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "question_generation_jobs",
        sa.Column("status", sa.String(), server_default="PENDING", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("question_generation_jobs", "status")
    op.drop_column("question_generation_jobs", "question_count")
    op.drop_column("question_generation_jobs", "topic")
