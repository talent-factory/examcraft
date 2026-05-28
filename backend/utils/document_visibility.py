"""Document visibility filtering (TF-354 privacy fix).

Replaces ``TenantFilter`` for *document reads*. ``TenantFilter`` scopes only by
``institution_id``, which meant every member of an institution could read every
colleague's uploads. These helpers add the owner + ``visibility`` dimension:

- A document is visible to its owner regardless of visibility.
- A document is visible to other institution members only when its
  ``visibility`` is ``INSTITUTION`` and it belongs to their institution.
- SuperUsers bypass the filter (status quo, deliberately preserved).

All document-read paths (list, single-doc endpoints, RAG document selection)
must route through here rather than duplicating the predicate — a single source
of truth keeps the privacy guarantee from drifting between call sites.
"""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Query

from models.auth import User
from models.document import Document, DocumentVisibility


def filter_documents_for_user(query: Query, user: User) -> Query:
    """Restrict a ``Document`` query to rows the user may see.

    SuperUser bypasses the filter. Otherwise: owner rows OR institution-shared
    rows within the user's institution.
    """
    if user.is_superuser:
        return query

    return query.filter(
        or_(
            Document.user_id == user.id,
            and_(
                Document.visibility == DocumentVisibility.INSTITUTION,
                Document.institution_id == user.institution_id,
            ),
        )
    )


def is_document_visible_for(user: User, document: Document) -> bool:
    """True if ``user`` may read ``document`` under the visibility rules."""
    if user.is_superuser:
        return True
    if document.user_id is not None and document.user_id == user.id:
        return True
    return (
        document.visibility == DocumentVisibility.INSTITUTION
        and document.institution_id is not None
        and document.institution_id == user.institution_id
    )


def assert_document_visible_for(
    user: User,
    document: Document,
    *,
    locale: Optional[str] = None,
    detail_key: str = "documents_not_found",
) -> None:
    """Raise 404 if ``document`` is not visible to ``user``.

    Deliberately 404 (not 403): a 403 would confirm that a private document
    with this id exists, leaking its existence to a colleague who must not see
    it. 404 makes a hidden document indistinguishable from a missing one.
    """
    if is_document_visible_for(user, document):
        return

    # Imported lazily (not at module top) to keep this low-level helper free of a
    # module-load dependency on the services layer; t() is only needed here, on
    # the error path.
    from services.translation_service import t

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=t(detail_key, locale=locale),
    )
