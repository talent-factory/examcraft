"""
Authentication API Endpoints
Profile, avatar and feature endpoints. Login runs through OIDC (api/auth_oidc.py).
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, status, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from database import get_db
from models.auth import (
    User,
    Role,
)
from services.avatar_service import AvatarService
from services.audit_service import AuditService
from services.translation_service import get_request_locale
from utils.auth_utils import (
    get_current_active_user,
)
from errors import api_error

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ============================================================================
# Pydantic Models (Request/Response Schemas)
# ============================================================================


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


class InstitutionResponse(BaseModel):
    """Institution response (embedded in user profile)"""

    id: int
    name: str
    subscription_tier: Optional[str] = None

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
    institution: Optional[InstitutionResponse] = None
    oauth_provider: Optional[str] = None  # OAuth provider (google, microsoft, etc.)
    avatar_url: Optional[str] = None  # Profile picture URL (from OAuth or uploaded)
    preferred_language: Optional[str] = None
    roles: list[RoleResponse]
    created_at: str
    # The login before the current one (TF-1060); None on the first login
    previous_login_at: Optional[str] = None

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


def _effective_role_responses(user: User) -> List[RoleResponse]:
    """RoleResponse entries for a user's direct roles + active Granted Roles.

    TF-637 review fix: ``has_permission()`` (models/auth.py) treats a Role
    granted via direct Org-Unit membership as additive to a user's direct
    roles, but this endpoint previously built ``roles[]`` from
    ``current_user.roles`` only. The frontend (``AuthContext.tsx``'s
    ``hasPermission``/``hasRole``, ``PermissionGuard.tsx``) reads
    permissions exclusively from that ``roles[]`` list -- so a user who
    passed every backend permission check via a Granted Role saw no UI for
    it. Folding Granted Roles into the same list (rather than inventing a
    second frontend concept) fixes that without any frontend change.

    Deduplicated by role id, since a user can hold the same Role both
    directly and via one or more Org-Unit grants. Only *active* grants are
    included, mirroring ``has_permission()``'s ``is_active`` check -- an
    inactive granted role shouldn't appear to authorize UI the backend
    would then reject.

    Centralized here (was previously duplicated verbatim between GET and
    PATCH ``/me``) so the permissions-parsing logic and this dedup rule
    can't drift between the two call sites.
    """
    from utils.permissions import parse_role_permissions

    seen_role_ids: set[int] = set()
    effective_roles: list[Role] = []
    for role in user.roles:
        if role.id not in seen_role_ids:
            seen_role_ids.add(role.id)
            effective_roles.append(role)
    for membership in user.org_unit_memberships:
        granted_role = membership.org_unit.role
        if (
            granted_role
            and granted_role.is_active
            and granted_role.id not in seen_role_ids
        ):
            seen_role_ids.add(granted_role.id)
            effective_roles.append(granted_role)

    return [
        RoleResponse(
            id=role.id,
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            permissions=parse_role_permissions(role.permissions),
            is_system_role=role.is_system_role,
            created_at=role.created_at.isoformat(),
        )
        for role in effective_roles
    ]


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
):
    """
    Get current user profile

    - Returns user information
    - Includes institution and roles with permissions
    """

    # Direct roles + active Granted Roles from Org-Unit membership
    # (TF-637) -- see _effective_role_responses for why they're merged here.
    role_responses = _effective_role_responses(current_user)

    institution_resp = None
    if current_user.institution:
        institution_resp = InstitutionResponse(
            id=current_user.institution.id,
            name=current_user.institution.name,
            subscription_tier=current_user.institution.subscription_tier,
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
        institution=institution_resp,
        oauth_provider=current_user.oauth_provider,
        avatar_url=current_user.avatar_url,
        preferred_language=current_user.preferred_language,
        roles=role_responses,
        created_at=current_user.created_at.isoformat(),
        previous_login_at=current_user.previous_login_at.isoformat()
        if current_user.previous_login_at
        else None,
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

    # Direct roles + active Granted Roles from Org-Unit membership
    # (TF-637) -- see _effective_role_responses for why they're merged here.
    role_responses = _effective_role_responses(current_user)

    institution_resp = None
    if current_user.institution:
        institution_resp = InstitutionResponse(
            id=current_user.institution.id,
            name=current_user.institution.name,
            subscription_tier=current_user.institution.subscription_tier,
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
        institution=institution_resp,
        oauth_provider=current_user.oauth_provider,
        avatar_url=current_user.avatar_url,
        preferred_language=current_user.preferred_language,
        roles=role_responses,
        created_at=current_user.created_at.isoformat(),
        previous_login_at=current_user.previous_login_at.isoformat()
        if current_user.previous_login_at
        else None,
    )


# TF-768: Reset tokens live one hour; at most this many can be issued per user
# within one hour (silently capped, so the cap itself leaks nothing).
PASSWORD_RESET_TOKEN_TTL = timedelta(hours=1)
PASSWORD_RESET_MAX_REQUESTS_PER_HOUR = 3


# ============================================================================
# OAuth Endpoints
# ============================================================================


# ============================================================================
# Avatar Proxy Endpoint
# ============================================================================


@router.get("/avatar/{user_id}")
async def get_user_avatar(
    user_id: int,
    request: Request,
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
    locale = get_request_locale(request)
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise api_error(status.HTTP_404_NOT_FOUND, "auth_user_not_found", locale)

    if not user.avatar_url:
        raise api_error(status.HTTP_404_NOT_FOUND, "auth_avatar_not_found", locale)

    # Download and cache avatar
    avatar_service = AvatarService()
    avatar_bytes = avatar_service.get_avatar(user_id, user.avatar_url)

    if not avatar_bytes:
        raise api_error(
            status.HTTP_502_BAD_GATEWAY, "auth_avatar_download_failed", locale
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


class EvaluationLimitsResponse(BaseModel):
    """Evaluation tier limits, mirrored from ``auswertung_quotas.TierLimits``.

    ``-1`` = unlimited. The values come from ``get_limits_for_user`` so the
    frontend can disable gated actions up front; the 402 checks stay the gate.
    """

    tier: str
    label: str
    exams_per_month: int
    submissions_per_exam: int
    drivers: List[str]
    llm_grading: bool
    class_history_stats: bool
    review_bulk: bool
    custom_grading_schemes: bool
    custom_llm_model: bool

    class Config:
        from_attributes = True


class UserFeaturesResponse(BaseModel):
    """User features and subscription tier response"""

    subscription_tier: str
    features: List[str]
    quotas: dict
    evaluation_limits: EvaluationLimitsResponse


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
    - evaluation_limits: Evaluation tier limits (``auswertung_quotas``)

    Used by frontend to determine which components to load and display
    """
    from config.features import TIER_FEATURES, TIER_QUOTAS, SubscriptionTier
    from services.auswertung_quotas import (
        UnknownTierError,
        get_limits,
        get_tier_for_institution,
    )

    institution = current_user.institution

    # Same tier resolution as the 402 gates: unknown → free (outside
    # production), no institution → free instead of an AttributeError/500.
    # In production the 402 gates raise for a misconfigured tier, but this
    # read-only endpoint must not take down every feature gate in the app:
    # fall back to the most restrictive tier and log at error level.
    try:
        tier_value = get_tier_for_institution(institution)
    except UnknownTierError:
        logger.error(
            "Features-Endpunkt: unbekannter Tier für Benutzer %s, Fallback auf 'free'",
            current_user.id,
            exc_info=True,
        )
        tier_value = "free"
    tier = SubscriptionTier(tier_value)

    # Get features for this tier
    features = TIER_FEATURES.get(tier, [])
    feature_names = [f.value for f in features]

    # Build quota response with current usage
    if institution is None:
        free_quotas = TIER_QUOTAS[SubscriptionTier.FREE]
        quotas = {
            "max_documents": free_quotas["max_documents"],
            "max_questions_per_month": free_quotas["max_questions_per_month"],
            "max_users": free_quotas["max_users"],
        }
    else:
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
        subscription_tier=tier.value,
        features=feature_names,
        quotas=quotas,
        evaluation_limits=EvaluationLimitsResponse.model_validate(
            get_limits(tier_value)
        ),
    )
