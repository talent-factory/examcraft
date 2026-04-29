"""TF-321: add question_source_documents join table and migrate JSON data

Revision ID: 2026_04_23_tf321_a
Revises: 05d0b35da403
Create Date: 2026-04-24

"""

from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa

revision: str = "2026_04_23_tf321_a"
down_revision: Union[str, None] = "05d0b35da403"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: create table (fails loudly if it already exists — schema drift protection)
    op.create_table(
        "question_source_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["question_id"], ["question_reviews.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id", "document_id"),
    )
    op.create_index(
        "ix_question_source_documents_question_id",
        "question_source_documents",
        ["question_id"],
    )

    # Step 2: migrate existing JSON data (best-effort, skip unresolvable names)
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, institution_id, source_documents FROM question_reviews "
            "WHERE source_documents IS NOT NULL"
        )
    ).fetchall()

    for q_id, institution_id, source_docs in rows:
        if not source_docs:
            continue
        if isinstance(source_docs, str):
            try:
                source_docs = json.loads(source_docs)
            except (ValueError, TypeError):
                continue
        if not isinstance(source_docs, list):
            continue

        for fname in source_docs:
            if not fname or not isinstance(fname, str):
                continue
            doc_row = conn.execute(
                sa.text(
                    "SELECT id FROM documents "
                    "WHERE original_filename = :fname "
                    "AND institution_id IS NOT DISTINCT FROM :inst_id "
                    "LIMIT 1"
                ),
                {"fname": fname, "inst_id": institution_id},
            ).fetchone()
            if doc_row:
                conn.execute(
                    sa.text(
                        "INSERT INTO question_source_documents (question_id, document_id) "
                        "VALUES (:q_id, :d_id) ON CONFLICT DO NOTHING"
                    ),
                    {"q_id": q_id, "d_id": doc_row.id},
                )


def downgrade() -> None:
    op.drop_index(
        "ix_question_source_documents_question_id",
        table_name="question_source_documents",
    )
    op.drop_table("question_source_documents")
