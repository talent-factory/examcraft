"""Institution.llm_model_for_grading auf logische Namen migrieren.

upgrade:  Jede NON-NULL Rohmodell-ID → 'examcraft/grading'.
downgrade: 'examcraft/grading'-Zeilen werden auf NULL gesetzt
           (kein verlustfreier Rückweg, da der Rohname nicht gespeichert ist).

Revision ID: tf439_grade_logical
Revises:     moodle_feedback_push_job
Create Date: 2026-06-19
"""

from alembic import op
import sqlalchemy as sa

# ---------------------------------------------------------------------------
# Alembic-Metadaten
# ---------------------------------------------------------------------------
revision = "tf439_grade_logical"
down_revision = "moodle_feedback_push_job"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Setzt alle gesetzten llm_model_for_grading-Werte auf den logischen Namen."""
    op.execute(
        sa.text(
            "UPDATE institutions"
            "  SET llm_model_for_grading = 'examcraft/grading'"
            "  WHERE llm_model_for_grading IS NOT NULL"
        )
    )


def downgrade() -> None:
    """Setzt 'examcraft/grading'-Zeilen auf NULL (Roh-ID nicht mehr bekannt)."""
    op.execute(
        sa.text(
            "UPDATE institutions"
            "  SET llm_model_for_grading = NULL"
            "  WHERE llm_model_for_grading = 'examcraft/grading'"
        )
    )
