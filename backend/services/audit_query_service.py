"""Audit-Log read/query service (TF-415).

Read path for the in-app audit view. The visible scope is derived server-side
from the caller's role — there is NO client-settable scope parameter. Kept
separate from the write-focused AuditService so each module has one clear
responsibility.

No ``from __future__ import annotations`` here: not needed, and we keep this
module consistent with api/activity.py's deliberate avoidance of it.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, contains_eager, joinedload

from models.auth import AuditLog, User
from services.audit_service import ACTIONS_BY_CATEGORY, AUDIT_CATEGORIES

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuditScope:
    """Server-derived visibility scope for an audit query.

    institution_id: None → all institutions (SuperAdmin); else pinned tenant.
    allowed_categories: categories the caller may ever see.
    can_see_pii: whether ip_address / user_agent may be returned.
    is_superuser: drives orphan visibility + the no-action-restriction path.
    """

    institution_id: Optional[int]
    allowed_categories: frozenset[str]
    can_see_pii: bool
    is_superuser: bool


def _is_admin_role(user: User) -> bool:
    """Mirror of api.admin._is_admin_role — checks the 'admin' role by name."""
    return any(role.name == "admin" for role in user.roles)


def resolve_scope(user: User) -> AuditScope:
    """Derive the audit visibility scope from the caller's role.

    Raises HTTPException 403 for non-admins and for institution admins without
    an institution (defence-in-depth, mirrors api/activity.py).
    """
    if user.is_superuser:
        return AuditScope(
            institution_id=None,
            allowed_categories=frozenset(AUDIT_CATEGORIES),
            can_see_pii=True,
            is_superuser=True,
        )
    if _is_admin_role(user):
        if user.institution_id is None:
            raise HTTPException(
                status_code=403,
                detail="Audit view requires institution membership",
            )
        return AuditScope(
            institution_id=user.institution_id,
            allowed_categories=frozenset({"business", "admin"}),
            can_see_pii=False,
            is_superuser=False,
        )
    raise HTTPException(
        status_code=403,
        detail="Not enough permissions to view audit logs",
    )


def query_audit_logs(
    db: Session,
    scope: AuditScope,
    *,
    categories: Optional[list] = None,
    action: Optional[str] = None,
    status: Optional[str] = None,
    resource_type: Optional[str] = None,
    user_id: Optional[int] = None,
    institution_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 25,
    offset: int = 0,
):
    """Return (rows, total) for the given scope + filters.

    Tenancy model (deliberate): scope is by the *actor's* institution
    (``AuditLog.user_id -> User.institution_id``), i.e. an institution-admin
    sees actions performed *by* members of their institution — not actions
    performed by outsiders *on* their institution's resources. This matches the
    "what did my institution's users do" intent; resource-owner scoping would be
    a different feature.

    Scoping rules:
      - Institution-admin: INNER JOIN users + filter institution_id. The INNER
        JOIN strips orphan rows (user_id NULL) — desired (no owner → no tenant).
      - SuperAdmin: LEFT OUTER JOIN users so orphan rows stay visible; optional
        institution_id filter.
    Category rules:
      - requested categories must be a subset of scope.allowed_categories (403).
      - requested → action IN (union of those categories' actions).
      - no request + admin → action IN (business+admin) (fail-closed: excludes
        uncategorized actions).
      - no request + superuser → no action restriction (sees uncategorized too).
    """
    if categories:
        invalid = [c for c in categories if c not in scope.allowed_categories]
        if invalid:
            raise HTTPException(
                status_code=403,
                detail=f"Categories not permitted for your role: {invalid}",
            )
        requested = set(categories)
    else:
        requested = None

    q = db.query(AuditLog)

    # impersonator (TF-742) is a second, unrelated relationship to the same
    # `users` table -- eager-loaded via a plain joinedload on its own alias
    # rather than folded into the contains_eager(AuditLog.user) chain above,
    # which is bound to the *scoping* join on User. It is deliberately not
    # institution-scoped: an institution-admin must see a SuperAdmin's own
    # impersonation of one of their institution's users, scoping is already
    # enforced via the target (AuditLog.user_id -> User.institution_id).
    if scope.institution_id is not None:
        q = (
            q.join(User, AuditLog.user_id == User.id)
            .filter(User.institution_id == scope.institution_id)
            .options(contains_eager(AuditLog.user), joinedload(AuditLog.impersonator))
        )
    else:
        q = q.outerjoin(User, AuditLog.user_id == User.id).options(
            contains_eager(AuditLog.user), joinedload(AuditLog.impersonator)
        )
        if institution_id is not None:
            q = q.filter(User.institution_id == institution_id)

    if requested is not None:
        actions = set().union(
            *(ACTIONS_BY_CATEGORY[c] for c in requested)
        )  # requested is non-empty (guarded above)
        q = q.filter(AuditLog.action.in_(actions))
    elif not scope.is_superuser:
        actions = set().union(
            *(ACTIONS_BY_CATEGORY[c] for c in scope.allowed_categories)
        )
        q = q.filter(AuditLog.action.in_(actions))

    if user_id is not None:
        if scope.institution_id is not None:
            target = db.get(User, user_id)
            if target is None or target.institution_id != scope.institution_id:
                raise HTTPException(
                    status_code=403, detail="user_id outside your institution"
                )
        q = q.filter(AuditLog.user_id == user_id)

    if action is not None:
        q = q.filter(AuditLog.action == action)
    if status is not None:
        q = q.filter(AuditLog.status == status)
    if resource_type is not None:
        q = q.filter(AuditLog.resource_type == resource_type)
    if date_from is not None:
        q = q.filter(AuditLog.created_at >= date_from)
    if date_to is not None:
        q = q.filter(AuditLog.created_at <= date_to)

    total = q.with_entities(AuditLog.id).count()
    rows = q.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    return rows, total
