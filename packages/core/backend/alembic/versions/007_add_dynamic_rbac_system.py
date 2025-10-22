"""add dynamic rbac system

Revision ID: 007_add_dynamic_rbac_system
Revises: add_gdpr_fields
Create Date: 2025-10-20 17:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "007_add_dynamic_rbac_system"
down_revision = "add_gdpr_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Erstellt alle Tabellen für das dynamische RBAC-System:
    - features: Feature-Definitionen
    - rbac_roles: Erweiterte Rollen (separate von bestehender 'roles' Tabelle)
    - role_features: Many-to-Many Mapping Roles <-> Features
    - subscription_tiers: Pricing Tiers (Free, Starter, Professional, Enterprise)
    - tier_quotas: Ressourcen-Limits pro Tier
    - tier_features: Many-to-Many Mapping Tiers <-> Features
    - organizations: Multi-Tenant Organizations mit Subscription
    - resource_usage: Ressourcen-Nutzungs-Tracking
    - permission_audit_log: Audit Trail für Compliance
    """

    # ============================================
    # FEATURES
    # ============================================
    op.create_table(
        "features",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column(
            "is_active", sa.Boolean, nullable=False, server_default="true", index=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("name ~ '^[a-z0-9_]+$'", name="check_feature_name_format"),
    )

    # ============================================
    # RBAC ROLES (erweiterte Rollen)
    # ============================================
    op.create_table(
        "rbac_roles",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_system_role", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "is_active", sa.Boolean, nullable=False, server_default="true", index=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.CheckConstraint("name ~ '^[a-z0-9_]+$'", name="check_rbac_role_name_format"),
    )

    # ============================================
    # ROLE-FEATURE MAPPING
    # ============================================
    op.create_table(
        "role_features",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "role_id",
            sa.String(255),
            sa.ForeignKey("rbac_roles.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "feature_id",
            sa.String(255),
            sa.ForeignKey("features.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_role_feature_unique",
        "role_features",
        ["role_id", "feature_id"],
        unique=True,
    )

    # ============================================
    # SUBSCRIPTION TIERS
    # ============================================
    op.create_table(
        "subscription_tiers",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("price_monthly", sa.DECIMAL(10, 2), nullable=True),
        sa.Column("price_yearly", sa.DECIMAL(10, 2), nullable=True),
        sa.Column(
            "is_active", sa.Boolean, nullable=False, server_default="true", index=True
        ),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # ============================================
    # TIER QUOTAS
    # ============================================
    op.create_table(
        "tier_quotas",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "tier_id",
            sa.String(255),
            sa.ForeignKey("subscription_tiers.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("resource_type", sa.String(100), nullable=False, index=True),
        sa.Column("quota_limit", sa.Integer, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_tier_quota_unique",
        "tier_quotas",
        ["tier_id", "resource_type"],
        unique=True,
    )

    # ============================================
    # TIER-FEATURE MAPPING
    # ============================================
    op.create_table(
        "tier_features",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "tier_id",
            sa.String(255),
            sa.ForeignKey("subscription_tiers.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "feature_id",
            sa.String(255),
            sa.ForeignKey("features.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_tier_feature_unique",
        "tier_features",
        ["tier_id", "feature_id"],
        unique=True,
    )

    # ============================================
    # ORGANIZATIONS
    # ============================================
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, index=True),
        sa.Column(
            "tier_id",
            sa.String(255),
            sa.ForeignKey("subscription_tiers.id"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "subscription_status",
            sa.String(50),
            nullable=False,
            server_default="active",
            index=True,
        ),
        sa.Column("subscription_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subscription_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.CheckConstraint(
            "subscription_status IN ('active', 'suspended', 'cancelled', 'trial')",
            name="check_subscription_status",
        ),
    )

    # ============================================
    # RESOURCE USAGE
    # ============================================
    op.create_table(
        "resource_usage",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "organization_id",
            sa.String(255),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("resource_type", sa.String(100), nullable=False, index=True),
        sa.Column("usage_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "period_start", sa.DateTime(timezone=True), nullable=False, index=True
        ),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_resource_usage_unique",
        "resource_usage",
        ["organization_id", "resource_type", "period_start"],
        unique=True,
    )

    # ============================================
    # PERMISSION AUDIT LOG
    # ============================================
    op.create_table(
        "permission_audit_log",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(255), nullable=False, index=True),
        sa.Column("action", sa.String(100), nullable=False, index=True),
        sa.Column("resource_type", sa.String(100), nullable=True, index=True),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
    )
    op.create_index(
        "idx_audit_user_action", "permission_audit_log", ["user_id", "action"]
    )
    op.create_index("idx_audit_timestamp", "permission_audit_log", ["timestamp"])


def downgrade() -> None:
    """
    Entfernt alle RBAC-Tabellen in umgekehrter Reihenfolge
    """
    op.drop_table("permission_audit_log")
    op.drop_table("resource_usage")
    op.drop_table("organizations")
    op.drop_table("tier_features")
    op.drop_table("tier_quotas")
    op.drop_table("subscription_tiers")
    op.drop_table("role_features")
    op.drop_table("rbac_roles")
    op.drop_table("features")
