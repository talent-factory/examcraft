"""
Authentication Models for ExamCraft AI
User, Role, Institution models for multi-tenant authentication
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Table,
    Text,
    CheckConstraint,
    Index,
    ARRAY,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text
from datetime import datetime, timezone
import enum
import sys
import os

# Add parent directory to path to import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Base


SUPPORTED_LANGUAGES = ("de", "en", "fr", "it")


# Enums
class UserRole(str, enum.Enum):
    """User roles for RBAC (Python Enum for type safety)"""

    ADMIN = "admin"
    DOZENT = "dozent"
    ASSISTANT = "assistant"
    VIEWER = "viewer"


class UserStatus(str, enum.Enum):
    """User Account Status"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


# Association table for many-to-many relationship between User and Role
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("assigned_at", DateTime(timezone=True), server_default=func.now()),
    # assigned_by removed to avoid ambiguous foreign key paths
)


class Institution(Base):
    """
    Institution model for multi-tenancy
    Represents educational institutions (universities, schools, etc.)
    """

    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, index=True)

    # Institution Details
    name = Column(String(200), nullable=False, unique=True, index=True)
    slug = Column(
        String(100), nullable=False, unique=True, index=True
    )  # URL-friendly identifier
    domain = Column(
        String(100), nullable=True, unique=True
    )  # Email domain for auto-assignment

    # Contact Information
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)

    # Address
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)

    # Settings (JSON)
    settings = Column(Text, nullable=True)  # JSON string for flexible settings

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # TF-410: marks the single platform-wide "system" institution that owns
    # system-visible prompts (and other global seed data). Exactly one row may
    # have ``is_system = true`` — enforced by a partial unique index in the
    # migration. Replaces the old "lowest id" seed convention.
    is_system = Column(Boolean, default=False, nullable=False, index=True)

    # Subscription Info (TF-116 monetization strategy)
    subscription_tier = Column(
        String(50), default="free", nullable=False
    )  # free, starter, professional, enterprise
    features_enabled = Column(
        ARRAY(String), nullable=True
    )  # Optional: Manual feature overrides

    # Quotas (based on subscription_tier, see backend/config/features.py)
    max_users = Column(Integer, default=1, nullable=False)
    max_documents = Column(Integer, default=5, nullable=False)
    max_questions_per_month = Column(Integer, default=20, nullable=False)

    # Review workflow
    require_second_reviewer = Column(Boolean, default=False)

    # Institution-wide default grading scheme (FK; per-exam overrides
    # via Exam.grading_scheme_id). NULL means "use the platform's
    # built-in defaults".
    default_grading_scheme_id = Column(
        Integer,
        # ON DELETE RESTRICT for the same reason as Exam.grading_scheme_id
        # — silently nulling an institution's default scheme is a data-
        # loss surprise. The API's DELETE endpoint pre-checks this so
        # the user gets a friendly 409, not a 500 from a raw constraint
        # violation.
        ForeignKey("grading_schemes.id", ondelete="RESTRICT"),
        nullable=True,
    )

    # TF-336: Enterprise tier can choose the Claude model per institution
    # ("claude-sonnet-4-..." or "claude-opus-4-..."). NULL =
    # platform default (Sonnet). Value validation happens service-side
    # (e.g. claude_service.py); the DB holds the string raw so a
    # model update never requires a schema migration.
    llm_model_for_grading = Column(String(100), nullable=True)

    # Timestamps
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
    users = relationship(
        "User", back_populates="institution", cascade="all, delete-orphan"
    )
    subscriptions = relationship(
        "Subscription", back_populates="institution", cascade="all, delete-orphan"
    )
    resource_usage = relationship(
        "ResourceUsage", back_populates="institution", cascade="all, delete-orphan"
    )
    students = relationship(
        "Student", back_populates="institution", cascade="all, delete-orphan"
    )
    student_classes = relationship(
        "StudentClass", back_populates="institution", cascade="all, delete-orphan"
    )
    grading_schemes = relationship(
        "GradingScheme",
        back_populates="institution",
        cascade="all, delete-orphan",
        foreign_keys="GradingScheme.institution_id",
    )
    default_grading_scheme = relationship(
        "GradingScheme", foreign_keys=[default_grading_scheme_id]
    )
    import_jobs = relationship(
        "ImportJob", back_populates="institution", cascade="all, delete-orphan"
    )
    moodle_connection = relationship(
        "MoodleConnection",
        back_populates="institution",
        cascade="all, delete-orphan",
        uselist=False,
    )
    org_units = relationship(
        "OrgUnit", back_populates="institution", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Institution(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class Role(Base):
    """
    Role model for RBAC
    Defines permissions and access levels
    """

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)

    # Role Details
    name = Column(
        String(50), nullable=False, unique=True, index=True
    )  # admin, dozent, assistant, viewer
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Permissions (JSON string with list of permissions)
    permissions = Column(
        Text, nullable=False
    )  # JSON: ["create_questions", "review_questions", ...]

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_system_role = Column(
        Boolean, default=False, nullable=False
    )  # System roles cannot be deleted

    # Timestamps
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
    users = relationship("User", secondary=user_roles, back_populates="roles")

    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}')>"


class User(Base):
    """
    User model for authentication
    Stores user information and credentials
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Authentication
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth-only users

    # User Details
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    display_name = Column(String(200), nullable=True)  # Optional custom display name

    # Profile
    avatar_url = Column(
        String(2000), nullable=True
    )  # Increased for OAuth providers (Google URLs can be very long - up to 2000 chars)
    bio = Column(Text, nullable=True)
    phone = Column(String(50), nullable=True)

    # Institution Association
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Status
    status = Column(
        String(20), default=UserStatus.PENDING.value, nullable=False, index=True
    )
    is_email_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)  # Platform-wide Admin

    # OAuth
    oauth_provider = Column(String(50), nullable=True)  # google, microsoft, etc.
    oauth_id = Column(String(255), nullable=True, unique=True, index=True)

    # Security
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)  # IPv6 support
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    last_failed_login = Column(DateTime(timezone=True), nullable=True)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    # Password Reset
    password_reset_token = Column(String(255), nullable=True, unique=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)

    # Email Verification
    email_verification_token = Column(String(255), nullable=True, unique=True)
    email_verification_expires = Column(DateTime(timezone=True), nullable=True)

    # Audit Tracking
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    registration_method = Column(
        String(20), nullable=True
    )  # password, google, microsoft

    # Preferences (JSON)
    preferences = Column(Text, nullable=True)  # JSON string for user preferences

    # Language Preference (i18n)
    preferred_language = Column(String(5), nullable=True, default=None)

    # GDPR Compliance
    deletion_requested_at = Column(
        DateTime(timezone=True), nullable=True
    )  # When user requested deletion
    scheduled_deletion_date = Column(
        DateTime(timezone=True), nullable=True
    )  # When account will be deleted

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete

    # Relationships
    institution = relationship("Institution", back_populates="users")
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    sessions = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs = relationship(
        "AuditLog",
        back_populates="user",
        # TF-745: KEIN cascade="all, delete-orphan" — die DB-FK ist
        # ondelete="SET NULL" (AuditLog.user_id soll bei User-Löschung
        # anonymisiert werden, nicht die Zeile gelöscht werden).
        # passive_deletes=True lässt die DB die FK-Aktion ausführen, statt
        # dass der ORM vorher selbst löscht.
        passive_deletes=True,
        foreign_keys="AuditLog.user_id",
    )
    oauth_accounts = relationship(
        "OAuthAccount", back_populates="user", cascade="all, delete-orphan"
    )
    org_unit_memberships = relationship(
        "UserOrgUnit", back_populates="user", cascade="all, delete-orphan"
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive', 'suspended', 'pending')",
            name="check_user_status",
        ),
        CheckConstraint(
            "preferred_language IN ('de', 'en', 'fr', 'it') OR preferred_language IS NULL",
            name="ck_user_preferred_language",
        ),
    )

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', status='{self.status}')>"

    @property
    def full_name(self):
        """Returns full name of user"""
        return f"{self.first_name} {self.last_name}"

    def has_role(self, role_name: str) -> bool:
        """Check if user has specific role"""
        return any(role.name == role_name for role in self.roles)

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        # Superuser has all permissions
        if self.is_superuser:
            return True

        from utils.permissions import parse_role_permissions

        for role in self.roles:
            # TF-637 review fix: is_active is now checked here too, not only
            # on the Granted Role loop below -- before this fix, Role.is_active
            # was defined on the model but never consulted anywhere, so
            # deactivating a role only partially revoked it (Org-Unit-granted
            # instances stopped working, direct assignments didn't).
            if (
                role.is_active
                and role.permissions
                and permission in parse_role_permissions(role.permissions)
            ):
                return True

        # Granted Role (TF-637): a permission is also inherited from the
        # Role that an OrgUnit grants to its *direct* members. Additive to
        # the loop above, and deliberately NOT cascaded through the
        # composite hierarchy the way Access Scope
        # (get_user_accessible_org_unit_ids) is -- see
        # docs/adr/0003-granted-role-not-cascading.md.
        for membership in self.org_unit_memberships:
            granted_role = membership.org_unit.role
            if (
                granted_role
                and granted_role.is_active
                and granted_role.permissions
                and permission in parse_role_permissions(granted_role.permissions)
            ):
                return True

        return False


class UserSession(Base):
    """
    User Session model for JWT token management
    Stores active sessions and enables token revocation
    """

    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # User Association
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Session Details
    token_jti = Column(String(255), nullable=False, unique=True, index=True)  # JWT ID
    refresh_token_jti = Column(String(255), nullable=True, unique=True, index=True)

    # Device/Client Info
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)
    device_type = Column(String(50), nullable=True)  # web, mobile, desktop

    # Session Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_activity_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, is_active={self.is_active})>"


class AuditLog(Base):
    """
    Audit Log model for security & GDPR compliance
    Stores all security-relevant actions
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # User Association
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # TF-740: set when this action happened while an admin was impersonating
    # user_id (see ImpersonationSession). user_id stays the target user so
    # institution-scoping (join on User.institution_id) is unaffected;
    # impersonator_user_id records who actually performed the action.
    # Not yet populated by this PR — auto-filled by AuditService.log_action
    # from a context-local value set during impersonated requests, see TF-742.
    impersonator_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Action Details
    action = Column(
        String(100), nullable=False, index=True
    )  # login, logout, create_question, etc.
    resource_type = Column(
        String(100), nullable=True, index=True
    )  # user, question, document, etc.
    resource_id = Column(String(100), nullable=True, index=True)

    # Request Details
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Additional Data (JSON)
    additional_data = Column(
        Text, nullable=True
    )  # JSON string with additional information

    # Status
    status = Column(String(20), nullable=False)  # success, failure, error
    error_message = Column(Text, nullable=True)

    # Timestamp
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    user = relationship("User", back_populates="audit_logs", foreign_keys=[user_id])
    impersonator = relationship("User", foreign_keys=[impersonator_user_id])

    def __repr__(self):
        return (
            f"<AuditLog(id={self.id}, action='{self.action}', status='{self.status}')>"
        )


# TF-740: the closed set of valid ImpersonationSession.end_reason values.
# "manual" = admin explicitly returned; "timeout" = the hard 30-minute
# session timeout enforced by the auth layer (see TF-741). Reused by the
# CHECK constraint below and by ImpersonationSession.end() so the two
# cannot drift apart.
IMPERSONATION_END_REASONS = ("manual", "timeout")


class ImpersonationSession(Base):
    """
    Impersonation session model (TF-740, part of the TF-739 epic).

    Tracks each "switch user" session an admin (holding the opt-in
    ``users:impersonate`` permission) starts against a target user. One row
    per session, from start (``started_at``) to either a manual return
    (``end_reason="manual"``) or the hard 30-minute timeout enforced by the
    auth layer (``end_reason="timeout"``, see TF-741). A session with
    ``ended_at is None`` is still active; use ``end()`` to transition it.

    ``admin_user_id``/``target_user_id`` are nullable despite always being
    set at creation: ``ondelete="SET NULL"`` needs somewhere to null the FK
    to when a referenced user is later deleted (e.g. GDPR erasure, see
    api/gdpr.py) — the row survives with a NULL actor/target instead of
    blocking the delete. A CHECK constraint still requires the two to differ
    whenever both are set (no self-impersonation), and a partial-unique
    index (migration-only, not expressible in the ORM layer) allows at most
    one *active* (``ended_at IS NULL``) session per admin at a time — no
    nested impersonation, per the TF-739 epic's scope rules.
    """

    __tablename__ = "impersonation_sessions"

    id = Column(Integer, primary_key=True, index=True)

    admin_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    target_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    reason = Column(Text, nullable=False)

    started_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at = Column(DateTime(timezone=True), nullable=True)
    end_reason = Column(String(20), nullable=True)  # see IMPERSONATION_END_REASONS

    __table_args__ = (
        CheckConstraint(
            "end_reason IN ('manual', 'timeout') OR end_reason IS NULL",
            name="ck_impersonation_sessions_end_reason",
        ),
        # NULL-safe on purpose: once either FK is nulled out by a user
        # deletion, this comparison evaluates to NULL (not FALSE) and the
        # constraint passes — it only guards against admin == target while
        # both are still set.
        CheckConstraint(
            "admin_user_id <> target_user_id",
            name="ck_impersonation_sessions_admin_target_distinct",
        ),
        CheckConstraint(
            "(ended_at IS NULL) = (end_reason IS NULL)",
            name="ck_impersonation_sessions_end_pairing",
        ),
        # TF-739: an admin can't nest a second impersonation while one is
        # already active — enforced at the DB level via a partial unique
        # index over "still-active" rows (ended_at IS NULL). Declared here
        # (not just in the migration) so it also applies to Base.metadata
        # .create_all()-built schemas, e.g. in tests.
        Index(
            "ix_impersonation_sessions_one_active_per_admin",
            "admin_user_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
    )

    # Relationships
    admin_user = relationship("User", foreign_keys=[admin_user_id])
    target_user = relationship("User", foreign_keys=[target_user_id])

    def end(self, reason: str) -> None:
        """Mark this session as ended, setting ``ended_at``/``end_reason``
        together so the pairing invariant enforced by the CHECK constraint
        above can never be violated from here.

        Raises ``ValueError`` if the session is already ended or ``reason``
        isn't one of ``IMPERSONATION_END_REASONS``.
        """
        if self.ended_at is not None:
            raise ValueError(
                f"ImpersonationSession {self.id} is already ended "
                f"(end_reason={self.end_reason!r})"
            )
        if reason not in IMPERSONATION_END_REASONS:
            raise ValueError(
                f"invalid end_reason {reason!r}, expected one of "
                f"{IMPERSONATION_END_REASONS}"
            )
        self.ended_at = datetime.now(timezone.utc)
        self.end_reason = reason

    def __repr__(self):
        return (
            f"<ImpersonationSession(id={self.id}, admin_user_id={self.admin_user_id}, "
            f"target_user_id={self.target_user_id})>"
        )


class OAuthProvider(str, enum.Enum):
    """OAuth Provider Types"""

    GOOGLE = "google"
    MICROSOFT = "microsoft"
    GITHUB = "github"  # Future support


class OAuthAccount(Base):
    """
    OAuth Account model for social login
    Links a user to OAuth provider accounts (Google, Microsoft, etc.)
    """

    __tablename__ = "oauth_accounts"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # OAuth Provider Info
    provider = Column(
        String(20), nullable=False, index=True
    )  # google, microsoft, github
    provider_user_id = Column(
        String(255), nullable=False, index=True
    )  # OAuth Provider's User ID

    # OAuth Tokens (encrypted in production)
    access_token = Column(
        Text, nullable=True
    )  # OAuth Access Token (optional, for API calls)
    refresh_token = Column(Text, nullable=True)  # OAuth Refresh Token (optional)
    token_expires_at = Column(
        DateTime(timezone=True), nullable=True
    )  # Token Expiration

    # User Profile from OAuth Provider
    email = Column(String(255), nullable=True)  # Email from OAuth Provider
    name = Column(String(255), nullable=True)  # Full Name from OAuth Provider
    picture = Column(
        Text, nullable=True
    )  # Profile Picture URL (TEXT for very long OAuth URLs)

    # Metadata
    raw_user_info = Column(Text, nullable=True)  # JSON string of raw OAuth user info

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="oauth_accounts")

    # Constraints
    __table_args__ = (
        # Unique constraint: One OAuth account per provider per user
        CheckConstraint(
            "provider IN ('google', 'microsoft', 'github')", name="valid_oauth_provider"
        ),
    )

    def __repr__(self):
        return f"<OAuthAccount(id={self.id}, provider='{self.provider}', user_id={self.user_id})>"


class EmailVerificationToken(Base):
    """
    Email Verification Tokens
    Stores tokens for email verification with expiration
    """

    __tablename__ = "email_verification_tokens"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # User Reference
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Token
    token = Column(String(255), unique=True, nullable=False, index=True)

    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Status
    is_used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user = relationship("User", backref="verification_tokens")

    def __repr__(self):
        return f"<EmailVerificationToken(id={self.id}, user_id={self.user_id}, is_used={self.is_used})>"
