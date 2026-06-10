"""tf400: Kompetenzrahmen (HKB) + Handlungskompetenzen (HK) + QuestionReview-Bezug

Neue Tabellen competency_frameworks + competencies; additive, nullable Spalten
competency_id (FK SET NULL) + ln_level auf question_reviews. Nicht-destruktiv,
unbedenklich unter AUTO_MIGRATE=true. Altbestand bleibt NULL. (TF-400)

Revision ID: tf400_competency_frameworks
Revises: tf396_question_archive
Create Date: 2026-06-09
"""

from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = "tf400_competency_frameworks"
down_revision: Union[str, None] = "tf396_question_archive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "competency_frameworks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("module_code", sa.String(length=20), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rendered_text", sa.Text(), nullable=False),
        sa.Column(
            "language", sa.String(length=10), nullable=False, server_default="de"
        ),
        sa.Column("institution_id", sa.Integer(), nullable=True),
        sa.Column(
            "visibility",
            sa.String(length=20),
            nullable=False,
            server_default="institution",
        ),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "is_archived", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "visibility IN ('private', 'institution')",
            name="ck_competency_frameworks_visibility_valid",
        ),
    )
    op.create_index(
        "ix_competency_frameworks_institution_id",
        "competency_frameworks",
        ["institution_id"],
    )

    op.create_table(
        "competencies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("framework_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("descriptors", sa.JSON(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["framework_id"], ["competency_frameworks.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "framework_id", "code", name="ux_competencies_framework_code"
        ),
    )
    op.create_index("ix_competencies_framework_id", "competencies", ["framework_id"])

    op.add_column(
        "question_reviews",
        sa.Column("competency_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "question_reviews",
        sa.Column("ln_level", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_question_reviews_competency_id_competencies",
        "question_reviews",
        "competencies",
        ["competency_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_question_reviews_competency_id",
        "question_reviews",
        ["competency_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_question_reviews_competency_id", table_name="question_reviews")
    op.drop_constraint(
        "fk_question_reviews_competency_id_competencies",
        "question_reviews",
        type_="foreignkey",
    )
    op.drop_column("question_reviews", "ln_level")
    op.drop_column("question_reviews", "competency_id")
    op.drop_index("ix_competencies_framework_id", table_name="competencies")
    op.drop_table("competencies")
    op.drop_index(
        "ix_competency_frameworks_institution_id",
        table_name="competency_frameworks",
    )
    op.drop_table("competency_frameworks")
