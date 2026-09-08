"""Tags API for ExamCraft AI."""

import logging
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from errors import api_error
from models.auth import User
from models.tag import Tag, QuestionTag, TagKind
from models.tag_merge_log import TagMergeLog
from services.translation_service import DEFAULT_LOCALE, get_request_locale
from utils.auth_utils import get_current_active_user, require_permission

logger = logging.getLogger(__name__)

TagScope = Literal["global", "institution"]
# TF-397: tag namespace. 'content' tags classify questions/documents, 'prompt'
# tags classify prompt templates. Default stays 'content' everywhere so
# existing question/document tagging is unaffected. ``TagKind`` is imported
# from models.tag (single source of truth) so the literal isn't redeclared here.

router = APIRouter(prefix="/api/v1/tags", tags=["Tags"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class TagOut(BaseModel):
    id: int
    name: str
    institution_id: Optional[int] = None
    scope: TagScope
    kind: TagKind = "content"
    usage_count: int
    is_archived: bool
    is_own: bool = False

    model_config = {"from_attributes": True}


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    scope: TagScope = "institution"
    kind: TagKind = "content"


class TagRename(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)


class MergeRequest(BaseModel):
    source_ids: List[int] = Field(..., min_length=1)
    target_id: int


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _visible_tags_query(db: Session, current_user: User):
    """Returns the query for visible tags (own institution + global)."""
    return db.query(Tag).filter(
        (Tag.institution_id == current_user.institution_id) | (Tag.scope == "global")
    )


def _get_tag_for_write(
    tag_id: int, current_user: User, db: Session, locale: str = DEFAULT_LOCALE
) -> Tag:
    """Returns the tag if it belongs to the user's institution (or global + superuser).

    ``locale`` is passed in rather than resolved here: this helper has no
    Request of its own, and every caller already resolved one (TF-773).
    """
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise api_error(404, "tags_not_found", locale)
    if tag.scope == "institution" and tag.institution_id != current_user.institution_id:
        raise api_error(403, "tags_access_denied", locale)
    if tag.scope == "global" and not current_user.is_superuser:
        # TF-397: a prompt-kind global tag may be managed by its creator,
        # mirroring the relaxed create rule (prompt editors don't need
        # superuser for their own prompt tags). Content global tags unchanged.
        if not (tag.kind == "prompt" and tag.created_by == current_user.id):
            raise api_error(403, "tags_global_edit_superuser_only", locale)
    return tag


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=List[TagOut])
async def list_tags(
    include_archived: bool = Query(False),
    kind: TagKind = Query("content"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[TagOut]:
    """All visible tags (own institution + global), sorted alphabetically.

    TF-397: by default only 'content' tags are returned, so question/document
    tagging and the tag management list stay unchanged. `kind=prompt` returns
    the prompt template tags for the prompt editor.
    """
    q = _visible_tags_query(db, current_user).filter(Tag.kind == kind)
    if not include_archived:
        q = q.filter(Tag.is_archived == False)  # noqa: E712
    tags = q.order_by(func.lower(Tag.name)).all()

    # Compute usage_count live from QuestionTag (more reliable than a denormalized counter)
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
            kind=tag.kind,
            institution_id=tag.institution_id,
            is_archived=tag.is_archived,
            usage_count=counts.get(tag.id, 0),
            is_own=tag.created_by == current_user.id,
        )
        for tag in tags
    ]


@router.post("", response_model=TagOut, status_code=200)
async def create_tag(
    request: Request,
    body: TagCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Tag:
    """Create a tag or return an existing one (case-insensitive, case-preserving).

    RBAC (TF-397):
    - kind='content': requires 'create_questions'; global content tags require
      superuser (unchanged from TF-372).
    - kind='prompt': requires 'prompt:create' (prompt management). This makes
      inline creation of global prompt tags possible without superuser —
      prompts are effectively global (no institution_id), so the superuser
      rule would otherwise be a blocker for regular prompt editors.
    """
    locale = get_request_locale(request, current_user)
    if body.kind == "prompt":
        if not current_user.has_permission("prompt:create"):
            raise api_error(403, "tags_prompt_create_permission_required", locale)
    else:
        if not current_user.has_permission("create_questions"):
            raise api_error(403, "tags_create_questions_permission_required", locale)
        if body.scope == "global" and not current_user.is_superuser:
            raise api_error(403, "tags_global_create_superuser_only", locale)

    name = body.name.strip()
    name_lower = name.lower()
    institution_id = None if body.scope == "global" else current_user.institution_id

    q = db.query(Tag).filter(
        func.lower(Tag.name) == name_lower,
        Tag.scope == body.scope,
        Tag.kind == body.kind,
    )
    if body.scope == "institution":
        q = q.filter(Tag.institution_id == institution_id)
    existing = q.first()
    if existing:
        return existing

    tag = Tag(
        name=name,
        scope=body.scope,
        kind=body.kind,
        institution_id=institution_id,
        created_by=current_user.id,
    )
    db.add(tag)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise api_error(409, "tags_name_exists", locale)
    db.refresh(tag)
    logger.info(
        "Tag %r (scope=%s, kind=%s) created by user_id=%s",
        tag.name,
        tag.scope,
        tag.kind,
        current_user.id,
    )
    return tag


@router.patch("/{tag_id}", response_model=TagOut)
async def rename_tag(
    request: Request,
    tag_id: int,
    body: TagRename,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Tag:
    """Rename a tag. Admin may rename all tags; others only their own."""
    locale = get_request_locale(request, current_user)
    tag = _get_tag_for_write(tag_id, current_user, db, locale)

    is_admin = current_user.has_permission("manage_settings")
    if not is_admin and tag.created_by != current_user.id:
        raise api_error(403, "tags_access_denied", locale)

    new_name = body.name.strip()
    new_name_lower = new_name.lower()

    # TF-397: uniqueness is per (scope, kind, lower(name)), so the duplicate
    # pre-check must also scope by kind — otherwise renaming a 'prompt' tag to a
    # name only held by a 'content' tag (or vice versa) raises a false 409.
    duplicate = (
        db.query(Tag)
        .filter(
            func.lower(Tag.name) == new_name_lower,
            Tag.id != tag_id,
            Tag.scope == tag.scope,
            Tag.institution_id == tag.institution_id,
            Tag.kind == tag.kind,
        )
        .first()
    )
    if duplicate:
        raise api_error(409, "tags_name_exists_on_rename", locale)

    tag.name = new_name
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise api_error(409, "tags_name_exists", locale)
    db.refresh(tag)
    return tag


@router.post("/{tag_id}/archive", response_model=TagOut)
async def archive_tag(
    request: Request,
    tag_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Tag:
    """Archive a tag. Admin may archive all tags; others only their own."""
    locale = get_request_locale(request, current_user)
    tag = _get_tag_for_write(tag_id, current_user, db, locale)

    is_admin = current_user.has_permission("manage_settings")
    if not is_admin and tag.created_by != current_user.id:
        raise api_error(403, "tags_access_denied", locale)

    tag.is_archived = True
    db.commit()
    db.refresh(tag)
    logger.info("Tag %r archiviert von user_id=%s", tag.name, current_user.id)
    return tag


@router.post("/{tag_id}/unarchive", response_model=TagOut)
async def unarchive_tag(
    request: Request,
    tag_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Tag:
    """Restore an archived tag. Admin may restore all tags; others only their own."""
    locale = get_request_locale(request, current_user)
    tag = _get_tag_for_write(tag_id, current_user, db, locale)

    is_admin = current_user.has_permission("manage_settings")
    if not is_admin and tag.created_by != current_user.id:
        raise api_error(403, "tags_access_denied", locale)

    tag.is_archived = False
    db.commit()
    db.refresh(tag)
    logger.info("Tag %r wiederhergestellt von user_id=%s", tag.name, current_user.id)
    return tag


@router.delete("/{tag_id}", status_code=204)
async def delete_tag(
    request: Request,
    tag_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Permanently delete a tag. Only archived tags with usage_count == 0.
    Admin may delete all such tags; others only their own.
    """
    locale = get_request_locale(request, current_user)
    tag = _get_tag_for_write(tag_id, current_user, db, locale)

    # TF-397: prompt-kind tags are linked to Prompts via the premium `prompt_tags`
    # table, which this core endpoint cannot inspect. Permanent deletion would
    # cascade and silently strip the tag from active prompts — block it here and
    # let prompt-tag cleanup happen through the prompt-management surface.
    if tag.kind == "prompt":
        raise api_error(422, "tags_prompt_delete_not_allowed", locale)

    is_admin = current_user.has_permission("manage_settings")
    if not is_admin and tag.created_by != current_user.id:
        raise api_error(403, "tags_access_denied", locale)
    if not tag.is_archived:
        raise api_error(422, "tags_delete_archived_only", locale)

    live_count = (
        db.query(func.count(QuestionTag.question_id))
        .filter(QuestionTag.tag_id == tag_id)
        .scalar()
    )
    if live_count > 0:
        raise api_error(422, "tags_still_in_use", locale)

    db.delete(tag)
    db.commit()
    logger.info(
        "Tag %r (id=%s) gelöscht von user_id=%s", tag.name, tag_id, current_user.id
    )


@router.post("/merge", response_model=List[TagOut])
async def merge_tags(
    request: Request,
    body: MergeRequest,
    current_user: User = Depends(require_permission("manage_settings")),
    db: Session = Depends(get_db),
) -> List[Tag]:
    """Merge multiple source tags into one target tag.

    - Source tags are archived
    - All question assignments are migrated to the target tag
    - A TagMergeLog entry is created per source tag
    """
    locale = get_request_locale(request, current_user)
    if body.target_id in body.source_ids:
        raise api_error(422, "tags_merge_target_in_sources", locale)

    target = _get_tag_for_write(body.target_id, current_user, db, locale)

    # Pre-validate all sources before any mutation — failure mid-merge would
    # otherwise leave the merge log half-written and partial reassignments
    # committed via the rollback boundary that's only at the endpoint level.
    sources = [
        _get_tag_for_write(sid, current_user, db, locale) for sid in body.source_ids
    ]

    # TF-397: this endpoint only reassigns QuestionTag links — it has no knowledge
    # of the premium prompt_tags join. Merging a 'prompt'-kind tag would archive
    # the source while its prompt links dangle at an archived tag, and would let
    # prompt/content namespaces bleed into each other. Block it (mirrors the
    # prompt-kind guard in delete_tag); prompt-tag housekeeping happens in the
    # Prompt-Editor surface.
    involved_kinds = {t.kind for t in (target, *sources)}
    if "prompt" in involved_kinds:
        raise api_error(422, "tags_prompt_merge_not_allowed", locale)

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
