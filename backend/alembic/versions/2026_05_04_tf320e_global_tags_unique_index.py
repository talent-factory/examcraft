"""tf320e: Unique Index für globale Tags (lower(name) WHERE scope='global')

Revision ID: tf320e5a6b7c8
Revises: tf320d4f5a6b7
Create Date: 2026-05-04
"""

from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = "tf320e5a6b7c8"
down_revision: Union[str, None] = "tf320d4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uix_global_tag_name_lower",
        "tags",
        [sa.text("lower(name)")],
        unique=True,
        postgresql_where=sa.text("scope = 'global'"),
    )


def downgrade() -> None:
    op.drop_index("uix_global_tag_name_lower", table_name="tags")
