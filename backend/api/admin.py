"""
Admin API Endpoints
User Management, Role Assignment, Institution Management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
import logging
import json

from database import get_db
from models.auth import User, Role, Institution, UserStatus
from services.translation_service import t, get_request_locale
from utils.auth_utils import get_current_superuser, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin"])


def _is_admin_role(user: User) -> bool:
    """Check if user has admin role."""
    return any(role.name == "admin" for role in user.roles)


def _require_same_institution(
    current_user: User, target_user: User, locale: str = "de"
) -> None:
    """Raise 403 if non-superuser tries to access user from different institution."""
    if (
        not current_user.is_superuser
        and current_user.institution_id != target_user.institution_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=t("admin_cross_institution_access_denied", locale=locale),
        )


def _require_write_access(
    current_user: User, target_user: User, locale: str = "de"
) -> None:
    """Raise 403 if user cannot edit the target user.
    Superuser can edit anyone. Admin can edit users in own institution.
    """
    if current_user.is_superuser:
        return
    if (
        _is_admin_role(current_user)
        and current_user.institution_id == target_user.institution_id
    ):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=t("admin_insufficient_permissions", locale=locale),
    )


# ============================================================================
# Pydantic Models (Request/Response Schemas)
# ============================================================================


class RoleResponse(BaseModel):
    """Role response"""

    id: int
    name: str
    display_name: str
    description: Optional[str]
    permissions: List[str]
    is_system_role: bool
    created_at: str

    class Config:
        from_attributes = True


class InstitutionResponse(BaseModel):
    """Institution response"""

    id: int
    name: str
    slug: str
    domain: Optional[str] = None
    subscription_tier: str
    max_users: int
    max_documents: int
    max_questions_per_month: int
    is_active: bool
    require_second_reviewer: bool = False
    default_grading_scheme_id: Optional[int] = None
    created_at: str

    class Config:
        from_attributes = True


class UserListItem(BaseModel):
    """User list item response"""

    id: int
    email: str
    first_name: str
    last_name: str
    institution_id: int
    institution_name: str
    roles: List[str]
    status: str
    is_superuser: bool
    last_login_at: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class UserDetailResponse(BaseModel):
    """User detail response"""

    id: int
    email: str
    first_name: str
    last_name: str
    institution_id: int
    institution_name: str
    roles: List[RoleResponse]
    status: str
    is_superuser: bool
    last_login_at: Optional[str]
    created_at: str
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class UpdateUserRequest(BaseModel):
    """Update user request"""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None


class UpdateUserStatusRequest(BaseModel):
    """Update user status request"""

    status: UserStatus


class AssignRoleRequest(BaseModel):
    """Assign role request"""

    role_id: int


class UserListResponse(BaseModel):
    """User list response with pagination"""

    users: List[UserListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    can_edit: bool = False


class TransferUserRequest(BaseModel):
    """Body for POST /api/admin/users/{user_id}/transfer."""

    target_institution_id: int = Field(..., gt=0)
    transfer_documents: bool = True
    transfer_exams: bool = True
    transfer_questions: bool = True
    transfer_tags: bool = True


class TransferPreviewCountsModel(BaseModel):
    documents: int
    exams: int
    questions: int
    tags: int


class TransferExcludedCountsModel(BaseModel):
    students: int
    classes: int
    submissions: int


class TransferPreviewResponse(BaseModel):
    source_institution_id: int
    source_institution_name: str
    target_institution_id: int
    target_institution_name: str
    transferable: TransferPreviewCountsModel
    excluded: TransferExcludedCountsModel


class TransferUserResponse(BaseModel):
    user: UserDetailResponse
    transferred: TransferPreviewCountsModel


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    institution_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List users with institution-scoped access.

    - Superuser: sees all users, can filter by institution
    - Admin/Others: sees only users of own institution
    """
    # Build query
    query = db.query(User)

    # Non-superusers always see only their own institution
    if not current_user.is_superuser:
        query = query.filter(User.institution_id == current_user.institution_id)
    elif institution_id:
        # Superuser can optionally filter by institution
        query = query.filter(User.institution_id == institution_id)

    # Apply search filter
    if search:
        search_filter = or_(
            User.email.ilike(f"%{search}%"),
            User.first_name.ilike(f"%{search}%"),
            User.last_name.ilike(f"%{search}%"),
        )
        query = query.filter(search_filter)

    # Apply role filter
    if role:
        query = query.join(User.roles).filter(Role.name == role)

    # Apply status filter
    if status:
        query = query.filter(User.status == status)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    users = query.offset(offset).limit(page_size).all()

    # Build response
    user_items = []
    for user in users:
        user_items.append(
            UserListItem(
                id=user.id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                institution_id=user.institution_id,
                institution_name=user.institution.name if user.institution else "N/A",
                roles=[role.name for role in user.roles],
                status=user.status,
                is_superuser=user.is_superuser,
                last_login_at=user.last_login_at.isoformat()
                if user.last_login_at
                else None,
                created_at=user.created_at.isoformat(),
            )
        )

    total_pages = (total + page_size - 1) // page_size

    # Superuser and admin can edit users
    can_edit = current_user.is_superuser or _is_admin_role(current_user)

    return UserListResponse(
        users=user_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        can_edit=can_edit,
    )


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get user details with institution-scoped access.

    - Superuser: can view any user
    - Others: can only view users in own institution
    """
    locale = get_request_locale(request, current_user)
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("admin_user_not_found", locale=locale),
        )

    _require_same_institution(current_user, user, locale)

    # Build role responses with parsed permissions
    role_responses = []
    for role in user.roles:
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

    return UserDetailResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        institution_id=user.institution_id,
        institution_name=user.institution.name if user.institution else "N/A",
        roles=role_responses,
        status=user.status,
        is_superuser=user.is_superuser,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


@router.patch("/users/{user_id}", response_model=UserDetailResponse)
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update user details.

    - Superuser: can edit any user
    - Admin: can edit users in own institution
    - Others: 403
    """
    locale = get_request_locale(http_request, current_user)
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("admin_user_not_found", locale=locale),
        )

    _require_write_access(current_user, user, locale)

    # Update fields
    if request.first_name is not None:
        user.first_name = request.first_name

    if request.last_name is not None:
        user.last_name = request.last_name

    if request.email is not None:
        # Check if email is already taken
        existing_user = (
            db.query(User)
            .filter(User.email == request.email, User.id != user_id)
            .first()
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=t("admin_email_already_in_use", locale=locale),
            )
        user.email = request.email

    db.commit()
    db.refresh(user)

    logger.info(f"User updated by admin: {user.email} (ID: {user.id})")

    # Build role responses
    role_responses = []
    for role in user.roles:
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

    return UserDetailResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        institution_id=user.institution_id,
        institution_name=user.institution.name if user.institution else "N/A",
        roles=role_responses,
        status=user.status,
        is_superuser=user.is_superuser,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


@router.patch("/users/{user_id}/status", response_model=UserDetailResponse)
async def update_user_status(
    user_id: int,
    request: UpdateUserStatusRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update user status.

    - Superuser: can change any user's status
    - Admin: can change status of users in own institution
    - Others: 403
    """
    locale = get_request_locale(http_request, current_user)
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("admin_user_not_found", locale=locale),
        )

    _require_write_access(current_user, user, locale)

    # Prevent admin from deactivating themselves
    if user.id == current_user.id and request.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("admin_cannot_deactivate_self", locale=locale),
        )

    user.status = request.status.value
    db.commit()
    db.refresh(user)

    logger.info(f"User status updated by admin: {user.email} -> {user.status}")

    # Build role responses
    role_responses = []
    for role in user.roles:
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

    return UserDetailResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        institution_id=user.institution_id,
        institution_name=user.institution.name if user.institution else "N/A",
        roles=role_responses,
        status=user.status,
        is_superuser=user.is_superuser,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


@router.post("/users/{user_id}/roles", response_model=UserDetailResponse)
async def assign_role_to_user(
    user_id: int,
    request: AssignRoleRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Assign role to user.

    - Superuser: can assign roles to any user
    - Admin: can assign roles to users in own institution
    - Others: 403
    """
    locale = get_request_locale(http_request, current_user)
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("admin_user_not_found", locale=locale),
        )

    _require_write_access(current_user, user, locale)

    role = db.query(Role).filter(Role.id == request.role_id).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("admin_role_not_found", locale=locale),
        )

    # Check if user already has this role
    if role in user.roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("admin_user_already_has_role", locale=locale),
        )

    user.roles.append(role)
    db.commit()
    db.refresh(user)

    logger.info(f"Role '{role.name}' assigned to user {user.email} by admin")

    # Build role responses
    role_responses = []
    for r in user.roles:
        permissions = r.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except json.JSONDecodeError:
                permissions = []
        elif not isinstance(permissions, list):
            permissions = []

        role_responses.append(
            RoleResponse(
                id=r.id,
                name=r.name,
                display_name=r.display_name,
                description=r.description,
                permissions=permissions,
                is_system_role=r.is_system_role,
                created_at=r.created_at.isoformat(),
            )
        )

    return UserDetailResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        institution_id=user.institution_id,
        institution_name=user.institution.name if user.institution else "N/A",
        roles=role_responses,
        status=user.status,
        is_superuser=user.is_superuser,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


@router.delete("/users/{user_id}/roles/{role_id}", response_model=UserDetailResponse)
async def remove_role_from_user(
    user_id: int,
    role_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove role from user.

    - Superuser: can remove roles from any user
    - Admin: can remove roles from users in own institution
    - Others: 403
    """
    locale = get_request_locale(request, current_user)
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("admin_user_not_found", locale=locale),
        )

    _require_write_access(current_user, user, locale)

    role = db.query(Role).filter(Role.id == role_id).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("admin_role_not_found", locale=locale),
        )

    # Check if user has this role
    if role not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("admin_user_does_not_have_role", locale=locale),
        )

    # Prevent removing last role
    if len(user.roles) == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("admin_cannot_remove_last_role", locale=locale),
        )

    user.roles.remove(role)
    db.commit()
    db.refresh(user)

    logger.info(f"Role '{role.name}' removed from user {user.email} by admin")

    # Build role responses
    role_responses = []
    for r in user.roles:
        permissions = r.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except json.JSONDecodeError:
                permissions = []
        elif not isinstance(permissions, list):
            permissions = []

        role_responses.append(
            RoleResponse(
                id=r.id,
                name=r.name,
                display_name=r.display_name,
                description=r.description,
                permissions=permissions,
                is_system_role=r.is_system_role,
                created_at=r.created_at.isoformat(),
            )
        )

    return UserDetailResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        institution_id=user.institution_id,
        institution_name=user.institution.name if user.institution else "N/A",
        roles=role_responses,
        status=user.status,
        is_superuser=user.is_superuser,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """
    List all roles (Superuser only)

    - Returns all available roles
    - Requires 'manage_users' permission
    """
    roles = db.query(Role).all()

    role_responses = []
    for role in roles:
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

    return role_responses


@router.get("/institutions", response_model=List[InstitutionResponse])
async def list_institutions(
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """
    List all institutions (Superuser only)

    - Returns all institutions
    - Requires 'manage_users' permission
    """
    institutions = db.query(Institution).all()

    return [
        InstitutionResponse(
            id=inst.id,
            name=inst.name,
            slug=inst.slug,
            domain=inst.domain,
            subscription_tier=inst.subscription_tier,
            max_users=inst.max_users,
            max_documents=inst.max_documents,
            max_questions_per_month=inst.max_questions_per_month,
            is_active=inst.is_active,
            require_second_reviewer=inst.require_second_reviewer,
            default_grading_scheme_id=inst.default_grading_scheme_id,
            created_at=inst.created_at.isoformat(),
        )
        for inst in institutions
    ]


def _validate_default_grading_scheme_id(
    db: Session,
    scheme_id: Optional[int],
    institution_id: Optional[int],
    locale: str,
) -> Optional[int]:
    """Validate a proposed ``Institution.default_grading_scheme_id``.

    A system scheme (``institution_id IS NULL``) is always allowed; an
    institution-scoped scheme must belong to ``institution_id``. Shares the
    validation *shape* of ``api.exams._resolve_grading_scheme_id`` (system
    always allowed, foreign-tenant scheme → 422) so the institution default
    can never point at a foreign tenant's scheme — but compares against the
    target ``institution_id`` (the institution being configured) rather than
    the caller's ``user.institution_id``, because the SuperAdmin actor here
    legitimately configures *other* tenants. Do not merge the two helpers on
    that assumption. ``None`` clears the default; ``institution_id=None``
    (e.g. a not-yet-persisted institution) permits only system schemes.
    """
    if scheme_id is None:
        return None

    from models.grading_scheme import GradingScheme

    scheme = db.query(GradingScheme).filter(GradingScheme.id == scheme_id).one_or_none()
    if scheme is None or (
        scheme.institution_id is not None and scheme.institution_id != institution_id
    ):
        raise HTTPException(
            status_code=422,
            detail=t("admin_invalid_grading_scheme", locale=locale),
        )
    return scheme_id


class UpdateInstitutionRequest(BaseModel):
    """Request model for updating institution"""

    name: Optional[str] = None
    domain: Optional[str] = None
    subscription_tier: Optional[str] = None
    is_active: Optional[bool] = None
    require_second_reviewer: Optional[bool] = None
    default_grading_scheme_id: Optional[int] = None


@router.patch("/institutions/{institution_id}", response_model=InstitutionResponse)
async def update_institution(
    institution_id: int,
    update_data: UpdateInstitutionRequest,
    request: Request,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """
    Update institution (Admin only)

    - Updates institution details
    - Automatically updates quotas when subscription_tier changes
    - Requires 'manage_users' permission
    """
    locale = get_request_locale(request, current_user)
    from config.features import SubscriptionTier

    # Get institution
    institution = db.query(Institution).filter(Institution.id == institution_id).first()
    if not institution:
        raise HTTPException(
            status_code=404, detail=t("admin_institution_not_found", locale=locale)
        )

    # Update fields
    if update_data.name is not None:
        institution.name = update_data.name
        # Update slug from name
        institution.slug = update_data.name.lower().replace(" ", "-")

    if update_data.domain is not None:
        institution.domain = update_data.domain

    if update_data.is_active is not None:
        institution.is_active = update_data.is_active

    if update_data.require_second_reviewer is not None:
        institution.require_second_reviewer = update_data.require_second_reviewer

    # Default grading scheme — the Note-resolver's institution-wide fallback.
    # ``model_fields_set`` distinguishes an explicit ``null`` (clear the
    # default) from an omitted field (leave it untouched).
    if "default_grading_scheme_id" in update_data.model_fields_set:
        institution.default_grading_scheme_id = _validate_default_grading_scheme_id(
            db,
            update_data.default_grading_scheme_id,
            institution.id,
            locale,
        )

    # Update subscription tier and quotas
    if update_data.subscription_tier is not None:
        # Validate tier
        try:
            tier = SubscriptionTier(update_data.subscription_tier)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=t("admin_invalid_subscription_tier", locale=locale),
            )

        institution.subscription_tier = tier.value

        # Sync quotas from tier_quotas DB table (single source of truth)
        from utils.tenant_utils import sync_institution_quotas

        sync_institution_quotas(institution, db)

    db.commit()
    db.refresh(institution)

    return InstitutionResponse(
        id=institution.id,
        name=institution.name,
        slug=institution.slug,
        domain=institution.domain,
        subscription_tier=institution.subscription_tier,
        max_users=institution.max_users,
        max_documents=institution.max_documents,
        max_questions_per_month=institution.max_questions_per_month,
        is_active=institution.is_active,
        require_second_reviewer=institution.require_second_reviewer,
        default_grading_scheme_id=institution.default_grading_scheme_id,
        created_at=institution.created_at.isoformat(),
    )


class CreateInstitutionRequest(BaseModel):
    """Request model for creating institution"""

    name: str
    domain: str
    subscription_tier: str = "free"
    default_grading_scheme_id: Optional[int] = None


@router.post("/institutions", response_model=InstitutionResponse, status_code=201)
async def create_institution(
    institution_data: CreateInstitutionRequest,
    request: Request,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """
    Create new institution (Superuser only)

    - Creates new institution with specified tier
    - Automatically sets quotas based on tier
    - Requires 'manage_users' permission
    """
    locale = get_request_locale(request, current_user)
    from config.features import SubscriptionTier, TIER_QUOTAS

    # Validate tier
    try:
        tier = SubscriptionTier(institution_data.subscription_tier)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=t("admin_invalid_subscription_tier", locale=locale),
        )

    # Check if domain already exists
    existing = (
        db.query(Institution)
        .filter(Institution.domain == institution_data.domain)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=t("admin_institution_domain_exists", locale=locale),
        )

    # Get quotas for tier
    quotas = TIER_QUOTAS[tier]

    # Validate the optional default scheme *before* persisting anything — a
    # brand-new institution owns no schemes yet, so only a system scheme (or
    # None) is valid; an institution-scoped id is rejected with 422. Passing
    # ``institution_id=None`` expresses exactly that (system-only) rule, and
    # validating up front means a rejection never emits a half-written INSERT
    # that would otherwise depend on connection-pool rollback to undo.
    validated_scheme_id = _validate_default_grading_scheme_id(
        db,
        institution_data.default_grading_scheme_id,
        None,
        locale,
    )

    # Create institution
    institution = Institution(
        name=institution_data.name,
        slug=institution_data.name.lower().replace(" ", "-"),
        domain=institution_data.domain,
        subscription_tier=tier.value,
        max_users=quotas["max_users"],
        max_documents=quotas["max_documents"],
        max_questions_per_month=quotas["max_questions_per_month"],
        is_active=True,
        default_grading_scheme_id=validated_scheme_id,
    )

    db.add(institution)
    db.commit()
    db.refresh(institution)

    return InstitutionResponse(
        id=institution.id,
        name=institution.name,
        slug=institution.slug,
        domain=institution.domain,
        subscription_tier=institution.subscription_tier,
        max_users=institution.max_users,
        max_documents=institution.max_documents,
        max_questions_per_month=institution.max_questions_per_month,
        is_active=institution.is_active,
        require_second_reviewer=institution.require_second_reviewer,
        default_grading_scheme_id=institution.default_grading_scheme_id,
        created_at=institution.created_at.isoformat(),
    )


@router.get(
    "/users/{user_id}/transfer-preview",
    response_model=TransferPreviewResponse,
)
async def preview_user_transfer(
    user_id: int,
    request: Request,
    target_institution_id: int = Query(..., gt=0),
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """Preview which artifacts would move if user is transferred (SuperAdmin only).

    Counts are scoped to the user's *current* institution. Excluded counts
    (students/classes/submissions) are informational.
    """
    from services.user_institution_transfer_service import (
        preview_transfer,
        TransferError,
    )

    locale = get_request_locale(request, current_user)
    try:
        preview = preview_transfer(db, user_id, target_institution_id)
    except TransferError as e:
        raise HTTPException(status_code=e.http_status, detail=t(e.code, locale=locale))

    return TransferPreviewResponse(
        source_institution_id=preview.source_institution_id,
        source_institution_name=preview.source_institution_name,
        target_institution_id=preview.target_institution_id,
        target_institution_name=preview.target_institution_name,
        transferable=TransferPreviewCountsModel(
            documents=preview.transferable.documents,
            exams=preview.transferable.exams,
            questions=preview.transferable.questions,
            tags=preview.transferable.tags,
        ),
        excluded=TransferExcludedCountsModel(
            students=preview.excluded.students,
            classes=preview.excluded.classes,
            submissions=preview.excluded.submissions,
        ),
    )


@router.post(
    "/users/{user_id}/transfer",
    response_model=TransferUserResponse,
)
async def transfer_user_to_institution(
    user_id: int,
    body: TransferUserRequest,
    request: Request,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """Move user (and optionally artifacts) to another institution (SuperAdmin only).

    Validation order (mirrors service-layer pre-condition checks):
    1. Authorization (SuperAdmin) — enforced by `Depends(get_current_superuser)`
    2. User exists — 404 admin_user_not_found
    3. user_id != current_user.id (self-move forbidden) — 400 admin_transfer_self_forbidden
    4. Target institution exists — 404 admin_institution_not_found
    5. target != source — 400 admin_transfer_same_institution
    """
    from services.user_institution_transfer_service import (
        transfer_user,
        TransferError,
        TransferFlags,
    )
    import tasks.rag_tasks as _rag_tasks

    locale = get_request_locale(request, current_user)
    flags = TransferFlags(
        documents=body.transfer_documents,
        exams=body.transfer_exams,
        questions=body.transfer_questions,
        tags=body.transfer_tags,
    )

    try:
        stats = transfer_user(
            db=db,
            user_id=user_id,
            target_institution_id=body.target_institution_id,
            flags=flags,
            actor=current_user,
        )
    except TransferError as e:
        raise HTTPException(status_code=e.http_status, detail=t(e.code, locale=locale))

    # Dispatch Qdrant re-index tasks AFTER commit. Service already committed.
    # If dispatch itself fails (broker outage, etc.), `documents.pending_reindex`
    # remains True as a future operational marker — there is no automatic
    # sweeper today; recovery is currently manual (TF-352 follow-up).
    for doc_id in stats.document_ids:
        try:
            _rag_tasks.reindex_document_to_institution.delay(doc_id)
        except Exception as exc:
            logger.error(
                "Failed to dispatch reindex for document %s: %s",
                doc_id,
                exc,
            )

    # Reload user for response (institution_id is now fresh after commit)
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        # Defensive (TF-371): transfer_user already proved the user exists
        # within the same transaction, so this is currently unreachable. Guard
        # anyway so a future refactor that weakens that transactional guarantee
        # fails loud with a 404 instead of an opaque AttributeError on
        # `user.roles` / `user.institution` below.
        raise HTTPException(
            status_code=404, detail=t("admin_user_not_found", locale=locale)
        )

    role_responses = []
    for role in user.roles:
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

    return TransferUserResponse(
        user=UserDetailResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            institution_id=user.institution_id,
            institution_name=user.institution.name if user.institution else "N/A",
            roles=role_responses,
            status=user.status,
            is_superuser=user.is_superuser,
            last_login_at=user.last_login_at.isoformat()
            if user.last_login_at
            else None,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat() if user.updated_at else None,
        ),
        transferred=TransferPreviewCountsModel(
            documents=stats.documents,
            exams=stats.exams,
            questions=stats.questions,
            tags=stats.tags,
        ),
    )
