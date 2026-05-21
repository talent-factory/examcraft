"""merge_tf345_wizard_into_v1.4_release

Revision ID: 3224d11cd8d8
Revises: db80a58dc700, tf345_wizard_sessions
Create Date: 2026-05-21 17:26:25.271102

"""

from typing import Sequence, Union

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


# revision identifiers, used by Alembic.
revision: str = "3224d11cd8d8"
down_revision: Union[str, None] = ("db80a58dc700", "tf345_wizard_sessions")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
