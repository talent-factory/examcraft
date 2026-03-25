"""remove_organizations_table_migrate_resource_usage

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-18

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = "b2c3d4e5f6a7"  # pragma: allowlist secret
down_revision = "a1b2c3d4e5f6"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    try:
        columns = [c["name"] for c in inspector.get_columns(table)]
        return column in columns
    except Exception:
        return False


def _table_exists(table: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return table in inspector.get_table_names()


def upgrade() -> None:
    # Step 1: Add institution_id column to resource_usage if not exists
    if _table_exists("resource_usage") and not _column_exists(
        "resource_usage", "institution_id"
    ):
        op.add_column(
            "resource_usage",
            sa.Column(
                "institution_id",
                sa.Integer(),
                sa.ForeignKey("institutions.id", ondelete="CASCADE"),
                nullable=True,
            ),
        )

        # Step 2: Migrate data — extract integer from "org_X" strings
        op.execute(
            text(
                """
            UPDATE resource_usage
            SET institution_id = CAST(
                REPLACE(organization_id, 'org_', '') AS INTEGER
            )
            WHERE organization_id IS NOT NULL
            AND organization_id LIKE 'org_%'
            """
            )
        )

        # Step 3: Drop old column and constraint
        if _column_exists("resource_usage", "organization_id"):
            # Drop the unique index first if it exists
            try:
                op.drop_index("idx_resource_usage_unique", table_name="resource_usage")
            except Exception:
                pass

            op.drop_column("resource_usage", "organization_id")

            # Create new unique index
            op.create_index(
                "idx_resource_usage_unique",
                "resource_usage",
                ["institution_id", "resource_type", "period_start"],
                unique=True,
            )

    # Step 4: Drop organizations table if it exists
    if _table_exists("organizations"):
        op.drop_table("organizations")


def downgrade() -> None:
    # Recreate organizations table
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("tier_id", sa.String(255), nullable=True),
        sa.Column("subscription_status", sa.String(50), nullable=False),
        sa.Column("subscription_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subscription_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # Add organization_id back to resource_usage
    if _table_exists("resource_usage") and not _column_exists(
        "resource_usage", "organization_id"
    ):
        op.add_column(
            "resource_usage",
            sa.Column("organization_id", sa.String(255), nullable=True),
        )

        # Migrate data back
        op.execute(
            text(
                """
            UPDATE resource_usage
            SET organization_id = 'org_' || CAST(institution_id AS VARCHAR)
            WHERE institution_id IS NOT NULL
            """
            )
        )

        if _column_exists("resource_usage", "institution_id"):
            try:
                op.drop_index("idx_resource_usage_unique", table_name="resource_usage")
            except Exception:
                pass
            op.drop_column("resource_usage", "institution_id")
            op.create_index(
                "idx_resource_usage_unique",
                "resource_usage",
                ["organization_id", "resource_type", "period_start"],
                unique=True,
            )
