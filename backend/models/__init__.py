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
    QuestionSourceDocument,
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
from models.tag import Tag, QuestionTag
from models.tag_merge_log import TagMergeLog
from models.competency import CompetencyFramework, Competency
from models.grading_scheme import GradingScheme
from models.student import Student, StudentClass, StudentClassMembership
from models.org_unit import OrgUnit, UserOrgUnit
from models.submission import (
    Submission,
    Attempt,
    AttemptAnswer,
    Grade,
    GradeHistory,
    ImportJob,
    MoodleConnection,
)

__all__ = [
    "Document",
    "QuestionReview",
    "ReviewComment",
    "ReviewHistory",
    "ReviewStatus",
    "QuestionSourceDocument",
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
    # Tag Models
    "Tag",
    "QuestionTag",
    "TagMergeLog",
    # Competency frameworks (TF-400)
    "CompetencyFramework",
    "Competency",
    # Grading schemes (system + per-institution)
    "GradingScheme",
    # Student master data
    "Student",
    "StudentClass",
    "StudentClassMembership",
    # Org-Unit-Hierarchie (Abteilung/Team)
    "OrgUnit",
    "UserOrgUnit",
    # Submissions / grades / import
    "Submission",
    "Attempt",
    "AttemptAnswer",
    "Grade",
    "GradeHistory",
    "ImportJob",
    "MoodleConnection",
]
