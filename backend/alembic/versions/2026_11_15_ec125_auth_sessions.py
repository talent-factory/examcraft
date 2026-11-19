"""add auth_sessions (EXAMCRAFT-125)

Server-side sessions for the single login via tessera/Zitadel (ADR 0008).
Additive: a new table, nothing existing is touched. The cookie token is
stored as a SHA-256 hash.

Revision ID: ec125_auth_sessions
Revises: ec121_users_zitadel_sub
Create Date: 2026-11-15 10:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "ec125_auth_sessions"
down_revision: Union[str, None] = "ec121_users_zitadel_sub"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "impersonator_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "impersonation_session_id",
            sa.Integer(),
            sa.ForeignKey("impersonation_sessions.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("authenticated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_sessions_id", "auth_sessions", ["id"])
    op.create_index(
        "ix_auth_sessions_token_hash", "auth_sessions", ["token_hash"], unique=True
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index(
        "ix_auth_sessions_impersonator_id", "auth_sessions", ["impersonator_id"]
    )
    op.create_index(
        "ix_auth_sessions_impersonation_session_id",
        "auth_sessions",
        ["impersonation_session_id"],
    )
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_table("auth_sessions")
