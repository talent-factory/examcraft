"""add dismissed_at to question_generation_jobs (TF-736)

`/active-tasks` now keeps under-filled generations (context_limited) in the
generation panel for 8 hours instead of 30 minutes. Closing such an entry was
only remembered in the tab's sessionStorage, so it came back in every new tab,
after a new login and on every other device — for up to 8 hours. The endpoint
skips rows with dismissed_at set.

Existing rows get NULL ("never dismissed"), which is what they are.

Revision ID: tf736_job_dismissed_at
Revises: password_reset_tokens
Create Date: 2026-09-28 10:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "tf736_job_dismissed_at"
down_revision: Union[str, None] = "password_reset_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "question_generation_jobs",
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("question_generation_jobs", "dismissed_at")
