"""TF-355 document-tag helpers: visibility, attach/detach, filter constants.

Document tagging reuses the existing ``tags`` table but adds a ``user`` scope
(owner-only) on top of the question-tag system's ``institution``/``global``
scopes. Kept separate from ``api/tags.py`` so the question-tag endpoints stay
untouched (decision §10.1).
"""

from typing import List

from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Query, Session

from models.auth import User
from models.document import Document, DocumentStatus, DocumentVisibility
from models.tag import DocumentTag, Tag

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
    institution's ``institution`` tags + all ``global`` tags."""
    return db.query(Tag).filter(
        Tag.is_archived.is_(False),
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
) -> None:
    """Attach each tag to the document (idempotent). Enforces the block rule:
    an ``institution``-scope tag may only go on an ``institution``-visible doc.
    Caller is responsible for the owner check and for committing.
    """
    existing = {
        r.tag_id
        for r in db.query(DocumentTag).filter(DocumentTag.document_id == document.id)
    }
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


def detach_tag_from_document(db: Session, document: Document, tag_id: int) -> None:
    """Remove a tag link if present (no error if absent). Caller commits."""
    db.query(DocumentTag).filter(
        DocumentTag.document_id == document.id, DocumentTag.tag_id == tag_id
    ).delete(synchronize_session=False)


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
