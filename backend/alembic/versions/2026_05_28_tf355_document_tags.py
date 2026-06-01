"""Add ``document_tags`` join table + ``ux_tags_user_name`` partial index (TF-355).

Creates the many-to-many join table between documents and tags, plus the
partial unique index that enforces case-insensitive tag name uniqueness per
user (mirrors the Tag model's ``__table_args__``).

Steps:
1. Create ``document_tags`` table with composite PK (document_id, tag_id),
   CASCADE FK constraints and ``created_at`` timestamp.
2. Index ``ix_document_tags_tag_id`` for efficient reverse lookups by tag.
3. ``ux_tags_user_name`` partial unique index on
   ``tags (created_by, LOWER(name)) WHERE scope = 'user'`` — matches the
   SQLAlchemy model declaration. IF NOT EXISTS so it is safe when
   ``create_all`` already built it (test/dev databases).

Additive and idempotent (indexes guarded by ``IF NOT EXISTS``).
Safe for ``AUTO_MIGRATE=true`` deploys — no manual step required.

Revision ID: tf355_document_tags
Revises: tf354_documents_visibility
"""

from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "tf355_document_tags"
down_revision: Union[str, None] = "tf354_documents_visibility"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_tags",
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("document_id", "tag_id"),
    )
    op.create_index(
        "ix_document_tags_tag_id", "document_tags", ["tag_id"], unique=False
    )
    # Mirrors the Tag model's __table_args__ index. IF NOT EXISTS so it is safe even
    # where create_all already built it (test/dev databases).
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_tags_user_name "
        "ON tags (created_by, LOWER(name)) WHERE scope = 'user'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_tags_user_name")
    op.drop_index("ix_document_tags_tag_id", table_name="document_tags")
    op.drop_table("document_tags")
