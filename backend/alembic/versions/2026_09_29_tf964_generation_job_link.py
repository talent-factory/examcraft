"""link question_reviews to their generation job, count redeliveries (TF-964)

A generation that died after saving its questions but before SUCCESS left the
questions in the review queue and the job on PENDING (later reconciled to
FAILURE by the watchdog). The retry button (or a redelivered message) then
generated the whole set a second time.

question_reviews.generation_job_id records which job created a question; it
is written in the same commit as the job's SUCCESS, so a task can tell at
start that its job already finished. ON DELETE SET NULL: deleting a job row
must never take the questions with it.

question_generation_jobs.redelivery_count bounds how often a job's message is
redelivered after the worker was lost (reject_on_worker_lost=True).

Existing rows: generation_job_id = NULL (link not recorded, so the
idempotency check does not detect jobs from before this revision) and
redelivery_count = 0 through the server default.

Revision ID: tf964_generation_job_link
Revises: tf961_schema_reconcile
Create Date: 2026-09-29 16:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "tf964_generation_job_link"
down_revision: Union[str, None] = "tf961_schema_reconcile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "question_reviews",
        sa.Column("generation_job_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_question_reviews_generation_job_id",
        "question_reviews",
        "question_generation_jobs",
        ["generation_job_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_question_reviews_generation_job_id",
        "question_reviews",
        ["generation_job_id"],
    )
    op.add_column(
        "question_generation_jobs",
        sa.Column(
            "redelivery_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("question_generation_jobs", "redelivery_count")
    op.drop_index(
        "ix_question_reviews_generation_job_id", table_name="question_reviews"
    )
    op.drop_constraint(
        "fk_question_reviews_generation_job_id",
        "question_reviews",
        type_="foreignkey",
    )
    op.drop_column("question_reviews", "generation_job_id")
