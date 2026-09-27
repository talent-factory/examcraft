"""Portfolio assessment: new table portfolio_phase_results (Epic 4).

Additive migration: grading result per phase (criteria scores, rationale,
checklist, per-phase transparency warnings). One row per (assessment_id,
phase_id) -- a retry after a failure updates the existing row.

Revision ID: portfolio_phase_result
Revises: portfolio_doc_phase_fk_restrict
"""

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "portfolio_phase_result"
down_revision: Union[str, None] = "portfolio_doc_phase_fk_restrict"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "portfolio_phase_results" in inspector.get_table_names():
        return

    op.create_table(
        "portfolio_phase_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "assessment_id",
            UUID(as_uuid=True),
            sa.ForeignKey("portfolio_assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "phase_id",
            UUID(as_uuid=True),
            sa.ForeignKey("portfolio_template_phases.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("criterion_results", JSONB(), nullable=True),
        sa.Column("total_points", sa.Float(), nullable=True),
        sa.Column("max_points", sa.Float(), nullable=True),
        sa.Column("warnings", JSONB(), nullable=True),
        sa.Column(
            "reviewer_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="check_portfolio_phase_result_status",
        ),
        sa.CheckConstraint(
            "status != 'completed' OR ("
            "criterion_results IS NOT NULL AND total_points IS NOT NULL "
            "AND max_points IS NOT NULL)",
            name="check_portfolio_phase_result_completed_has_score",
        ),
        sa.UniqueConstraint(
            "assessment_id",
            "phase_id",
            name="uq_portfolio_phase_result_assessment_phase",
        ),
    )
    op.create_index(
        "ix_portfolio_phase_results_assessment_id",
        "portfolio_phase_results",
        ["assessment_id"],
    )


def downgrade() -> None:
    op.drop_table("portfolio_phase_results")
