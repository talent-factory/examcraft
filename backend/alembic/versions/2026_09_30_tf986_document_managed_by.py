"""documents.managed_by: hide feature-owned documents from generic surfaces (TF-986)

Portfolio ingestion stored every submitted file as a regular private
document of the teacher, so the files showed up in the document list, the
RAG/chat document selection and the MCP document tools. documents.managed_by
names the feature module that owns a row; utils.document_visibility hides
every row where it is set.

Backfill: documents already linked to a portfolio submission
(portfolio_documents.document_id) get managed_by = 'portfolio_assessment'.
Downgrade drops the column; the rows become regular documents again.

Revision ID: tf986_document_managed_by
Revises: tf964_generation_job_link
Create Date: 2026-09-30 16:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "tf986_document_managed_by"
down_revision: Union[str, None] = "tf964_generation_job_link"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("managed_by", sa.String(length=50), nullable=True),
    )
    op.execute(
        "UPDATE documents SET managed_by = 'portfolio_assessment' "
        "WHERE id IN (SELECT document_id FROM portfolio_documents)"
    )


def downgrade() -> None:
    op.drop_column("documents", "managed_by")
