"""Portfolio-Assessment: extracted_text on portfolio_documents (TF-941).

Additive migration: nullable Text column for the full file text already
extracted during ingestion -- Epic 3 (classification) reads it, and Epic 4
(grading engine, not yet implemented) will read it once built, instead of
re-extracting it via Docling/OCR. NULL for rows created before this
migration.

Revision ID: portfolio_doc_extracted_text
Revises: portfolio_job_storage_key
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "portfolio_doc_extracted_text"
down_revision: Union[str, None] = "portfolio_job_storage_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("portfolio_documents")}

    if "extracted_text" not in columns:
        op.add_column(
            "portfolio_documents",
            sa.Column("extracted_text", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("portfolio_documents", "extracted_text")
