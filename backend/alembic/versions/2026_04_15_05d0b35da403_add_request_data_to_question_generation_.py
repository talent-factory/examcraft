"""add request_data to question_generation_jobs

Revision ID: 05d0b35da403
Revises: 2026_04_14_feedback
Create Date: 2026-04-15 17:52:28.979941

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '05d0b35da403'
down_revision: Union[str, None] = '2026_04_14_feedback'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('question_generation_jobs', sa.Column('request_data', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('question_generation_jobs', 'request_data')
