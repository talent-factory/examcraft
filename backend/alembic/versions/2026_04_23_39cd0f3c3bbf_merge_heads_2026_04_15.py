"""merge heads 2026-04-15

Revision ID: 39cd0f3c3bbf
Revises: 43cbb6db6e06, 05d0b35da403
Create Date: 2026-04-23 06:47:08.367880

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "39cd0f3c3bbf"
down_revision: Union[str, None] = ("43cbb6db6e06", "05d0b35da403")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
