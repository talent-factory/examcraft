"""Add pending_reindex flag to documents for institution transfer.

Used by the SuperAdmin institution-transfer flow (TF-352): when a user is
moved to a new institution along with their documents, each affected
document is marked pending_reindex=True so a Celery task can re-upload its
Qdrant vector payload with the new institution_id.

Partial index keeps the sweep cheap — only rows with pending_reindex=true
are indexed, so the periodic re-index lookup stays O(pending) instead of
O(documents).

Revision ID: tf352_documents_pending_reindex
Revises: 3224d11cd8d8
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "tf352_documents_pending_reindex"
down_revision: Union[str, None] = "3224d11cd8d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "pending_reindex",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_index(
        "ix_documents_pending_reindex",
        "documents",
        ["pending_reindex"],
        postgresql_where=sa.text("pending_reindex = true"),
    )


def downgrade() -> None:
    op.drop_index("ix_documents_pending_reindex", table_name="documents")
    op.drop_column("documents", "pending_reindex")
