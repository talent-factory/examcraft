"""TF-331: add display_name to documents for user-editable titles

Revision ID: tf331_display_name
Revises: 9d70cdf25a49
Create Date: 2026-04-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "tf331_display_name"
down_revision: Union[str, None] = "9d70cdf25a49"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("display_name", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """Drop the ``display_name`` column.

    DESTRUCTIVE: every user-set rename is lost permanently. With
    ``AUTO_MIGRATE=true`` in production this rollback runs unattended,
    so before downgrading export the data first::

        psql -c "COPY (SELECT id, display_name FROM documents \
                       WHERE display_name IS NOT NULL) \
                 TO STDOUT WITH CSV HEADER" > display_names_backup.csv
    """
    op.drop_column("documents", "display_name")
