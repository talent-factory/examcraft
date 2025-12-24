"""
ExamCraft AI - Database Models (Core Package)

This package contains all SQLAlchemy ORM models for the Core application.
Premium features (Chat, Prompts) are available in the Premium package.
"""

from models.document import Document
from models.question_review import (
    QuestionReview,
    ReviewComment,
    ReviewHistory,
    ReviewStatus,
)
from models.auth import (
    User,
    Role,
    Institution,
    UserSession,
    AuditLog,
    UserRole,
    UserStatus,
    OAuthAccount,
    OAuthProvider,
)
from models.rbac import (
    Feature,
    RoleFeature,
    RBACRole,
    SubscriptionTier,
    TierQuota,
    TierFeature,
    Organization,
    ResourceUsage,
    PermissionAuditLog,
    PermissionAuditLog,
)
from models.subscription import (
    Subscription,
    SubscriptionStatus,
)

__all__ = [
    "Document",
    "QuestionReview",
    "ReviewComment",
    "ReviewHistory",
    "ReviewStatus",
    "User",
    "Role",
    "Institution",
    "UserSession",
    "AuditLog",
    "UserRole",
    "UserStatus",
    "OAuthAccount",
    "OAuthProvider",
    # RBAC Models
    "Feature",
    "RoleFeature",
    "RBACRole",
    "SubscriptionTier",
    "TierQuota",
    "TierFeature",
    "Organization",
    "ResourceUsage",
    "PermissionAuditLog",
    "Subscription",
    "SubscriptionStatus",
]
