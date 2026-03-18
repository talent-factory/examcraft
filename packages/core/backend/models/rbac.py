"""
RBAC (Role-Based Access Control) Models für ExamCraft AI
Erweiterte Models für dynamisches Permission-System, Feature-Gating und Ressourcen-Quotas
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    DECIMAL,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
import sys
import os

# Add parent directory to path to import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Base


# ============================================
# FEATURE-PERMISSIONS
# ============================================


class Feature(Base):
    """
    Feature Model für granulare Permission-Kontrolle
    Definiert einzelne Features/Funktionen der Applikation
    """

    __tablename__ = "features"

    id = Column(String(255), primary_key=True)  # feat_question_gen_ai
    name = Column(
        String(100), nullable=False, unique=True, index=True
    )  # question_generation_ai
    display_name = Column(String(200), nullable=False)  # "KI-Prüfung erstellen"
    description = Column(Text, nullable=True)
    category = Column(
        String(50), nullable=True
    )  # generation, management, administration, integration
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    role_features = relationship(
        "RoleFeature", back_populates="feature", cascade="all, delete-orphan"
    )
    tier_features = relationship(
        "TierFeature", back_populates="feature", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("name ~ '^[a-z0-9_]+$'", name="check_feature_name_format"),
    )

    def __repr__(self):
        return f"<Feature(id='{self.id}', name='{self.name}')>"


class RoleFeature(Base):
    """
    Many-to-Many Mapping zwischen Roles und Features
    Definiert welche Features eine Rolle nutzen darf
    """

    __tablename__ = "role_features"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(
        String(255),
        ForeignKey("rbac_roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature_id = Column(
        String(255),
        ForeignKey("features.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    role = relationship("RBACRole", back_populates="role_features")
    feature = relationship("Feature", back_populates="role_features")

    # Constraints
    __table_args__ = (
        Index("idx_role_feature_unique", "role_id", "feature_id", unique=True),
    )

    def __repr__(self):
        return (
            f"<RoleFeature(role_id='{self.role_id}', feature_id='{self.feature_id}')>"
        )


# ============================================
# DYNAMIC ROLES (erweitert bestehende Role-Tabelle)
# ============================================


class RBACRole(Base):
    """
    Erweiterte Role-Tabelle für dynamisches RBAC
    Separate Tabelle um bestehende 'roles' nicht zu brechen
    """

    __tablename__ = "rbac_roles"

    id = Column(
        String(255), primary_key=True
    )  # role_admin, role_dozent, role_custom_xyz
    name = Column(
        String(100), nullable=False, unique=True, index=True
    )  # admin, dozent, custom_xyz
    display_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_system_role = Column(
        Boolean, default=False, nullable=False
    )  # System-Rollen können nicht gelöscht werden
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by = Column(String(255), nullable=True)  # User ID des Erstellers

    # Relationships
    role_features = relationship(
        "RoleFeature", back_populates="role", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("name ~ '^[a-z0-9_]+$'", name="check_rbac_role_name_format"),
    )

    def __repr__(self):
        return f"<RBACRole(id='{self.id}', name='{self.name}')>"


# ============================================
# SUBSCRIPTION TIERS & QUOTAS
# ============================================


class SubscriptionTier(Base):
    """
    Subscription Tier Model für Monetarisierung
    Definiert verschiedene Pricing-Tiers (Free, Starter, Professional, Enterprise)
    """

    __tablename__ = "subscription_tiers"

    id = Column(
        String(255), primary_key=True
    )  # tier_free, tier_starter, tier_professional, tier_enterprise
    name = Column(
        String(50), nullable=False, unique=True, index=True
    )  # free, starter, professional, enterprise
    display_name = Column(
        String(100), nullable=False
    )  # "Free", "Starter", "Professional", "Enterprise"
    description = Column(Text, nullable=True)
    price_monthly = Column(DECIMAL(10, 2), nullable=True)  # 0.00, 19.00, 49.00, 149.00
    price_yearly = Column(
        DECIMAL(10, 2), nullable=True
    )  # 0.00, 190.00, 490.00, 1490.00
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    sort_order = Column(Integer, default=0, nullable=False)  # Für Sortierung in UI
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    tier_quotas = relationship(
        "TierQuota", back_populates="tier", cascade="all, delete-orphan"
    )
    tier_features = relationship(
        "TierFeature", back_populates="tier", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<SubscriptionTier(id='{self.id}', name='{self.name}')>"


class TierQuota(Base):
    """
    Ressourcen-Quotas pro Subscription Tier
    Definiert Limits für Dokumente, Fragen, User, Storage, etc.
    """

    __tablename__ = "tier_quotas"

    id = Column(Integer, primary_key=True, index=True)
    tier_id = Column(
        String(255),
        ForeignKey("subscription_tiers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resource_type = Column(
        String(100), nullable=False, index=True
    )  # documents, questions_per_month, users, storage_mb
    quota_limit = Column(Integer, nullable=False)  # -1 = unlimited
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    tier = relationship("SubscriptionTier", back_populates="tier_quotas")

    # Constraints
    __table_args__ = (
        Index("idx_tier_quota_unique", "tier_id", "resource_type", unique=True),
    )

    def __repr__(self):
        return f"<TierQuota(tier_id='{self.tier_id}', resource_type='{self.resource_type}', limit={self.quota_limit})>"


class TierFeature(Base):
    """
    Many-to-Many Mapping zwischen Subscription Tiers und Features
    Definiert welche Features in welchem Tier verfügbar sind
    """

    __tablename__ = "tier_features"

    id = Column(Integer, primary_key=True, index=True)
    tier_id = Column(
        String(255),
        ForeignKey("subscription_tiers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature_id = Column(
        String(255),
        ForeignKey("features.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    tier = relationship("SubscriptionTier", back_populates="tier_features")
    feature = relationship("Feature", back_populates="tier_features")

    # Constraints
    __table_args__ = (
        Index("idx_tier_feature_unique", "tier_id", "feature_id", unique=True),
    )

    def __repr__(self):
        return (
            f"<TierFeature(tier_id='{self.tier_id}', feature_id='{self.feature_id}')>"
        )


class ResourceUsage(Base):
    """
    Ressourcen-Nutzungs-Tracking pro Institution
    Trackt monatliche Nutzung von Dokumenten, Fragen, etc.
    """

    __tablename__ = "resource_usage"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resource_type = Column(
        String(100), nullable=False, index=True
    )  # documents, questions_per_month, storage_mb
    usage_count = Column(Integer, default=0, nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    institution = relationship("Institution", back_populates="resource_usage")

    # Constraints
    __table_args__ = (
        Index(
            "idx_resource_usage_unique",
            "institution_id",
            "resource_type",
            "period_start",
            unique=True,
        ),
    )

    def __repr__(self):
        return f"<ResourceUsage(institution='{self.institution_id}', type='{self.resource_type}', count={self.usage_count})>"


# ============================================
# AUDIT TRAIL
# ============================================


class PermissionAuditLog(Base):
    """
    Audit Log für Permission-Checks und RBAC-Aktionen
    Compliance-konform (GDPR, SOC2)
    """

    __tablename__ = "permission_audit_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    action = Column(
        String(100), nullable=False, index=True
    )  # access_granted, access_denied, role_changed, feature_accessed
    resource_type = Column(
        String(100), nullable=True, index=True
    )  # feature, role, organization
    resource_id = Column(String(255), nullable=True)
    details = Column(JSONB, nullable=True)  # Zusätzliche Details als JSON
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Indexes für Performance
    __table_args__ = (
        Index("idx_audit_user_action", "user_id", "action"),
        Index("idx_audit_timestamp", "timestamp"),
    )

    def __repr__(self):
        return f"<PermissionAuditLog(user='{self.user_id}', action='{self.action}', timestamp={self.timestamp})>"
