"""tf320: case-insensitive unique index on tags(lower(name), institution_id)

Ersetzt den case-sensitiven UniqueConstraint durch einen funktionalen Unique-Index
auf lower(name), sodass 'Python' und 'python' als identisch erkannt werden.

Revision ID: tf320b2c3d4e5
Revises: tf320a1b2c3d4
Create Date: 2026-04-29
"""

from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = "tf320b2c3d4e5"
down_revision: Union[str, None] = "tf320a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_tag_name_institution", "tags", type_="unique")
    op.create_index(
        "uix_tag_name_lower_institution",
        "tags",
        [sa.text("lower(name)"), "institution_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uix_tag_name_lower_institution", table_name="tags")
    op.create_unique_constraint(
        "uq_tag_name_institution", "tags", ["name", "institution_id"]
    )
