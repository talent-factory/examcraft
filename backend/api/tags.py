"""Tags API für ExamCraft AI."""

import logging
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models.auth import User
from models.tag import Tag, QuestionTag
from models.tag_merge_log import TagMergeLog
from utils.auth_utils import get_current_active_user, require_permission

logger = logging.getLogger(__name__)

TagScope = Literal["global", "institution"]

router = APIRouter(prefix="/api/v1/tags", tags=["Tags"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class TagOut(BaseModel):
    id: int
    name: str
    institution_id: Optional[int] = None
    scope: TagScope
    usage_count: int
    is_archived: bool
    is_own: bool = False

    model_config = {"from_attributes": True}


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    scope: TagScope = "institution"


class TagRename(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)


class MergeRequest(BaseModel):
    source_ids: List[int] = Field(..., min_length=1)
    target_id: int


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _visible_tags_query(db: Session, current_user: User):
    """Gibt die Query für sichtbare Tags zurück (eigene Institution + global)."""
    return db.query(Tag).filter(
        (Tag.institution_id == current_user.institution_id) | (Tag.scope == "global")
    )


def _get_tag_for_write(tag_id: int, current_user: User, db: Session) -> Tag:
    """Gibt Tag zurück wenn er zur Institution des Users gehört (oder global + superuser)."""
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag nicht gefunden.")
    if tag.scope == "institution" and tag.institution_id != current_user.institution_id:
        raise HTTPException(status_code=403, detail="Zugriff verweigert.")
    if tag.scope == "global" and not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Nur superuser darf globale Tags bearbeiten."
        )
    return tag


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=List[TagOut])
async def list_tags(
    include_archived: bool = Query(False),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[TagOut]:
    """Alle sichtbaren Tags (eigene Institution + global), alphabetisch sortiert."""
    q = _visible_tags_query(db, current_user)
    if not include_archived:
        q = q.filter(Tag.is_archived == False)  # noqa: E712
    tags = q.order_by(func.lower(Tag.name)).all()

    # usage_count live aus QuestionTag berechnen (verlässlicher als denormalisierter Zähler)
    counts: dict[int, int] = {}
    if tags:
        counts = dict(
            db.query(QuestionTag.tag_id, func.count(QuestionTag.question_id))
            .filter(QuestionTag.tag_id.in_([t.id for t in tags]))
            .group_by(QuestionTag.tag_id)
            .all()
        )

    return [
        TagOut(
            id=tag.id,
            name=tag.name,
            scope=tag.scope,
            institution_id=tag.institution_id,
            is_archived=tag.is_archived,
            usage_count=counts.get(tag.id, 0),
            is_own=tag.created_by == current_user.id,
        )
        for tag in tags
    ]


@router.post("", response_model=TagOut, status_code=200)
async def create_tag(
    body: TagCreate,
    current_user: User = Depends(require_permission("create_questions")),
    db: Session = Depends(get_db),
) -> Tag:
    """Tag erstellen oder vorhandenen zurückgeben (case-insensitiv, case-preserving).
    Globale Tags nur für superuser.
    """
    if body.scope == "global" and not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Nur superuser darf globale Tags erstellen."
        )

    name = body.name.strip()
    name_lower = name.lower()
    institution_id = None if body.scope == "global" else current_user.institution_id

    q = db.query(Tag).filter(
        func.lower(Tag.name) == name_lower, Tag.scope == body.scope
    )
    if body.scope == "institution":
        q = q.filter(Tag.institution_id == institution_id)
    existing = q.first()
    if existing:
        return existing

    tag = Tag(
        name=name,
        scope=body.scope,
        institution_id=institution_id,
        created_by=current_user.id,
    )
    db.add(tag)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Tag mit diesem Namen existiert bereits."
        )
    db.refresh(tag)
    logger.info(
        "Tag %r (scope=%s) created by user_id=%s", tag.name, tag.scope, current_user.id
    )
    return tag


@router.patch("/{tag_id}", response_model=TagOut)
async def rename_tag(
    tag_id: int,
    body: TagRename,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Tag:
    """Tag umbenennen. Admin darf alle Tags umbenennen; andere nur eigene."""
    tag = _get_tag_for_write(tag_id, current_user, db)

    is_admin = current_user.has_permission("manage_settings")
    if not is_admin and tag.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Zugriff verweigert.")

    new_name = body.name.strip()
    new_name_lower = new_name.lower()

    duplicate = (
        db.query(Tag)
        .filter(
            func.lower(Tag.name) == new_name_lower,
            Tag.id != tag_id,
            Tag.scope == tag.scope,
            Tag.institution_id == tag.institution_id,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=409, detail="Ein Tag mit diesem Namen existiert bereits."
        )

    tag.name = new_name
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Tag mit diesem Namen existiert bereits."
        )
    db.refresh(tag)
    return tag


@router.post("/{tag_id}/archive", response_model=TagOut)
async def archive_tag(
    tag_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Tag:
    """Tag archivieren. Admin darf alle Tags archivieren; andere nur eigene."""
    tag = _get_tag_for_write(tag_id, current_user, db)

    is_admin = current_user.has_permission("manage_settings")
    if not is_admin and tag.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Zugriff verweigert.")

    tag.is_archived = True
    db.commit()
    db.refresh(tag)
    logger.info("Tag %r archiviert von user_id=%s", tag.name, current_user.id)
    return tag


@router.post("/{tag_id}/unarchive", response_model=TagOut)
async def unarchive_tag(
    tag_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Tag:
    """Archivierten Tag wiederherstellen. Admin darf alle Tags wiederherstellen; andere nur eigene."""
    tag = _get_tag_for_write(tag_id, current_user, db)

    is_admin = current_user.has_permission("manage_settings")
    if not is_admin and tag.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Zugriff verweigert.")

    tag.is_archived = False
    db.commit()
    db.refresh(tag)
    logger.info("Tag %r wiederhergestellt von user_id=%s", tag.name, current_user.id)
    return tag


@router.delete("/{tag_id}", status_code=204)
async def delete_tag(
    tag_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Tag permanent löschen. Nur archivierte Tags mit usage_count == 0.
    Admin darf alle solche Tags löschen; andere nur eigene.
    """
    tag = _get_tag_for_write(tag_id, current_user, db)

    is_admin = current_user.has_permission("manage_settings")
    if not is_admin and tag.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Zugriff verweigert.")
    if not tag.is_archived:
        raise HTTPException(
            status_code=422, detail="Nur archivierte Tags können gelöscht werden."
        )

    live_count = (
        db.query(func.count(QuestionTag.question_id))
        .filter(QuestionTag.tag_id == tag_id)
        .scalar()
    )
    if live_count > 0:
        raise HTTPException(
            status_code=422, detail="Tag wird noch von Fragen verwendet."
        )

    db.delete(tag)
    db.commit()
    logger.info(
        "Tag %r (id=%s) gelöscht von user_id=%s", tag.name, tag_id, current_user.id
    )


@router.post("/merge", response_model=List[TagOut])
async def merge_tags(
    body: MergeRequest,
    current_user: User = Depends(require_permission("manage_settings")),
    db: Session = Depends(get_db),
) -> List[Tag]:
    """Mehrere Quell-Tags in einen Ziel-Tag zusammenführen.

    - Quell-Tags werden archiviert
    - Alle Fragen-Zuweisungen werden auf den Ziel-Tag migriert
    - Pro Quell-Tag wird ein TagMergeLog-Eintrag erstellt
    """
    if body.target_id in body.source_ids:
        raise HTTPException(
            status_code=422, detail="Ziel-Tag darf nicht unter den Quell-Tags sein."
        )

    target = _get_tag_for_write(body.target_id, current_user, db)

    # Pre-validate all sources before any mutation — failure mid-merge would
    # otherwise leave the merge log half-written and partial reassignments
    # committed via the rollback boundary that's only at the endpoint level.
    sources = [_get_tag_for_write(sid, current_user, db) for sid in body.source_ids]

    for source in sources:
        source_qt = db.query(QuestionTag).filter(QuestionTag.tag_id == source.id).all()
        questions_migrated = 0

        for qt in source_qt:
            exists = (
                db.query(QuestionTag)
                .filter(
                    QuestionTag.question_id == qt.question_id,
                    QuestionTag.tag_id == body.target_id,
                )
                .first()
            )
            if not exists:
                db.add(QuestionTag(question_id=qt.question_id, tag_id=body.target_id))
                questions_migrated += 1
            db.delete(qt)

        source.is_archived = True

        db.add(
            TagMergeLog(
                source_tag_id=source.id,
                target_tag_id=body.target_id,
                merged_by=current_user.id,
                questions_migrated=questions_migrated,
            )
        )

    db.commit()
    db.refresh(target)
    logger.info(
        "Tags %s in Tag %r gemergt von user_id=%s",
        body.source_ids,
        target.name,
        current_user.id,
    )
    return [target]
