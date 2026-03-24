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
    ResourceUsage,
    PermissionAuditLog,
)
from models.subscription import (
    Subscription,
    SubscriptionStatus,
)
from models.email_event import (
    EmailEvent,
    EmailSuppressionList,
    EmailEventType,
    EmailType,
)
from models.exam import Exam, ExamQuestion, ExamStatus

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
    "ResourceUsage",
    "PermissionAuditLog",
    "Subscription",
    "SubscriptionStatus",
    # Email Event Models
    "EmailEvent",
    "EmailSuppressionList",
    "EmailEventType",
    "EmailType",
    # Exam Composer Models
    "Exam",
    "ExamQuestion",
    "ExamStatus",
]
