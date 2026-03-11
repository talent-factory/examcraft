"""initial_database_schema

Revision ID: 4d90a37a3aac
Revises:
Create Date: 2026-01-27 12:29:26.669229

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "4d90a37a3aac"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Initial database schema baseline.

    This migration serves as a baseline marker for the existing database schema.
    All tables already exist in the database, so no changes are applied.

    This includes:
    - Core tables: users, institutions, roles, documents, subscriptions, etc.
    - Premium tables: prompts, chat_sessions, chat_messages, etc. (managed separately)
    """
    # No operations - all tables already exist
    pass


def downgrade() -> None:
    """
    Downgrade not supported for initial baseline migration.
    """
    # No downgrade operations - this is the initial baseline
    pass
