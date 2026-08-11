"""
Authentication Utilities für FastAPI
Dependencies für Token Validation und User Authentication
"""

import logging
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.auth import User, UserStatus
from services.auth_service import AuthService
from services.translation_service import get_request_locale, t

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


async def get_current_superuser(
    request: Request, current_user: User = Depends(get_current_user)
) -> User:
    """
    FastAPI Dependency: Get current superuser

    Args:
        request: Current request, used to resolve the response locale
        current_user: Current user from get_current_user

    Returns:
        User object

    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        locale = get_request_locale(request, current_user)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=t("admin_insufficient_permissions", locale=locale),
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
    require_same_institution: bool = True,
) -> None:
    """
    Enforce that user owns obj, or is superuser (which gets logged).

    Behavior:
        - obj is None                               → HTTPException 404
        - obj has no <owner_field> attribute        → HTTPException 500
        - obj.institution_id != user.institution_id → HTTPException 403
          (when require_same_institution=True and obj has institution_id;
          superuser bypasses with audit log)
        - obj.<owner_field> is None (orphan)        → return + warning log
          (only after the institution check above passes)
        - obj.<owner_field> == user.id              → return
        - user.is_superuser                         → return + audit log
        - else                                      → HTTPException 403

    Tenant boundary: by default, the helper refuses cross-institution access
    even for orphan resources (owner_id is None). Previously the orphan branch
    returned success without checking institution_id, which meant a non-admin,
    non-superuser user from institution B could touch an orphan resource from
    institution A. Pass ``require_same_institution=False`` only when the
    resource is intentionally cross-tenant.

    Note: callers that need cross-owner DSGVO trails (delete_document,
    retry_generation) layer log_admin_cross_owner / log_superuser_bypass
    *outside* this helper for non-orphan paths. Orphan resources that pass
    the tenant check still return silently below — the orphan log line is a
    warning, not an audit entry.

    Args:
        obj: The resource object to check (must have id and owner_field attributes).
        user: The authenticated user requesting access.
        action: Concrete action being performed (e.g. "process", "delete", "view").
        db: SQLAlchemy session, used for audit log.
        resource_type: Audit-log resource type (e.g. "document", "chat_session").
        owner_field: Attribute name on obj holding the owner user_id.
        request: Optional FastAPI Request for IP/user-agent in audit log.
        require_same_institution: When True (default) and obj exposes an
            ``institution_id`` attribute, refuse access from users in a
            different institution. Superusers bypass with audit log.

    Raises:
        HTTPException 404 if obj is None.
        HTTPException 500 if obj does not have the requested owner_field
            (programmer error — caller passed wrong owner_field or model
            schema drifted; safer to fail loud than silently grant access).
        HTTPException 403 if user is neither owner nor superuser, or if
            require_same_institution=True and the resource belongs to a
            different institution.
    """
    if obj is None:
        raise HTTPException(status_code=404, detail="Resource not found")

    if not hasattr(obj, owner_field):
        logger.error(
            f"enforce_resource_access: {type(obj).__name__} has no attribute "
            f"{owner_field!r} — programmer error or schema drift"
        )
        raise HTTPException(status_code=500, detail="Internal authorization error")

    # Tenant boundary check FIRST — before owner check, so an orphan resource
    # in a different institution still rejects a non-superuser regardless of
    # owner_field state.
    if require_same_institution and hasattr(obj, "institution_id"):
        obj_institution_id = getattr(obj, "institution_id")
        user_institution_id = getattr(user, "institution_id", None)
        if obj_institution_id is not None and obj_institution_id != user_institution_id:
            if not user.is_superuser:
                logger.warning(
                    "enforce_resource_access: cross-institution access blocked "
                    "for %s id=%s (user.institution_id=%s, obj.institution_id=%s)",
                    resource_type,
                    getattr(obj, "id", "?"),
                    user_institution_id,
                    obj_institution_id,
                )
                raise HTTPException(status_code=403, detail="Access denied")
            # Superuser cross-institution access is allowed but audited
            # below in the bypass branch — fall through.

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
