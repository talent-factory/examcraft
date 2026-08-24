"""OrgUnit CRUD API (department/team hierarchy) -- stage 0 foundation.

Design: docs/superpowers/specs/2026-08-07-org-unit-hierarchie-design.md
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.auth import Role, User
from models.org_unit import KNOWN_UNIT_TYPES, OrgUnit, UserOrgUnit
from services.audit_service import AuditService
from services.org_unit_service import (
    assign_user_to_org_unit,
    create_org_unit,
    delete_org_unit,
    get_descendant_counts_for_institution,
    get_descendant_ids,
    move_org_unit,
    remove_user_from_org_unit,
    validate_sibling_name_unique,
)
from utils.auth_utils import get_current_active_user, require_permission


_STRICT_OUT = ConfigDict(extra="forbid")

router = APIRouter(prefix="/api/v1/org-units", tags=["OrgUnits"])


class OrgUnitOut(BaseModel):
    model_config = _STRICT_OUT

    id: int
    parent_org_unit_id: int | None
    unit_type: str
    name: str
    descendant_count: int
    role_id: int | None
    role_name: str | None
    created_at: datetime
    updated_at: datetime


class OrgUnitListOut(BaseModel):
    model_config = _STRICT_OUT

    items: list[OrgUnitOut]


# `from __future__ import annotations` turns the field annotations into
# strings, and main.py loads this module via spec_from_file_location under a
# synthetic name — so Pydantic can't reliably resolve `datetime` (OrgUnitOut)
# or the nested `list[OrgUnitOut]` (OrgUnitListOut) once many other modules
# are already loaded in the same process (same TF-435 pattern as
# PushJobOut in moodle_feedback_push.py). Rebuild eagerly here, where both
# names are in the module namespace, so the schema is fully defined under
# every load path.
OrgUnitOut.model_rebuild()
OrgUnitListOut.model_rebuild()


class OrgUnitCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    unit_type: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    parent_org_unit_id: int | None = None
    role_id: int | None = None

    @field_validator("unit_type")
    @classmethod
    def _unit_type_must_be_known(cls, value: str) -> str:
        # KNOWN_UNIT_TYPES is deliberately not a DB enum (see models/org_unit.py)
        # -- this validation sits only at the API boundary, so a typo from the
        # admin UI doesn't unnoticedly create a new "level". Internal callers
        # of the service functions remain unrestricted.
        if value not in KNOWN_UNIT_TYPES:
            raise ValueError(
                "unit_type muss einer der bekannten Werte sein: "
                + ", ".join(KNOWN_UNIT_TYPES)
            )
        return value


class OrgUnitUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=200)
    parent_org_unit_id: int | None = Field(default=None)
    move_to_root: bool = False
    role_id: int | None = Field(default=None)


class MembershipCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: int
    role: str | None = Field(default=None, max_length=50)


def _load_org_unit_for_user(*, db: Session, user: User, org_unit_id: int) -> OrgUnit:
    """Load an OrgUnit for the current institution; 404 otherwise.

    404 (not 403) is intentional: revealing existence-but-no-access leaks
    information about other tenants (matches student_classes.py pattern).
    """
    org_unit = (
        db.query(OrgUnit)
        .filter(
            OrgUnit.id == org_unit_id,
            OrgUnit.institution_id == user.institution_id,
        )
        .one_or_none()
    )
    if org_unit is None:
        raise HTTPException(status_code=404, detail="OrgUnit nicht gefunden")
    return org_unit


def _is_admin_role(user: User) -> bool:
    """Mirror of api.admin._is_admin_role -- checks the 'admin' role by name.

    Local copy rather than importing from api.admin (established pattern,
    see services/audit_query_service.py) to avoid cross-API-module coupling.
    """
    return any(role.name == "admin" for role in user.roles)


def _load_role_for_institution(
    *, db: Session, role_id: int, current_user: User
) -> Role:
    """Load a Role by id; 403 if the caller may not grant it, 404 if unknown.

    Role is global (no institution_id, TF-603/621), so unlike
    ``_load_org_unit_for_user`` there is no institution-scoping check on the
    Role lookup itself. Granting one *is* still access-controlled, though
    (TF-637 review fix): every OrgUnit endpoint here is gated only by the
    routinely-grantable ``manage_org_units`` permission, which -- without
    this check -- would let any holder grant themselves the global
    ``admin`` role via an OrgUnit and then self-assign membership into it,
    completely bypassing the stricter write-access gate that protects
    *direct* role assignment (``_require_write_access`` /
    ``api/admin.py::assign_role_to_user``, which requires superuser or the
    "admin" role). Mirroring that same gate here keeps both role-granting
    paths at parity instead of one being a backdoor around the other. Only
    gates *granting* a role -- clearing one (``role_id=None``) never
    reaches this function, since it can't escalate anything.
    """
    if not (current_user.is_superuser or _is_admin_role(current_user)):
        raise HTTPException(
            status_code=403,
            detail="Nur Admins duerfen einer Org-Unit eine Rolle verleihen",
        )
    role = db.query(Role).filter(Role.id == role_id).one_or_none()
    if role is None:
        raise HTTPException(status_code=404, detail="Role nicht gefunden")
    return role


def _to_out(org_unit: OrgUnit, descendant_count: int) -> OrgUnitOut:
    return OrgUnitOut(
        id=org_unit.id,
        parent_org_unit_id=org_unit.parent_org_unit_id,
        unit_type=org_unit.unit_type,
        name=org_unit.name,
        descendant_count=descendant_count,
        role_id=org_unit.role_id,
        role_name=org_unit.role.display_name if org_unit.role else None,
        created_at=org_unit.created_at,
        updated_at=org_unit.updated_at,
    )


def _to_out_single(db: Session, org_unit: OrgUnit) -> OrgUnitOut:
    """``_to_out`` for a single, freshly-loaded OrgUnit (create/update/delete).

    One recursive-CTE call, not the N+1 pattern -- for the list endpoint use
    ``get_descendant_counts_for_institution`` instead (one query for all rows).
    """
    descendant_count = len(get_descendant_ids(db, org_unit.id)) - 1
    return _to_out(org_unit, descendant_count)


@router.get("", response_model=OrgUnitListOut)
async def list_org_units(
    current_user: User = Depends(require_permission("manage_org_units")),
    db: Session = Depends(get_db),
) -> OrgUnitListOut:
    rows = (
        db.query(OrgUnit)
        .options(joinedload(OrgUnit.role))
        .filter(OrgUnit.institution_id == current_user.institution_id)
        .order_by(OrgUnit.name)
        .all()
    )
    counts = get_descendant_counts_for_institution(db, current_user.institution_id)
    return OrgUnitListOut(items=[_to_out(row, counts.get(row.id, 0)) for row in rows])


@router.get("/mine", response_model=OrgUnitListOut)
async def list_my_org_units(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> OrgUnitListOut:
    """OrgUnits the caller is a member of (TF-620).

    Deliberately **not** gated by ``manage_org_units`` — every authenticated
    user needs this to pick a target OrgUnit for the ``team`` document
    visibility tier, not just admins. Scoped to the caller's own
    ``UserOrgUnit`` memberships within their institution (no institution-wide
    listing here; that stays admin-only via ``list_org_units`` above).
    """
    if current_user.institution_id is None:
        return OrgUnitListOut(items=[])
    rows = (
        db.query(OrgUnit)
        .options(joinedload(OrgUnit.role))
        .join(UserOrgUnit, UserOrgUnit.org_unit_id == OrgUnit.id)
        .filter(
            UserOrgUnit.user_id == current_user.id,
            OrgUnit.institution_id == current_user.institution_id,
        )
        .order_by(OrgUnit.name)
        .all()
    )
    counts = get_descendant_counts_for_institution(db, current_user.institution_id)
    return OrgUnitListOut(items=[_to_out(row, counts.get(row.id, 0)) for row in rows])


@router.post("", response_model=OrgUnitOut, status_code=status.HTTP_201_CREATED)
async def create_org_unit_endpoint(
    body: OrgUnitCreateIn,
    http_request: Request,
    current_user: User = Depends(require_permission("manage_org_units")),
    db: Session = Depends(get_db),
) -> OrgUnitOut:
    if body.parent_org_unit_id is not None:
        _load_org_unit_for_user(
            db=db, user=current_user, org_unit_id=body.parent_org_unit_id
        )
    if body.role_id is not None:
        _load_role_for_institution(
            db=db, role_id=body.role_id, current_user=current_user
        )
    try:
        org_unit = create_org_unit(
            db,
            institution_id=current_user.institution_id,
            unit_type=body.unit_type,
            name=body.name,
            parent_org_unit_id=body.parent_org_unit_id,
            role_id=body.role_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if body.role_id is not None:
        AuditService.log_event_best_effort(
            db=db,
            action=AuditService.ACTION_SET_ORG_UNIT_ROLE,
            user_id=current_user.id,
            resource_type=AuditService.RESOURCE_ORG_UNIT,
            resource_id=org_unit.id,
            additional_data={"role_id": body.role_id},
            request=http_request,
        )

    return _to_out_single(db, org_unit)


@router.patch("/{org_unit_id}", response_model=OrgUnitOut)
async def update_org_unit_endpoint(
    org_unit_id: int,
    body: OrgUnitUpdateIn,
    http_request: Request,
    current_user: User = Depends(require_permission("manage_org_units")),
    db: Session = Depends(get_db),
) -> OrgUnitOut:
    org_unit = _load_org_unit_for_user(
        db=db, user=current_user, org_unit_id=org_unit_id
    )

    if body.name is not None:
        org_unit.name = body.name

    fields_set = body.model_fields_set

    # Granted Role (TF-637). Staged on the ORM object here, not committed
    # yet -- whichever branch below runs next (move_org_unit or the plain
    # rename branch) commits the whole pending transaction, this included.
    # Audit-logged once after the fact, from the diff, so it fires exactly
    # once regardless of which branch actually persisted it.
    role_id_changed = False
    old_role_id = org_unit.role_id
    if "role_id" in fields_set:
        if body.role_id is not None:
            _load_role_for_institution(
                db=db, role_id=body.role_id, current_user=current_user
            )
        if body.role_id != old_role_id:
            org_unit.role_id = body.role_id
            role_id_changed = True

    if (
        body.move_to_root
        and "parent_org_unit_id" in fields_set
        and body.parent_org_unit_id is not None
    ):
        # Mirror-image of the null-parent-without-move_to_root ambiguity
        # below: move_to_root=true together with an explicit non-null
        # parent_org_unit_id is contradictory. Silently dropping the parent
        # value (the previous behaviour) is exactly the kind of silent
        # no-op / API-contract footgun that ambiguity is rejected for.
        raise HTTPException(
            status_code=422,
            detail=(
                "move_to_root: true zusammen mit einem nicht-null "
                "parent_org_unit_id ist mehrdeutig -- sende nur eines von "
                "beiden."
            ),
        )
    elif body.move_to_root:
        try:
            move_org_unit(db, org_unit, None)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    elif "parent_org_unit_id" in fields_set and body.parent_org_unit_id is not None:
        _load_org_unit_for_user(
            db=db, user=current_user, org_unit_id=body.parent_org_unit_id
        )
        try:
            move_org_unit(db, org_unit, body.parent_org_unit_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    elif "parent_org_unit_id" in fields_set and body.parent_org_unit_id is None:
        # Explicitly sent null without move_to_root is ambiguous -- rather
        # than silently having no effect, reject it (a silent no-op instead
        # of a detach would be an API-contract footgun).
        raise HTTPException(
            status_code=422,
            detail=(
                "parent_org_unit_id: null ist mehrdeutig -- verwende "
                "move_to_root: true, um eine OrgUnit auf oberste Ebene zu "
                "verschieben."
            ),
        )
    else:
        if body.name is not None:
            try:
                validate_sibling_name_unique(
                    db,
                    institution_id=current_user.institution_id,
                    parent_org_unit_id=org_unit.parent_org_unit_id,
                    name=body.name,
                    exclude_id=org_unit.id,
                )
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
        db.commit()
        db.refresh(org_unit)

    if role_id_changed:
        AuditService.log_event_best_effort(
            db=db,
            action=(
                AuditService.ACTION_SET_ORG_UNIT_ROLE
                if org_unit.role_id is not None
                else AuditService.ACTION_CLEAR_ORG_UNIT_ROLE
            ),
            user_id=current_user.id,
            resource_type=AuditService.RESOURCE_ORG_UNIT,
            resource_id=org_unit.id,
            additional_data={
                "old_role_id": old_role_id,
                "new_role_id": org_unit.role_id,
            },
            request=http_request,
        )

    return _to_out_single(db, org_unit)


@router.delete("/{org_unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_org_unit_endpoint(
    org_unit_id: int,
    current_user: User = Depends(require_permission("manage_org_units")),
    db: Session = Depends(get_db),
) -> Response:
    """Deletes the OrgUnit incl. all descendants (CASCADE).

    The API itself unconditionally performs the cascade -- the confirmation
    ("show descendant_count, obtain explicit user confirmation") is purely
    a frontend responsibility (see AdminOrgUnits.tsx), not a server-side
    guarantee. A direct API call without the UI can therefore delete an
    entire sub-hierarchy without warning.
    """
    org_unit = _load_org_unit_for_user(
        db=db, user=current_user, org_unit_id=org_unit_id
    )
    try:
        delete_org_unit(db, org_unit)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{org_unit_id}/members", status_code=status.HTTP_201_CREATED)
async def assign_member_endpoint(
    org_unit_id: int,
    body: MembershipCreateIn,
    http_request: Request,
    current_user: User = Depends(require_permission("manage_org_units")),
    db: Session = Depends(get_db),
) -> dict:
    org_unit = _load_org_unit_for_user(
        db=db, user=current_user, org_unit_id=org_unit_id
    )
    target_user = (
        db.query(User)
        .filter(
            User.id == body.user_id,
            User.institution_id == current_user.institution_id,
        )
        .one_or_none()
    )
    if target_user is None:
        raise HTTPException(status_code=404, detail="User nicht gefunden")
    try:
        assign_user_to_org_unit(
            db, user_id=body.user_id, org_unit_id=org_unit_id, role=body.role
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    # TF-637 review fix: audited unconditionally (not only when
    # org_unit.role_id is set) -- a Granted Role can be attached to this
    # OrgUnit *after* the membership already exists, so gating the audit
    # write on the role_id at assignment-time would miss exactly the
    # membership that later starts conferring permissions.
    AuditService.log_event_best_effort(
        db=db,
        action=AuditService.ACTION_ASSIGN_ORG_UNIT_MEMBER,
        user_id=current_user.id,
        resource_type=AuditService.RESOURCE_ORG_UNIT,
        resource_id=org_unit.id,
        additional_data={"org_unit_id": org_unit.id, "user_id": body.user_id},
        request=http_request,
    )
    return {"user_id": body.user_id, "org_unit_id": org_unit_id}


@router.delete(
    "/{org_unit_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_member_endpoint(
    org_unit_id: int,
    user_id: int,
    http_request: Request,
    current_user: User = Depends(require_permission("manage_org_units")),
    db: Session = Depends(get_db),
) -> Response:
    org_unit = _load_org_unit_for_user(
        db=db, user=current_user, org_unit_id=org_unit_id
    )
    try:
        remove_user_from_org_unit(db, user_id=user_id, org_unit_id=org_unit_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    AuditService.log_event_best_effort(
        db=db,
        action=AuditService.ACTION_REMOVE_ORG_UNIT_MEMBER,
        user_id=current_user.id,
        resource_type=AuditService.RESOURCE_ORG_UNIT,
        resource_id=org_unit.id,
        additional_data={"org_unit_id": org_unit.id, "user_id": user_id},
        request=http_request,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
