"""TF-403: rename question_type 'multiple_choice' (single-answer) -> 'single_choice'.

The freed name 'multiple_choice' is reused for the new multi-answer type in
application code (later phase); this migration converts all EXISTING single-answer
rows so the string flip is unambiguous. Authoritative store is question_reviews;
prompts.use_case/tags carry the type->template mapping.

Design / constraints (per project conventions):
- Single in-transaction revision, plain UPDATEs (no CONCURRENTLY).
- Revision id <= 32 chars (alembic_version is VARCHAR(32)).
- The ``prompts`` UPDATEs are GUARDED on the ``prompts`` table existing, because
  ``prompts`` is a premium model created via ``create_all`` only when premium is
  mounted. In core-only deployments ``prompts`` is absent, so those statements are
  a no-op there (mirrors the guard in tf397_prompt_template_tags).
- Not destructive on upgrade.
- DOWNGRADE IS ONE-WAY-LOSSY ONCE THE NEW TYPE IS IN USE. The reverse UPDATEs
  fold every 'single_choice' row back into 'multiple_choice'. That is safe ONLY
  immediately after this revision, before any genuine multi-answer
  'multiple_choice' rows are authored (those arrive in the later application
  phase). Run downgrade afterwards and the renamed single-answer rows become
  indistinguishable from real multi-answer rows: their JSON-array correct_answer
  then hits the single-answer grading path and is mis-graded. Treat downgrade as
  a rollback hatch for an immediate-after-deploy revert only; do NOT run it once
  multi-answer questions exist.

Revision ID: tf403_qtype_rename
Revises: tf346_prompt_institution
Create Date: 2026-06-12
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "tf403_qtype_rename"
# Re-parented onto tf346 (merged from develop) to keep a single linear head —
# both originally chained off tf399_doc_personal_tags, which created a
# multi-head after the develop merge and broke `alembic upgrade head`.
down_revision: Union[str, None] = "tf346_prompt_institution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # question_reviews is a core table -> always present.
    op.execute(
        "UPDATE question_reviews SET question_type = 'single_choice' "
        "WHERE question_type = 'multiple_choice'"
    )

    # prompts is premium-only (created via create_all when premium is mounted).
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "prompts" in set(inspector.get_table_names()):
        op.execute(
            "UPDATE prompts SET use_case = 'question_generation_single_choice' "
            "WHERE use_case = 'question_generation_multiple_choice'"
        )
        op.execute(
            "UPDATE prompts SET tags = array_replace(tags, 'multiple_choice', 'single_choice') "
            "WHERE 'multiple_choice' = ANY(tags)"
        )


def downgrade() -> None:
    op.execute(
        "UPDATE question_reviews SET question_type = 'multiple_choice' "
        "WHERE question_type = 'single_choice'"
    )

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "prompts" in set(inspector.get_table_names()):
        op.execute(
            "UPDATE prompts SET use_case = 'question_generation_multiple_choice' "
            "WHERE use_case = 'question_generation_single_choice'"
        )
        op.execute(
            "UPDATE prompts SET tags = array_replace(tags, 'single_choice', 'multiple_choice') "
            "WHERE 'single_choice' = ANY(tags)"
        )
