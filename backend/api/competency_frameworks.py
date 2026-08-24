"""Competency framework API (HKB/module + HK) for ExamCraft AI (TF-400).

Visibility (private/team/institution) + ``competencies:read_all`` bypass
since TF-644 — see ``models.competency.CompetencyFrameworkVisibility`` and
``utils.competency_visibility``.
"""

import logging
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models.auth import User
from models.competency import (
    CompetencyFramework,
    CompetencyFrameworkVisibility,
    Competency,
)
from services.org_unit_service import get_user_accessible_org_unit_ids
from utils.auth_utils import get_current_active_user, require_permission
from utils.competency_parser import parse_competencies
from utils.competency_visibility import (
    assert_framework_visible_for,
    filter_frameworks_for_user,
)

logger = logging.getLogger(__name__)

Visibility = Literal["private", "team", "institution"]

router = APIRouter(
    prefix="/api/v1/competency-frameworks", tags=["Competency Frameworks"]
)


class DescriptorIn(BaseModel):
    text: str = Field(..., min_length=1)
    ln_level: Optional[int] = Field(None, ge=1, le=4)


class CompetencyIn(BaseModel):
    # Code format as produced by the parser (one letter + digits, e.g. "B3").
    # Tagging (competency_code → competency_id) relies on this; both write
    # paths (explicit API input + rendered_text) must share it.
    code: str = Field(..., min_length=1, max_length=10, pattern=r"^[A-Za-z]\d+$")
    title: str = Field(..., min_length=1)
    descriptors: Optional[List[DescriptorIn]] = None
    position: int = 0


class DescriptorOut(BaseModel):
    text: str
    ln_level: Optional[int] = None

    model_config = {"from_attributes": True}


class CompetencyOut(BaseModel):
    id: int
    code: str
    title: str
    descriptors: Optional[List[DescriptorOut]] = None
    position: int

    model_config = {"from_attributes": True}


class FrameworkCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    module_code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    rendered_text: str = Field(..., min_length=1)
    language: str = "de"
    visibility: Visibility = "institution"
    # TF-644: only meaningful together with visibility="team"; validated +
    # cleared by _resolve_framework_visibility_for_create.
    org_unit_id: Optional[int] = None
    competencies: List[CompetencyIn] = Field(default_factory=list)


class FrameworkUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    module_code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    rendered_text: Optional[str] = Field(None, min_length=1)
    language: Optional[str] = None
    visibility: Optional[Visibility] = None
    # TF-644: validated + cleared by _resolve_framework_visibility_update.
    org_unit_id: Optional[int] = None


class FrameworkOut(BaseModel):
    id: int
    name: str
    module_code: Optional[str] = None
    description: Optional[str] = None
    rendered_text: str
    language: str
    institution_id: Optional[int] = None
    org_unit_id: Optional[int] = None
    created_by: Optional[int] = None
    visibility: Visibility
    is_archived: bool
    competencies: List[CompetencyOut] = Field(default_factory=list)

    # TF-644: fw.visibility is a CompetencyFrameworkVisibility enum member
    # when this model is built from_attributes off the ORM object directly
    # (every endpoint below does) — normalize to the plain string value the
    # field declares. Mirrors question_review.QuestionReviewOut's identical
    # _normalize_visibility validator (TF-642).
    @field_validator("visibility", mode="before")
    @classmethod
    def _normalize_visibility(cls, value):
        return (
            value.value if isinstance(value, CompetencyFrameworkVisibility) else value
        )

    model_config = {"from_attributes": True}


def _get_for_write(fw_id: int, user: User, db: Session) -> CompetencyFramework:
    """TF-644: fetch a framework for a mutation endpoint (update/archive/
    unarchive).

    Visibility check runs with ``allow_read_all_bypass=False`` (ADR-0004:
    ``competencies:read_all`` stays strictly read-only, mirrors Document/
    Prompt/Question/Exam) and ``require_same_institution=True`` (mutations
    need the stricter institution-drift-proof check, mirrors
    ``exam_visibility``/``document_visibility``). Preserves the pre-TF-644
    behaviour that a non-owner ``manage_settings`` admin still can't reach a
    colleague's *private* framework — visibility is checked first, the
    owner-or-admin write gate only decides what an already-visible framework
    may do.
    """
    fw = db.query(CompetencyFramework).filter(CompetencyFramework.id == fw_id).first()
    if not fw:
        raise HTTPException(status_code=404, detail="Kompetenzrahmen nicht gefunden.")
    assert_framework_visible_for(
        user, fw, db, allow_read_all_bypass=False, require_same_institution=True
    )
    is_admin = user.has_permission("manage_settings")
    if not is_admin and fw.created_by != user.id:
        raise HTTPException(status_code=403, detail="Zugriff verweigert.")
    return fw


@router.get("", response_model=List[FrameworkOut])
async def list_frameworks(
    include_archived: bool = Query(False),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    q = filter_frameworks_for_user(db.query(CompetencyFramework), current_user, db)
    if not include_archived:
        q = q.filter(CompetencyFramework.is_archived == False)  # noqa: E712
    return q.order_by(func.lower(CompetencyFramework.name)).all()


def _sync_competencies_from_text(fw: CompetencyFramework) -> int:
    """TF-400: derives HKs from fw.rendered_text and upserts them by code.

    FK-preserving: existing codes are updated, new ones added; codes no
    longer present in the text are kept (otherwise
    question_reviews.competency_id would be lost via SET NULL). Returns
    the number of HKs found in the text.
    """
    parsed = parse_competencies(fw.rendered_text)
    existing = {c.code: c for c in fw.competencies}
    seen: set[str] = set()
    for p in parsed:
        code = p["code"]
        # Free text can contain the same ### code multiple times — only the
        # first occurrence counts. Without dedup there would be two competency
        # rows with the same code, causing a UniqueViolation
        # (ux_competencies_framework_code).
        if code in seen:
            logger.info(
                "Kompetenzrahmen id=%s: doppeltes HK-Heading %r im rendered_text "
                "— nur das erste Vorkommen wird übernommen",
                fw.id,
                code,
            )
            continue
        seen.add(code)
        current = existing.get(code)
        if current is None:
            fw.competencies.append(
                Competency(
                    code=code,
                    title=p["title"],
                    descriptors=p["descriptors"] or None,
                    position=p["position"],
                )
            )
        else:
            current.title = p["title"]
            current.descriptors = p["descriptors"] or None
            current.position = p["position"]
    return len(seen)


def _commit_or_conflict(db: Session, user_id: int) -> None:
    """Commit; an IntegrityError (e.g. a duplicate competency code from a
    race/parallel edit) is reported as a clean 400 instead of a raw 500,
    and the session is rolled back."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.error(
            "Kompetenzrahmen-Persistenz fehlgeschlagen (IntegrityError) user=%s",
            user_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=400,
            detail="Kompetenzrahmen konnte nicht gespeichert werden "
            "(Integritätskonflikt, z. B. doppelter Kompetenz-Code).",
        )


def _resolve_framework_visibility_for_create(
    body: "FrameworkCreate", user: User, db: Session
) -> tuple:
    """TF-644: validate visibility/org_unit_id at framework creation time.

    Mirrors ``exams._resolve_exam_visibility_for_create`` — no ownership
    gate needed (the creator is always the owner of the row they're about
    to create). Unlike ``Exam.institution_id`` (NOT NULL),
    ``CompetencyFramework.institution_id`` IS nullable — mirrors
    ``question_review``'s orphan guard: a user without an institution can't
    create an institution-wide framework (would trip
    ``ck_competency_frameworks_inst_vis_requires_institution``
    as an opaque 500 via ``_commit_or_conflict`` otherwise).
    """
    visibility = CompetencyFrameworkVisibility(body.visibility)
    org_unit_id = body.org_unit_id

    if (
        visibility == CompetencyFrameworkVisibility.INSTITUTION
        and user.institution_id is None
    ):
        raise HTTPException(
            status_code=400,
            detail="Institutions-Sichtbarkeit erfordert eine Institution.",
        )

    if visibility == CompetencyFrameworkVisibility.TEAM:
        if org_unit_id is None:
            raise HTTPException(
                status_code=400,
                detail="Team-Sichtbarkeit erfordert eine Org-Unit (org_unit_id).",
            )
        # SuperUser bugfix (mirrors question_review/exam): validating against
        # the ACTING user's own membership would reject a superuser, who
        # typically belongs to no Org-Unit and often has institution_id=None
        # — they may set ANY org_unit_id on behalf of its actual owners.
        if not user.is_superuser:
            accessible = (
                get_user_accessible_org_unit_ids(db, user.id, user.institution_id)
                if user.institution_id
                else set()
            )
            if org_unit_id not in accessible:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Team-Sichtbarkeit erfordert eine eigene Org-Unit "
                        "(org_unit_id), der du selbst angehörst."
                    ),
                )
    else:
        org_unit_id = None

    return visibility, org_unit_id


@router.post("", response_model=FrameworkOut, status_code=201)
async def create_framework(
    body: FrameworkCreate,
    current_user: User = Depends(require_permission("create_questions")),
    db: Session = Depends(get_db),
):
    visibility, org_unit_id = _resolve_framework_visibility_for_create(
        body, current_user, db
    )
    fw = CompetencyFramework(
        name=body.name.strip(),
        module_code=body.module_code,
        description=body.description,
        rendered_text=body.rendered_text,
        language=body.language,
        visibility=visibility,
        org_unit_id=org_unit_id,
        institution_id=current_user.institution_id,
        created_by=current_user.id,
    )
    if body.competencies:
        # Duplicate codes are a client error → clear 400 instead of UniqueViolation.
        seen: set[str] = set()
        for c in body.competencies:
            if c.code in seen:
                raise HTTPException(
                    status_code=400,
                    detail=f"Doppelter Kompetenz-Code {c.code!r}: Codes müssen je "
                    "Kompetenzrahmen eindeutig sein.",
                )
            seen.add(c.code)
            fw.competencies.append(
                Competency(
                    code=c.code,
                    title=c.title,
                    descriptors=[d.model_dump() for d in c.descriptors]
                    if c.descriptors
                    else None,
                    position=c.position,
                )
            )
    else:
        # TF-400: no HKs explicitly given → derive from rendered_text, so
        # frameworks captured via the GUI also get structured tagging.
        _sync_competencies_from_text(fw)
    db.add(fw)
    _commit_or_conflict(db, current_user.id)
    db.refresh(fw)
    logger.info(
        "Kompetenzrahmen erstellt: id=%s name=%r user=%s",
        fw.id,
        fw.name,
        current_user.id,
    )
    return fw


@router.get("/{fw_id}", response_model=FrameworkOut)
async def get_framework(
    fw_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    fw = (
        filter_frameworks_for_user(db.query(CompetencyFramework), current_user, db)
        .filter(CompetencyFramework.id == fw_id)
        .first()
    )
    if not fw:
        raise HTTPException(status_code=404, detail="Kompetenzrahmen nicht gefunden.")
    return fw


def _resolve_framework_visibility_update(
    fw: CompetencyFramework,
    fields: dict,
    user: User,
    db: Session,
) -> Optional[dict]:
    """TF-644: validate a visibility/org_unit_id change on ``PUT /{fw_id}``.

    Mirrors ``exams._resolve_exam_visibility_update``, adapted to
    ``update_framework``'s ``exclude_unset``-based partial-update convention.

    Unlike Exam/QuestionReview (broader permission+institution-scoped write
    gate, needing a narrower owner-or-SuperUser restriction specifically for
    visibility), entry to ``update_framework`` already runs through
    ``_get_for_write``'s owner-or-``manage_settings``-admin gate for the
    *entire* endpoint — there is no separate ownership-only restriction to
    add here: an admin trusted with full write access to this framework may
    also re-tier it (still subject to the Org-Unit membership check below
    unless they're a SuperUser).

    Returns ``None`` when visibility/org_unit_id weren't touched, else the
    ``{"visibility": CompetencyFrameworkVisibility, "org_unit_id":
    Optional[int]}`` pair to apply.
    """
    if not fields:
        return None

    new_visibility = (
        CompetencyFrameworkVisibility(fields["visibility"])
        if fields.get("visibility") is not None
        else fw.visibility
    )
    new_org_unit_id = (
        fields["org_unit_id"] if "org_unit_id" in fields else fw.org_unit_id
    )

    if new_visibility == fw.visibility and new_org_unit_id == fw.org_unit_id:
        # No-op: exclude_unset only proves the caller sent the key, not that
        # it changes anything — mirrors exams._resolve_exam_visibility_update.
        return None

    if (
        new_visibility == CompetencyFrameworkVisibility.INSTITUTION
        and fw.institution_id is None
    ):
        # Bugfix: an orphaned framework (institution_id IS NULL) would
        # otherwise pass validation here and then trip
        # ck_competency_frameworks_inst_vis_requires_institution
        # on commit, surfacing as an opaque 500 via _commit_or_conflict
        # instead of this clear 400. Mirrors question_review's identical
        # guard.
        raise HTTPException(
            status_code=400,
            detail="Institutions-Sichtbarkeit erfordert eine Institution.",
        )

    if new_visibility == CompetencyFrameworkVisibility.TEAM:
        if new_org_unit_id is None:
            raise HTTPException(
                status_code=400,
                detail="Team-Sichtbarkeit erfordert eine Org-Unit (org_unit_id).",
            )
        if not user.is_superuser:
            accessible = (
                get_user_accessible_org_unit_ids(db, user.id, user.institution_id)
                if user.institution_id
                else set()
            )
            if new_org_unit_id not in accessible:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Team-Sichtbarkeit erfordert eine eigene Org-Unit "
                        "(org_unit_id), der du selbst angehörst."
                    ),
                )
    else:
        new_org_unit_id = None

    return {"visibility": new_visibility, "org_unit_id": new_org_unit_id}


@router.put("/{fw_id}", response_model=FrameworkOut)
async def update_framework(
    fw_id: int,
    body: FrameworkUpdate,
    current_user: User = Depends(require_permission("create_questions")),
    db: Session = Depends(get_db),
):
    fw = _get_for_write(fw_id, current_user, db)
    fields = body.model_dump(exclude_unset=True)
    # TF-644: visibility/org_unit_id are validated together (team requires a
    # membership-checked org_unit_id) — pop them out of the generic
    # attribute loop below and apply the resolved, validated pair instead.
    visibility_fields = {
        k: fields.pop(k) for k in ("visibility", "org_unit_id") if k in fields
    }
    visibility_update = _resolve_framework_visibility_update(
        fw, visibility_fields, current_user, db
    )
    if visibility_update is not None:
        fw.visibility = visibility_update["visibility"]
        fw.org_unit_id = visibility_update["org_unit_id"]
    for field, value in fields.items():
        setattr(fw, field, value)
    # TF-400: re-derive the structured HKs when rendered_text changed
    # (upsert by code), so the tagging stays consistent with the source.
    if "rendered_text" in fields:
        _sync_competencies_from_text(fw)
    _commit_or_conflict(db, current_user.id)
    db.refresh(fw)
    logger.info(
        "Kompetenzrahmen aktualisiert: id=%s name=%r user=%s",
        fw.id,
        fw.name,
        current_user.id,
    )
    return fw


@router.post("/{fw_id}/archive", response_model=FrameworkOut)
async def archive_framework(
    fw_id: int,
    current_user: User = Depends(require_permission("create_questions")),
    db: Session = Depends(get_db),
):
    fw = _get_for_write(fw_id, current_user, db)
    fw.is_archived = True
    db.commit()
    db.refresh(fw)
    logger.info(
        "Kompetenzrahmen archiviert: id=%s name=%r user=%s",
        fw.id,
        fw.name,
        current_user.id,
    )
    return fw


@router.post("/{fw_id}/unarchive", response_model=FrameworkOut)
async def unarchive_framework(
    fw_id: int,
    current_user: User = Depends(require_permission("create_questions")),
    db: Session = Depends(get_db),
):
    fw = _get_for_write(fw_id, current_user, db)
    fw.is_archived = False
    db.commit()
    db.refresh(fw)
    logger.info(
        "Kompetenzrahmen reaktiviert: id=%s name=%r user=%s",
        fw.id,
        fw.name,
        current_user.id,
    )
    return fw
