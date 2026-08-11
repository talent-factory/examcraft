"""Document visibility filtering (TF-354 privacy fix, TF-620 Org-Unit scoping).

Replaces ``TenantFilter`` for *document reads*. ``TenantFilter`` scopes only by
``institution_id``, which meant every member of an institution could read every
colleague's uploads. These helpers add the owner + ``visibility`` dimension:

- A document is visible to its owner regardless of visibility.
- A document is visible to other institution members only when its
  ``visibility`` is ``INSTITUTION`` and it belongs to their institution.
- A document is visible to a colleague when its ``visibility`` is ``TEAM`` and
  the colleague has access to its ``org_unit_id`` — hierarchically: a member
  of an ancestor Org-Unit also sees documents scoped to a descendant
  (``services.org_unit_service.get_user_accessible_org_unit_ids``, the "Stufe
  1" consumption point that primitive was built for).
- SuperUsers bypass the filter (status quo, deliberately preserved).

All document-read paths (list, single-doc endpoints, RAG document selection)
must route through here rather than duplicating the predicate — a single source
of truth keeps the privacy guarantee from drifting between call sites.
"""

from typing import Optional, Set

from fastapi import HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Query, Session

from models.auth import User
from models.document import Document, DocumentVisibility
from services.org_unit_service import get_user_accessible_org_unit_ids


def filter_documents_for_user(query: Query, user: User, db: Session) -> Query:
    """Restrict a ``Document`` query to rows the user may see.

    SuperUser bypasses the filter. Otherwise: owner rows OR institution-shared
    rows within the user's institution OR team-shared rows scoped to an
    Org-Unit the user has (hierarchical) access to.
    """
    if user.is_superuser:
        return query

    conditions = [
        Document.user_id == user.id,
        and_(
            Document.visibility == DocumentVisibility.INSTITUTION,
            Document.institution_id == user.institution_id,
        ),
    ]

    if user.institution_id is not None:
        accessible_org_unit_ids = get_user_accessible_org_unit_ids(
            db, user.id, user.institution_id
        )
        if accessible_org_unit_ids:
            conditions.append(
                and_(
                    Document.visibility == DocumentVisibility.TEAM,
                    Document.org_unit_id.in_(accessible_org_unit_ids),
                )
            )

    return query.filter(or_(*conditions))


def is_document_visible_for(
    user: User,
    document: Document,
    db: Session,
    *,
    accessible_org_unit_ids: Optional[Set[int]] = None,
) -> bool:
    """True if ``user`` may read ``document`` under the visibility rules.

    ``accessible_org_unit_ids``: optional pre-computed result of
    ``get_user_accessible_org_unit_ids`` for ``user``. Pass this when calling
    in a loop over multiple documents (e.g. validating a client-supplied
    ``document_ids`` list) — each call otherwise re-runs that hierarchical
    membership lookup (a recursive CTE per Org-Unit membership), turning an
    N-document check into an O(N) query fan-out for no reason, since the
    caller's own accessible set doesn't change between documents (TF-620).
    """
    if user.is_superuser:
        return True
    if document.user_id is not None and document.user_id == user.id:
        return True
    if (
        document.visibility == DocumentVisibility.INSTITUTION
        and document.institution_id is not None
        and document.institution_id == user.institution_id
    ):
        return True
    if (
        document.visibility == DocumentVisibility.TEAM
        and document.org_unit_id is not None
        and user.institution_id is not None
    ):
        if accessible_org_unit_ids is None:
            accessible_org_unit_ids = get_user_accessible_org_unit_ids(
                db, user.id, user.institution_id
            )
        return document.org_unit_id in accessible_org_unit_ids
    return False


def get_accessible_org_unit_ids_for(user: User, db: Session) -> Set[int]:
    """Pre-compute ``user``'s accessible Org-Unit ids once, to pass as
    ``is_document_visible_for``'s ``accessible_org_unit_ids`` across a loop
    over multiple documents instead of recomputing it per document (TF-620).
    """
    if not user.institution_id:
        return set()
    return get_user_accessible_org_unit_ids(db, user.id, user.institution_id)


def assert_document_visible_for(
    user: User,
    document: Document,
    db: Session,
    *,
    locale: Optional[str] = None,
    detail_key: str = "documents_not_found",
) -> None:
    """Raise 404 if ``document`` is not visible to ``user``.

    Deliberately 404 (not 403): a 403 would confirm that a private document
    with this id exists, leaking its existence to a colleague who must not see
    it. 404 makes a hidden document indistinguishable from a missing one.
    """
    if is_document_visible_for(user, document, db):
        return

    # Imported lazily (not at module top) to keep this low-level helper free of a
    # module-load dependency on the services layer; t() is only needed here, on
    # the error path.
    from services.translation_service import t

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=t(detail_key, locale=locale),
    )
