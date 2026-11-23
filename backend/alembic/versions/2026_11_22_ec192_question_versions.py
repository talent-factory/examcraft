"""question_versions: Schema und Backfill der Fragen-Versionen (EXAMCRAFT-192)

Legt ``question_versions`` an, schreibt für jede bestehende Frage Version 1
(Inhalt und Review-Status der Zeile in ``question_reviews``; ``edited`` wird zu
``pending``) und hängt jede Prüfungsposition an die Version 1 ihrer Frage
(``exam_questions.question_version_id``).

Additiv: die Inhalts- und Statusspalten von ``question_reviews`` bleiben
unverändert, die laufende Anwendung liest sie weiter. Die Umstellung der
Lese-/Schreibpfade folgt in EXAMCRAFT-175/189.

Revision ID: ec192_question_versions
Revises: ec168_user_avatar_storage
Create Date: 2026-11-22 22:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "ec192_question_versions"
down_revision: Union[str, None] = "ec168_user_avatar_storage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "question_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(50), nullable=False),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("correct_answer", sa.Text(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.String(20), nullable=False),
        sa.Column("topic", sa.String(200), nullable=False),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("bloom_level", sa.Integer(), nullable=True),
        sa.Column("ln_level", sa.Integer(), nullable=True),
        sa.Column("estimated_time_minutes", sa.Integer(), nullable=True),
        sa.Column("quality_tier", sa.String(1), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("competency_id", sa.Integer(), nullable=True),
        sa.Column("source_chunks", sa.JSON(), nullable=True),
        sa.Column("source_documents", sa.JSON(), nullable=True),
        sa.Column("generation_metadata", sa.JSON(), nullable=True),
        sa.Column("exam_id", sa.String(100), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "review_status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["question_reviews.id"],
            name="fk_question_versions_question_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["competency_id"],
            ["competencies.id"],
            name="fk_question_versions_competency_id_competencies",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_question_versions_created_by_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            name="fk_question_versions_reviewed_by_users",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "question_id", "version_number", name="uq_question_versions_number"
        ),
        sa.CheckConstraint(
            "review_status IN ('pending', 'in_review', 'approved', "
            "'rejected', 'withdrawn')",
            name="ck_question_versions_review_status",
        ),
        sa.CheckConstraint(
            "ln_level IS NULL OR (ln_level >= 1 AND ln_level <= 4)",
            name="ck_question_versions_ln_level_range",
        ),
        sa.CheckConstraint(
            "version_number >= 1", name="ck_question_versions_number_positive"
        ),
    )
    op.create_index("ix_question_versions_id", "question_versions", ["id"])
    op.create_index(
        "ix_question_versions_question_id", "question_versions", ["question_id"]
    )
    op.create_index(
        "ix_question_versions_competency_id", "question_versions", ["competency_id"]
    )
    op.create_index("ix_question_versions_exam_id", "question_versions", ["exam_id"])
    op.create_index(
        "ix_question_versions_review_status", "question_versions", ["review_status"]
    )
    op.create_index(
        "uq_question_versions_one_open",
        "question_versions",
        ["question_id"],
        unique=True,
        postgresql_where=sa.text("review_status IN ('pending', 'in_review')"),
    )

    # Backfill: every existing question becomes version 1 of itself.
    op.execute(
        """
        INSERT INTO question_versions (
            question_id, version_number, question_text, question_type, options,
            correct_answer, explanation, difficulty, topic, language,
            bloom_level, ln_level, estimated_time_minutes, quality_tier,
            confidence_score, competency_id, source_chunks, source_documents,
            generation_metadata, exam_id, created_by, review_status,
            reviewed_by, reviewed_at, created_at, updated_at
        )
        SELECT
            id, 1, question_text, question_type, options,
            correct_answer, explanation, difficulty, topic, language,
            bloom_level, ln_level, estimated_time_minutes, quality_tier,
            confidence_score, competency_id, source_chunks, source_documents,
            generation_metadata, exam_id, created_by,
            CASE WHEN review_status = 'edited' THEN 'pending'
                 ELSE review_status END,
            reviewed_by, reviewed_at, created_at, updated_at
        FROM question_reviews
        """
    )

    op.add_column(
        "exam_questions",
        sa.Column("question_version_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_exam_questions_question_version_id",
        "exam_questions",
        ["question_version_id"],
    )
    op.execute(
        """
        UPDATE exam_questions eq
        SET question_version_id = qv.id
        FROM question_versions qv
        WHERE qv.question_id = eq.question_id AND qv.version_number = 1
        """
    )
    op.create_foreign_key(
        "fk_exam_questions_question_version_id",
        "exam_questions",
        "question_versions",
        ["question_version_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_exam_questions_question_version_id", "exam_questions", type_="foreignkey"
    )
    op.drop_index("ix_exam_questions_question_version_id", table_name="exam_questions")
    op.drop_column("exam_questions", "question_version_id")
    op.drop_table("question_versions")
