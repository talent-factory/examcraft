"""add track_progress to help_onboarding_progress (TF-625)

Progress of the optional deep-dive tracks. Kept separate from the linear
core-tour progress (current_step / completed_steps / skipped_steps) so a
deep dive cannot wrongly mark the core tour complete, and so the track id
stays stable when steps are renumbered.

Revision ID: tf625_track_progress
Revises: tf644_competency_visibility
Create Date: 2026-08-24 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "tf625_track_progress"
# Beim Merge von develop (02.09.2026) auf dessen Kopf umgehängt. Vorher
# "tf644_competency_visibility" — dieselbe Wurzel wie develops
# tf740/tf745-Kette, was zwei Alembic-Heads ergab und jedes "upgrade head"
# abbrechen liess. Diese Datei ist die Wurzel der beiden TF-625-Migrationen
# (tf625_track_progress -> tf625_hint_i18n_key); es genügt daher, hier
# umzuhängen.
down_revision: Union[str, None] = "tf745_fk_ondelete_cascade"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "help_onboarding_progress",
        sa.Column(
            "track_progress",
            sa.JSON(),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("help_onboarding_progress", "track_progress")
