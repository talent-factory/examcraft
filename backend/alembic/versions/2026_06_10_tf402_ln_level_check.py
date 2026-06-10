"""tf402: CHECK-Constraint ln_level 1–4 auf question_reviews

Erzwingt den dokumentierten LN-Stufen-Bereich (1–4, distinkt von bloom_level
1–6) auf question_reviews.ln_level als Backstop hinter der App-seitigen
Klemmung (_coerce_ln_level). Additive, nicht-destruktiv: ln_level wurde in tf400
nullable hinzugefügt, Altbestand ist NULL und verletzt den CHECK nicht —
unbedenklich unter AUTO_MIGRATE=true. (TF-400)

Revision ID: tf402_ln_level_check
Revises: tf401_competency_prompt_vars
Create Date: 2026-06-10
"""

from typing import Union

from alembic import op

revision: str = "tf402_ln_level_check"
down_revision: Union[str, None] = "tf401_competency_prompt_vars"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "check_ln_level_range",
        "question_reviews",
        "ln_level IS NULL OR (ln_level >= 1 AND ln_level <= 4)",
    )


def downgrade() -> None:
    op.drop_constraint("check_ln_level_range", "question_reviews", type_="check")
