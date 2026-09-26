"""Portfolio-Assessment: phase_id FK on portfolio_documents SET NULL -> RESTRICT
(TF-941 review fix).

There is currently no phase/template deletion endpoint, but SET NULL would
silently violate the ck_portfolio_document_auto_requires_phase CHECK
constraint (added in portfolio_doc_confidence_chk) the moment such a
feature deletes a phase that has an auto-classified document pointing at
it: the cascade would null phase_id while leaving
classification_source='auto' untouched. RESTRICT instead blocks that
deletion outright, consistent with PortfolioAssessment.template_id's
RESTRICT for the same class of "don't silently orphan
classification/grading data" reasoning.

Revision ID: portfolio_doc_phase_fk_restrict
Revises: portfolio_doc_confidence_chk
"""

from typing import Union

from alembic import op

revision: str = "portfolio_doc_phase_fk_restrict"
down_revision: Union[str, None] = "portfolio_doc_confidence_chk"
branch_labels = None
depends_on = None

_CONSTRAINT = "portfolio_documents_phase_id_fkey"


def upgrade() -> None:
    op.drop_constraint(_CONSTRAINT, "portfolio_documents", type_="foreignkey")
    op.create_foreign_key(
        _CONSTRAINT,
        "portfolio_documents",
        "portfolio_template_phases",
        ["phase_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(_CONSTRAINT, "portfolio_documents", type_="foreignkey")
    op.create_foreign_key(
        _CONSTRAINT,
        "portfolio_documents",
        "portfolio_template_phases",
        ["phase_id"],
        ["id"],
        ondelete="SET NULL",
    )
