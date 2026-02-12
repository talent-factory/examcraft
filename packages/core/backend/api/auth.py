"""
Authentication API Endpoints
Login, Logout, Register, Profile, Password Reset
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
import logging
import os

from database import get_db
from models.auth import User, Role, Institution, UserStatus, UserRole
from services.auth_service import AuthService
from services.avatar_service import AvatarService
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


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation"""

    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class SetPasswordRequest(BaseModel):
    """Set password for OAuth-only users"""

    password: str = Field(..., min_length=8, max_length=100)


class PasswordChangeRequest(BaseModel):
    """Password change request (authenticated user)"""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


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
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
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
                status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found"
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
    from services.audit_service import AuditService

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
            detail="Incorrect email or password",
        )

    # Verify password
    if not AuthService.verify_password(request.password, user.password_hash):
        # Increment failed login attempts
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        db.commit()

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
            detail="Incorrect email or password",
        )

    # Check if user is active
    if user.status != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"Account is {user.status}"
        )

    # Reset failed login attempts
    user.failed_login_attempts = 0
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
            detail="Invalid or expired refresh token",
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
    import json

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
        roles=role_responses,
        created_at=current_user.created_at.isoformat(),
    )


@router.patch("/me", response_model=UserProfileResponse)
async def update_current_user_profile(
    request: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update current user profile

    - Updates user information
    - Returns updated profile
    """
    if request.first_name is not None:
        current_user.first_name = request.first_name

    if request.last_name is not None:
        current_user.last_name = request.last_name

    if request.bio is not None:
        current_user.bio = request.bio

    if request.avatar_url is not None:
        current_user.avatar_url = request.avatar_url

    db.commit()
    db.refresh(current_user)

    logger.info(f"User profile updated: {current_user.email} (ID: {current_user.id})")

    import json

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

    # Check if user already has a password
    if current_user.password_hash is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a password. Use /change-password instead.",
        )

    # Set password
    current_user.password_hash = AuthService.get_password_hash(request.password)
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
            detail="Current password is incorrect",
        )

    # Update password
    current_user.password_hash = AuthService.get_password_hash(request.new_password)
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
        detail="Password reset confirmation not yet implemented",
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
            detail="Invalid verification token",
        )

    # Check if already used
    if email_token.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token already used",
        )

    # Check if expired
    if email_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token expired. Please request a new one.",
        )

    # Get user
    user = db.query(User).filter(User.id == email_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Mark email as verified
    user.is_email_verified = True
    user.status = UserStatus.ACTIVE.value

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
        logger.error(
            f"Failed to queue SubscribeFlow task for {user.email}: {str(e)}"
        )
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
            detail="Email already verified",
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
            detail="Failed to send verification email",
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
            detail=f"Unsupported OAuth provider: {provider}. Supported: google, microsoft",
        )

    from services.oauth_service import OAuthService
    from fastapi.responses import RedirectResponse

    oauth_service = OAuthService(db)

    # Generate callback URL
    # Handle X-Forwarded-Proto for reverse proxies (Fly.io, Render, etc.)
    base_url = str(request.base_url).rstrip("/")
    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    if forwarded_proto == "https" and base_url.startswith("http://"):
        base_url = base_url.replace("http://", "https://", 1)
    redirect_uri = f"{base_url}/api/auth/oauth/{provider}/callback"

    try:
        authorization_url = oauth_service.get_authorization_url(provider, redirect_uri)
        # Direct redirect to OAuth provider
        return RedirectResponse(url=authorization_url, status_code=302)
    except Exception as e:
        logger.error(f"OAuth login failed for {provider}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth login failed: {str(e)}",
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
            detail=f"Unsupported OAuth provider: {provider}",
        )

    from services.oauth_service import OAuthService

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

        # Generate JWT tokens and create session
        tokens = AuthService.create_tokens_for_user(
            user=user,
            db=db,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )

        logger.info(f"OAuth login successful for user {user.email} via {provider}")

        # Redirect to frontend with tokens
        from fastapi.responses import RedirectResponse

        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        redirect_url = (
            f"{frontend_url}/auth/callback?"
            f"access_token={tokens['access_token']}&"
            f"refresh_token={tokens['refresh_token']}&"
            f"token_type={tokens['token_type']}"
        )
        return RedirectResponse(url=redirect_url)

    except ValueError as e:
        logger.error(f"OAuth callback failed for {provider}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"OAuth callback error for {provider}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth authentication failed: {str(e)}",
        )


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
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if not user.avatar_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User has no avatar"
        )

    # Download and cache avatar
    avatar_service = AvatarService()
    avatar_bytes = avatar_service.get_avatar(user_id, user.avatar_url)

    if not avatar_bytes:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to download avatar from OAuth provider",
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
