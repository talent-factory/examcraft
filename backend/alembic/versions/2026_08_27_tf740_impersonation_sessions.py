"""Impersonation data model + permission (TF-740, part of the TF-739 epic).

Additive migration (no data loss): creates the new ``impersonation_sessions``
table (nullable admin/target FKs with ``ON DELETE SET NULL`` so the audit
trail row survives a later user deletion instead of blocking it, plus CHECK
constraints on ``end_reason``, admin/target distinctness and the
``ended_at``/``end_reason`` pairing, and a partial-unique index enforcing at
most one active session per admin) and adds
``audit_logs.impersonator_user_id``. The new ``users:impersonate``
permission string itself lives in ``utils/permissions.py`` / the custom role
editor — no seed-role change, no DB migration needed for it (it is
deliberately not seeded to any default role, see ``OPT_IN_ONLY_PERMISSIONS``).

Revision ID: tf740_impersonation_sessions
Revises: tf644_competency_visibility
Create Date: 2026-08-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "tf740_impersonation_sessions"
down_revision: Union[str, None] = "tf644_competency_visibility"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "impersonation_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        # Nullable despite always being set at creation: ondelete="SET NULL"
        # below needs somewhere to null the FK to when a referenced user is
        # later deleted (e.g. GDPR erasure) — the audit trail row survives
        # with a NULL actor/target instead of blocking the delete.
        sa.Column("admin_user_id", sa.Integer(), nullable=True),
        sa.Column("target_user_id", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_reason", sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(
            ["admin_user_id"],
            ["users.id"],
            name="fk_impersonation_sessions_admin_user_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["users.id"],
            name="fk_impersonation_sessions_target_user_id_users",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "end_reason IN ('manual', 'timeout') OR end_reason IS NULL",
            name="ck_impersonation_sessions_end_reason",
        ),
        sa.CheckConstraint(
            "admin_user_id <> target_user_id",
            name="ck_impersonation_sessions_admin_target_distinct",
        ),
        sa.CheckConstraint(
            "(ended_at IS NULL) = (end_reason IS NULL)",
            name="ck_impersonation_sessions_end_pairing",
        ),
    )
    op.create_index(
        op.f("ix_impersonation_sessions_id"),
        "impersonation_sessions",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_impersonation_sessions_admin_user_id"),
        "impersonation_sessions",
        ["admin_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_impersonation_sessions_target_user_id"),
        "impersonation_sessions",
        ["target_user_id"],
        unique=False,
    )
    # TF-739: an admin can't nest a second impersonation while one is
    # already active — enforced here at the DB level (defense-in-depth
    # alongside whatever TF-741's auth layer checks) via a partial unique
    # index over "still-active" rows (ended_at IS NULL).
    op.create_index(
        "ix_impersonation_sessions_one_active_per_admin",
        "impersonation_sessions",
        ["admin_user_id"],
        unique=True,
        postgresql_where=sa.text("ended_at IS NULL"),
    )

    op.add_column(
        "audit_logs",
        sa.Column("impersonator_user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_audit_logs_impersonator_user_id_users",
        "audit_logs",
        "users",
        ["impersonator_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_audit_logs_impersonator_user_id"),
        "audit_logs",
        ["impersonator_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_impersonator_user_id"), table_name="audit_logs")
    op.drop_constraint(
        "fk_audit_logs_impersonator_user_id_users",
        "audit_logs",
        type_="foreignkey",
    )
    op.drop_column("audit_logs", "impersonator_user_id")

    op.drop_index(
        "ix_impersonation_sessions_one_active_per_admin",
        table_name="impersonation_sessions",
    )
    op.drop_index(
        op.f("ix_impersonation_sessions_target_user_id"),
        table_name="impersonation_sessions",
    )
    op.drop_index(
        op.f("ix_impersonation_sessions_admin_user_id"),
        table_name="impersonation_sessions",
    )
    op.drop_index(
        op.f("ix_impersonation_sessions_id"), table_name="impersonation_sessions"
    )
    op.drop_table("impersonation_sessions")
