"""tf396: archive axis (archived_at/by/reason) on question_reviews

Orthogonal to review_status. archived_at IS NULL => active; set =>
archived (hidden from bank/lists, but retained in exams). Additive,
nullable columns + partial index — non-destructive, safe under
AUTO_MIGRATE=true. Existing rows stay NULL ("active"). (TF-396)

Revision ID: tf396_question_archive
Revises: tf383_question_gen_metadata
Create Date: 2026-06-08
"""

from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = "tf396_question_archive"
down_revision: Union[str, None] = "tf383_question_gen_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "question_reviews",
        sa.Column("archived_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "question_reviews",
        sa.Column("archived_by", sa.Integer(), nullable=True),
    )
    op.add_column(
        "question_reviews",
        sa.Column("archive_reason", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_question_reviews_archived_by_users",
        "question_reviews",
        "users",
        ["archived_by"],
        ["id"],
        ondelete="SET NULL",
    )
    # Partial index ONLY on archived rows (archived_at IS NOT NULL):
    # speeds up the archive/admin cleanup view (archived_only). The
    # default filter (archived_at IS NULL) does NOT benefit from this index —
    # Postgres only uses a partial index when the query predicate implies
    # the index predicate; IS NULL excludes all indexed rows. Deliberate:
    # the archived set is small and selective, the active (IS NULL) set is
    # large and unselective. Plain CREATE INDEX (no CONCURRENTLY — would
    # break in-transaction migration tests).
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_question_reviews_archived_at "
        "ON question_reviews (archived_at) WHERE archived_at IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_question_reviews_archived_at")
    op.drop_constraint(
        "fk_question_reviews_archived_by_users",
        "question_reviews",
        type_="foreignkey",
    )
    op.drop_column("question_reviews", "archive_reason")
    op.drop_column("question_reviews", "archived_by")
    op.drop_column("question_reviews", "archived_at")
