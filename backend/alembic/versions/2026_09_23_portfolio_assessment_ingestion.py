"""Portfolio-Assessment: Assessment/Document/Job/GitHub-Credential-Tabellen.

Spec: docs/superpowers/specs/2026-09-22-portfolio-assessment-design.md,
Abschnitt "Ergaenzungen aus Epic 2".

Additive Migration (keine bestehenden Tabellen betroffen): legt die vier
Tabellen fuer Assessment-Anlage + Ingestion (ZIP + optionaler
GitHub-Repo-Tarball) an. ``source_repository_token_encrypted`` aus dem
urspruenglichen Spec-Entwurf existiert bewusst NICHT -- der GitHub-Token
liegt user-seitig in ``portfolio_github_credentials``, nicht am Assessment.

Status-/Kategorie-Spalten (``status``, ``origin``, ``classification_source``,
``job_type``) sind VARCHAR + CHECK-Constraint, gleiches Muster wie
``portfolio_templates.visibility`` -- kein Postgres-ENUM-Typ, damit ein
spaeterer neuer Wert kein ``ALTER TYPE ... ADD VALUE`` ausserhalb einer
Transaktion braucht.

Revision ID: portfolio_assessment_ingestion
Revises: portfolio_templates_foundation
"""

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "portfolio_assessment_ingestion"
down_revision: Union[str, None] = "portfolio_templates_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = inspector.get_table_names()

    if "portfolio_github_credentials" not in existing:
        op.create_table(
            "portfolio_github_credentials",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                unique=True,
            ),
            sa.Column("token_encrypted", sa.Text(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )

    if "portfolio_assessments" not in existing:
        op.create_table(
            "portfolio_assessments",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "template_id",
                UUID(as_uuid=True),
                sa.ForeignKey("portfolio_templates.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("template_version", sa.Integer(), nullable=False),
            sa.Column(
                "institution_id",
                sa.Integer(),
                sa.ForeignKey("institutions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "student_id",
                sa.Integer(),
                sa.ForeignKey("students.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "created_by",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "status", sa.String(20), nullable=False, server_default="uploading"
            ),
            sa.Column("framework_conditions", sa.Text(), nullable=True),
            sa.Column("source_repository_url", sa.String(500), nullable=True),
            sa.Column("source_repository_ref", sa.String(100), nullable=True),
            sa.Column(
                "grading_scheme_id",
                sa.Integer(),
                sa.ForeignKey("grading_schemes.id", ondelete="RESTRICT"),
                nullable=True,
            ),
            sa.Column("overall_points_awarded", sa.Float(), nullable=True),
            sa.Column("overall_points_max", sa.Float(), nullable=True),
            sa.Column("overall_percentage", sa.Float(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.CheckConstraint(
                "status IN ('uploading', 'classifying', 'ready_to_grade', "
                "'grading', 'completed', 'failed')",
                name="check_portfolio_assessment_status",
            ),
        )
        op.create_index(
            "ix_portfolio_assessments_template_id",
            "portfolio_assessments",
            ["template_id"],
        )
        op.create_index(
            "ix_portfolio_assessments_institution_id",
            "portfolio_assessments",
            ["institution_id"],
        )
        op.create_index(
            "ix_portfolio_assessments_student_id",
            "portfolio_assessments",
            ["student_id"],
        )

    if "portfolio_documents" not in existing:
        op.create_table(
            "portfolio_documents",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "assessment_id",
                UUID(as_uuid=True),
                sa.ForeignKey("portfolio_assessments.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "document_id",
                sa.Integer(),
                sa.ForeignKey("documents.id", ondelete="CASCADE"),
                nullable=False,
                unique=True,
            ),
            sa.Column(
                "phase_id",
                UUID(as_uuid=True),
                sa.ForeignKey("portfolio_template_phases.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("origin", sa.String(20), nullable=False),
            sa.Column("original_relative_path", sa.String(1000), nullable=False),
            sa.Column("classification_confidence", sa.Float(), nullable=True),
            sa.Column("classification_source", sa.String(10), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.CheckConstraint(
                "origin IN ('upload_zip', 'github_repository')",
                name="check_portfolio_document_origin",
            ),
            sa.CheckConstraint(
                "classification_source IS NULL OR classification_source IN "
                "('auto', 'manual')",
                name="check_portfolio_document_classification_source",
            ),
        )
        op.create_index(
            "ix_portfolio_documents_assessment_id",
            "portfolio_documents",
            ["assessment_id"],
        )
        op.create_index(
            "ix_portfolio_documents_phase_id", "portfolio_documents", ["phase_id"]
        )

    if "portfolio_assessment_jobs" not in existing:
        op.create_table(
            "portfolio_assessment_jobs",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "assessment_id",
                UUID(as_uuid=True),
                sa.ForeignKey("portfolio_assessments.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("job_type", sa.String(20), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
            sa.Column("files_total", sa.Integer(), nullable=True),
            sa.Column("files_done", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_log", JSONB(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.CheckConstraint(
                "job_type IN ('ingest', 'classify', 'grade')",
                name="check_portfolio_assessment_job_type",
            ),
            sa.CheckConstraint(
                "status IN ('queued', 'running', 'completed', 'failed')",
                name="check_portfolio_assessment_job_status",
            ),
        )
        op.create_index(
            "ix_portfolio_assessment_jobs_assessment_id",
            "portfolio_assessment_jobs",
            ["assessment_id"],
        )


def downgrade() -> None:
    op.drop_table("portfolio_assessment_jobs")
    op.drop_table("portfolio_documents")
    op.drop_table("portfolio_assessments")
    op.drop_table("portfolio_github_credentials")
