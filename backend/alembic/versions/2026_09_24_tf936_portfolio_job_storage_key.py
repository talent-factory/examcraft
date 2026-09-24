"""Portfolio-Assessment: storage_key auf portfolio_assessment_jobs (TF-936).

Additive Migration: nullable Spalte fuer den ZIP-Storage-Key eines
Ingestion-Jobs, damit der geplante Watchdog-Task (``reap_stuck_portfolio_
ingestion_jobs``) ein verwaistes Archiv identifizieren und loeschen kann.
NULL fuer classify/grade-Jobs (kein Archiv) und fuer ingest-Jobs, die vor
dieser Migration erstellt wurden.

Revision ID: portfolio_job_storage_key
Revises: portfolio_assessment_ingestion
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "portfolio_job_storage_key"
down_revision: Union[str, None] = "portfolio_assessment_ingestion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("portfolio_assessment_jobs")}

    if "storage_key" not in columns:
        op.add_column(
            "portfolio_assessment_jobs",
            sa.Column("storage_key", sa.String(500), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("portfolio_assessment_jobs", "storage_key")
