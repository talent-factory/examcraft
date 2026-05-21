"""merge_tf337_and_tf320_heads

Revision ID: db80a58dc700
Revises: tf337_audit_logs_idx, tf320e5a6b7c8
Create Date: 2026-05-06 12:17:19.294567

"""

from typing import Sequence, Union

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


# revision identifiers, used by Alembic.
revision: str = "db80a58dc700"
down_revision: Union[str, None] = ("tf337_audit_logs_idx", "tf320e5a6b7c8")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
