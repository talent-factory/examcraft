"""increase_avatar_url_length

Revision ID: b9585b1a8163
Revises: 7786194d9cd6
Create Date: 2025-10-20 07:18:14.166305

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9585b1a8163'
down_revision: Union[str, None] = '7786194d9cd6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Increase avatar_url column length from VARCHAR(500) to VARCHAR(1000)
    # This is needed for OAuth providers like Google that can have very long avatar URLs
    op.alter_column('users', 'avatar_url',
                    existing_type=sa.String(500),
                    type_=sa.String(1000),
                    existing_nullable=True)


def downgrade() -> None:
    # Revert avatar_url column length back to VARCHAR(500)
    op.alter_column('users', 'avatar_url',
                    existing_type=sa.String(1000),
                    type_=sa.String(500),
                    existing_nullable=True)

