"""Add feedback_clusters table and extend help_faq_cache

Revision ID: 2026_04_14_feedback
Revises: 2026_03_31_add_skipped_steps
Create Date: 2026-04-14
"""
from alembic import op
import sqlalchemy as sa

revision = "2026_04_14_feedback"
down_revision = "2026_03_31_add_skipped_steps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feedback_clusters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("topic_label", sa.String(100), nullable=False),
        sa.Column("vector_id", sa.String(36), nullable=True),
        sa.Column("positive_count", sa.Integer(), default=0, nullable=False),
        sa.Column("negative_count", sa.Integer(), default=0, nullable=False),
        sa.Column("total_count", sa.Integer(), default=0, nullable=False),
        sa.Column("status", sa.String(20), default="aktiv", nullable=False),
        sa.Column("suggested_answer_de", sa.Text(), nullable=True),
        sa.Column("suggested_answer_en", sa.Text(), nullable=True),
        sa.Column("docs_gap", sa.Boolean(), default=False, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.add_column("help_faq_cache", sa.Column("approved_by", sa.Integer(), nullable=True))
    op.add_column("help_faq_cache", sa.Column("cluster_id", sa.Integer(), nullable=True))
    op.add_column("help_faq_cache", sa.Column("faq_status", sa.String(20), server_default="vorgeschlagen", nullable=False))

    op.create_foreign_key("fk_faq_approved_by", "help_faq_cache", "users", ["approved_by"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_faq_cluster_id", "help_faq_cache", "feedback_clusters", ["cluster_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_help_faq_cache_cluster_id", "help_faq_cache", ["cluster_id"])


def downgrade() -> None:
    op.drop_index("ix_help_faq_cache_cluster_id")
    op.drop_constraint("fk_faq_cluster_id", "help_faq_cache", type_="foreignkey")
    op.drop_constraint("fk_faq_approved_by", "help_faq_cache", type_="foreignkey")
    op.drop_column("help_faq_cache", "faq_status")
    op.drop_column("help_faq_cache", "cluster_id")
    op.drop_column("help_faq_cache", "approved_by")
    op.drop_table("feedback_clusters")
