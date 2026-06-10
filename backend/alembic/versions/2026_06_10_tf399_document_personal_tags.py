"""Add ``document_personal_tags`` table for per-user tag assignments (TF-399).

Personal (per-user) document↔tag assignments live in their own table so the
existing shared ``document_tags`` table — and its composite PK — stays
untouched. A ``user``-scope tag can be attached to any document the user can
see; the assignment is visible only to that user (``user_id`` is part of the
primary key). Shared (``institution``/``global``) assignments remain in
``document_tags``.

Steps:
1. Create ``document_personal_tags`` with composite PK
   (document_id, tag_id, user_id), CASCADE FK constraints and a ``created_at``
   timestamp.
2. ``ix_document_personal_tags_user_id`` — plain index on ``user_id`` (the
   read/filter path always scopes by the current user). IF NOT EXISTS so it is
   safe where ``create_all`` already built it (test/dev databases).

Additive and non-destructive: no backfill, no data migration — existing shared
assignments are unaffected. Plain ``CREATE INDEX`` (no ``CONCURRENTLY``) so it
runs inside the migration transaction. Safe for ``AUTO_MIGRATE=true`` deploys.

Revision ID: tf399_doc_personal_tags
Revises: tf398_exam_archive
Create Date: 2026-06-10
"""

from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "tf399_doc_personal_tags"
down_revision: Union[str, None] = "tf398_exam_archive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_personal_tags",
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("document_id", "tag_id", "user_id"),
    )
    # Read/filter path always scopes by user_id ("my personal tags on these
    # documents"). IF NOT EXISTS keeps it safe where create_all already built it.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_personal_tags_user_id "
        "ON document_personal_tags (user_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_personal_tags_user_id")
    op.drop_table("document_personal_tags")
