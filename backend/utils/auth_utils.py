"""
Authentication Utilities für FastAPI
Dependencies für Token Validation und User Authentication
"""

import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.auth import User, UserStatus
from services.auth_service import AuthService

logger = logging.getLogger(__name__)

# HTTP Bearer Token Security Scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI Dependency: Get current authenticated user from JWT token

    Args:
        credentials: HTTP Bearer credentials
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Decode token
    payload = AuthService.decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user ID from token
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if token is revoked
    token_jti = payload.get("jti")
    if token_jti and AuthService.is_token_revoked(token_jti, db):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database with roles (needed for permission checks)
    user = (
        db.query(User)
        .options(joinedload(User.roles))
        .filter(User.id == int(user_id))
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if user.status != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User account is {user.status}",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    FastAPI Dependency: Get current active user

    Args:
        current_user: Current user from get_current_user

    Returns:
        User object

    Raises:
        HTTPException: If user is not active
    """
    if current_user.status != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is not active"
        )

    return current_user


async def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    """
    FastAPI Dependency: Get current superuser

    Args:
        current_user: Current user from get_current_user

    Returns:
        User object

    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    return current_user


def require_role(required_role: str):
    """
    FastAPI Dependency Factory: Require specific role

    Args:
        required_role: Role name required (admin, dozent, assistant, viewer)

    Returns:
        Dependency function

    Example:
        @router.get("/admin-only")
        async def admin_endpoint(user: User = Depends(require_role("admin"))):
            ...
    """

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.has_role(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )
        return current_user

    return role_checker


def require_permission(required_permission: str):
    """
    FastAPI Dependency Factory: Require specific permission

    Args:
        required_permission: Permission name required

    Returns:
        Dependency function

    Example:
        @router.post("/questions")
        async def create_question(user: User = Depends(require_permission("create_questions"))):
            ...
    """

    async def permission_checker(
        current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
    ) -> User:
        # Check permission
        has_perm = current_user.has_permission(required_permission)

        if not has_perm:
            # Audit log: Permission denied
            from services.audit_service import AuditService

            AuditService.log_permission_denied(
                db,
                current_user.id,
                action="access_endpoint",
                required_permission=required_permission,
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required_permission}' required",
            )
        return current_user

    return permission_checker


def enforce_resource_access(
    obj,
    user: User,
    action: str,
    db: Session,
    resource_type: str,
    owner_field: str = "user_id",
    request=None,
) -> None:
    """
    Enforce that user owns obj, or is superuser (which gets logged).

    Behavior:
        - obj is None                               → HTTPException 404
        - obj has no <owner_field> attribute        → HTTPException 500
        - obj.<owner_field> is None (orphan)        → return + warning log
        - obj.<owner_field> == user.id              → return
        - user.is_superuser                         → return + audit log
        - else                                      → HTTPException 403

    Orphan resources (owner_id is None) arise legitimately when a User row is
    soft-deleted via ON DELETE SET NULL. They are intentionally allowed for
    any authenticated user — treated as institution-shared. If you need
    stricter handling for a specific resource type, do not use this helper.

    Args:
        obj: The resource object to check (must have id and owner_field attributes).
        user: The authenticated user requesting access.
        action: Concrete action being performed (e.g. "process", "delete", "view").
        db: SQLAlchemy session, used for audit log.
        resource_type: Audit-log resource type (e.g. "document", "chat_session").
        owner_field: Attribute name on obj holding the owner user_id.
        request: Optional FastAPI Request for IP/user-agent in audit log.

    Raises:
        HTTPException 404 if obj is None.
        HTTPException 500 if obj does not have the requested owner_field
            (programmer error — caller passed wrong owner_field or model
            schema drifted; safer to fail loud than silently grant access).
        HTTPException 403 if user is neither owner nor superuser.
    """
    if obj is None:
        raise HTTPException(status_code=404, detail="Resource not found")

    if not hasattr(obj, owner_field):
        logger.error(
            f"enforce_resource_access: {type(obj).__name__} has no attribute "
            f"{owner_field!r} — programmer error or schema drift"
        )
        raise HTTPException(status_code=500, detail="Internal authorization error")

    owner_id = getattr(obj, owner_field)
    if owner_id is None:
        logger.warning(
            f"Orphan {resource_type} {getattr(obj, 'id', '?')} accessed by "
            f"user {user.id} (action={action!r})"
        )
        return

    if owner_id == user.id:
        return

    if user.is_superuser:
        from services.audit_service import AuditService

        AuditService.log_superuser_bypass(
            db=db,
            superuser=user,
            resource_type=resource_type,
            resource_id=getattr(obj, "id", None),
            action=action,
            owner_user_id=owner_id,
            request=request,
        )
        return

    raise HTTPException(status_code=403, detail="Access denied")


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    FastAPI Dependency: Get current user if authenticated, None otherwise
    Useful for endpoints that work with or without authentication

    Args:
        credentials: Optional HTTP Bearer credentials
        db: Database session

    Returns:
        User object or None
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = AuthService.decode_token(token)

        if not payload:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        # Check if token is revoked
        token_jti = payload.get("jti")
        if token_jti and AuthService.is_token_revoked(token_jti, db):
            return None

        user = db.query(User).filter(User.id == int(user_id)).first()

        if user and user.status == UserStatus.ACTIVE.value:
            return user

        return None
    except Exception:
        return None
