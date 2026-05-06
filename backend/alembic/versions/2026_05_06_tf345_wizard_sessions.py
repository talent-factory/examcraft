"""Create wizard_sessions and wizard_messages tables.

The PromptWizard feature (KI-Assistent tab in Prompt-Bibliothek) stores
AI-guided prompt creation sessions in these two tables. They were
implemented in the premium models but never migrated, causing every
GET /api/v1/wizard/sessions request to fail with a 500 because
Postgres reported "relation 'wizard_sessions' does not exist".

Revision ID: tf345_wizard_sessions
Revises: tf337_audit_logs_idx
"""

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "tf345_wizard_sessions"
down_revision: Union[str, None] = "tf337_audit_logs_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = inspector.get_table_names()

    if "wizard_sessions" not in existing:
        op.create_table(
            "wizard_sessions",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False
            ),
            sa.Column(
                "title", sa.String(255), nullable=True, server_default="Neue Session"
            ),
            sa.Column("status", sa.String(50), nullable=False, server_default="active"),
            sa.Column(
                "reference_prompt_id",
                UUID(as_uuid=True),
                sa.ForeignKey("prompts.id"),
                nullable=True,
            ),
            sa.Column(
                "generated_prompt_id",
                UUID(as_uuid=True),
                sa.ForeignKey("prompts.id"),
                nullable=True,
            ),
            sa.Column("collected_parameters", JSONB(), nullable=True),
            sa.Column("generated_template", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.CheckConstraint(
                "status IN ('active', 'completed', 'cancelled')",
                name="check_wizard_session_status",
            ),
        )
        op.create_index("ix_wizard_sessions_user_id", "wizard_sessions", ["user_id"])
        op.create_index("ix_wizard_sessions_status", "wizard_sessions", ["status"])

    if "wizard_messages" not in existing:
        op.create_table(
            "wizard_messages",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "session_id",
                UUID(as_uuid=True),
                sa.ForeignKey("wizard_sessions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("role", sa.String(50), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("message_metadata", JSONB(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.CheckConstraint(
                "role IN ('system', 'assistant', 'user')",
                name="check_wizard_message_role",
            ),
        )
        op.create_index(
            "ix_wizard_messages_session_id", "wizard_messages", ["session_id"]
        )


def downgrade() -> None:
    op.drop_table("wizard_messages")
    op.drop_table("wizard_sessions")
