"""merge two heads before adding job metadata columns

Revision ID: 524100100e68
Revises: b2c3d4e5f6a7, d74c69d53df6
Create Date: 2026-03-19 20:51:17.389680

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "524100100e68"
down_revision: Union[str, None] = ("b2c3d4e5f6a7", "d74c69d53df6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
