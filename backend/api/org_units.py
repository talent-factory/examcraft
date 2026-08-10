"""OrgUnit-CRUD-API (Abteilung/Team-Hierarchie) -- Stufe 0 Fundament.

Design: docs/superpowers/specs/2026-08-07-org-unit-hierarchie-design.md
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from database import get_db
from models.auth import User
from models.org_unit import KNOWN_UNIT_TYPES, OrgUnit
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
from utils.auth_utils import require_permission


_STRICT_OUT = ConfigDict(extra="forbid")

router = APIRouter(prefix="/api/v1/org-units", tags=["OrgUnits"])


class OrgUnitOut(BaseModel):
    model_config = _STRICT_OUT

    id: int
    parent_org_unit_id: int | None
    unit_type: str
    name: str
    descendant_count: int
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

    @field_validator("unit_type")
    @classmethod
    def _unit_type_must_be_known(cls, value: str) -> str:
        # KNOWN_UNIT_TYPES ist bewusst kein DB-Enum (siehe models/org_unit.py)
        # -- diese Validierung sitzt nur an der API-Grenze, damit Tippfehler
        # aus der Admin-UI nicht unbemerkt eine neue "Ebene" erzeugen. Interne
        # Aufrufer der Service-Funktionen bleiben unrestricted.
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


def _to_out(org_unit: OrgUnit, descendant_count: int) -> OrgUnitOut:
    return OrgUnitOut(
        id=org_unit.id,
        parent_org_unit_id=org_unit.parent_org_unit_id,
        unit_type=org_unit.unit_type,
        name=org_unit.name,
        descendant_count=descendant_count,
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
        .filter(OrgUnit.institution_id == current_user.institution_id)
        .order_by(OrgUnit.name)
        .all()
    )
    counts = get_descendant_counts_for_institution(db, current_user.institution_id)
    return OrgUnitListOut(items=[_to_out(row, counts.get(row.id, 0)) for row in rows])


@router.post("", response_model=OrgUnitOut, status_code=status.HTTP_201_CREATED)
async def create_org_unit_endpoint(
    body: OrgUnitCreateIn,
    current_user: User = Depends(require_permission("manage_org_units")),
    db: Session = Depends(get_db),
) -> OrgUnitOut:
    if body.parent_org_unit_id is not None:
        _load_org_unit_for_user(
            db=db, user=current_user, org_unit_id=body.parent_org_unit_id
        )
    try:
        org_unit = create_org_unit(
            db,
            institution_id=current_user.institution_id,
            unit_type=body.unit_type,
            name=body.name,
            parent_org_unit_id=body.parent_org_unit_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_out_single(db, org_unit)


@router.patch("/{org_unit_id}", response_model=OrgUnitOut)
async def update_org_unit_endpoint(
    org_unit_id: int,
    body: OrgUnitUpdateIn,
    current_user: User = Depends(require_permission("manage_org_units")),
    db: Session = Depends(get_db),
) -> OrgUnitOut:
    org_unit = _load_org_unit_for_user(
        db=db, user=current_user, org_unit_id=org_unit_id
    )

    if body.name is not None:
        org_unit.name = body.name

    fields_set = body.model_fields_set

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
        # Explizit gesendetes null ohne move_to_root ist mehrdeutig -- statt
        # still keinen Effekt zu haben, lieber ablehnen (silent no-op statt
        # Detach waere ein API-Contract-Fussangel).
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

    return _to_out_single(db, org_unit)


@router.delete("/{org_unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_org_unit_endpoint(
    org_unit_id: int,
    current_user: User = Depends(require_permission("manage_org_units")),
    db: Session = Depends(get_db),
) -> Response:
    """Loescht die OrgUnit inkl. aller Nachfahren (CASCADE).

    Die API selbst fuehrt die Kaskade unbedingt aus -- die Bestaetigung
    ("descendant_count anzeigen, explizite Nutzer-Bestaetigung einholen")
    ist reine Frontend-Verantwortung (siehe AdminOrgUnits.tsx), keine
    Server-seitige Garantie. Ein direkter API-Aufruf ohne UI kann also ohne
    Warnung eine ganze Teilhierarchie loeschen.
    """
    org_unit = _load_org_unit_for_user(
        db=db, user=current_user, org_unit_id=org_unit_id
    )
    delete_org_unit(db, org_unit)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{org_unit_id}/members", status_code=status.HTTP_201_CREATED)
async def assign_member_endpoint(
    org_unit_id: int,
    body: MembershipCreateIn,
    current_user: User = Depends(require_permission("manage_org_units")),
    db: Session = Depends(get_db),
) -> dict:
    _load_org_unit_for_user(db=db, user=current_user, org_unit_id=org_unit_id)
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
    return {"user_id": body.user_id, "org_unit_id": org_unit_id}


@router.delete(
    "/{org_unit_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_member_endpoint(
    org_unit_id: int,
    user_id: int,
    current_user: User = Depends(require_permission("manage_org_units")),
    db: Session = Depends(get_db),
) -> Response:
    _load_org_unit_for_user(db=db, user=current_user, org_unit_id=org_unit_id)
    try:
        remove_user_from_org_unit(db, user_id=user_id, org_unit_id=org_unit_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
