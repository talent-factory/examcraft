"""Audit-Log read API (TF-415) — in-app, RBAC-scoped audit view.

GET /api/v1/audit. Scope is derived server-side from the caller's role via
services.audit_query_service.resolve_scope (SuperAdmin: all institutions + all
categories + PII; Institution-Admin: own institution + business/admin, no PII).
Every successful query writes a `view_audit_log` event (audit-the-auditor).

No ``from __future__ import annotations`` — see api/activity.py for the
Pydantic-v2 Literal forward-ref rationale.
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from database import get_db
from models.auth import User
from services.audit_query_service import query_audit_logs, resolve_scope
from services.audit_service import AUDIT_CATEGORIES, AuditService, category_for_action
from utils.auth_utils import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/audit", tags=["Audit"])

_VALID_CATEGORIES = frozenset(AUDIT_CATEGORIES)
_STRICT_OUT = ConfigDict(extra="forbid")


class AuditLogOut(BaseModel):
    model_config = _STRICT_OUT

    id: int
    created_at: datetime
    user_id: int | None = None
    actor: str | None = None
    impersonator: str | None = None
    action: str
    category: str
    resource_type: str | None = None
    resource_id: str | None = None
    status: str
    error_message: str | None = None
    additional_data: dict | None = (
        None  # SuperAdmin only (free-form blob, may carry PII)
    )
    ip_address: str | None = None  # SuperAdmin only
    user_agent: str | None = None  # SuperAdmin only


class AuditLogListOut(BaseModel):
    model_config = _STRICT_OUT

    items: list[AuditLogOut]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    has_more: bool = False


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_additional(raw):
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except (json.JSONDecodeError, TypeError):
        return None


def _row_to_out(log, *, can_see_pii: bool) -> AuditLogOut:
    actor = None
    if log.user is not None:
        actor = log.user.full_name or log.user.email
    impersonator = None
    if log.impersonator is not None:
        impersonator = log.impersonator.full_name or log.impersonator.email
    return AuditLogOut(
        id=log.id,
        created_at=_to_utc(log.created_at),
        user_id=log.user_id,
        actor=actor,
        impersonator=impersonator,
        action=log.action,
        category=category_for_action(log.action),
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        status=log.status,
        error_message=log.error_message,
        # additional_data is an unstructured JSON blob whose contents vary by
        # call-site and can carry PII (emails, changed-field values). Gate it on
        # the same can_see_pii flag as ip/user_agent so a future business/admin
        # call-site that logs sensitive data never silently surfaces it to an
        # institution-admin. SuperAdmin (can_see_pii=True) still sees everything.
        additional_data=_parse_additional(log.additional_data) if can_see_pii else None,
        ip_address=log.ip_address if can_see_pii else None,
        user_agent=log.user_agent if can_see_pii else None,
    )


@router.get("", response_model=AuditLogListOut)
def list_audit_logs(
    category: str | None = Query(
        default=None, description="CSV: business,admin,auth,security"
    ),
    action: str | None = Query(default=None),
    status: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    institution_id: int | None = Query(
        default=None, description="SuperAdmin-only filter"
    ),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuditLogListOut:
    """RBAC-scoped audit log listing. Scope derived from the caller's role."""
    scope = resolve_scope(current_user)  # raises 403 for non-admins

    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must be <= date_to")

    categories = None
    if category:
        categories = [c.strip() for c in category.split(",") if c.strip()]
        invalid = [c for c in categories if c not in _VALID_CATEGORIES]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail={"message": "Unknown category", "unknown": invalid},
            )

    rows, total = query_audit_logs(
        db,
        scope,
        categories=categories,
        action=action,
        status=status,
        resource_type=resource_type,
        user_id=user_id,
        institution_id=institution_id if scope.is_superuser else None,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )

    items = [_row_to_out(r, can_see_pii=scope.can_see_pii) for r in rows]

    # Audit-the-auditor: record who queried what (security category → super-only).
    # Audit write has its own exception handling and never raises; result already assembled.
    AuditService.log_action(
        db=db,
        action=AuditService.ACTION_VIEW_AUDIT_LOG,
        user_id=current_user.id,
        resource_type="audit_log",
        additional_data={
            "categories": categories,
            "action": action,
            "status": status,
            "resource_type": resource_type,
            "target_user_id": user_id,
            "institution_id": institution_id,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "result_count": len(items),
            "total": total,
        },
        request=request,
    )

    return AuditLogListOut(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(items) < total,
    )
