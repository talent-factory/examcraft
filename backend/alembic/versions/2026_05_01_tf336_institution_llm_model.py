"""TF-336: ``institutions.llm_model_for_grading`` (NULLABLE).

Enterprise-tier institutions können das LLM-Modell für die Bewertung
offener Fragen pro Institution wählen (Sonnet/Opus). NULL bedeutet "der
Default des Plattform-Setups" — also kein Override. Die Spalte ist
additiv, kein Downtime-Risiko, ``AUTO_MIGRATE=true`` zieht sie beim
Deploy automatisch.
"""

from typing import Union

import sqlalchemy as sa
from alembic import op


revision: str = "tf336_llm_model"
down_revision: Union[str, None] = "tf335_fk_restrict"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "institutions",
        sa.Column("llm_model_for_grading", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("institutions", "llm_model_for_grading")
