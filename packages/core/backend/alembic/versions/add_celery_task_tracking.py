"""Add Celery task tracking fields to Document model

Revision ID: add_celery_task_tracking
Revises: b9585b1a8163
Create Date: 2025-11-03 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_celery_task_tracking"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to documents table
    op.add_column("documents", sa.Column("task_id", sa.String(100), nullable=True))
    op.add_column("documents", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("processing_info", sa.JSON(), nullable=True))

    # Create index on task_id for faster lookups
    op.create_index("ix_documents_task_id", "documents", ["task_id"])

    # Add new DocumentStatus enum values
    # Note: This is handled by the model definition, but we need to update the enum type
    # For PostgreSQL, we need to add the new values to the enum type
    op.execute("ALTER TYPE documentstatus ADD VALUE 'queued' BEFORE 'uploaded'")
    op.execute("ALTER TYPE documentstatus ADD VALUE 'completed' BEFORE 'processed'")
    op.execute("ALTER TYPE documentstatus ADD VALUE 'failed' BEFORE 'error'")


def downgrade() -> None:
    # Remove index
    op.drop_index("ix_documents_task_id", table_name="documents")

    # Remove columns
    op.drop_column("documents", "processing_info")
    op.drop_column("documents", "error_message")
    op.drop_column("documents", "task_id")

    # Note: Removing enum values is not supported in PostgreSQL
    # The old enum values will remain in the database
