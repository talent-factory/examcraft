"""
Authentication Utilities für FastAPI
Dependencies für Token Validation und User Authentication
"""

import logging
from typing import Optional
from fastapi import Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session, joinedload, selectinload

from database import get_db
from models.auth import User, UserStatus
from models.org_unit import OrgUnit, UserOrgUnit
from services.auth_service import AuthService
from services.translation_service import get_request_locale
from utils.impersonation_context import (
    ImpersonationContext,
    get_impersonation_context,
    set_impersonation_context,
)
from errors import api_error

logger = logging.getLogger(__name__)

# HTTP Bearer Token Security Scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    request: Request = None,
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

    # No user is known yet on this path, so the locale can only come from
    # Accept-Language — get_request_locale falls back to "de" without one.
    locale = get_request_locale(request)
    bearer = {"WWW-Authenticate": "Bearer"}

    # Decode token
    payload = AuthService.decode_token(token)

    if not payload:
        raise api_error(
            status.HTTP_401_UNAUTHORIZED, "auth_token_invalid", locale, bearer
        )

    # Get user ID from token
    user_id: str = payload.get("sub")
    if user_id is None:
        raise api_error(
            status.HTTP_401_UNAUTHORIZED, "auth_token_invalid", locale, bearer
        )

    # Check if token is revoked
    token_jti = payload.get("jti")
    if token_jti and AuthService.is_token_revoked(token_jti, db):
        raise api_error(
            status.HTTP_401_UNAUTHORIZED, "auth_token_revoked", locale, bearer
        )

    # Get user from database with roles (needed for permission checks).
    # TF-637 review fix: has_permission() now also walks
    # org_unit_memberships -> org_unit -> role (Granted Role) on every call
    # where the direct-role loop above doesn't already match -- i.e. on the
    # entire 403 path, and any request whose permission comes from a
    # Granted Role. Without eager-loading that chain here, each of those
    # calls issues 1 + 2N lazy queries (N = number of org-unit
    # memberships) on this already-hot dependency. selectinload (not
    # joinedload) for the one-to-many memberships collection avoids a
    # fan-out join against the single-row User query above.
    user = (
        db.query(User)
        .options(
            joinedload(User.roles),
            selectinload(User.org_unit_memberships)
            .joinedload(UserOrgUnit.org_unit)
            .joinedload(OrgUnit.role),
        )
        .filter(User.id == int(user_id))
        .first()
    )

    if user is None:
        # TF-773 review: deliberately a distinct code from the 404
        # auth_user_not_found used by admin/user-lookup endpoints (auth.py).
        # This path means "a valid JWT no longer resolves to a user" (e.g.
        # deleted after the token was issued) — an authentication failure,
        # not a REST resource lookup, so it stays 401 with its own code
        # rather than reusing a 404 code under a different status.
        raise api_error(
            status.HTTP_401_UNAUTHORIZED, "auth_token_user_not_found", locale, bearer
        )

    # TF-741: recognize impersonation claims minted by
    # AuthService.create_impersonation_token and populate the
    # request-scoped ImpersonationContext from them. This is the
    # foundation the audit follow-up ticket (TF-742) will build on, and is
    # also what the account-security guard (block_during_impersonation)
    # reads.
    impersonator_id = payload.get("impersonator_id")
    impersonation_session_id = payload.get("impersonation_session_id")
    is_impersonating = (
        impersonator_id is not None and impersonation_session_id is not None
    )
    set_impersonation_context(
        ImpersonationContext(
            impersonator_id=impersonator_id,
            impersonation_session_id=impersonation_session_id,
            token_jti=token_jti,
        )
        if is_impersonating
        else None
    )

    # Check if user is active — skipped for impersonation tokens: the
    # ticket explicitly allows starting a session against a
    # suspended/inactive/pending user (support use case), which only
    # works end-to-end if this check doesn't then 403 every subsequent
    # request made with that token.
    if not is_impersonating and user.status != UserStatus.ACTIVE.value:
        # The user is known from here on, so their preferred_language wins
        # over Accept-Language.
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            "auth_account_status_invalid",
            get_request_locale(request, user),
            status=user.status,
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
    request: Request = None,
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
    # TF-741: same impersonation bypass as get_current_user — this
    # dependency re-checks status independently, so without this an
    # impersonated request for a suspended/inactive/pending user would
    # still 403 here even though get_current_user already let it through.
    if (
        get_impersonation_context() is None
        and current_user.status != UserStatus.ACTIVE.value
    ):
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            "auth_account_not_active",
            get_request_locale(request, current_user),
        )

    return current_user


def block_during_impersonation(
    request: Request,
    current_user: User = Depends(get_current_active_user),
) -> None:
    """FastAPI dependency: reject account-security actions during impersonation.

    TF-741 acceptance criterion: account-security actions are locked while
    an impersonation session is active (one test per locked action). Add
    as an extra ``Depends()`` on any endpoint that changes credentials,
    deletes the account, or changes billing.

    Depends on ``get_current_active_user`` (rather than reading the
    ImpersonationContext standalone) so FastAPI's dependency graph
    guarantees ``get_current_user`` has already run — and therefore
    already populated the ImpersonationContext for this request — before
    this check executes, regardless of parameter order on the endpoint.
    """
    if get_impersonation_context() is not None:
        locale = get_request_locale(request, current_user)
        raise api_error(
            status.HTTP_403_FORBIDDEN, "impersonation_action_locked", locale
        )


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
        raise api_error(
            status.HTTP_403_FORBIDDEN, "admin_insufficient_permissions", locale
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

    async def role_checker(
        current_user: User = Depends(get_current_user),
        request: Request = None,
    ) -> User:
        if not current_user.has_role(required_role):
            raise api_error(
                status.HTTP_403_FORBIDDEN,
                "auth_role_required",
                get_request_locale(request, current_user),
                role=required_role,
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
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        request: Request = None,
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

            raise api_error(
                status.HTTP_403_FORBIDDEN,
                "auth_permission_required",
                get_request_locale(request, current_user),
                permission=required_permission,
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
    locale = get_request_locale(request, user)

    if obj is None:
        raise api_error(404, "auth_resource_not_found", locale)

    if not hasattr(obj, owner_field):
        logger.error(
            f"enforce_resource_access: {type(obj).__name__} has no attribute "
            f"{owner_field!r} — programmer error or schema drift"
        )
        raise api_error(500, "auth_authorization_error", locale)

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
                raise api_error(403, "auth_access_denied", locale)
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

    raise api_error(403, "auth_access_denied", locale)


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
