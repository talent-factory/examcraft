"""add generated_question_count and context_limited to question_generation_jobs (TF-736)

An under-filled RAG generation (fewer questions than requested because the
selected documents ran out of material) was only explained in the Celery
result's quality_metrics. That result expires (Celery default: 24 h), after
which nothing recorded that 15 were requested and 6 were created.

The requested count already lives in question_count; generated_question_count
is its counterpart. No column for the notice text: the frontend renders it in
the user's language from the two counts.

Existing rows get context_limited = FALSE through the server default and
generated_question_count = NULL ("not recorded"), which is what they are.

Revision ID: tf736_generation_job_outcome
Revises: tf625_hint_i18n_key
Create Date: 2026-09-19 10:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "tf736_generation_job_outcome"
down_revision: Union[str, None] = "tf625_hint_i18n_key"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "question_generation_jobs",
        sa.Column("generated_question_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "question_generation_jobs",
        sa.Column(
            "context_limited",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("question_generation_jobs", "context_limited")
    op.drop_column("question_generation_jobs", "generated_question_count")
