"""add users.zitadel_sub (EXAMCRAFT-121)

Preparation release for the single login via tessera/Zitadel (ADR 0008).
The column is additive and unused until the cutover: the bulk import writes
the Zitadel subject into it, and after the cutover users are resolved by
``sub`` only.

Existing rows stay NULL. A unique index guards the mapping; PostgreSQL
allows any number of NULLs in a unique index.

Revision ID: ec121_users_zitadel_sub
Revises: tf1060_previous_login_at
Create Date: 2026-11-13 14:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "ec121_users_zitadel_sub"
down_revision: Union[str, None] = "tf1060_previous_login_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("zitadel_sub", sa.String(255), nullable=True))
    op.create_index("ix_users_zitadel_sub", "users", ["zitadel_sub"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_zitadel_sub", table_name="users")
    op.drop_column("users", "zitadel_sub")
