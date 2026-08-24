"""
RBAC API Endpoints for ExamCraft AI
REST API for RBAC Management (Roles, Features, Permissions, Quotas)
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from services.rbac_service import RBACService
from services.translation_service import t, get_request_locale
from utils.auth_utils import get_current_user, get_current_active_user
from models.auth import User
from models.rbac import Feature, RBACRole, SubscriptionTier, TierQuota

router = APIRouter(prefix="/api/v1/rbac", tags=["RBAC"])


# ============================================
# PYDANTIC SCHEMAS
# ============================================


class FeatureResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: Optional[str]
    category: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class RBACRoleResponse(BaseModel):
    """Response schema for RBACRole (feature-tier "System A" roles).

    Named distinctly from api.admin.RoleResponse (permission-based "System B"
    roles, models.auth.Role) — the two describe unrelated domain concepts and
    were previously both called RoleResponse in different modules, which is
    confusing when navigating by symbol name (TF-603 review follow-up).
    """

    id: str
    name: str
    display_name: str
    description: Optional[str]
    is_system_role: bool
    is_active: bool
    features: List[FeatureResponse] = []

    class Config:
        from_attributes = True


class SubscriptionTierResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: Optional[str]
    price_monthly: float
    price_yearly: float
    is_active: bool
    sort_order: int

    class Config:
        from_attributes = True


class TierQuotaResponse(BaseModel):
    tier_id: str
    resource_type: str
    quota_limit: int

    class Config:
        from_attributes = True


class QuotaCheckResponse(BaseModel):
    allowed: bool
    current_usage: Optional[int] = None
    quota_limit: Optional[int] = None
    remaining: Optional[int] = None
    requested: Optional[int] = None
    reason: Optional[str] = None


class ResourceUsageResponse(BaseModel):
    institution_id: int
    resource_type: str
    usage_count: int
    period_start: datetime
    period_end: datetime

    class Config:
        from_attributes = True


# ============================================
# FEATURE ENDPOINTS
# ============================================


@router.get("/features", response_model=List[FeatureResponse])
async def list_features(
    category: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lists all available features.
    Optionally filterable by category.
    """
    query = db.query(Feature)

    if category:
        query = query.filter(Feature.category == category)

    if active_only:
        query = query.filter(Feature.is_active)

    features = query.all()
    return features


@router.get("/features/{feature_id}", response_model=FeatureResponse)
async def get_feature(
    feature_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns details for a specific feature.
    """
    locale = get_request_locale(request, current_user)
    feature = db.query(Feature).filter(Feature.id == feature_id).first()
    if not feature:
        raise HTTPException(
            status_code=404, detail=t("rbac_feature_not_found", locale=locale)
        )
    return feature


# ============================================
# ROLE ENDPOINTS
# ============================================


@router.get("/roles", response_model=List[RBACRoleResponse])
async def list_roles(
    include_system_roles: bool = True,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lists all roles.
    """
    rbac_service = RBACService(db)
    roles = rbac_service.list_roles(
        include_system_roles=include_system_roles, include_inactive=include_inactive
    )

    # Load features for each role
    result = []
    for role in roles:
        features = rbac_service.get_role_features(role.id)
        role_dict = RBACRoleResponse.from_orm(role).dict()
        role_dict["features"] = [FeatureResponse.from_orm(f) for f in features]
        result.append(role_dict)

    return result


@router.get("/roles/{role_id}", response_model=RBACRoleResponse)
async def get_role(
    role_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns details for a specific role.
    """
    locale = get_request_locale(request, current_user)
    role = db.query(RBACRole).filter(RBACRole.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=404, detail=t("rbac_role_not_found", locale=locale)
        )

    rbac_service = RBACService(db)
    features = rbac_service.get_role_features(role.id)

    role_dict = RBACRoleResponse.from_orm(role).dict()
    role_dict["features"] = [FeatureResponse.from_orm(f) for f in features]
    return role_dict


# ============================================
# SUBSCRIPTION TIER ENDPOINTS
# ============================================


@router.get("/tiers", response_model=List[SubscriptionTierResponse])
async def list_subscription_tiers(
    active_only: bool = True, db: Session = Depends(get_db)
):
    """
    Lists all subscription tiers.
    Public endpoint (no auth required).
    """
    query = db.query(SubscriptionTier)

    if active_only:
        query = query.filter(SubscriptionTier.is_active)

    tiers = query.order_by(SubscriptionTier.sort_order).all()
    return tiers


@router.get("/tiers/current", response_model=SubscriptionTierResponse)
async def get_current_tier(request: Request, db: Session = Depends(get_db)):
    """
    Returns the current/default subscription tier.
    Based on the DEFAULT_SUBSCRIPTION_TIER environment variable.
    Public endpoint (no auth required).

    **DEPRECATED**: Use /tiers/my instead to get the authenticated user's institution tier.
    """
    import os

    locale = get_request_locale(request)
    default_tier_name = os.getenv("DEFAULT_SUBSCRIPTION_TIER", "free")

    tier = (
        db.query(SubscriptionTier)
        .filter(SubscriptionTier.name == default_tier_name)
        .first()
    )

    if not tier:
        # Fallback to free tier if default not found
        tier = (
            db.query(SubscriptionTier).filter(SubscriptionTier.name == "free").first()
        )

    if not tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("rbac_tier_not_found", locale=locale),
        )

    return tier


@router.get("/tiers/my", response_model=SubscriptionTierResponse)
async def get_my_tier(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Returns the subscription tier of the logged-in user's institution.
    Requires Authentication.

    Returns:
        SubscriptionTierResponse: Subscription tier of the user's institution
    """
    locale = get_request_locale(request, current_user)
    from models.auth import Institution

    # Get user's institution
    institution = (
        db.query(Institution)
        .filter(Institution.id == current_user.institution_id)
        .first()
    )

    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("rbac_institution_not_found", locale=locale),
        )

    # Get subscription tier
    tier = (
        db.query(SubscriptionTier)
        .filter(SubscriptionTier.name == institution.subscription_tier)
        .first()
    )

    if not tier:
        # Fallback to free tier if institution tier not found
        tier = (
            db.query(SubscriptionTier).filter(SubscriptionTier.name == "free").first()
        )

    if not tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("rbac_tier_not_found", locale=locale),
        )

    return tier


@router.get("/tiers/{tier_id}/quotas", response_model=List[TierQuotaResponse])
async def get_tier_quotas(tier_id: str, db: Session = Depends(get_db)):
    """
    Returns all quotas for a subscription tier.
    Public endpoint (no auth required).
    """
    quotas = db.query(TierQuota).filter(TierQuota.tier_id == tier_id).all()
    return quotas


# ============================================
# PERMISSION & QUOTA CHECK ENDPOINTS
# ============================================


@router.get("/check-permission/{feature_name}")
async def check_feature_permission(
    feature_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Checks whether the current user has access to a feature.
    """
    rbac_service = RBACService(db)
    has_access = rbac_service.user_has_feature_access(
        user_id=current_user.id, feature_name=feature_name, log_access=False
    )

    return {"has_access": has_access, "feature": feature_name}


@router.get("/check-quota/{resource_type}", response_model=QuotaCheckResponse)
async def check_resource_quota(
    resource_type: str,
    requested_amount: int = 1,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Checks whether the user's institution still has quota available.
    """
    locale = get_request_locale(request, current_user)
    if not current_user.institution_id:
        raise HTTPException(
            status_code=400, detail=t("rbac_no_institution", locale=locale)
        )

    rbac_service = RBACService(db)
    quota_check = rbac_service.check_resource_quota(
        institution_id=current_user.institution_id,
        resource_type=resource_type,
        requested_amount=requested_amount,
    )

    return quota_check
