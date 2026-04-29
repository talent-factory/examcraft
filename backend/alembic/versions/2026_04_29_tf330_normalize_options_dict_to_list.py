"""TF-330: normalize legacy dict-shaped question_reviews.options to JSON arrays

Revision ID: tf330_options_norm
Revises: ab73e5f9c201
Create Date: 2026-04-29 00:00:00.000000

Older generation paths persisted ``question_reviews.options`` as a JSON object
keyed by 'A'/'B'/'C'/'D'. The Pydantic ``ReviewQueueResponse`` schema accepts
only ``List[str]``, so legacy rows surface as 500s on
``GET /question-review/queue``. This migration rewrites every legacy row to the
canonical JSON-array shape.

Precondition: the legacy shape is known to use letter keys ('A'..'D'). The
UPDATE filters on ``?| array['A','B','C','D']`` so a hypothetical numeric-key
shape ('1','10','2',...) is left untouched — lex-sort of those keys would
silently reorder answers, and there is no way to reverse the rewrite.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "tf330_options_norm"
down_revision: Union[str, None] = "ab73e5f9c201"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Cast through ::jsonb so the same SQL works whether the underlying column
    # type is JSON or JSONB.
    op.execute(
        """
        UPDATE question_reviews
        SET options = (
            SELECT jsonb_agg(value ORDER BY key)
            FROM jsonb_each_text(options::jsonb)
        )
        WHERE options IS NOT NULL
          AND jsonb_typeof(options::jsonb) = 'object'
          AND options::jsonb ?| array['A', 'B', 'C', 'D'];
        """
    )


def downgrade() -> None:
    # Raise instead of silently no-op'ing: the original 'A'/'B'/'C'/'D' keys
    # were positional and cannot be reconstructed from the array. A silent
    # ``pass`` would let ``alembic downgrade -1`` report success while leaving
    # the data forward-migrated, misleading any operator rolling back a
    # release.
    raise NotImplementedError(
        "TF-330 is a one-way data fix; the original A/B/C/D keys cannot be "
        "reconstructed from the canonicalized array. Restore from backup if "
        "rollback is required."
    )
