"""tf398: archive axis (archived_at/by/reason) on exams

Orthogonal to status (draft/finalized/exported). archived_at IS NULL =>
active; set => archived (hidden from the active composer overview,
status stays untouched). Additive, nullable columns + partial index —
non-destructive, safe under AUTO_MIGRATE=true. Existing rows stay NULL
("active"). Mirrors the TF-396 pattern (question_reviews). (TF-398)

Revision ID: tf398_exam_archive
Revises: tf397_prompt_template_tags
Create Date: 2026-06-10
"""

from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = "tf398_exam_archive"
# Rebased from tf396 onto tf397 (develop head) to avoid a multi-head
# after merging develop — tf400/401/402/397 also chain off tf396, so
# tf398 is queued behind the develop head.
down_revision: Union[str, None] = "tf397_prompt_template_tags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "exams",
        sa.Column("archived_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "exams",
        sa.Column("archived_by", sa.Integer(), nullable=True),
    )
    op.add_column(
        "exams",
        sa.Column("archive_reason", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_exams_archived_by_users",
        "exams",
        "users",
        ["archived_by"],
        ["id"],
        ondelete="SET NULL",
    )
    # Partial index ONLY on archived rows (archived_at IS NOT NULL):
    # speeds up the archive overview (archived_only). The default filter
    # (archived_at IS NULL) does NOT benefit from this index — Postgres only
    # uses a partial index when the query predicate implies the index
    # predicate; IS NULL excludes all indexed rows. Deliberate: the archived
    # set is small and selective, the active (IS NULL) set is large and
    # unselective. Plain CREATE INDEX (no CONCURRENTLY — would break
    # in-transaction migration tests).
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_exams_archived_at "
        "ON exams (archived_at) WHERE archived_at IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_exams_archived_at")
    op.drop_constraint(
        "fk_exams_archived_by_users",
        "exams",
        type_="foreignkey",
    )
    op.drop_column("exams", "archive_reason")
    op.drop_column("exams", "archived_by")
    op.drop_column("exams", "archived_at")
