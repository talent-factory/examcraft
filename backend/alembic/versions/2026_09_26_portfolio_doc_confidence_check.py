"""Portfolio-Assessment: CHECK constraints for classification confidence/source
on portfolio_documents (TF-941 review fix).

Additive migration: enforces at the DB level that
- classification_confidence, if set, is a valid probability (0..1)
- classification_source='auto' always implies phase_id IS NOT NULL

Both invariants were previously only enforced by application code
(portfolio_classification_service.map_batch_result_to_updates).

Revision ID: portfolio_doc_confidence_chk
Revises: portfolio_doc_extracted_text
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "portfolio_doc_confidence_chk"
down_revision: Union[str, None] = "portfolio_doc_extracted_text"
branch_labels = None
depends_on = None

_CONFIDENCE_CONSTRAINT = "check_portfolio_document_classification_confidence_range"
_AUTO_REQUIRES_PHASE_CONSTRAINT = "ck_portfolio_document_auto_requires_phase"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {
        c["name"] for c in inspector.get_check_constraints("portfolio_documents")
    }

    if _CONFIDENCE_CONSTRAINT not in existing:
        op.create_check_constraint(
            _CONFIDENCE_CONSTRAINT,
            "portfolio_documents",
            "classification_confidence IS NULL OR "
            "(classification_confidence >= 0 AND classification_confidence <= 1)",
        )
    if _AUTO_REQUIRES_PHASE_CONSTRAINT not in existing:
        op.create_check_constraint(
            _AUTO_REQUIRES_PHASE_CONSTRAINT,
            "portfolio_documents",
            "classification_source != 'auto' OR phase_id IS NOT NULL",
        )


def downgrade() -> None:
    op.drop_constraint(
        _AUTO_REQUIRES_PHASE_CONSTRAINT, "portfolio_documents", type_="check"
    )
    op.drop_constraint(_CONFIDENCE_CONSTRAINT, "portfolio_documents", type_="check")
