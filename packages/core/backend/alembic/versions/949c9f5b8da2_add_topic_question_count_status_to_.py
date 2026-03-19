"""add topic, question_count, status to question_generation_jobs

Revision ID: 949c9f5b8da2
Revises: 524100100e68
Create Date: 2026-03-19 20:51:23.550601

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "949c9f5b8da2"  # pragma: allowlist secret
down_revision: Union[str, None] = "524100100e68"  # pragma: allowlist secret
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
    # Pre-existing jobs completed before this feature — mark as SUCCESS
    op.execute(
        "UPDATE question_generation_jobs SET status = 'SUCCESS' WHERE topic IS NULL"
    )


def downgrade() -> None:
    op.drop_column("question_generation_jobs", "status")
    op.drop_column("question_generation_jobs", "question_count")
    op.drop_column("question_generation_jobs", "topic")
