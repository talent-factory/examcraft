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
# Rebased onto develop's head on merge (2026-09-02). Was previously
# "tf644_competency_visibility" — the same root as develop's tf740/tf745
# chain, which produced two Alembic heads and made every "upgrade head" abort.
# This file is the root of the two TF-625 migrations (tf625_track_progress ->
# tf625_hint_i18n_key), so rebasing it here is enough.
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
