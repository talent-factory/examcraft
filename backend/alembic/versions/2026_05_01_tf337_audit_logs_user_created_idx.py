"""Composite index ``(user_id, created_at DESC)`` on ``audit_logs``.

Backs the ``GET /api/v1/activity`` endpoint which paginates per-user
events with ``ORDER BY created_at DESC LIMIT/OFFSET``. Without this
index the per-user dashboard widget plus the new pagination page both
fall back to the existing single-column index on ``user_id`` and sort
the matching rows in memory — fine at ~hundreds of rows, slow once a
single user has thousands.

Column order: leading ``user_id`` because every query filters on it;
trailing ``created_at DESC`` matches the ORDER BY so PostgreSQL can
walk the index in order and skip a sort. Reversing the columns
(``created_at, user_id``) would force a full index scan for every
per-user query.

Additive, idempotent (``IF NOT EXISTS``), no data rewrite. Safe for
``AUTO_MIGRATE=true`` deploys.
"""

from typing import Union

from alembic import op


revision: str = "tf337_audit_logs_idx"
down_revision: Union[str, None] = "tf336_llm_model"
branch_labels = None
depends_on = None


INDEX_NAME = "ix_audit_logs_user_id_created_at_desc"


def upgrade() -> None:
    # Plain (non-CONCURRENTLY) CREATE INDEX runs inside the migration
    # transaction. ``audit_logs`` is small in prod today; if a future
    # cleanup grows the table by orders of magnitude this can be
    # re-issued CONCURRENTLY in a hand-rolled SQL step.
    op.execute(
        f"CREATE INDEX IF NOT EXISTS {INDEX_NAME} "
        "ON audit_logs (user_id, created_at DESC)"
    )


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
