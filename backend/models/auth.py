"""
Authentication Models für ExamCraft AI
User, Role, Institution Models für Multi-Tenant Authentication
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Table, Text, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import sys
import os

# Add parent directory to path to import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Base


# Enums
class UserRole(str, enum.Enum):
    """User Roles für RBAC (Python Enum für Type-Safety)"""
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


# Association Table für Many-to-Many Relationship zwischen User und Role
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('assigned_at', DateTime(timezone=True), server_default=func.now()),
    # assigned_by removed to avoid ambiguous foreign key paths
)


class Institution(Base):
    """
    Institution Model für Multi-Tenancy
    Repräsentiert Bildungseinrichtungen (Hochschulen, Schulen, etc.)
    """
    __tablename__ = "institutions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Institution Details
    name = Column(String(200), nullable=False, unique=True, index=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)  # URL-friendly identifier
    domain = Column(String(100), nullable=True, unique=True)  # Email domain für Auto-Assignment
    
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
    settings = Column(Text, nullable=True)  # JSON string für flexible Settings
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Subscription Info (für zukünftige Freemium Features)
    subscription_tier = Column(String(50), default="free", nullable=False)  # free, starter, professional, enterprise
    max_users = Column(Integer, default=5, nullable=False)
    max_documents = Column(Integer, default=100, nullable=False)
    max_questions_per_month = Column(Integer, default=500, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    users = relationship("User", back_populates="institution", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Institution(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class Role(Base):
    """
    Role Model für RBAC
    Definiert Berechtigungen und Zugriffslevel
    """
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Role Details
    name = Column(String(50), nullable=False, unique=True, index=True)  # admin, dozent, assistant, viewer
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Permissions (JSON string mit Liste von Permissions)
    permissions = Column(Text, nullable=False)  # JSON: ["create_questions", "review_questions", ...]
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_system_role = Column(Boolean, default=False, nullable=False)  # System Roles können nicht gelöscht werden
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")
    
    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}')>"


class User(Base):
    """
    User Model für Authentication
    Speichert Benutzerinformationen und Credentials
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Authentication
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=True)  # Nullable für OAuth-only Users
    
    # User Details
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    display_name = Column(String(200), nullable=True)  # Optional custom display name
    
    # Profile
    avatar_url = Column(String(1000), nullable=True)  # Increased for OAuth providers (Google URLs can be very long)
    bio = Column(Text, nullable=True)
    phone = Column(String(50), nullable=True)
    
    # Institution Association
    institution_id = Column(Integer, ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Status
    status = Column(String(20), default=UserStatus.PENDING.value, nullable=False, index=True)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)  # Platform-wide Admin
    
    # OAuth
    oauth_provider = Column(String(50), nullable=True)  # google, microsoft, etc.
    oauth_id = Column(String(255), nullable=True, unique=True, index=True)
    
    # Security
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)  # IPv6 support
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Password Reset
    password_reset_token = Column(String(255), nullable=True, unique=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Email Verification
    email_verification_token = Column(String(255), nullable=True, unique=True)
    email_verification_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Preferences (JSON)
    preferences = Column(Text, nullable=True)  # JSON string für User Preferences
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete
    
    # Relationships
    institution = relationship("Institution", back_populates="users")
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    oauth_accounts = relationship("OAuthAccount", back_populates="user", cascade="all, delete-orphan")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive', 'suspended', 'pending')",
            name='check_user_status'
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
        for role in self.roles:
            if role.permissions:
                # permissions is already a Python list (SQLAlchemy JSON type)
                perms = role.permissions if isinstance(role.permissions, list) else []
                if permission in perms:
                    return True
        return False


class UserSession(Base):
    """
    User Session Model für JWT Token Management
    Speichert aktive Sessions und ermöglicht Token Revocation
    """
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User Association
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
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
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, is_active={self.is_active})>"


class AuditLog(Base):
    """
    Audit Log Model für Security & GDPR Compliance
    Speichert alle sicherheitsrelevanten Aktionen
    """
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User Association
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Action Details
    action = Column(String(100), nullable=False, index=True)  # login, logout, create_question, etc.
    resource_type = Column(String(100), nullable=True, index=True)  # user, question, document, etc.
    resource_id = Column(String(100), nullable=True, index=True)
    
    # Request Details
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Additional Data (JSON)
    additional_data = Column(Text, nullable=True)  # JSON string mit zusätzlichen Informationen

    # Status
    status = Column(String(20), nullable=False)  # success, failure, error
    error_message = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', status='{self.status}')>"


class OAuthProvider(str, enum.Enum):
    """OAuth Provider Types"""
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    GITHUB = "github"  # Future support


class OAuthAccount(Base):
    """
    OAuth Account Model für Social Login
    Verknüpft User mit OAuth Provider Accounts (Google, Microsoft, etc.)
    """
    __tablename__ = "oauth_accounts"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # OAuth Provider Info
    provider = Column(String(20), nullable=False, index=True)  # google, microsoft, github
    provider_user_id = Column(String(255), nullable=False, index=True)  # OAuth Provider's User ID

    # OAuth Tokens (encrypted in production)
    access_token = Column(Text, nullable=True)  # OAuth Access Token (optional, for API calls)
    refresh_token = Column(Text, nullable=True)  # OAuth Refresh Token (optional)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)  # Token Expiration

    # User Profile from OAuth Provider
    email = Column(String(255), nullable=True)  # Email from OAuth Provider
    name = Column(String(255), nullable=True)  # Full Name from OAuth Provider
    picture = Column(String(1000), nullable=True)  # Profile Picture URL (increased for OAuth providers)

    # Metadata
    raw_user_info = Column(Text, nullable=True)  # JSON string of raw OAuth user info

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="oauth_accounts")

    # Constraints
    __table_args__ = (
        # Unique constraint: One OAuth account per provider per user
        CheckConstraint("provider IN ('google', 'microsoft', 'github')", name="valid_oauth_provider"),
    )

    def __repr__(self):
        return f"<OAuthAccount(id={self.id}, provider='{self.provider}', user_id={self.user_id})>"

