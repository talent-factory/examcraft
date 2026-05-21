"""Grading-Schemes CRUD API (TF-335 Spec 4.5–4.6, 7.6).

Endpoints:

* ``GET    /api/v1/grading-schemes`` — System schemes plus the caller's
  institution-scoped schemes (the only two scopes a user ever needs).
* ``POST   /api/v1/grading-schemes`` — create an institution-scoped
  scheme. ``grading_schemes:manage`` permission required.
* ``GET    /api/v1/grading-schemes/{id}`` — single scheme.
* ``PATCH  /api/v1/grading-schemes/{id}`` — update — system schemes
  reject with 403; only the caller's own institution can edit its own.
* ``DELETE /api/v1/grading-schemes/{id}`` — same scope rules. Schemes
  referenced by an exam are rejected with 409 to avoid orphaning the
  ``exam.grading_scheme_id`` FK; ``ON DELETE SET NULL`` would silently
  drop the configured scheme on every referenced exam, which is worse
  than blocking the delete.

Multi-Tenancy: every list/load is filtered by
``current_user.institution_id`` plus the ``institution_id IS NULL``
system-scheme rows. There is no cross-tenant read path.

No ``from __future__ import annotations``: FastAPI/Pydantic v2 needs
real runtime types for OpenAPI generation when route bodies are read
from ``BaseModel`` subclasses.
"""

import logging
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db
from models.auth import Institution, User
from models.exam import Exam
from models.grading_scheme import GradingScheme, GradingSchemeConfig
from utils.auth_utils import require_permission, get_current_active_user

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/v1/grading-schemes", tags=["Grading Schemes"])


_VALID_DISPLAY_FORMATS = ("numeric", "letter", "pass_fail")
_STRICT = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------


class GradingSchemeOut(BaseModel):
    model_config = _STRICT

    id: int
    institution_id: int | None
    name: str
    display_format: Literal["numeric", "letter", "pass_fail"]
    config: GradingSchemeConfig
    is_default_for_institution: bool
    is_system_scheme: bool
    created_at: datetime
    updated_at: datetime


class GradingSchemeListOut(BaseModel):
    model_config = _STRICT

    schemes: list[GradingSchemeOut]


class GradingSchemeCreate(BaseModel):
    model_config = _STRICT

    name: str = Field(..., min_length=1, max_length=200)
    display_format: Literal["numeric", "letter", "pass_fail"]
    config: GradingSchemeConfig
    is_default_for_institution: bool = False


class GradingSchemeUpdate(BaseModel):
    model_config = _STRICT

    name: str | None = Field(None, min_length=1, max_length=200)
    display_format: Literal["numeric", "letter", "pass_fail"] | None = None
    config: GradingSchemeConfig | None = None
    is_default_for_institution: bool | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_out(scheme: GradingScheme) -> GradingSchemeOut:
    return GradingSchemeOut(
        id=scheme.id,
        institution_id=scheme.institution_id,
        name=scheme.name,
        display_format=scheme.display_format,
        config=scheme.config,
        is_default_for_institution=scheme.is_default_for_institution,
        is_system_scheme=scheme.institution_id is None,
        created_at=scheme.created_at,
        updated_at=scheme.updated_at,
    )


def _load_scheme_for_user(
    *, db: Session, user: User, scheme_id: int, for_write: bool = False
) -> GradingScheme:
    """Load a scheme accessible to the user.

    For reads: system scheme ``OR`` user's institution. For writes:
    only the user's institution — system schemes raise 403 with a
    machine-readable detail so the frontend can surface "System-Schema
    nicht editierbar" without an extra round-trip.
    """
    scheme = db.query(GradingScheme).filter(GradingScheme.id == scheme_id).one_or_none()
    if scheme is None:
        raise HTTPException(status_code=404, detail="Grading-Scheme nicht gefunden")

    is_system = scheme.institution_id is None
    is_own = scheme.institution_id == user.institution_id

    if not (is_system or is_own):
        # Don't leak existence across tenants.
        raise HTTPException(status_code=404, detail="Grading-Scheme nicht gefunden")

    if for_write and is_system:
        raise HTTPException(
            status_code=403,
            detail="System-Grading-Schemes sind nicht editierbar",
        )

    return scheme


def _clear_other_defaults(
    db: Session, institution_id: int, keep_id: int | None
) -> None:
    """Demote the previous default before promoting a new one.

    The partial unique index ``uq_grading_schemes_default_per_institution``
    guarantees at most one default per institution at the DB level —
    this function avoids hitting that constraint by clearing any other
    flagged scheme for the same institution before commit.
    """
    query = db.query(GradingScheme).filter(
        GradingScheme.institution_id == institution_id,
        GradingScheme.is_default_for_institution.is_(True),
    )
    if keep_id is not None:
        query = query.filter(GradingScheme.id != keep_id)
    for other in query.all():
        other.is_default_for_institution = False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=GradingSchemeListOut)
async def list_grading_schemes(
    include_system: bool = Query(default=True),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> GradingSchemeListOut:
    """List system + own institution schemes.

    Read access is granted to every active user — the dropdown in the
    ExamComposer needs to show all schemes regardless of role. Editing
    is gated separately by ``grading_schemes:manage`` on the write
    endpoints.
    """
    filters = []
    if current_user.institution_id is not None:
        filters.append(GradingScheme.institution_id == current_user.institution_id)
    if include_system:
        filters.append(GradingScheme.institution_id.is_(None))

    if not filters:
        # No institution + system schemes excluded — nothing to show.
        return GradingSchemeListOut(schemes=[])

    schemes = (
        db.query(GradingScheme)
        .filter(or_(*filters))
        .order_by(
            GradingScheme.institution_id.is_(None).desc(),
            GradingScheme.name,
        )
        .all()
    )
    return GradingSchemeListOut(schemes=[_to_out(s) for s in schemes])


@router.get("/{scheme_id}", response_model=GradingSchemeOut)
async def get_grading_scheme(
    scheme_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> GradingSchemeOut:
    scheme = _load_scheme_for_user(db=db, user=current_user, scheme_id=scheme_id)
    return _to_out(scheme)


@router.post("", response_model=GradingSchemeOut, status_code=201)
async def create_grading_scheme(
    payload: GradingSchemeCreate,
    current_user: User = Depends(require_permission("grading_schemes:manage")),
    db: Session = Depends(get_db),
) -> GradingSchemeOut:
    if current_user.institution_id is None:
        raise HTTPException(
            status_code=400,
            detail="Benutzer muss einer Institution zugeordnet sein",
        )

    if payload.is_default_for_institution:
        _clear_other_defaults(db, current_user.institution_id, keep_id=None)

    scheme = GradingScheme(
        institution_id=current_user.institution_id,
        name=payload.name,
        display_format=payload.display_format,
        # ``config`` is the discriminated union (already validated by
        # Pydantic on request parse). Persist as plain JSON for the
        # JSON column.
        config=payload.config.model_dump(),
        is_default_for_institution=payload.is_default_for_institution,
    )
    db.add(scheme)
    try:
        db.commit()
        db.refresh(scheme)
    except IntegrityError as exc:
        db.rollback()
        logger.warning("grading_schemes create conflict: %s", exc)
        raise HTTPException(
            status_code=409,
            detail="Grading-Scheme mit diesem Namen existiert bereits",
        )
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("grading_schemes create db error: %s", exc)
        raise HTTPException(status_code=500, detail="Datenbankfehler")

    return _to_out(scheme)


@router.patch("/{scheme_id}", response_model=GradingSchemeOut)
async def update_grading_scheme(
    scheme_id: int,
    payload: GradingSchemeUpdate,
    current_user: User = Depends(require_permission("grading_schemes:manage")),
    db: Session = Depends(get_db),
) -> GradingSchemeOut:
    scheme = _load_scheme_for_user(
        db=db, user=current_user, scheme_id=scheme_id, for_write=True
    )

    # model_dump serialises the discriminated union back to a plain
    # dict — that's what the JSON column expects.
    update = payload.model_dump(exclude_unset=True)

    promote_to_default = update.get("is_default_for_institution") is True

    # Demote any prior default FIRST and flush so the partial-unique
    # index ``uq_grading_schemes_default_per_institution`` cannot be
    # transiently violated when SQLAlchemy reorders the UPDATEs at
    # flush time.
    if promote_to_default and scheme.institution_id is not None:
        _clear_other_defaults(db, scheme.institution_id, keep_id=scheme.id)
        db.flush()

    for key, value in update.items():
        setattr(scheme, key, value)

    try:
        db.commit()
        db.refresh(scheme)
    except IntegrityError as exc:
        db.rollback()
        logger.warning("grading_schemes update conflict: %s", exc)
        raise HTTPException(
            status_code=409,
            detail="Grading-Scheme-Update verletzt eine Eindeutigkeit",
        )
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("grading_schemes update db error: %s", exc)
        raise HTTPException(status_code=500, detail="Datenbankfehler")

    return _to_out(scheme)


@router.delete("/{scheme_id}", status_code=204)
async def delete_grading_scheme(
    scheme_id: int,
    current_user: User = Depends(require_permission("grading_schemes:manage")),
    db: Session = Depends(get_db),
) -> None:
    scheme = _load_scheme_for_user(
        db=db, user=current_user, scheme_id=scheme_id, for_write=True
    )

    # Pre-flight friendly check: surface a 409 with a useful message
    # before touching the DB. The FK is ``ON DELETE RESTRICT`` so the
    # constraint is the authoritative race-safe enforcer — this lookup
    # is a UX nicety. If the pre-check loses the race against a
    # concurrent attach, the IntegrityError catch below translates the
    # raw constraint violation into the same 409.
    exam_in_use = (
        db.query(Exam.id)
        .filter(Exam.grading_scheme_id == scheme_id)
        .limit(1)
        .one_or_none()
    )
    if exam_in_use is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Grading-Scheme wird von mindestens einer Prüfung referenziert "
                "und kann nicht gelöscht werden"
            ),
        )

    institution_default = (
        db.query(Institution.id)
        .filter(Institution.default_grading_scheme_id == scheme_id)
        .limit(1)
        .one_or_none()
    )
    if institution_default is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Grading-Scheme ist als Institution-Default gesetzt und "
                "kann nicht gelöscht werden — bitte zuerst einen anderen "
                "Default wählen"
            ),
        )

    db.delete(scheme)
    try:
        db.commit()
    except IntegrityError as exc:
        # Race: someone attached the scheme between our pre-check and
        # the DELETE COMMIT. The DB constraint stopped the corruption;
        # surface as 409 with the same shape.
        db.rollback()
        logger.warning("grading_schemes delete race: %s", exc)
        raise HTTPException(
            status_code=409,
            detail=("Grading-Scheme wird referenziert und kann nicht gelöscht werden"),
        )
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("grading_schemes delete db error: %s", exc)
        raise HTTPException(status_code=500, detail="Datenbankfehler")
