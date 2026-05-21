"""Activity API — paginated, single-source-of-truth activity feed.

Multi-tenancy invariant: ``scope=institution`` MUST never leak across
tenants. The JOIN on ``users.institution_id`` enforces that, and the
route rejects callers without an ``institution_id`` so a NULL caller
cannot match other unassigned users.

The feed only surfaces successful actions (``status == "success"``);
failed generations are intentionally excluded from the activity stream.

Note: ``from __future__ import annotations`` is intentionally NOT used
here. Pydantic v2 cannot reliably resolve ``Literal[...]`` forward
references that the ``__future__`` import produces, leading to a
``ActivityItemOut is not fully defined`` error at request time on
Python 3.11. The native ``list[...]`` / ``int | None`` syntax already
works without the future import on our minimum Python (3.11+).
"""

import logging
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from database import get_db
from models.auth import AuditLog, User
from utils.audit_title import extract_audit_title
from utils.auth_utils import get_current_active_user


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/activity", tags=["Activity"])


# ---------------------------------------------------------------------------
# Activity-Type ↔ AuditLog.action mapping
# ---------------------------------------------------------------------------

ActivityType = Literal[
    "document_uploaded",
    "document_deleted",
    "questions_generated",
    "question_approved",
    "question_rejected",
    "exam_created",
    "exam_deleted",
]

# Activity-Type → audit_logs.action. Insertion order is intentionally
# the UI rendering order; the frontend type list mirrors this sequence.
TYPE_TO_ACTION: dict[ActivityType, str] = {
    "document_uploaded": "create_document",
    "document_deleted": "delete_document",
    "questions_generated": "create_question",
    "question_approved": "approve_question",
    "question_rejected": "reject_question",
    "exam_created": "create_exam",
    "exam_deleted": "delete_exam",
}

ACTION_TO_TYPE: dict[str, ActivityType] = {
    action: t for t, action in TYPE_TO_ACTION.items()
}

SUPPORTED_TYPES: tuple[ActivityType, ...] = tuple(TYPE_TO_ACTION.keys())
SUPPORTED_ACTIONS: tuple[str, ...] = tuple(TYPE_TO_ACTION.values())

TITLE_KEYS_BY_TYPE: dict[ActivityType, tuple[str, ...]] = {
    "document_uploaded": ("original_filename", "filename"),
    "document_deleted": ("original_filename", "filename"),
    "questions_generated": ("topic",),
    "question_approved": ("topic",),
    "question_rejected": ("topic",),
    "exam_created": ("title",),
    "exam_deleted": ("title",),
}


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

_STRICT_OUT = ConfigDict(extra="forbid")


class ActivityItemOut(BaseModel):
    model_config = _STRICT_OUT

    id: str
    type: ActivityType
    title: str
    timestamp: datetime
    # Only populated when scope=institution so the frontend can show
    # "von User #X" without a second round-trip.
    actor_user_id: int | None = None


class ActivityListOut(BaseModel):
    model_config = _STRICT_OUT

    items: list[ActivityItemOut]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    has_more: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_types(types_csv: str | None) -> list[str] | None:
    """Parse ``types=document_uploaded,exam_created`` → list of actions.

    Returns:
        ``None`` if no ``types`` filter was supplied → caller falls
        back to the implicit "all supported actions" filter.
        Otherwise a list of audit-log action strings ready to drop
        into a ``WHERE action IN (...)`` clause.

    Raises:
        HTTPException(422) if any token is unknown — fail loud rather
        than silently returning empty results, which would look like a
        backend bug to the caller.
    """
    if types_csv is None:
        return None
    tokens = [tok.strip() for tok in types_csv.split(",") if tok.strip()]
    if not tokens:
        return None
    actions: list[str] = []
    unknown: list[str] = []
    for tok in tokens:
        action = TYPE_TO_ACTION.get(tok)  # type: ignore[arg-type]
        if action is None:
            unknown.append(tok)
        else:
            actions.append(action)
    if unknown:
        # Surface to ops at WARNING so a frontend regression emitting
        # bad tokens stands out from normal traffic, not just in 422
        # response bodies.
        logger.warning("Activity types filter rejected unknown tokens: %s", unknown)
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Unbekannter Activity-Type",
                "unknown_types": unknown,
                "supported_types": list(SUPPORTED_TYPES),
            },
        )
    return actions


def _row_to_item(log: AuditLog, *, include_actor: bool) -> ActivityItemOut | None:
    activity_type = ACTION_TO_TYPE.get(log.action)
    if activity_type is None:
        # Defence against future drift between SUPPORTED_ACTIONS and
        # ACTION_TO_TYPE — should be unreachable under the WHERE clause.
        # ERROR (not WARNING) so Sentry catches the drift: when this
        # fires, the WHERE clause matched a row whose action lacks a
        # mapping, and the response will report total > len(items).
        logger.error(
            "AuditLog id=%s has unmapped action=%s — skipping in activity feed; "
            "total/items pagination will be off until the map is updated",
            log.id,
            log.action,
        )
        return None
    title = extract_audit_title(
        log,
        fallback_title=str(log.resource_id) if log.resource_id else "—",
        preferred_keys=TITLE_KEYS_BY_TYPE.get(activity_type, ()),
    )
    return ActivityItemOut(
        id=f"audit_{log.id}",
        type=activity_type,
        title=title,
        timestamp=_to_utc(log.created_at),
        actor_user_id=log.user_id if include_actor else None,
    )


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.get("", response_model=ActivityListOut)
def list_activity(
    scope: Literal["own", "institution"] = Query(default="own"),
    types: str | None = Query(
        default=None,
        description=(
            "Comma-separated activity types — one or more of: "
            "document_uploaded, document_deleted, questions_generated, "
            "question_approved, question_rejected, exam_created, exam_deleted"
        ),
    ),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ActivityListOut:
    """Paginated activity feed.

    Multi-tenancy: ``scope=institution`` JOINs ``users`` and filters
    on the caller's ``institution_id`` — events from other tenants
    are unreachable. ``scope=institution`` is intentionally not
    RBAC-gated; institution-internal visibility is by-design.
    """
    actions_filter = _parse_types(types)

    # Always restrict to the supported actions: an action like
    # ``login`` would otherwise leak through the implicit "all
    # actions" path into the response, with no Activity-Type to
    # render on the frontend.
    base_action_filter = (
        actions_filter if actions_filter is not None else list(SUPPORTED_ACTIONS)
    )

    base_query = db.query(AuditLog).filter(
        AuditLog.action.in_(base_action_filter),
        AuditLog.status == "success",
    )

    if scope == "own":
        base_query = base_query.filter(AuditLog.user_id == current_user.id)
    else:
        # Defence-in-depth: a user without an institution must not be
        # able to widen the query, otherwise the JOIN below would
        # match every other unassigned user across tenants. The
        # User.institution_id NOT NULL constraint already blocks this,
        # but an explicit 403 keeps the contract checkable.
        if current_user.institution_id is None:
            raise HTTPException(
                status_code=403,
                detail="scope=institution requires institution membership",
            )
        # JOIN users and filter on the caller's institution. The JOIN
        # strips audit rows whose user_id is NULL (FK ON DELETE SET
        # NULL) — fine, those events have no owner and can't be
        # assigned to any institution anyway.
        base_query = base_query.join(User, AuditLog.user_id == User.id).filter(
            User.institution_id == current_user.institution_id
        )

    total = base_query.with_entities(AuditLog.id).count()

    rows = (
        base_query.order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    include_actor = scope == "institution"
    items = [
        item
        for item in (_row_to_item(log, include_actor=include_actor) for log in rows)
        if item is not None
    ]
    return ActivityListOut(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(items) < total,
    )
