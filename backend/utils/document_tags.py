"""TF-355 document-tag helpers: visibility, attach/detach, filter constants.

Document tagging reuses the existing ``tags`` table but adds a ``user`` scope
(owner-only) on top of the question-tag system's ``institution``/``global``
scopes. Kept separate from ``api/tags.py`` so the question-tag endpoints stay
untouched (decision §10.1).
"""

from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Query, Session

from models.auth import User
from models.document import Document, DocumentStatus, DocumentVisibility
from models.tag import DocumentPersonalTag, DocumentTag, Tag

# Status-group → enum-set mapping (DocumentStatus carries new + legacy values).
STATUS_GROUPS = {
    "uploaded": [DocumentStatus.UPLOADED],
    "processing": [DocumentStatus.QUEUED, DocumentStatus.PROCESSING],
    "processed": [DocumentStatus.COMPLETED, DocumentStatus.PROCESSED],
    "error": [DocumentStatus.FAILED, DocumentStatus.ERROR],
}

MIME_FAMILIES = {
    "pdf": ["application/pdf"],
    "word": [
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ],
    "markdown": ["text/markdown"],
    "text": ["text/plain"],
}


def visible_tags_for_user(db: Session, user: User) -> Query:
    """Tags the user may attach to documents: own ``user`` tags + their
    institution's ``institution`` tags + all ``global`` tags.

    Restricted to ``kind == "content"``: TF-397 introduced a ``kind`` dimension
    (``content`` vs ``prompt``) on the shared ``tags`` table. Prompt-template
    tags must never appear in the document tag picker or be attachable to a
    document (personal *or* shared), so the document-tag world stays
    content-only — the same default the question/document tag UI assumed before
    the kind split existed.
    """
    return db.query(Tag).filter(
        Tag.is_archived.is_(False),
        Tag.kind == "content",
        or_(
            and_(Tag.scope == "user", Tag.created_by == user.id),
            and_(Tag.scope == "institution", Tag.institution_id == user.institution_id),
            Tag.scope == "global",
        ),
    )


def _visible_tag_for_attach(db: Session, tag_id: int, user: User) -> Tag:
    """Return a tag the user may attach, else raise 404 (don't leak existence)."""
    tag = visible_tags_for_user(db, user).filter(Tag.id == tag_id).first()
    if tag is None:
        from services.translation_service import t

        raise HTTPException(status_code=404, detail=t("documents_tag_not_found"))
    return tag


def attach_tags_to_document(
    db: Session, document: Document, tag_ids: List[int], user: User
) -> List[int]:
    """Attach each tag to the document (idempotent). Enforces the block rule:
    an ``institution``-scope tag may only go on an ``institution``-visible doc.
    Caller is responsible for the owner check and for committing.

    Returns the tag ids that were **actually** newly attached (already-present
    links are skipped), so the caller can audit only the effective change.
    """
    existing = {
        r.tag_id
        for r in db.query(DocumentTag).filter(DocumentTag.document_id == document.id)
    }
    added: List[int] = []
    for tag_id in dict.fromkeys(tag_ids):  # de-dupe, preserve order
        tag = _visible_tag_for_attach(db, tag_id, user)
        if (
            tag.scope == "institution"
            and document.visibility != DocumentVisibility.INSTITUTION
        ):
            from services.translation_service import t

            raise HTTPException(
                status_code=400,
                detail=t("documents_tag_institution_requires_shared"),
            )
        if tag_id not in existing:
            db.add(DocumentTag(document_id=document.id, tag_id=tag_id))
            existing.add(tag_id)
            added.append(tag_id)
    return added


def detach_tag_from_document(db: Session, document: Document, tag_id: int) -> int:
    """Remove a tag link if present (no error if absent). Caller commits.

    Returns the number of rows deleted (0 when the link was already absent), so
    the caller can audit only an effective removal.
    """
    return (
        db.query(DocumentTag)
        .filter(DocumentTag.document_id == document.id, DocumentTag.tag_id == tag_id)
        .delete(synchronize_session=False)
    )


def attach_tags_for_user(
    db: Session,
    document: Document,
    tag_ids: List[int],
    user: User,
    *,
    is_owner: bool,
) -> List[int]:
    """Attach tags, routing by scope (TF-399).

    * ``user``-scope  → personal assignment (``document_personal_tags``),
      allowed for anyone who can *see* the document — no ownership required.
    * ``institution``/``global``-scope → shared assignment (``document_tags``),
      **owner-only**; a non-owner gets 403.

    Caller asserts document visibility and commits.

    Returns the **shared** tag ids that were actually newly attached (empty when
    only personal tags changed or nothing changed). Personal assignments are
    private to the user and deliberately excluded — the caller audits only the
    shared, institution-visible change.
    """
    existing_personal = {
        r.tag_id
        for r in db.query(DocumentPersonalTag).filter(
            DocumentPersonalTag.document_id == document.id,
            DocumentPersonalTag.user_id == user.id,
        )
    }
    shared_ids: List[int] = []
    for tag_id in dict.fromkeys(tag_ids):  # de-dupe, preserve order
        tag = _visible_tag_for_attach(db, tag_id, user)
        if tag.scope == "user":
            if tag_id not in existing_personal:
                db.add(
                    DocumentPersonalTag(
                        document_id=document.id, tag_id=tag_id, user_id=user.id
                    )
                )
                existing_personal.add(tag_id)
        else:
            if not is_owner:
                from services.translation_service import t

                raise HTTPException(
                    status_code=403, detail=t("documents_tag_owner_only")
                )
            shared_ids.append(tag_id)
    if shared_ids:
        # Reuse the shared path (keeps the institution-requires-shared block).
        return attach_tags_to_document(db, document, shared_ids, user)
    return []


def detach_tag_for_user(
    db: Session,
    document: Document,
    tag_id: int,
    user: User,
    *,
    is_owner: bool,
) -> Optional[int]:
    """Detach a tag, routing by scope (TF-399).

    * ``user``-scope  → remove only the caller's personal assignment.
    * ``institution``/``global``-scope (or an unknown/deleted tag) → shared
      detach, **owner-only**.

    Idempotent (no error if the link is absent). Caller commits.

    Returns the tag id when a **shared** link was actually removed, else
    ``None`` (personal removal, or a no-op). The caller audits only an effective
    shared removal — personal removals are private and a no-op writes no row.
    """
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if tag is not None and tag.scope == "user":
        db.query(DocumentPersonalTag).filter(
            DocumentPersonalTag.document_id == document.id,
            DocumentPersonalTag.tag_id == tag_id,
            DocumentPersonalTag.user_id == user.id,
        ).delete(synchronize_session=False)
        return None
    if not is_owner:
        from services.translation_service import t

        raise HTTPException(status_code=403, detail=t("documents_tag_owner_only"))
    removed = detach_tag_from_document(db, document, tag_id)
    return tag_id if removed else None


def detach_institution_tags(db: Session, document: Document) -> int:
    """Remove all ``institution``-scope tag links from a document.

    Used when a document leaves ``institution`` visibility (e.g. an owner flips
    it back to ``private``): ``attach_tags_to_document`` forbids attaching an
    institution tag to a non-shared doc, so retaining such tags after a
    downgrade would persist a state the attach path rejects. Detaching keeps
    tag scope and document visibility coherent (TF-369 follow-up). Caller
    commits. Returns the number of links removed.
    """
    inst_tag_ids = [
        row.tag_id
        for row in (
            db.query(DocumentTag.tag_id)
            .join(Tag, Tag.id == DocumentTag.tag_id)
            .filter(
                DocumentTag.document_id == document.id,
                Tag.scope == "institution",
            )
        )
    ]
    if inst_tag_ids:
        db.query(DocumentTag).filter(
            DocumentTag.document_id == document.id,
            DocumentTag.tag_id.in_(inst_tag_ids),
        ).delete(synchronize_session=False)
    return len(inst_tag_ids)
