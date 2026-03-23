"""
Authentication API Endpoints
Login, Logout, Register, Profile, Password Reset
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
import logging
import os
import re
import json
import secrets

from database import get_db
from models.auth import User, Role, Institution, UserStatus, UserRole
from services.auth_service import AuthService
from services.avatar_service import AvatarService
from services.audit_service import AuditService
from services.oauth_service import OAuthService
from services.redis_service import RedisService
from services.translation_service import t, get_request_locale
from utils.auth_utils import get_current_user, get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()


# ============================================================================
# Pydantic Models (Request/Response Schemas)
# ============================================================================


class RegisterRequest(BaseModel):
    """User registration request"""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    institution_slug: Optional[str] = None  # Optional: join existing institution

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class LoginRequest(BaseModel):
    """User login request"""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""

    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Password reset request"""

    email: EmailStr


def _validate_password_strength(v: str) -> str:
    """Shared password strength validator."""
    if not re.search(r"[A-Z]", v):
        raise ValueError("Passwort muss mindestens einen Grossbuchstaben enthalten")
    if not re.search(r"[a-z]", v):
        raise ValueError("Passwort muss mindestens einen Kleinbuchstaben enthalten")
    if not re.search(r"\d", v):
        raise ValueError("Passwort muss mindestens eine Zahl enthalten")
    return v


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation"""

    token: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class SetPasswordRequest(BaseModel):
    """Set password for OAuth-only users"""

    password: str = Field(..., min_length=8, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class PasswordChangeRequest(BaseModel):
    """Password change request (authenticated user)"""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class RoleResponse(BaseModel):
    """Role response"""

    id: int
    name: str
    display_name: str
    description: Optional[str]
    permissions: list[str]
    is_system_role: bool
    created_at: str

    class Config:
        from_attributes = True


class UserProfileResponse(BaseModel):
    """User profile response"""

    id: int
    email: str
    first_name: str
    last_name: str
    status: str
    is_superuser: bool
    is_email_verified: bool  # Email verification status
    institution_id: Optional[int]
    institution_name: Optional[str]
    oauth_provider: Optional[str] = None  # OAuth provider (google, microsoft, etc.)
    avatar_url: Optional[str] = None  # Profile picture URL (from OAuth or uploaded)
    preferred_language: Optional[str] = None
    roles: list[RoleResponse]
    created_at: str

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    """User profile update request"""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = None
    preferred_language: Optional[str] = Field(None, pattern="^(de|en|fr|it)$")


# ============================================================================
# API Endpoints
# ============================================================================


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    request: RegisterRequest, http_request: Request, db: Session = Depends(get_db)
):
    """
    Register a new user

    - Creates new user account
    - Assigns default 'viewer' role
    - Returns JWT tokens
    """
    locale = get_request_locale(http_request)
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("auth_email_taken", locale=locale),
        )

    # Get or create institution
    institution = None
    if request.institution_slug:
        # Explicit institution slug provided
        institution = (
            db.query(Institution)
            .filter(Institution.slug == request.institution_slug)
            .first()
        )
        if not institution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=t("auth_institution_not_found", locale=locale),
            )
    else:
        # Try to find institution by email domain (Auto-Assignment)
        email_domain = request.email.split("@")[1]
        institution = (
            db.query(Institution).filter(Institution.domain == email_domain).first()
        )

        # If no domain match, create or find personal institution
        if not institution:
            personal_slug = f"{request.email.split('@')[0]}-personal"

            # Check if personal institution already exists
            institution = (
                db.query(Institution).filter(Institution.slug == personal_slug).first()
            )

            # Create new personal institution if it doesn't exist
            if not institution:
                institution = Institution(
                    name=f"{request.first_name} {request.last_name}",
                    slug=personal_slug,
                    domain=None,  # No domain for personal institutions
                    subscription_tier="free",
                    max_users=1,
                    max_documents=10,
                    max_questions_per_month=50,
                )
                db.add(institution)
                db.flush()  # Get institution.id

    # Create user (email not verified yet)
    user = User(
        email=request.email,
        password_hash=AuthService.get_password_hash(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        institution_id=institution.id,
        status=UserStatus.PENDING.value,  # Pending until email verified
        is_email_verified=False,
        is_superuser=False,
        registration_method="password",
        password_changed_at=func.now(),
    )
    db.add(user)
    db.flush()  # Get user.id

    # Assign default 'viewer' role
    viewer_role = db.query(Role).filter(Role.name == UserRole.VIEWER.value).first()
    if not viewer_role:
        # Create default viewer role if it doesn't exist
        viewer_role = Role(
            name=UserRole.VIEWER.value,
            display_name="Viewer",
            description="Can view questions and exams, upload and manage documents",
            permissions=[
                "view_questions",
                "view_exams",
                "documents:read",
                "create_documents",
                "delete_documents",
            ],
            is_system_role=True,
        )
        db.add(viewer_role)
        db.flush()

    user.roles.append(viewer_role)

    # Generate verification token
    from services.email_service import EmailService
    from models.auth import EmailVerificationToken
    from datetime import datetime, timedelta, timezone

    verification_token = EmailService.generate_verification_token()
    token_expires = datetime.now(timezone.utc) + timedelta(hours=24)

    # Store verification token
    email_token = EmailVerificationToken(
        user_id=user.id,
        token=verification_token,
        expires_at=token_expires,
        is_used=False,
    )
    db.add(email_token)
    db.commit()
    db.refresh(user)

    # Audit log: User registration
    AuditService.log_register(db, user.id, user.email, request=http_request)

    # Send verification email (async via background task)
    try:
        EmailService.send_verification_email(
            email=user.email,
            first_name=user.first_name,
            verification_token=verification_token,
        )
        logger.info(f"Verification email sent to {user.email}")
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
        # Don't fail registration if email fails

    # Create tokens (user can login but features limited until verified)
    tokens = AuthService.create_tokens_for_user(
        user,
        db,
        user_agent=http_request.headers.get("user-agent"),
        ip_address=http_request.client.host if http_request.client else None,
    )

    logger.info(
        f"New user registered: {user.email} (ID: {user.id}) - Verification email sent"
    )

    return tokens


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest, http_request: Request, db: Session = Depends(get_db)
):
    """
    Login with email and password

    - Validates credentials
    - Returns JWT tokens
    - Creates session record
    """
    locale = get_request_locale(http_request)
    # Get user by email
    user = db.query(User).filter(User.email == request.email).first()

    from services.audit_service import AuditService

    if not user:
        # Audit log: Failed login (user not found)
        AuditService.log_login(
            db,
            None,
            success=False,
            request=http_request,
            error_message="User not found",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=t("auth_invalid_credentials", locale=locale),
        )

    # Account lockout check
    MAX_FAILED_ATTEMPTS = 10
    LOCKOUT_DURATION_SECONDS = 30 * 60  # 30 minutes

    if (user.failed_login_attempts or 0) >= MAX_FAILED_ATTEMPTS:
        if (
            user.last_failed_login is None
            or (datetime.now(timezone.utc) - user.last_failed_login).total_seconds()
            < LOCKOUT_DURATION_SECONDS
        ):
            # Still locked (or timestamp missing from migration — treat as locked for safety)
            AuditService.log_login(
                db,
                user.id,
                success=False,
                request=http_request,
                error_message="Account locked due to too many failed attempts",
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=t("auth_account_locked", locale=locale),
            )
        else:
            # Lockout period expired, reset counter
            user.failed_login_attempts = 0
            try:
                db.commit()
            except Exception as commit_err:
                logger.error(
                    f"Failed to reset lockout counter for user {user.id}: {commit_err}",
                    exc_info=True,
                )
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=t("auth_login_service_unavailable", locale=locale),
                )

    # Verify password
    if not AuthService.verify_password(request.password, user.password_hash):
        # Increment failed login attempts
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        user.last_failed_login = datetime.now(timezone.utc)
        try:
            db.commit()
        except Exception as commit_err:
            logger.error(
                f"Failed to persist login attempt counter for user {user.id}: {commit_err}"
            )
            db.rollback()

        # Audit log: Failed login (wrong password)
        AuditService.log_login(
            db,
            user.id,
            success=False,
            request=http_request,
            error_message="Incorrect password",
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=t("auth_invalid_credentials", locale=locale),
        )

    # Check if user is active
    if user.status != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=t("auth_account_disabled", locale=locale),
        )

    # Reset failed login attempts
    user.failed_login_attempts = 0
    user.last_failed_login = None
    # Track login
    user.last_login_at = func.now()
    user.last_login_ip = http_request.client.host if http_request.client else None
    db.commit()

    # Audit log: Successful login
    AuditService.log_login(db, user.id, success=True, request=http_request)

    # Create tokens
    tokens = AuthService.create_tokens_for_user(
        user,
        db,
        user_agent=http_request.headers.get("user-agent"),
        ip_address=http_request.client.host if http_request.client else None,
    )

    logger.info(f"User logged in: {user.email} (ID: {user.id})")

    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest, http_request: Request, db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token

    - Validates refresh token
    - Returns new access token
    """
    tokens = AuthService.refresh_access_token(
        request.refresh_token,
        db,
        user_agent=http_request.headers.get("user-agent"),
        ip_address=http_request.client.host if http_request.client else None,
    )

    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=t("auth_token_invalid", locale=get_request_locale(http_request)),
        )

    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Logout current user

    - Revokes all active sessions
    - Invalidates all tokens
    """
    count = AuthService.revoke_all_user_sessions(current_user.id, db)

    # Audit log: User logout
    from services.audit_service import AuditService

    AuditService.log_logout(db, current_user.id, request=http_request)

    logger.info(f"User logged out: {current_user.email} (revoked {count} sessions)")

    return None


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
):
    """
    Get current user profile

    - Returns user information
    - Includes institution and roles with permissions
    """

    # Build role responses with parsed permissions
    role_responses = []
    for role in current_user.roles:
        # Parse permissions from JSON string if needed
        permissions = role.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except json.JSONDecodeError:
                permissions = []
        elif not isinstance(permissions, list):
            permissions = []

        role_responses.append(
            RoleResponse(
                id=role.id,
                name=role.name,
                display_name=role.display_name,
                description=role.description,
                permissions=permissions,
                is_system_role=role.is_system_role,
                created_at=role.created_at.isoformat(),
            )
        )

    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        status=current_user.status,
        is_superuser=current_user.is_superuser,
        is_email_verified=current_user.is_email_verified,
        institution_id=current_user.institution_id,
        institution_name=current_user.institution.name
        if current_user.institution
        else None,
        oauth_provider=current_user.oauth_provider,
        avatar_url=current_user.avatar_url,
        preferred_language=current_user.preferred_language,
        roles=role_responses,
        created_at=current_user.created_at.isoformat(),
    )


@router.patch("/me", response_model=UserProfileResponse)
async def update_current_user_profile(
    request: UserProfileUpdate,
    http_request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update current user profile

    - Updates user information
    - Returns updated profile
    """
    changed_fields = list(request.model_dump(exclude_unset=True).keys())

    if request.first_name is not None:
        current_user.first_name = request.first_name

    if request.last_name is not None:
        current_user.last_name = request.last_name

    if request.bio is not None:
        current_user.bio = request.bio

    if request.avatar_url is not None:
        current_user.avatar_url = request.avatar_url

    if request.preferred_language is not None:
        current_user.preferred_language = request.preferred_language

    db.commit()
    db.refresh(current_user)

    # Audit log for profile update (only if fields actually changed)
    if changed_fields:
        try:
            AuditService.log_action(
                db=db,
                action=AuditService.ACTION_UPDATE_USER,
                user_id=current_user.id,
                resource_type=AuditService.RESOURCE_USER,
                resource_id=str(current_user.id),
                additional_data={"changed_fields": changed_fields},
                request=http_request,
            )
        except Exception as e:
            logger.error(
                f"Failed to create audit log for profile update of user {current_user.id}: {e}"
            )
            db.refresh(current_user)  # Re-sync after potential rollback in AuditService

    logger.info(f"User profile updated: {current_user.email} (ID: {current_user.id})")

    # Build role responses with parsed permissions
    role_responses = []
    for role in current_user.roles:
        # Parse permissions from JSON string if needed
        permissions = role.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except json.JSONDecodeError:
                permissions = []
        elif not isinstance(permissions, list):
            permissions = []

        role_responses.append(
            RoleResponse(
                id=role.id,
                name=role.name,
                display_name=role.display_name,
                description=role.description,
                permissions=permissions,
                is_system_role=role.is_system_role,
                created_at=role.created_at.isoformat(),
            )
        )

    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        status=current_user.status,
        is_superuser=current_user.is_superuser,
        is_email_verified=current_user.is_email_verified,
        institution_id=current_user.institution_id,
        institution_name=current_user.institution.name
        if current_user.institution
        else None,
        oauth_provider=current_user.oauth_provider,
        avatar_url=current_user.avatar_url,
        preferred_language=current_user.preferred_language,
        roles=role_responses,
        created_at=current_user.created_at.isoformat(),
    )


@router.post("/set-password", status_code=status.HTTP_204_NO_CONTENT)
async def set_password(
    request: SetPasswordRequest,
    http_request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Set password for OAuth-only users (no existing password)

    - Only works if user has no password (OAuth-only)
    - Allows email/password login after this
    - Does NOT revoke sessions (user stays logged in)
    """
    from services.audit_service import AuditService

    locale = get_request_locale(http_request, current_user)
    # Check if user already has a password
    if current_user.password_hash is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("auth_password_already_set", locale=locale),
        )

    # Set password
    current_user.password_hash = AuthService.get_password_hash(request.password)
    current_user.password_changed_at = func.now()
    db.commit()

    # Audit log: Password set for OAuth user
    AuditService.log_password_change(
        db, current_user.id, success=True, request=http_request
    )

    logger.info(
        f"Password set for OAuth user: {current_user.email} (ID: {current_user.id})"
    )

    return None


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    request: PasswordChangeRequest,
    http_request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Change password for authenticated user

    - Validates current password
    - Updates to new password
    - Revokes all sessions (force re-login)
    """
    locale = get_request_locale(http_request, current_user)
    from services.audit_service import AuditService

    # Verify current password
    if not AuthService.verify_password(
        request.current_password, current_user.password_hash
    ):
        # Audit log: Failed password change
        AuditService.log_password_change(
            db,
            current_user.id,
            success=False,
            request=http_request,
            error_message="Current password is incorrect",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("auth_password_incorrect", locale=locale),
        )

    # Update password
    current_user.password_hash = AuthService.get_password_hash(request.new_password)
    current_user.password_changed_at = func.now()
    db.commit()

    # Revoke all sessions (force re-login on all devices)
    AuthService.revoke_all_user_sessions(current_user.id, db)

    # Audit log: Successful password change
    AuditService.log_password_change(
        db, current_user.id, success=True, request=http_request
    )

    logger.info(
        f"Password changed for user: {current_user.email} (ID: {current_user.id})"
    )

    return None


@router.post("/password-reset", status_code=status.HTTP_204_NO_CONTENT)
async def request_password_reset(
    request: PasswordResetRequest, db: Session = Depends(get_db)
):
    """
    Request password reset

    - Generates reset token
    - Sends reset email (TODO: implement email sending)
    - Always returns 204 (even if email doesn't exist - security)
    """
    user = db.query(User).filter(User.email == request.email).first()

    if user:
        # Generate reset token (TODO: implement token generation and email sending)
        # For now, just log it
        logger.info(f"Password reset requested for: {user.email}")
        # TODO: Send email with reset link

    # Always return success (don't reveal if email exists)
    return None


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_password_reset(
    request: PasswordResetConfirm, db: Session = Depends(get_db)
):
    """
    Confirm password reset with token

    - Validates reset token
    - Updates password
    - Revokes all sessions
    """
    # TODO: Implement token validation
    # For now, just return error
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=t("auth_password_reset_not_implemented"),
    )

    return None


@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(token: str, db: Session = Depends(get_db)):
    """
    Verify user email with token

    - Validates verification token
    - Marks email as verified
    - Activates user account
    - Sends welcome email
    """
    from models.auth import EmailVerificationToken
    from services.email_service import EmailService
    from datetime import datetime, timezone

    # Find token
    email_token = (
        db.query(EmailVerificationToken)
        .filter(EmailVerificationToken.token == token)
        .first()
    )

    if not email_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("auth_verification_token_invalid"),
        )

    # Check if already used
    if email_token.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("auth_verification_token_used"),
        )

    # Check if expired
    if email_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("auth_verification_token_expired"),
        )

    # Get user
    user = db.query(User).filter(User.id == email_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=t("auth_user_not_found")
        )

    # Mark email as verified
    user.is_email_verified = True
    user.status = UserStatus.ACTIVE.value
    user.email_verified_at = func.now()

    # Mark token as used
    email_token.is_used = True
    email_token.used_at = datetime.now(timezone.utc)

    db.commit()

    # Send welcome email
    try:
        EmailService.send_welcome_email(email=user.email, first_name=user.first_name)
        logger.info(f"Welcome email sent to {user.email}")
    except Exception as e:
        logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
        # Don't fail verification if welcome email fails

    # Subscribe to SubscribeFlow newsletter (async via Celery)
    try:
        from tasks.notification_tasks import subscribe_to_newsletter

        subscribe_to_newsletter.delay(
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            user_id=str(user.id),
            source="email_verification",
        )
        logger.info(f"SubscribeFlow subscription task queued for {user.email}")
    except Exception as e:
        logger.error(f"Failed to queue SubscribeFlow task for {user.email}: {str(e)}")
        # Don't fail verification if task queuing fails

    logger.info(f"Email verified for user: {user.email} (ID: {user.id})")

    return {
        "success": True,
        "message": "Email verified successfully",
        "user": {
            "email": user.email,
            "first_name": user.first_name,
            "is_email_verified": user.is_email_verified,
        },
    }


@router.post("/resend-verification", status_code=status.HTTP_200_OK)
async def resend_verification_email(email: EmailStr, db: Session = Depends(get_db)):
    """
    Resend verification email

    - Generates new verification token
    - Sends new verification email
    """
    from models.auth import EmailVerificationToken
    from services.email_service import EmailService
    from datetime import datetime, timedelta, timezone

    # Find user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Don't reveal if email exists
        return {
            "success": True,
            "message": "If the email exists, a verification email has been sent",
        }

    # Check if already verified
    if user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("auth_email_already_verified"),
        )

    # Invalidate old tokens
    old_tokens = (
        db.query(EmailVerificationToken)
        .filter(
            EmailVerificationToken.user_id == user.id,
            ~EmailVerificationToken.is_used,
        )
        .all()
    )
    for old_token in old_tokens:
        old_token.is_used = True
        old_token.used_at = datetime.now(timezone.utc)

    # Generate new token
    verification_token = EmailService.generate_verification_token()
    token_expires = datetime.now(timezone.utc) + timedelta(hours=24)

    # Store new token
    email_token = EmailVerificationToken(
        user_id=user.id,
        token=verification_token,
        expires_at=token_expires,
        is_used=False,
    )
    db.add(email_token)
    db.commit()

    # Send verification email
    try:
        EmailService.send_verification_email(
            email=user.email,
            first_name=user.first_name,
            verification_token=verification_token,
        )
        logger.info(f"Verification email resent to {user.email}")
    except Exception as e:
        logger.error(f"Failed to resend verification email to {user.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("auth_verification_email_failed"),
        )

    return {"success": True, "message": "Verification email sent"}


# ============================================================================
# OAuth Endpoints
# ============================================================================


class OAuthLoginResponse(BaseModel):
    """OAuth login redirect response"""

    authorization_url: str
    provider: str


@router.get("/oauth/{provider}/login")
async def oauth_login(provider: str, request: Request, db: Session = Depends(get_db)):
    """
    Initiate OAuth login flow

    **Supported Providers:** google, microsoft

    Redirects user directly to OAuth provider (Google, Microsoft, etc.)
    """
    if provider not in ["google", "microsoft"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("auth_oauth_provider_unsupported"),
        )

    oauth_service = OAuthService(db)

    # Generate callback URL
    # Handle X-Forwarded-Proto for reverse proxies (Fly.io, Render, etc.)
    base_url = str(request.base_url).rstrip("/")
    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    if forwarded_proto == "https" and base_url.startswith("http://"):
        base_url = base_url.replace("http://", "https://", 1)
    redirect_uri = f"{base_url}/api/auth/oauth/{provider}/callback"

    try:
        # Generate CSRF state token and store in Redis
        state = secrets.token_urlsafe(32)
        try:
            redis_client = RedisService.get_session_client()
            redis_client.setex(f"oauth_state:{state}", 600, "valid")  # 10 min TTL
        except Exception as redis_err:
            logger.error(f"Redis unavailable for OAuth state storage: {redis_err}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=t("auth_service_unavailable"),
            )

        authorization_url = oauth_service.get_authorization_url(
            provider, redirect_uri, state=state
        )
        # Direct redirect to OAuth provider
        return RedirectResponse(url=authorization_url, status_code=302)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth login failed for {provider}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("auth_oauth_login_failed"),
        )


@router.get("/oauth/{provider}/callback", response_model=TokenResponse)
async def oauth_callback(
    provider: str, code: str, request: Request, db: Session = Depends(get_db)
):
    """
    OAuth callback endpoint

    **Supported Providers:** google, microsoft

    Exchanges authorization code for access token and creates/logs in user
    """
    if provider not in ["google", "microsoft"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("auth_oauth_provider_unsupported"),
        )

    # Verify CSRF state parameter (required)
    state = request.query_params.get("state", "")
    if not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("auth_oauth_state_missing"),
        )
    try:
        redis_client = RedisService.get_session_client()
        # Atomic get-and-delete to prevent TOCTOU race on single-use state token
        try:
            stored = redis_client.getdel(f"oauth_state:{state}")
        except AttributeError:
            # redis-py < 4.0 does not expose getdel; fall back to non-atomic get+delete
            stored = redis_client.get(f"oauth_state:{state}")
            if stored:
                redis_client.delete(f"oauth_state:{state}")
        if not stored:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=t("auth_oauth_state_invalid"),
            )
    except HTTPException:
        raise
    except Exception as redis_err:
        logger.error(f"Redis unavailable for OAuth state verification: {redis_err}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=t("auth_service_unavailable"),
        )

    oauth_service = OAuthService(db)

    # Generate callback URL (must match authorization request)
    # Handle X-Forwarded-Proto for reverse proxies (Fly.io, Render, etc.)
    base_url = str(request.base_url).rstrip("/")
    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    if forwarded_proto == "https" and base_url.startswith("http://"):
        base_url = base_url.replace("http://", "https://", 1)
    redirect_uri = f"{base_url}/api/auth/oauth/{provider}/callback"

    try:
        # Exchange code for token
        token = await oauth_service.exchange_code_for_token(
            provider, code, redirect_uri
        )

        # Get user info from OAuth provider
        user_info = await oauth_service.get_user_info(provider, token)

        # Find or create user
        user = oauth_service.find_or_create_user_from_oauth(provider, user_info, token)

        # Track OAuth login (separate commit — find_or_create already committed internally)
        try:
            user.last_login_at = func.now()
            user.last_login_ip = request.client.host if request.client else None
            db.commit()
        except Exception as e:
            logger.error(
                f"Failed to track OAuth login metadata for user {user.id}: {e}"
            )
            db.rollback()
            db.refresh(user)  # Re-attach user to session after rollback

        # Generate JWT tokens and create session
        tokens = AuthService.create_tokens_for_user(
            user=user,
            db=db,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )

        logger.info(f"OAuth login successful for user {user.email} via {provider}")

        # Redirect to frontend using a short-lived code instead of passing tokens in URL
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        try:
            redis_client = RedisService.get_session_client()
            oauth_code = secrets.token_urlsafe(32)
            redis_client.setex(
                f"oauth_code:{oauth_code}",
                60,  # 60 seconds TTL
                json.dumps(tokens),
            )
            redirect_url = f"{frontend_url}/auth/callback?code={oauth_code}"
        except Exception as redis_err:
            logger.error(
                f"Redis unavailable when storing OAuth code for user {user.id}: {redis_err}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=t("auth_service_unavailable"),
            )
        return RedirectResponse(url=redirect_url)

    except ValueError as e:
        logger.error(f"OAuth callback failed for {provider}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("auth_oauth_login_failed"),
        )
    except Exception as e:
        logger.error(f"OAuth callback error for {provider}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("auth_oauth_login_failed"),
        )


class OAuthCodeExchangeRequest(BaseModel):
    """Short-lived OAuth code exchange request"""

    code: str


@router.post("/oauth/exchange")
async def exchange_oauth_code(request: OAuthCodeExchangeRequest):
    """Exchange a short-lived OAuth code for tokens."""
    try:
        redis_client = RedisService.get_session_client()
    except Exception as e:
        logger.error(f"Redis unavailable for OAuth code exchange: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=t("auth_service_unavailable"),
        )

    key = f"oauth_code:{request.code}"
    try:
        # Atomic get-and-delete to prevent TOCTOU race (single-use code)
        token_data = redis_client.getdel(key)
    except AttributeError:
        # redis-py < 4.0 does not expose getdel; fall back to non-atomic get+delete
        try:
            token_data = redis_client.get(key)
            if token_data:
                redis_client.delete(key)
        except Exception as fallback_err:
            logger.error(
                f"Redis error in getdel fallback for OAuth code exchange: {fallback_err}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=t("auth_service_unavailable"),
            )
    except Exception as e:
        logger.error(f"Redis error during OAuth code exchange: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=t("auth_service_unavailable"),
        )
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("auth_oauth_code_invalid"),
        )

    try:
        tokens = json.loads(token_data)
    except (json.JSONDecodeError, ValueError) as decode_err:
        logger.error(
            f"Failed to deserialize OAuth token data from Redis key {key!r}: {decode_err}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("auth_oauth_token_read_failed"),
        )

    return tokens


# ============================================================================
# Avatar Proxy Endpoint
# ============================================================================


@router.get("/avatar/{user_id}")
async def get_user_avatar(
    user_id: int,
    db: Session = Depends(get_db),
):
    """
    Avatar Proxy Endpoint

    Proxies OAuth avatar URLs (e.g., Google) to avoid rate limiting (429 errors).
    Caches avatar images in Redis for 24 hours.

    **Why this endpoint?**
    - Google's CDN rate limits direct avatar URL requests
    - This endpoint downloads the image once and caches it
    - Frontend uses this endpoint instead of the original OAuth URL

    **Example:**
    - Original: `https://lh3.googleusercontent.com/a-/ALV-UjUtfwF7...` (429 error)
    - Proxied: `http://localhost:8000/api/auth/avatar/1` (cached, no rate limit)
    """
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=t("auth_user_not_found")
        )

    if not user.avatar_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=t("auth_avatar_not_found")
        )

    # Download and cache avatar
    avatar_service = AvatarService()
    avatar_bytes = avatar_service.get_avatar(user_id, user.avatar_url)

    if not avatar_bytes:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=t("auth_avatar_download_failed"),
        )

    # Return image with appropriate content type
    # Detect content type from first bytes (magic numbers)
    content_type = "image/jpeg"  # Default
    if avatar_bytes[:4] == b"\x89PNG":
        content_type = "image/png"
    elif avatar_bytes[:3] == b"GIF":
        content_type = "image/gif"
    elif avatar_bytes[:4] == b"RIFF" and avatar_bytes[8:12] == b"WEBP":
        content_type = "image/webp"

    return Response(
        content=avatar_bytes,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=86400",  # 24 hours
            "X-Avatar-Source": "cached" if avatar_bytes else "downloaded",
        },
    )


# ============================================================================
# Feature Access Endpoints (RBAC Integration)
# ============================================================================


class UserFeaturesResponse(BaseModel):
    """User features and subscription tier response"""

    subscription_tier: str
    features: List[str]
    quotas: dict


@router.get("/features", response_model=UserFeaturesResponse)
async def get_user_features(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get current user's features and subscription tier

    Returns:
    - subscription_tier: User's institution subscription tier
    - features: List of enabled features for this tier
    - quotas: Current quota limits and usage

    Used by frontend to determine which components to load and display
    """
    from config.features import TIER_FEATURES, SubscriptionTier

    # Get user's institution
    institution = current_user.institution

    # Get subscription tier
    try:
        tier = SubscriptionTier(institution.subscription_tier)
    except ValueError:
        # Fallback to FREE if invalid tier
        logger.warning(
            f"Invalid subscription tier '{institution.subscription_tier}' for institution {institution.id}, defaulting to FREE"
        )
        tier = SubscriptionTier.FREE

    # Get features for this tier
    features = TIER_FEATURES.get(tier, [])
    feature_names = [f.value for f in features]

    # Build quota response with current usage
    quotas = {
        "max_documents": institution.max_documents,
        "max_questions_per_month": institution.max_questions_per_month,
        "max_users": institution.max_users,
        # TODO: Add current usage counts when usage tracking is implemented
        # "documents_used": 0,
        # "questions_used_this_month": 0,
        # "users_count": 0,
    }

    return UserFeaturesResponse(
        subscription_tier=tier.value, features=feature_names, quotas=quotas
    )
