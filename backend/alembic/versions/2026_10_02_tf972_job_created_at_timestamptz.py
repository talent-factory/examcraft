"""make question_generation_jobs.created_at timezone-aware (TF-972)

The column was created as `timestamp without time zone` while the model wrote
`datetime.now(UTC)`. Postgres stored the UTC wall-clock time and handed it
back naive, so `/active-tasks` serialized `created_at` without an offset —
and the browser read e.g. "19:21" as local time, two hours early in Swiss
summer time.

Existing values are UTC wall-clock times (the default always wrote UTC), so
they are converted with `AT TIME ZONE 'UTC'`, independent of the session
time zone. The downgrade converts back the same way.

Revision ID: tf972_job_created_at_tz
Revises: tf749_hash_source_attempt_id
Create Date: 2026-10-02 19:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "tf972_job_created_at_tz"
down_revision: Union[str, None] = "tf749_hash_source_attempt_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "question_generation_jobs",
        "created_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )


def downgrade() -> None:
    op.alter_column(
        "question_generation_jobs",
        "created_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
