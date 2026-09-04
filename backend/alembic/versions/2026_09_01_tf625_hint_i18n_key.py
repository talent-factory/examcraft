"""replace help_context_hints text columns with an i18n_key (TF-625)

The hint_text_de/hint_text_en columns made the context hint the only help
surface whose language the SERVER decided. Everything else in the product is
translated in the browser from translation.json, so switching the language
switched everything except the hint — it kept whatever language it had been
fetched in until a full reload.

e43b3ed did the same move for the onboarding tour (title_de/title_en in
help-onboarding-steps.json -> an explicit i18n_key plus help.tour.* in
translation.json). This finishes it for the hints, going straight to
i18n_key without an intermediate fr/it-columns step: that widened a
SQL-decided-language surface that should not have existed in the first
place, and (being new on this branch and never deployed) squashing it into
this migration avoids a no-op add-then-drop in every environment's history.

The table itself stays: help_dismissed_hints.hint_id references it, so the ids
must remain stable. Only the text leaves.

Nothing is lost by dropping the columns. There is no admin UI or API for these
rows — seed_help_hints owns them, runs on every startup (main.py), and its
upsert rewrites the text fields, so an edit made directly in SQL never survived
a restart anyway.

Revision ID: tf625_hint_i18n_key
Revises: tf625_track_progress
Create Date: 2026-09-01 10:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "tf625_hint_i18n_key"
down_revision: Union[str, None] = "tf625_track_progress"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Added nullable, then backfilled, then made NOT NULL: existing rows have
    # no key yet, and the seed only runs after migrations.
    op.add_column(
        "help_context_hints", sa.Column("i18n_key", sa.String(255), nullable=True)
    )

    # Derive the key from route_pattern. Covers both the current
    # seed_help_hints.DEFAULT_HINTS patterns and the two renamed-away patterns
    # a production row can still carry at migration time ("/documents/upload",
    # "/exam/create" — see seed_help_hints.OBSOLETE_ROUTE_PATTERNS): the seed
    # only runs once the app finishes starting, so a row created under the old
    # pattern is not backfilled by it until after this migration has already
    # run. "/admin/users" is also obsolete and has no current counterpart, so
    # it — like any row this CASE does not recognize — falls through to the
    # COALESCE default. That default is not a real translation key; it is
    # covered by `t(hint.i18n_key, 'Tipp verfügbar')` on the frontend, and the
    # row itself is deleted by seed_help_hints on the very next startup.
    op.execute(
        """
        UPDATE help_context_hints
        SET i18n_key = COALESCE(
            CASE route_pattern
                WHEN '/documents'          THEN 'help.hints.documents'
                WHEN '/documents/upload'   THEN 'help.hints.documents'
                WHEN '/questions/generate' THEN 'help.hints.questionsGenerate'
                WHEN '/exam/create'        THEN 'help.hints.questionsGenerate'
                WHEN '/questions/review'   THEN 'help.hints.questionsReview'
                WHEN '/exams/compose'      THEN 'help.hints.examsCompose'
                WHEN '/prompts'            THEN 'help.hints.prompts'
            END,
            'help.hints.unknown'
        )
        """
    )

    op.alter_column("help_context_hints", "i18n_key", nullable=False)

    op.drop_column("help_context_hints", "hint_text_en")
    op.drop_column("help_context_hints", "hint_text_de")


def downgrade() -> None:
    # de/en were NOT NULL before. Re-added nullable and left empty: the texts
    # live in translation.json now, and the next seed run would overwrite
    # whatever we invented here. A downgrade is expected to be followed by a
    # startup, which re-seeds.
    op.add_column(
        "help_context_hints", sa.Column("hint_text_de", sa.Text(), nullable=True)
    )
    op.add_column(
        "help_context_hints", sa.Column("hint_text_en", sa.Text(), nullable=True)
    )
    op.drop_column("help_context_hints", "i18n_key")
