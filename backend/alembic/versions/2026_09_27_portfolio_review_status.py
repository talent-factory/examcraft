"""Portfolio-Assessment: review_status-Spalten fuer Epic 5 (Aggregation,
Review-Override).

Additive Migration: ein Review-Status je Phasenergebnis
(proposed/approved/manual_override, mirrors GradeStatus) und ein
aggregierter Review-Status je Assessment (pending_review/
partially_reviewed/fully_reviewed, mirrors Submission.grade_status).
Backfill: bereits abgeschlossene Phasenergebnisse werden "proposed"
(ungeprueft im neuen Modell); overall_points_* (seit Epic 2 vorhanden,
vor Epic 4/5 nie befuellt) wird fuer Assessments mit bereits
abgeschlossenen Phasen nachgezogen. assessments.review_status braucht
keinen Daten-Backfill jenseits des server_default -- die Review-Aktion
existierte vor dieser Migration schlicht nicht.

Revision ID: portfolio_review_status
Revises: portfolio_phase_result
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "portfolio_review_status"
down_revision: Union[str, None] = "portfolio_phase_result"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    phase_result_columns = {
        c["name"] for c in inspector.get_columns("portfolio_phase_results")
    }
    assessment_columns = {
        c["name"] for c in inspector.get_columns("portfolio_assessments")
    }

    if "review_status" not in phase_result_columns:
        op.add_column(
            "portfolio_phase_results",
            sa.Column("review_status", sa.String(20), nullable=True),
        )
        op.execute(
            "UPDATE portfolio_phase_results SET review_status = 'proposed' "
            "WHERE status = 'completed'"
        )
        op.create_check_constraint(
            "check_portfolio_phase_result_review_status",
            "portfolio_phase_results",
            "review_status IS NULL OR review_status IN "
            "('proposed', 'approved', 'manual_override')",
        )
        op.create_check_constraint(
            "check_portfolio_phase_result_completed_has_review_status",
            "portfolio_phase_results",
            "status != 'completed' OR review_status IS NOT NULL",
        )

    if "review_status" not in assessment_columns:
        op.add_column(
            "portfolio_assessments",
            sa.Column(
                "review_status",
                sa.String(20),
                nullable=False,
                server_default="pending_review",
            ),
        )
        op.create_check_constraint(
            "check_portfolio_assessment_review_status",
            "portfolio_assessments",
            "review_status IN ('pending_review', 'partially_reviewed', "
            "'fully_reviewed')",
        )
        op.create_check_constraint(
            "check_portfolio_assessment_fully_reviewed_requires_completed",
            "portfolio_assessments",
            "review_status != 'fully_reviewed' OR status = 'completed'",
        )
        # overall_points_* existieren seit Epic 2, wurden aber nie
        # beschrieben -- fuer Assessments mit bereits abgeschlossenen
        # Phasen (Epic-4-Pilotlaeufe) nachziehen.
        op.execute(
            """
            UPDATE portfolio_assessments a
            SET
                overall_points_awarded = sub.awarded,
                overall_points_max = sub.max_pts,
                overall_percentage = CASE
                    WHEN sub.max_pts > 0 THEN (sub.awarded / sub.max_pts) * 100
                    ELSE 0
                END
            FROM (
                SELECT assessment_id,
                    SUM(total_points) AS awarded,
                    SUM(max_points) AS max_pts
                FROM portfolio_phase_results
                WHERE status = 'completed'
                GROUP BY assessment_id
            ) sub
            WHERE a.id = sub.assessment_id
            """
        )


def downgrade() -> None:
    op.drop_column("portfolio_assessments", "review_status")
    op.drop_column("portfolio_phase_results", "review_status")
