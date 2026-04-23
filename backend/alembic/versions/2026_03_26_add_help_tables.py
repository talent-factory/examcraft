"""add_help_tables

Revision ID: 2026_03_26_help
Revises: 06668c037bdb
Create Date: 2026-03-26 17:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026_03_26_help"
down_revision: Union[str, None] = "06668c037bdb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # help_onboarding_progress
    op.create_table(
        "help_onboarding_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_steps", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("role IN ('teacher', 'admin')", name="ck_onboarding_role"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_help_onboarding_progress_id"),
        "help_onboarding_progress",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_help_onboarding_progress_user_id"),
        "help_onboarding_progress",
        ["user_id"],
        unique=True,
    )

    # help_conversations
    op.create_table(
        "help_conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("messages", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("route", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_help_conversations_id"),
        "help_conversations",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_help_conversations_user_id"),
        "help_conversations",
        ["user_id"],
        unique=False,
    )

    # help_feedback
    op.create_table(
        "help_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("rating", sa.String(length=10), nullable=True),
        sa.Column("user_role", sa.String(length=20), nullable=True),
        sa.Column("user_tier", sa.String(length=30), nullable=True),
        sa.Column("route", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column("cluster_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="offen",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("rating IN ('up', 'down')", name="ck_feedback_rating"),
        sa.CheckConstraint(
            "status IN ('offen', 'in_bearbeitung', 'dokumentiert')",
            name="ck_feedback_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_help_feedback_id"), "help_feedback", ["id"], unique=False)
    op.create_index(
        op.f("ix_help_feedback_cluster_id"),
        "help_feedback",
        ["cluster_id"],
        unique=False,
    )

    # help_context_hints
    op.create_table(
        "help_context_hints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("route_pattern", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=True),
        sa.Column("tier", sa.String(length=30), nullable=True),
        sa.Column("hint_text_de", sa.Text(), nullable=False),
        sa.Column("hint_text_en", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_help_context_hints_id"),
        "help_context_hints",
        ["id"],
        unique=False,
    )

    # help_faq_cache
    op.create_table(
        "help_faq_cache",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("answer_de", sa.Text(), nullable=False),
        sa.Column("answer_en", sa.Text(), nullable=False),
        sa.Column("docs_links", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("source_files", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stale", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_help_faq_cache_id"), "help_faq_cache", ["id"], unique=False
    )

    # help_dismissed_hints
    op.create_table(
        "help_dismissed_hints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("hint_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["hint_id"], ["help_context_hints.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "hint_id", name="uq_dismissed_user_hint"),
    )
    op.create_index(
        op.f("ix_help_dismissed_hints_id"),
        "help_dismissed_hints",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_help_dismissed_hints_user_id"),
        "help_dismissed_hints",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_help_dismissed_hints_hint_id"),
        "help_dismissed_hints",
        ["hint_id"],
        unique=False,
    )

    # help_index_state
    op.create_table(
        "help_index_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("last_indexed_sha", sa.String(length=40), nullable=True),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("files_indexed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_deleted", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_help_index_state_id"),
        "help_index_state",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("help_index_state")
    op.drop_index(
        op.f("ix_help_dismissed_hints_hint_id"), table_name="help_dismissed_hints"
    )
    op.drop_table("help_dismissed_hints")
    op.drop_table("help_faq_cache")
    op.drop_table("help_context_hints")
    op.drop_table("help_feedback")
    op.drop_table("help_conversations")
    op.drop_table("help_onboarding_progress")
