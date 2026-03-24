"""fix_exam_created_by_nullable

Revision ID: e1f2a3b4c5d6
Revises: c233b732f127
Create Date: 2026-03-20 16:00:00.000000

Make exams.created_by nullable=True to match the ondelete="SET NULL" FK
behaviour — otherwise PostgreSQL raises a constraint violation when the
referenced user is deleted.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"  # pragma: allowlist secret
down_revision: Union[str, None] = "c233b732f127"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "exams",
        "created_by",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "exams",
        "created_by",
        existing_type=sa.Integer(),
        nullable=False,
    )
