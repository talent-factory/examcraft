"""tf383: generation_metadata (Prompt-/Template-Herkunft) auf question_reviews

Additive, nullable JSON-Spalte — speichert einen Snapshot der Vorlage/des
Prompts, mit dem eine Frage generiert wurde (TF-383). Nicht-destruktiv,
unbedenklich unter AUTO_MIGRATE=true. Altbestand bleibt NULL ("nicht erfasst").

Revision ID: tf383_question_gen_metadata
Revises: tf372_tags_scope_uniqueness
Create Date: 2026-06-01
"""

from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = "tf383_question_gen_metadata"
down_revision: Union[str, None] = "tf372_tags_scope_uniqueness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "question_reviews",
        sa.Column("generation_metadata", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("question_reviews", "generation_metadata")
