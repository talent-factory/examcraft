"""Portfolio-Assessment: Template/Phase/Criterion-Grundtabellen.

Spec: docs/superpowers/specs/2026-09-22-portfolio-assessment-design.md

Additive Migration (keine bestehenden Tabellen betroffen): legt die drei
Grundtabellen fuer wiederverwendbare, mehrphasige Bewertungs-Templates an.

``visibility`` ist bewusst ein ``VARCHAR`` + CHECK-Constraint (nicht ein
Postgres-ENUM-Typ wie ``promptvisibility``) -- ein spaeterer fuenfter Tier
braucht dann kein ``ALTER TYPE ... ADD VALUE`` ausserhalb einer Transaktion,
sondern nur ein Constraint-Update. Gleiches Muster wie
``grading_schemes.display_format``.

``org_unit_id`` auf ``portfolio_templates`` ist noetig, damit die
``team``-Sichtbarkeitsstufe (mirrors ``PromptVisibility``) ueberhaupt
adressierbar ist -- ohne Org-Unit-Bezug waere "mit meinem Team teilen"
bedeutungslos, exakt das Muster von ``documents``/``prompts``/``exams``.

Table-Erstellung ist auf "existiert noch nicht" GEGUARDET (Inspector-Check
statt bedingungslosem ``create_table``), analog ``tf397_prompt_template_tags``
/``tf345_wizard_sessions``: das toleriert einen bereits per ``create_all()``
gebootstrappten Scratch-Testpfad (Modelle -> Tabellen, dann ``stamp`` +
``upgrade``) und macht die Migration re-runnbar bei teilweise angewandtem
Zustand, statt bei "relation already exists" abzubrechen.

Revision ID: portfolio_templates_foundation
Revises: tf736_generation_job_outcome
"""

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "portfolio_templates_foundation"
down_revision: Union[str, None] = "tf736_generation_job_outcome"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = inspector.get_table_names()

    if "portfolio_templates" not in existing:
        op.create_table(
            "portfolio_templates",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "institution_id",
                sa.Integer(),
                sa.ForeignKey("institutions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "visibility",
                sa.String(20),
                nullable=False,
                server_default="private",
            ),
            sa.Column(
                "org_unit_id",
                sa.Integer(),
                sa.ForeignKey("org_units.id"),
                nullable=True,
            ),
            sa.Column(
                "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column(
                "created_by",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
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
                "visibility IN ('private', 'team', 'institution', 'system')",
                name="check_portfolio_template_visibility",
            ),
            sa.CheckConstraint(
                "(visibility = 'team') = (org_unit_id IS NOT NULL)",
                name="ck_portfolio_templates_team_visibility_requires_org_unit",
            ),
        )
        op.create_index(
            "ix_portfolio_templates_institution_id",
            "portfolio_templates",
            ["institution_id"],
        )
        op.create_index(
            "ix_portfolio_templates_org_unit_id",
            "portfolio_templates",
            ["org_unit_id"],
        )

    if "portfolio_template_phases" not in existing:
        op.create_table(
            "portfolio_template_phases",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "template_id",
                UUID(as_uuid=True),
                sa.ForeignKey("portfolio_templates.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("expected_folder_patterns", JSONB(), nullable=True),
            sa.UniqueConstraint(
                "template_id", "position", name="uq_portfolio_phase_template_position"
            ),
        )
        # No standalone template_id index: the unique constraint above
        # already provides one via its leading column.

    if "portfolio_criteria" not in existing:
        op.create_table(
            "portfolio_criteria",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "phase_id",
                UUID(as_uuid=True),
                sa.ForeignKey("portfolio_template_phases.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("type_tag", sa.String(50), nullable=True),
            sa.Column("max_points", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("rubric_by_score", JSONB(), nullable=False),
            sa.Column("checklist_items", JSONB(), nullable=True),
            sa.CheckConstraint(
                "max_points > 0", name="check_portfolio_criterion_max_points"
            ),
            sa.UniqueConstraint(
                "phase_id", "position", name="uq_portfolio_criterion_phase_position"
            ),
        )
        # No standalone phase_id index: the unique constraint above already
        # provides one via its leading column.


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = inspector.get_table_names()

    if "portfolio_criteria" in existing:
        op.drop_table("portfolio_criteria")
    if "portfolio_template_phases" in existing:
        op.drop_table("portfolio_template_phases")
    if "portfolio_templates" in existing:
        op.drop_table("portfolio_templates")
