"""Baseline schema: the database state that ``d715210cb3a3`` builds on (TF-434).

The Alembic chain used to start with ``d715210cb3a3``, which ALTERs ``users``
and therefore assumed a schema that no migration created. ``alembic upgrade
head`` against an empty database crashed at ``d74c69d53df6``; local
bootstraps had to fall back to ``create_all`` + ``stamp head`` and silently
skipped every migration body (data seeds such as tf333's grading schemes).

This revision is the new root of the chain. It creates the 29 tables that
existed right before ``d715210cb3a3`` was introduced (models at commit
``3a69eac6^``, core + premium), so the whole chain replays from an empty
database exactly like it ran in production.

The DDL is frozen on purpose: it must never import the current models,
otherwise later ALTER migrations would hit "already exists".

Existing databases (production, dev, CI) are already past this revision and
never run it — no ``alembic stamp`` is needed. As an extra safety net the
upgrade is a no-op when ``users`` already exists (legacy database without an
``alembic_version`` row that predates the Alembic chain).

Revision ID: tf434_baseline
Revises:
Create Date: 2026-09-29 (schema state of 2026-03-12)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "tf434_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Shared by several tables (emaileventtype is used twice), so the types are
# created once up front instead of implicitly per create_table().
DOCUMENTSTATUS_ENUM = postgresql.ENUM(
    "QUEUED",
    "PROCESSING",
    "COMPLETED",
    "FAILED",
    "UPLOADED",
    "PROCESSED",
    "ERROR",
    name="documentstatus",
    create_type=False,
)

EMAILEVENTTYPE_ENUM = postgresql.ENUM(
    "SENT",
    "DELIVERED",
    "BOUNCED",
    "OPENED",
    "CLICKED",
    "SPAM_COMPLAINT",
    "UNSUBSCRIBED",
    name="emaileventtype",
    create_type=False,
)

EMAILTYPE_ENUM = postgresql.ENUM(
    "VERIFICATION",
    "PASSWORD_RESET",
    "PAYMENT_CONFIRMATION",
    "NOTIFICATION",
    "WELCOME",
    "MARKETING",
    name="emailtype",
    create_type=False,
)

SUBSCRIPTIONSTATUS_ENUM = postgresql.ENUM(
    "ACTIVE",
    "PAST_DUE",
    "CANCELED",
    "INCOMPLETE",
    "INCOMPLETE_EXPIRED",
    "TRIALING",
    "UNPAID",
    "PAUSED",
    name="subscriptionstatus",
    create_type=False,
)

_ENUMS = (
    DOCUMENTSTATUS_ENUM,
    EMAILEVENTTYPE_ENUM,
    EMAILTYPE_ENUM,
    SUBSCRIPTIONSTATUS_ENUM,
)


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("users"):
        # Pre-Alembic legacy database: the baseline schema is already there.
        return

    for enum in _ENUMS:
        enum.create(bind, checkfirst=True)

    op.create_table(
        "email_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email_id", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("event_type", EMAILEVENTTYPE_ENUM, nullable=False),
        sa.Column("email_type", EMAILTYPE_ENUM, nullable=True),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("event_metadata", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_email_events_email_id"), "email_events", ["email_id"], unique=False
    )
    op.create_index(op.f("ix_email_events_id"), "email_events", ["id"], unique=False)
    op.create_index(
        "ix_email_events_provider_timestamp",
        "email_events",
        ["provider", "event_timestamp"],
        unique=False,
    )
    op.create_index(
        op.f("ix_email_events_recipient_email"),
        "email_events",
        ["recipient_email"],
        unique=False,
    )
    op.create_index(
        "ix_email_events_recipient_type",
        "email_events",
        ["recipient_email", "event_type"],
        unique=False,
    )
    op.create_table(
        "email_suppression_list",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "reason",
            EMAILEVENTTYPE_ENUM,
            nullable=False,
            comment="Reason for suppression (bounced, spam_complaint, unsubscribed)",
        ),
        sa.Column(
            "suppress_transactional",
            sa.Integer(),
            nullable=False,
            comment="1 = suppress transactional emails (only for bounces)",
        ),
        sa.Column(
            "suppress_marketing",
            sa.Integer(),
            nullable=False,
            comment="1 = suppress marketing emails",
        ),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("original_event_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_email_suppression_list_email"),
        "email_suppression_list",
        ["email"],
        unique=True,
    )
    op.create_index(
        op.f("ix_email_suppression_list_id"),
        "email_suppression_list",
        ["id"],
        unique=False,
    )
    op.create_table(
        "features",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("name ~ '^[a-z0-9_]+$'", name="check_feature_name_format"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_features_is_active"), "features", ["is_active"], unique=False
    )
    op.create_index(op.f("ix_features_name"), "features", ["name"], unique=True)
    op.create_table(
        "institutions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("domain", sa.String(length=100), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column("address_line1", sa.String(length=255), nullable=True),
        sa.Column("address_line2", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("settings", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("subscription_tier", sa.String(length=50), nullable=False),
        sa.Column("features_enabled", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("max_users", sa.Integer(), nullable=False),
        sa.Column("max_documents", sa.Integer(), nullable=False),
        sa.Column("max_questions_per_month", sa.Integer(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain"),
    )
    op.create_index(op.f("ix_institutions_id"), "institutions", ["id"], unique=False)
    op.create_index(
        op.f("ix_institutions_is_active"), "institutions", ["is_active"], unique=False
    )
    op.create_index(op.f("ix_institutions_name"), "institutions", ["name"], unique=True)
    op.create_index(op.f("ix_institutions_slug"), "institutions", ["slug"], unique=True)
    op.create_table(
        "permission_audit_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=True),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_audit_timestamp", "permission_audit_log", ["timestamp"], unique=False
    )
    op.create_index(
        "idx_audit_user_action",
        "permission_audit_log",
        ["user_id", "action"],
        unique=False,
    )
    op.create_index(
        op.f("ix_permission_audit_log_action"),
        "permission_audit_log",
        ["action"],
        unique=False,
    )
    op.create_index(
        op.f("ix_permission_audit_log_id"), "permission_audit_log", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_permission_audit_log_resource_type"),
        "permission_audit_log",
        ["resource_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_permission_audit_log_timestamp"),
        "permission_audit_log",
        ["timestamp"],
        unique=False,
    )
    op.create_index(
        op.f("ix_permission_audit_log_user_id"),
        "permission_audit_log",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("variables", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "category IN ('question_generation', 'chatbot', 'evaluation')",
            name="check_template_category",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_prompt_templates_category"),
        "prompt_templates",
        ["category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_prompt_templates_name"), "prompt_templates", ["name"], unique=True
    )
    op.create_table(
        "prompts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("tags", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("use_case", sa.String(length=255), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("author_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=True),
        sa.Column("tokens_estimated", sa.Integer(), nullable=True),
        sa.Column("qdrant_point_id", sa.String(length=255), nullable=True),
        sa.CheckConstraint(
            "category IN ('system_prompt', 'user_prompt', 'few_shot_example', 'template')",
            name="check_category",
        ),
        sa.CheckConstraint("version > 0", name="check_version"),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["prompts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_prompts_category"), "prompts", ["category"], unique=False)
    op.create_index(
        op.f("ix_prompts_is_active"), "prompts", ["is_active"], unique=False
    )
    op.create_index(op.f("ix_prompts_name"), "prompts", ["name"], unique=True)
    op.create_index(op.f("ix_prompts_use_case"), "prompts", ["use_case"], unique=False)
    op.create_table(
        "rbac_roles",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system_role", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.CheckConstraint("name ~ '^[a-z0-9_]+$'", name="check_rbac_role_name_format"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_rbac_roles_is_active"), "rbac_roles", ["is_active"], unique=False
    )
    op.create_index(op.f("ix_rbac_roles_name"), "rbac_roles", ["name"], unique=True)
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("permissions", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_system_role", sa.Boolean(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_roles_id"), "roles", ["id"], unique=False)
    op.create_index(op.f("ix_roles_name"), "roles", ["name"], unique=True)
    op.create_table(
        "subscription_tiers",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_monthly", sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column("price_yearly", sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_subscription_tiers_is_active"),
        "subscription_tiers",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_subscription_tiers_name"), "subscription_tiers", ["name"], unique=True
    )
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("tier_id", sa.String(length=255), nullable=True),
        sa.Column("subscription_status", sa.String(length=50), nullable=False),
        sa.Column("subscription_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subscription_end", sa.DateTime(timezone=True), nullable=True),
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
            "subscription_status IN ('active', 'suspended', 'cancelled', 'trial')",
            name="check_subscription_status",
        ),
        sa.ForeignKeyConstraint(
            ["tier_id"],
            ["subscription_tiers.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_organizations_name"), "organizations", ["name"], unique=False
    )
    op.create_index(
        op.f("ix_organizations_subscription_status"),
        "organizations",
        ["subscription_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_organizations_tier_id"), "organizations", ["tier_id"], unique=False
    )
    op.create_table(
        "prompt_usage_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("prompt_id", sa.UUID(), nullable=True),
        sa.Column("prompt_version", sa.Integer(), nullable=True),
        sa.Column("use_case", sa.String(length=255), nullable=True),
        sa.Column(
            "context_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("user_id", sa.String(length=255), nullable=True),
        sa.Column("session_id", sa.String(length=255), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["prompt_id"], ["prompts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_prompt_usage_logs_timestamp"),
        "prompt_usage_logs",
        ["timestamp"],
        unique=False,
    )
    op.create_index(
        op.f("ix_prompt_usage_logs_use_case"),
        "prompt_usage_logs",
        ["use_case"],
        unique=False,
    )
    op.create_table(
        "role_features",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.String(length=255), nullable=False),
        sa.Column("feature_id", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["feature_id"], ["features.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["rbac_roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_role_feature_unique",
        "role_features",
        ["role_id", "feature_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_role_features_feature_id"),
        "role_features",
        ["feature_id"],
        unique=False,
    )
    op.create_index(op.f("ix_role_features_id"), "role_features", ["id"], unique=False)
    op.create_index(
        op.f("ix_role_features_role_id"), "role_features", ["role_id"], unique=False
    )
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_price_id", sa.String(length=255), nullable=False),
        sa.Column("status", SUBSCRIPTIONSTATUS_ENUM, nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_subscriptions_id"), "subscriptions", ["id"], unique=False)
    op.create_index(
        op.f("ix_subscriptions_institution_id"),
        "subscriptions",
        ["institution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_subscriptions_stripe_customer_id"),
        "subscriptions",
        ["stripe_customer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_subscriptions_stripe_subscription_id"),
        "subscriptions",
        ["stripe_subscription_id"],
        unique=True,
    )
    op.create_table(
        "tier_features",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tier_id", sa.String(length=255), nullable=False),
        sa.Column("feature_id", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["feature_id"], ["features.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["tier_id"], ["subscription_tiers.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_tier_feature_unique",
        "tier_features",
        ["tier_id", "feature_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_tier_features_feature_id"),
        "tier_features",
        ["feature_id"],
        unique=False,
    )
    op.create_index(op.f("ix_tier_features_id"), "tier_features", ["id"], unique=False)
    op.create_index(
        op.f("ix_tier_features_tier_id"), "tier_features", ["tier_id"], unique=False
    )
    op.create_table(
        "tier_quotas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tier_id", sa.String(length=255), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("quota_limit", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tier_id"], ["subscription_tiers.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_tier_quota_unique",
        "tier_quotas",
        ["tier_id", "resource_type"],
        unique=True,
    )
    op.create_index(op.f("ix_tier_quotas_id"), "tier_quotas", ["id"], unique=False)
    op.create_index(
        op.f("ix_tier_quotas_resource_type"),
        "tier_quotas",
        ["resource_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tier_quotas_tier_id"), "tier_quotas", ["tier_id"], unique=False
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("avatar_url", sa.String(length=2000), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("is_email_verified", sa.Boolean(), nullable=False),
        sa.Column("is_superuser", sa.Boolean(), nullable=False),
        sa.Column("oauth_provider", sa.String(length=50), nullable=True),
        sa.Column("oauth_id", sa.String(length=255), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_ip", sa.String(length=45), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_reset_token", sa.String(length=255), nullable=True),
        sa.Column("password_reset_expires", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email_verification_token", sa.String(length=255), nullable=True),
        sa.Column(
            "email_verification_expires", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("preferences", sa.Text(), nullable=True),
        sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_deletion_date", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'suspended', 'pending')",
            name="check_user_status",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email_verification_token"),
        sa.UniqueConstraint("password_reset_token"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(
        op.f("ix_users_institution_id"), "users", ["institution_id"], unique=False
    )
    op.create_index(op.f("ix_users_oauth_id"), "users", ["oauth_id"], unique=True)
    op.create_index(op.f("ix_users_status"), "users", ["status"], unique=False)
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=True),
        sa.Column("resource_id", sa.String(length=100), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("additional_data", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False
    )
    op.create_index(
        op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False
    )
    op.create_index(op.f("ix_audit_logs_id"), "audit_logs", ["id"], unique=False)
    op.create_index(
        op.f("ix_audit_logs_resource_id"), "audit_logs", ["resource_id"], unique=False
    )
    op.create_index(
        op.f("ix_audit_logs_resource_type"),
        "audit_logs",
        ["resource_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"], unique=False
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("status", DOCUMENTSTATUS_ENUM, nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("institution_id", sa.Integer(), nullable=True),
        sa.Column("doc_metadata", sa.JSON(), nullable=True),
        sa.Column("content_preview", sa.Text(), nullable=True),
        sa.Column("vector_collection", sa.String(length=100), nullable=True),
        sa.Column("has_vectors", sa.Boolean(), nullable=True),
        sa.Column("task_id", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("processing_info", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_documents_id"), "documents", ["id"], unique=False)
    op.create_index(
        op.f("ix_documents_institution_id"),
        "documents",
        ["institution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_documents_task_id"), "documents", ["task_id"], unique=False
    )
    op.create_index(
        op.f("ix_documents_user_id"), "documents", ["user_id"], unique=False
    )
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_email_verification_tokens_id"),
        "email_verification_tokens",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_email_verification_tokens_token"),
        "email_verification_tokens",
        ["token"],
        unique=True,
    )
    op.create_table(
        "oauth_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("picture", sa.Text(), nullable=True),
        sa.Column("raw_user_info", sa.Text(), nullable=True),
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
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "provider IN ('google', 'microsoft', 'github')", name="valid_oauth_provider"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_oauth_accounts_id"), "oauth_accounts", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_oauth_accounts_provider"), "oauth_accounts", ["provider"], unique=False
    )
    op.create_index(
        op.f("ix_oauth_accounts_provider_user_id"),
        "oauth_accounts",
        ["provider_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_oauth_accounts_user_id"), "oauth_accounts", ["user_id"], unique=False
    )
    op.create_table(
        "question_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(length=50), nullable=False),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("correct_answer", sa.Text(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("topic", sa.String(length=200), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column("source_chunks", sa.JSON(), nullable=True),
        sa.Column("source_documents", sa.JSON(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("bloom_level", sa.Integer(), nullable=True),
        sa.Column("estimated_time_minutes", sa.Integer(), nullable=True),
        sa.Column("quality_tier", sa.String(length=1), nullable=True),
        sa.Column("review_status", sa.String(length=20), nullable=False),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("institution_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("exam_id", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint(
            "review_status IN ('pending', 'approved', 'rejected', 'edited', 'in_review')",
            name="check_review_status",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_question_reviews_exam_id"),
        "question_reviews",
        ["exam_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_question_reviews_id"), "question_reviews", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_question_reviews_institution_id"),
        "question_reviews",
        ["institution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_question_reviews_review_status"),
        "question_reviews",
        ["review_status"],
        unique=False,
    )
    op.create_table(
        "resource_usage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.String(length=255), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("usage_count", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
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
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_resource_usage_unique",
        "resource_usage",
        ["organization_id", "resource_type", "period_start"],
        unique=True,
    )
    op.create_index(
        op.f("ix_resource_usage_id"), "resource_usage", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_resource_usage_organization_id"),
        "resource_usage",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_resource_usage_period_start"),
        "resource_usage",
        ["period_start"],
        unique=False,
    )
    op.create_index(
        op.f("ix_resource_usage_resource_type"),
        "resource_usage",
        ["resource_type"],
        unique=False,
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_jti", sa.String(length=255), nullable=False),
        sa.Column("refresh_token_jti", sa.String(length=255), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("device_type", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "last_activity_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_sessions_expires_at"),
        "user_sessions",
        ["expires_at"],
        unique=False,
    )
    op.create_index(op.f("ix_user_sessions_id"), "user_sessions", ["id"], unique=False)
    op.create_index(
        op.f("ix_user_sessions_is_active"), "user_sessions", ["is_active"], unique=False
    )
    op.create_index(
        op.f("ix_user_sessions_refresh_token_jti"),
        "user_sessions",
        ["refresh_token_jti"],
        unique=True,
    )
    op.create_index(
        op.f("ix_user_sessions_token_jti"), "user_sessions", ["token_jti"], unique=True
    )
    op.create_index(
        op.f("ix_user_sessions_user_id"), "user_sessions", ["user_id"], unique=False
    )
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("document_ids", sa.ARRAY(sa.Integer()), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("message_count", sa.Integer(), nullable=False),
        sa.Column("is_exported_as_document", sa.Boolean(), nullable=False),
        sa.Column("exported_document_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["exported_document_id"], ["documents.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "review_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("comment_text", sa.Text(), nullable=False),
        sa.Column("comment_type", sa.String(length=50), nullable=True),
        sa.Column("author", sa.String(length=100), nullable=False),
        sa.Column("author_role", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["question_id"], ["question_reviews.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_review_comments_id"), "review_comments", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_review_comments_question_id"),
        "review_comments",
        ["question_id"],
        unique=False,
    )
    op.create_table(
        "review_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("old_status", sa.String(length=20), nullable=True),
        sa.Column("new_status", sa.String(length=20), nullable=True),
        sa.Column("changed_fields", sa.JSON(), nullable=True),
        sa.Column("changed_by", sa.String(length=100), nullable=False),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column(
            "changed_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["question_id"], ["question_reviews.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_review_history_id"), "review_history", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_review_history_question_id"),
        "review_history",
        ["question_id"],
        unique=False,
    )
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "timestamp", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["session_id"], ["chat_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_index(op.f("ix_review_history_question_id"), table_name="review_history")
    op.drop_index(op.f("ix_review_history_id"), table_name="review_history")
    op.drop_table("review_history")
    op.drop_index(op.f("ix_review_comments_question_id"), table_name="review_comments")
    op.drop_index(op.f("ix_review_comments_id"), table_name="review_comments")
    op.drop_table("review_comments")
    op.drop_table("chat_sessions")
    op.drop_index(op.f("ix_user_sessions_user_id"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_token_jti"), table_name="user_sessions")
    op.drop_index(
        op.f("ix_user_sessions_refresh_token_jti"), table_name="user_sessions"
    )
    op.drop_index(op.f("ix_user_sessions_is_active"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_id"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_expires_at"), table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_table("user_roles")
    op.drop_index(op.f("ix_resource_usage_resource_type"), table_name="resource_usage")
    op.drop_index(op.f("ix_resource_usage_period_start"), table_name="resource_usage")
    op.drop_index(
        op.f("ix_resource_usage_organization_id"), table_name="resource_usage"
    )
    op.drop_index(op.f("ix_resource_usage_id"), table_name="resource_usage")
    op.drop_index("idx_resource_usage_unique", table_name="resource_usage")
    op.drop_table("resource_usage")
    op.drop_index(
        op.f("ix_question_reviews_review_status"), table_name="question_reviews"
    )
    op.drop_index(
        op.f("ix_question_reviews_institution_id"), table_name="question_reviews"
    )
    op.drop_index(op.f("ix_question_reviews_id"), table_name="question_reviews")
    op.drop_index(op.f("ix_question_reviews_exam_id"), table_name="question_reviews")
    op.drop_table("question_reviews")
    op.drop_index(op.f("ix_oauth_accounts_user_id"), table_name="oauth_accounts")
    op.drop_index(
        op.f("ix_oauth_accounts_provider_user_id"), table_name="oauth_accounts"
    )
    op.drop_index(op.f("ix_oauth_accounts_provider"), table_name="oauth_accounts")
    op.drop_index(op.f("ix_oauth_accounts_id"), table_name="oauth_accounts")
    op.drop_table("oauth_accounts")
    op.drop_index(
        op.f("ix_email_verification_tokens_token"),
        table_name="email_verification_tokens",
    )
    op.drop_index(
        op.f("ix_email_verification_tokens_id"), table_name="email_verification_tokens"
    )
    op.drop_table("email_verification_tokens")
    op.drop_index(op.f("ix_documents_user_id"), table_name="documents")
    op.drop_index(op.f("ix_documents_task_id"), table_name="documents")
    op.drop_index(op.f("ix_documents_institution_id"), table_name="documents")
    op.drop_index(op.f("ix_documents_id"), table_name="documents")
    op.drop_table("documents")
    op.drop_index(op.f("ix_audit_logs_user_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_resource_type"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_resource_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index(op.f("ix_users_status"), table_name="users")
    op.drop_index(op.f("ix_users_oauth_id"), table_name="users")
    op.drop_index(op.f("ix_users_institution_id"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_tier_quotas_tier_id"), table_name="tier_quotas")
    op.drop_index(op.f("ix_tier_quotas_resource_type"), table_name="tier_quotas")
    op.drop_index(op.f("ix_tier_quotas_id"), table_name="tier_quotas")
    op.drop_index("idx_tier_quota_unique", table_name="tier_quotas")
    op.drop_table("tier_quotas")
    op.drop_index(op.f("ix_tier_features_tier_id"), table_name="tier_features")
    op.drop_index(op.f("ix_tier_features_id"), table_name="tier_features")
    op.drop_index(op.f("ix_tier_features_feature_id"), table_name="tier_features")
    op.drop_index("idx_tier_feature_unique", table_name="tier_features")
    op.drop_table("tier_features")
    op.drop_index(
        op.f("ix_subscriptions_stripe_subscription_id"), table_name="subscriptions"
    )
    op.drop_index(
        op.f("ix_subscriptions_stripe_customer_id"), table_name="subscriptions"
    )
    op.drop_index(op.f("ix_subscriptions_institution_id"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_id"), table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_index(op.f("ix_role_features_role_id"), table_name="role_features")
    op.drop_index(op.f("ix_role_features_id"), table_name="role_features")
    op.drop_index(op.f("ix_role_features_feature_id"), table_name="role_features")
    op.drop_index("idx_role_feature_unique", table_name="role_features")
    op.drop_table("role_features")
    op.drop_index(op.f("ix_prompt_usage_logs_use_case"), table_name="prompt_usage_logs")
    op.drop_index(
        op.f("ix_prompt_usage_logs_timestamp"), table_name="prompt_usage_logs"
    )
    op.drop_table("prompt_usage_logs")
    op.drop_index(op.f("ix_organizations_tier_id"), table_name="organizations")
    op.drop_index(
        op.f("ix_organizations_subscription_status"), table_name="organizations"
    )
    op.drop_index(op.f("ix_organizations_name"), table_name="organizations")
    op.drop_table("organizations")
    op.drop_index(op.f("ix_subscription_tiers_name"), table_name="subscription_tiers")
    op.drop_index(
        op.f("ix_subscription_tiers_is_active"), table_name="subscription_tiers"
    )
    op.drop_table("subscription_tiers")
    op.drop_index(op.f("ix_roles_name"), table_name="roles")
    op.drop_index(op.f("ix_roles_id"), table_name="roles")
    op.drop_table("roles")
    op.drop_index(op.f("ix_rbac_roles_name"), table_name="rbac_roles")
    op.drop_index(op.f("ix_rbac_roles_is_active"), table_name="rbac_roles")
    op.drop_table("rbac_roles")
    op.drop_index(op.f("ix_prompts_use_case"), table_name="prompts")
    op.drop_index(op.f("ix_prompts_name"), table_name="prompts")
    op.drop_index(op.f("ix_prompts_is_active"), table_name="prompts")
    op.drop_index(op.f("ix_prompts_category"), table_name="prompts")
    op.drop_table("prompts")
    op.drop_index(op.f("ix_prompt_templates_name"), table_name="prompt_templates")
    op.drop_index(op.f("ix_prompt_templates_category"), table_name="prompt_templates")
    op.drop_table("prompt_templates")
    op.drop_index(
        op.f("ix_permission_audit_log_user_id"), table_name="permission_audit_log"
    )
    op.drop_index(
        op.f("ix_permission_audit_log_timestamp"), table_name="permission_audit_log"
    )
    op.drop_index(
        op.f("ix_permission_audit_log_resource_type"), table_name="permission_audit_log"
    )
    op.drop_index(op.f("ix_permission_audit_log_id"), table_name="permission_audit_log")
    op.drop_index(
        op.f("ix_permission_audit_log_action"), table_name="permission_audit_log"
    )
    op.drop_index("idx_audit_user_action", table_name="permission_audit_log")
    op.drop_index("idx_audit_timestamp", table_name="permission_audit_log")
    op.drop_table("permission_audit_log")
    op.drop_index(op.f("ix_institutions_slug"), table_name="institutions")
    op.drop_index(op.f("ix_institutions_name"), table_name="institutions")
    op.drop_index(op.f("ix_institutions_is_active"), table_name="institutions")
    op.drop_index(op.f("ix_institutions_id"), table_name="institutions")
    op.drop_table("institutions")
    op.drop_index(op.f("ix_features_name"), table_name="features")
    op.drop_index(op.f("ix_features_is_active"), table_name="features")
    op.drop_table("features")
    op.drop_index(
        op.f("ix_email_suppression_list_id"), table_name="email_suppression_list"
    )
    op.drop_index(
        op.f("ix_email_suppression_list_email"), table_name="email_suppression_list"
    )
    op.drop_table("email_suppression_list")
    op.drop_index("ix_email_events_recipient_type", table_name="email_events")
    op.drop_index(op.f("ix_email_events_recipient_email"), table_name="email_events")
    op.drop_index("ix_email_events_provider_timestamp", table_name="email_events")
    op.drop_index(op.f("ix_email_events_id"), table_name="email_events")
    op.drop_index(op.f("ix_email_events_email_id"), table_name="email_events")
    op.drop_table("email_events")

    bind = op.get_bind()
    for enum in _ENUMS:
        enum.drop(bind, checkfirst=True)
