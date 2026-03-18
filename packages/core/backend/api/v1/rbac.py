"""
RBAC API Endpoints für ExamCraft AI
REST API für RBAC Management (Roles, Features, Permissions, Quotas)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from database import get_db
from services.rbac_service import RBACService
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


class RoleResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: Optional[str]
    is_system_role: bool
    is_active: bool
    features: List[FeatureResponse] = []

    class Config:
        from_attributes = True


class CreateRoleRequest(BaseModel):
    name: str = Field(..., pattern="^[a-z0-9_]+$")
    display_name: str
    description: Optional[str] = None
    feature_ids: List[str]


class UpdateRoleFeaturesRequest(BaseModel):
    feature_ids: List[str]


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
    Listet alle verfügbaren Features auf.
    Optional filterbar nach Kategorie.
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Gibt Details zu einem spezifischen Feature zurück.
    """
    feature = db.query(Feature).filter(Feature.id == feature_id).first()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    return feature


# ============================================
# ROLE ENDPOINTS
# ============================================


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    include_system_roles: bool = True,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Listet alle Rollen auf.
    """
    rbac_service = RBACService(db)
    roles = rbac_service.list_roles(
        include_system_roles=include_system_roles, include_inactive=include_inactive
    )

    # Features für jede Rolle laden
    result = []
    for role in roles:
        features = rbac_service.get_role_features(role.id)
        role_dict = RoleResponse.from_orm(role).dict()
        role_dict["features"] = [FeatureResponse.from_orm(f) for f in features]
        result.append(role_dict)

    return result


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Gibt Details zu einer spezifischen Rolle zurück.
    """
    role = db.query(RBACRole).filter(RBACRole.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    rbac_service = RBACService(db)
    features = rbac_service.get_role_features(role.id)

    role_dict = RoleResponse.from_orm(role).dict()
    role_dict["features"] = [FeatureResponse.from_orm(f) for f in features]
    return role_dict


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    request: CreateRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Erstellt eine neue Custom-Rolle.
    Nur für Admins.
    """
    # TODO: Check if user is admin
    rbac_service = RBACService(db)

    try:
        role = rbac_service.create_custom_role(
            name=request.name,
            display_name=request.display_name,
            description=request.description,
            feature_ids=request.feature_ids,
            created_by=current_user.id,
        )

        features = rbac_service.get_role_features(role.id)
        role_dict = RoleResponse.from_orm(role).dict()
        role_dict["features"] = [FeatureResponse.from_orm(f) for f in features]
        return role_dict
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/roles/{role_id}/features", response_model=RoleResponse)
async def update_role_features(
    role_id: str,
    request: UpdateRoleFeaturesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Aktualisiert die Features einer Rolle.
    Nur für Admins. System-Rollen können nicht geändert werden.
    """
    # TODO: Check if user is admin
    rbac_service = RBACService(db)

    try:
        role = rbac_service.update_role_features(
            role_id=role_id, feature_ids=request.feature_ids
        )

        features = rbac_service.get_role_features(role.id)
        role_dict = RoleResponse.from_orm(role).dict()
        role_dict["features"] = [FeatureResponse.from_orm(f) for f in features]
        return role_dict
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================
# SUBSCRIPTION TIER ENDPOINTS
# ============================================


@router.get("/tiers", response_model=List[SubscriptionTierResponse])
async def list_subscription_tiers(
    active_only: bool = True, db: Session = Depends(get_db)
):
    """
    Listet alle Subscription Tiers auf.
    Öffentlicher Endpoint (kein Auth erforderlich).
    """
    query = db.query(SubscriptionTier)

    if active_only:
        query = query.filter(SubscriptionTier.is_active)

    tiers = query.order_by(SubscriptionTier.sort_order).all()
    return tiers


@router.get("/tiers/current", response_model=SubscriptionTierResponse)
async def get_current_tier(db: Session = Depends(get_db)):
    """
    Gibt den aktuellen/Standard Subscription Tier zurück.
    Basiert auf der DEFAULT_SUBSCRIPTION_TIER Environment Variable.
    Öffentlicher Endpoint (kein Auth erforderlich).

    **DEPRECATED**: Use /tiers/my instead to get the authenticated user's institution tier.
    """
    import os

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
            detail=f"Subscription tier '{default_tier_name}' not found",
        )

    return tier


@router.get("/tiers/my", response_model=SubscriptionTierResponse)
async def get_my_tier(
    current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """
    Gibt den Subscription Tier der Institution des eingeloggten Users zurück.
    Requires Authentication.

    Returns:
        SubscriptionTierResponse: Subscription tier of the user's institution
    """
    from models.auth import Institution

    # Get user's institution
    institution = (
        db.query(Institution)
        .filter(Institution.id == current_user.institution_id)
        .first()
    )

    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User's institution not found"
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
            detail=f"Subscription tier '{institution.subscription_tier}' not found",
        )

    return tier


@router.get("/tiers/{tier_id}/quotas", response_model=List[TierQuotaResponse])
async def get_tier_quotas(tier_id: str, db: Session = Depends(get_db)):
    """
    Gibt alle Quotas für einen Subscription Tier zurück.
    Öffentlicher Endpoint (kein Auth erforderlich).
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
    Prüft ob der aktuelle User Zugriff auf ein Feature hat.
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Prüft ob die Institution des Users noch Quota verfügbar hat.
    """
    if not current_user.institution_id:
        raise HTTPException(status_code=400, detail="User has no institution")

    rbac_service = RBACService(db)
    quota_check = rbac_service.check_resource_quota(
        institution_id=current_user.institution_id,
        resource_type=resource_type,
        requested_amount=requested_amount,
    )

    return quota_check
