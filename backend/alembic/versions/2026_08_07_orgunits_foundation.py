"""Org-Unit-Hierarchie: org_units + user_org_units (Stufe 0 Fundament)

Spec: docs/superpowers/specs/2026-08-07-org-unit-hierarchie-design.md

Additive Migration (kein Datenverlust): legt zwei neue Tabellen an.
``org_units`` ist selbstreferenzierend (parent_org_unit_id) fuer eine
beliebig tiefe Organisationshierarchie unterhalb der Institution;
``user_org_units`` ist die M:N-Mitgliedschaft zwischen User und OrgUnit.

Revision ID: orgunits_foundation
Revises: tf500_attempt_idem_exam
Create Date: 2026-08-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "orgunits_foundation"
down_revision: Union[str, None] = "tf500_attempt_idem_exam"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "org_units",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("parent_org_unit_id", sa.Integer(), nullable=True),
        sa.Column("unit_type", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["parent_org_unit_id"], ["org_units.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(op.f("ix_org_units_id"), "org_units", ["id"], unique=False)
    op.create_index(
        op.f("ix_org_units_institution_id"),
        "org_units",
        ["institution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_org_units_parent_org_unit_id"),
        "org_units",
        ["parent_org_unit_id"],
        unique=False,
    )
    # Sibling-Name-Eindeutigkeit DB-seitig erzwingen (Service-Layer-Check in
    # org_unit_service.py bleibt als freundlicher 409-Vorab-Check, ist aber
    # SELECT-dann-INSERT und damit race-anfaellig ohne diese Constraint).
    # Zwei Indizes, weil NULL-Werte in einem Unique-Index nie als gleich
    # gelten: ein regulaerer Composite-Index deckt Geschwister mit
    # nicht-null parent_org_unit_id ab, der partielle Index separat die
    # Wurzel-Ebene (parent_org_unit_id IS NULL).
    op.create_index(
        "ix_org_units_unique_sibling_name",
        "org_units",
        ["institution_id", "parent_org_unit_id", "name"],
        unique=True,
    )
    op.create_index(
        "ix_org_units_unique_root_name",
        "org_units",
        ["institution_id", "name"],
        unique=True,
        postgresql_where=sa.text("parent_org_unit_id IS NULL"),
    )

    op.create_table(
        "user_org_units",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("org_unit_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_unit_id"], ["org_units.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "org_unit_id"),
    )


def downgrade() -> None:
    op.drop_table("user_org_units")
    op.drop_index("ix_org_units_unique_root_name", table_name="org_units")
    op.drop_index("ix_org_units_unique_sibling_name", table_name="org_units")
    op.drop_index(op.f("ix_org_units_parent_org_unit_id"), table_name="org_units")
    op.drop_index(op.f("ix_org_units_institution_id"), table_name="org_units")
    op.drop_index(op.f("ix_org_units_id"), table_name="org_units")
    op.drop_table("org_units")
