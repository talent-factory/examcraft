"""moodle feedback push job (TF-435)

Revision ID: moodle_feedback_push_job
Revises: tf428_import_progress
Create Date: 2026-06-17

"""

import sqlalchemy as sa
from alembic import op

revision = "moodle_feedback_push_job"
down_revision = "tf428_import_progress"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "moodle_feedback_push_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("exam_id", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(length=20), server_default="queued", nullable=False
        ),
        sa.Column("transport", sa.String(length=20), nullable=True),
        sa.Column("students_total", sa.Integer(), server_default="0", nullable=False),
        sa.Column("students_pushed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("students_skipped", sa.Integer(), server_default="0", nullable=False),
        sa.Column("students_failed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_log", sa.JSON(), nullable=True),
        sa.Column("triggered_by", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triggered_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'failed')",
            name="check_moodle_feedback_push_status",
        ),
        sa.CheckConstraint(
            "transport IS NULL OR transport IN ('plugin', 'gradebook')",
            name="check_moodle_feedback_push_transport",
        ),
        sa.CheckConstraint(
            "students_total >= 0 AND students_pushed >= 0 "
            "AND students_skipped >= 0 AND students_failed >= 0",
            name="check_moodle_feedback_push_counters",
        ),
        sa.CheckConstraint(
            "status != 'completed' OR "
            "students_pushed + students_skipped + students_failed = students_total",
            name="check_moodle_feedback_push_counter_sum",
        ),
    )
    op.create_index(
        "ix_moodle_feedback_push_jobs_institution_id",
        "moodle_feedback_push_jobs",
        ["institution_id"],
    )
    op.create_index(
        "ix_moodle_feedback_push_jobs_exam_id",
        "moodle_feedback_push_jobs",
        ["exam_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_moodle_feedback_push_jobs_exam_id",
        table_name="moodle_feedback_push_jobs",
    )
    op.drop_index(
        "ix_moodle_feedback_push_jobs_institution_id",
        table_name="moodle_feedback_push_jobs",
    )
    op.drop_table("moodle_feedback_push_jobs")
