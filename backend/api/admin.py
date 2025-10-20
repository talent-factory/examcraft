"""
Admin API Endpoints
User Management, Role Assignment, Institution Management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
import logging
import json

from database import get_db
from models.auth import User, Role, Institution, UserStatus, UserRole
from services.auth_service import AuthService
from utils.auth_utils import get_current_user, require_permission

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin"])


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
    domain: str
    subscription_tier: str
    max_users: int
    max_documents: int
    max_questions_per_month: int
    is_active: bool
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
    current_user: User = Depends(require_permission("manage_users")),
    db: Session = Depends(get_db)
):
    """
    List all users (Admin only)
    
    - Supports pagination
    - Supports search by email, first_name, last_name
    - Supports filtering by role, status, institution
    - Requires 'manage_users' permission
    """
    # Build query
    query = db.query(User)
    
    # Apply search filter
    if search:
        search_filter = or_(
            User.email.ilike(f"%{search}%"),
            User.first_name.ilike(f"%{search}%"),
            User.last_name.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    # Apply role filter
    if role:
        query = query.join(User.roles).filter(Role.name == role)
    
    # Apply status filter
    if status:
        query = query.filter(User.status == status)
    
    # Apply institution filter
    if institution_id:
        query = query.filter(User.institution_id == institution_id)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    users = query.offset(offset).limit(page_size).all()
    
    # Build response
    user_items = []
    for user in users:
        user_items.append(UserListItem(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            institution_id=user.institution_id,
            institution_name=user.institution.name if user.institution else "N/A",
            roles=[role.name for role in user.roles],
            status=user.status,
            is_superuser=user.is_superuser,
            last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
            created_at=user.created_at.isoformat()
        ))
    
    total_pages = (total + page_size - 1) // page_size
    
    return UserListResponse(
        users=user_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_permission("manage_users")),
    db: Session = Depends(get_db)
):
    """
    Get user details (Admin only)
    
    - Returns full user information
    - Includes roles with permissions
    - Requires 'manage_users' permission
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
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
        
        role_responses.append(RoleResponse(
            id=role.id,
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            permissions=permissions,
            is_system_role=role.is_system_role,
            created_at=role.created_at.isoformat()
        ))
    
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
        updated_at=user.updated_at.isoformat() if user.updated_at else None
    )


@router.patch("/users/{user_id}", response_model=UserDetailResponse)
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    current_user: User = Depends(require_permission("manage_users")),
    db: Session = Depends(get_db)
):
    """
    Update user details (Admin only)

    - Updates user information
    - Requires 'manage_users' permission
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update fields
    if request.first_name is not None:
        user.first_name = request.first_name

    if request.last_name is not None:
        user.last_name = request.last_name

    if request.email is not None:
        # Check if email is already taken
        existing_user = db.query(User).filter(
            User.email == request.email,
            User.id != user_id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
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

        role_responses.append(RoleResponse(
            id=role.id,
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            permissions=permissions,
            is_system_role=role.is_system_role,
            created_at=role.created_at.isoformat()
        ))

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
        updated_at=user.updated_at.isoformat() if user.updated_at else None
    )


@router.patch("/users/{user_id}/status", response_model=UserDetailResponse)
async def update_user_status(
    user_id: int,
    request: UpdateUserStatusRequest,
    current_user: User = Depends(require_permission("manage_users")),
    db: Session = Depends(get_db)
):
    """
    Update user status (Admin only)

    - Activates or deactivates user
    - Requires 'manage_users' permission
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent admin from deactivating themselves
    if user.id == current_user.id and request.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
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

        role_responses.append(RoleResponse(
            id=role.id,
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            permissions=permissions,
            is_system_role=role.is_system_role,
            created_at=role.created_at.isoformat()
        ))

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
        updated_at=user.updated_at.isoformat() if user.updated_at else None
    )


@router.post("/users/{user_id}/roles", response_model=UserDetailResponse)
async def assign_role_to_user(
    user_id: int,
    request: AssignRoleRequest,
    current_user: User = Depends(require_permission("manage_users")),
    db: Session = Depends(get_db)
):
    """
    Assign role to user (Admin only)

    - Adds role to user
    - Requires 'manage_users' permission
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    role = db.query(Role).filter(Role.id == request.role_id).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    # Check if user already has this role
    if role in user.roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has this role"
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

        role_responses.append(RoleResponse(
            id=r.id,
            name=r.name,
            display_name=r.display_name,
            description=r.description,
            permissions=permissions,
            is_system_role=r.is_system_role,
            created_at=r.created_at.isoformat()
        ))

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
        updated_at=user.updated_at.isoformat() if user.updated_at else None
    )


@router.delete("/users/{user_id}/roles/{role_id}", response_model=UserDetailResponse)
async def remove_role_from_user(
    user_id: int,
    role_id: int,
    current_user: User = Depends(require_permission("manage_users")),
    db: Session = Depends(get_db)
):
    """
    Remove role from user (Admin only)

    - Removes role from user
    - Requires 'manage_users' permission
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    role = db.query(Role).filter(Role.id == role_id).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    # Check if user has this role
    if role not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not have this role"
        )

    # Prevent removing last role
    if len(user.roles) == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove last role from user"
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

        role_responses.append(RoleResponse(
            id=r.id,
            name=r.name,
            display_name=r.display_name,
            description=r.description,
            permissions=permissions,
            is_system_role=r.is_system_role,
            created_at=r.created_at.isoformat()
        ))

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
        updated_at=user.updated_at.isoformat() if user.updated_at else None
    )


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    current_user: User = Depends(require_permission("manage_users")),
    db: Session = Depends(get_db)
):
    """
    List all roles (Admin only)

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

        role_responses.append(RoleResponse(
            id=role.id,
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            permissions=permissions,
            is_system_role=role.is_system_role,
            created_at=role.created_at.isoformat()
        ))

    return role_responses


@router.get("/institutions", response_model=List[InstitutionResponse])
async def list_institutions(
    current_user: User = Depends(require_permission("manage_users")),
    db: Session = Depends(get_db)
):
    """
    List all institutions (Admin only)

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
            created_at=inst.created_at.isoformat()
        )
        for inst in institutions
    ]

