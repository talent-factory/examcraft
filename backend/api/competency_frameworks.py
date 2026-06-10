"""Kompetenzrahmen-API (HKB/Modul + HK) für ExamCraft AI (TF-400)."""

import logging
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models.auth import User
from models.competency import CompetencyFramework, Competency
from utils.auth_utils import get_current_active_user, require_permission
from utils.competency_parser import parse_competencies

logger = logging.getLogger(__name__)

Visibility = Literal["private", "institution"]

router = APIRouter(
    prefix="/api/v1/competency-frameworks", tags=["Competency Frameworks"]
)


class DescriptorIn(BaseModel):
    text: str = Field(..., min_length=1)
    ln_level: Optional[int] = Field(None, ge=1, le=4)


class CompetencyIn(BaseModel):
    # Code-Format wie vom Parser erzeugt (ein Buchstabe + Ziffern, z. B. "B3").
    # Das Tagging (competency_code → competency_id) verlässt sich darauf; beide
    # Schreibpfade (explizite API-Eingabe + rendered_text) müssen es teilen.
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
    competencies: List[CompetencyIn] = Field(default_factory=list)


class FrameworkUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    module_code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    rendered_text: Optional[str] = Field(None, min_length=1)
    language: Optional[str] = None
    visibility: Optional[Visibility] = None


class FrameworkOut(BaseModel):
    id: int
    name: str
    module_code: Optional[str] = None
    description: Optional[str] = None
    rendered_text: str
    language: str
    institution_id: Optional[int] = None
    created_by: Optional[int] = None
    visibility: Visibility
    is_archived: bool
    competencies: List[CompetencyOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


def _visible_query(db: Session, user: User):
    """Frameworks der eigenen Institution; private nur für den Ersteller."""
    return db.query(CompetencyFramework).filter(
        CompetencyFramework.institution_id == user.institution_id,
        (CompetencyFramework.visibility == "institution")
        | (CompetencyFramework.created_by == user.id),
    )


def _get_for_write(fw_id: int, user: User, db: Session) -> CompetencyFramework:
    fw = _visible_query(db, user).filter(CompetencyFramework.id == fw_id).first()
    if not fw:
        raise HTTPException(status_code=404, detail="Kompetenzrahmen nicht gefunden.")
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
    q = _visible_query(db, current_user)
    if not include_archived:
        q = q.filter(CompetencyFramework.is_archived == False)  # noqa: E712
    return q.order_by(func.lower(CompetencyFramework.name)).all()


def _sync_competencies_from_text(fw: CompetencyFramework) -> int:
    """TF-400: leitet HKs aus fw.rendered_text ab und upsertet sie per Code.

    FK-schonend: bestehende Codes werden aktualisiert, neue ergänzt; nicht mehr
    im Text vorhandene Codes bleiben erhalten (sonst würde
    question_reviews.competency_id über SET NULL verloren gehen). Gibt die
    Anzahl der im Text gefundenen HKs zurück.
    """
    parsed = parse_competencies(fw.rendered_text)
    existing = {c.code: c for c in fw.competencies}
    seen: set[str] = set()
    for p in parsed:
        code = p["code"]
        # Freitext kann denselben ### Code mehrfach enthalten — nur das erste
        # Vorkommen zählt. Ohne Dedup gäbe es zwei Competency-Zeilen mit gleichem
        # Code und damit eine UniqueViolation (ux_competencies_framework_code).
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
    """Commit; eine IntegrityError (z. B. doppelter Kompetenz-Code aus
    Race/Parallel-Edit) wird als sauberer 400 statt als roher 500 gemeldet und
    die Session zurückgerollt."""
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


@router.post("", response_model=FrameworkOut, status_code=201)
async def create_framework(
    body: FrameworkCreate,
    current_user: User = Depends(require_permission("create_questions")),
    db: Session = Depends(get_db),
):
    fw = CompetencyFramework(
        name=body.name.strip(),
        module_code=body.module_code,
        description=body.description,
        rendered_text=body.rendered_text,
        language=body.language,
        visibility=body.visibility,
        institution_id=current_user.institution_id,
        created_by=current_user.id,
    )
    if body.competencies:
        # Doppelte Codes sind ein Client-Fehler → klarer 400 statt UniqueViolation.
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
        # TF-400: keine HKs explizit übergeben → aus rendered_text ableiten,
        # damit auch via GUI erfasste Frameworks strukturiertes Tagging erhalten.
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
        _visible_query(db, current_user).filter(CompetencyFramework.id == fw_id).first()
    )
    if not fw:
        raise HTTPException(status_code=404, detail="Kompetenzrahmen nicht gefunden.")
    return fw


@router.put("/{fw_id}", response_model=FrameworkOut)
async def update_framework(
    fw_id: int,
    body: FrameworkUpdate,
    current_user: User = Depends(require_permission("create_questions")),
    db: Session = Depends(get_db),
):
    fw = _get_for_write(fw_id, current_user, db)
    fields = body.model_dump(exclude_unset=True)
    for field, value in fields.items():
        setattr(fw, field, value)
    # TF-400: bei geändertem rendered_text die strukturierten HKs neu ableiten
    # (upsert per Code), damit das Tagging zur Quelle konsistent bleibt.
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
