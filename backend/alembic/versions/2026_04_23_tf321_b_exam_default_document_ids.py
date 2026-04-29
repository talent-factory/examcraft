"""TF-321: add default_document_ids to exams

Revision ID: 2026_04_23_tf321_b
Revises: 2026_04_23_tf321_a
Create Date: 2026-04-24

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "2026_04_23_tf321_b"
down_revision: Union[str, None] = "2026_04_23_tf321_a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("exams", sa.Column("default_document_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("exams", "default_document_ids")
