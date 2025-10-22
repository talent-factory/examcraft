"""Fix documents.user_id column type from VARCHAR to INTEGER

Revision ID: 009
Revises: 008_add_institution_id_to_documents
Create Date: 2025-10-21 10:05:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First, set non-numeric user_id values to NULL
    op.execute("""
        UPDATE documents
        SET user_id = NULL
        WHERE user_id IS NOT NULL AND user_id !~ '^[0-9]+$'
    """)

    # Alter the column type from VARCHAR to INTEGER
    # PostgreSQL will handle the conversion automatically
    op.execute("""
        ALTER TABLE documents
        ALTER COLUMN user_id TYPE INTEGER USING user_id::integer
    """)

    # Add the foreign key constraint
    op.create_foreign_key(
        "documents_user_id_fkey",
        "documents",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Drop the foreign key constraint
    op.drop_constraint("documents_user_id_fkey", "documents", type_="foreignkey")

    # Alter the column type back to VARCHAR
    op.execute("""
        ALTER TABLE documents
        ALTER COLUMN user_id TYPE VARCHAR(100)
    """)
