"""merge_tf321_and_tf330_heads

Revision ID: 9d70cdf25a49
Revises: 2026_04_23_tf321_b, tf330_options_norm
Create Date: 2026-04-29 10:23:24.118506

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "9d70cdf25a49"
down_revision: Union[str, None] = ("2026_04_23_tf321_b", "tf330_options_norm")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
