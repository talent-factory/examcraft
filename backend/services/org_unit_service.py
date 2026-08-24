"""Recursive hierarchy traversal for OrgUnit (Composite-pattern domain layer).

Adjacency-list storage (OrgUnit.parent_org_unit_id) + recursive CTEs for
ancestor/descendant queries. Encapsulates the "leaf vs. subtree doesn't
matter" property from the Composite pattern in two functions, used
uniformly by the service and API layers.

Design: docs/superpowers/specs/2026-08-07-org-unit-hierarchie-design.md
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.org_unit import OrgUnit, UserOrgUnit

logger = logging.getLogger(__name__)

# All three recursive CTEs carry a ``path`` array guard
# (``NOT o.id = ANY(d.path)``), even though the write path
# (``would_create_cycle`` in ``move_org_unit``) already prevents cycles.
# Defense in depth: should the check ever be bypassed (a race, a future
# caller, a manual DB change), an unguarded ``UNION ALL`` here would
# otherwise recurse forever and hang the DB connection for any
# institution with a data cycle -- especially fatal because
# ``get_descendant_counts_for_institution`` is called on every
# ``GET /org-units``.
_DESCENDANTS_SQL = text(
    """
    WITH RECURSIVE descendants AS (
        SELECT id, ARRAY[id] AS path FROM org_units WHERE id = :org_unit_id
        UNION ALL
        SELECT o.id, d.path || o.id
        FROM org_units o
        JOIN descendants d ON o.parent_org_unit_id = d.id
        WHERE NOT o.id = ANY(d.path)
    )
    SELECT id FROM descendants
    """
)

_ANCESTORS_SQL = text(
    """
    WITH RECURSIVE ancestors AS (
        SELECT id, parent_org_unit_id, ARRAY[id] AS path
        FROM org_units WHERE id = :org_unit_id
        UNION ALL
        SELECT o.id, o.parent_org_unit_id, a.path || o.id
        FROM org_units o
        JOIN ancestors a ON o.id = a.parent_org_unit_id
        WHERE NOT o.id = ANY(a.path)
    )
    SELECT id FROM ancestors
    """
)

_DESCENDANT_COUNTS_SQL = text(
    """
    WITH RECURSIVE pairs AS (
        SELECT id AS ancestor_id, id AS descendant_id, ARRAY[id] AS path
        FROM org_units WHERE institution_id = :institution_id
        UNION ALL
        SELECT p.ancestor_id, o.id, p.path || o.id
        FROM org_units o
        JOIN pairs p ON o.parent_org_unit_id = p.descendant_id
        WHERE o.institution_id = :institution_id AND NOT o.id = ANY(p.path)
    )
    SELECT ancestor_id, COUNT(*) - 1 AS descendant_count
    FROM pairs
    GROUP BY ancestor_id
    """
)


def get_descendant_ids(db: Session, org_unit_id: int) -> set[int]:
    """All descendants of ``org_unit_id``, including itself."""
    rows = db.execute(_DESCENDANTS_SQL, {"org_unit_id": org_unit_id}).fetchall()
    return {row[0] for row in rows}


def get_ancestor_ids(db: Session, org_unit_id: int) -> set[int]:
    """All ancestors of ``org_unit_id``, including itself."""
    rows = db.execute(_ANCESTORS_SQL, {"org_unit_id": org_unit_id}).fetchall()
    return {row[0] for row in rows}


def get_descendant_counts_for_institution(
    db: Session, institution_id: int
) -> dict[int, int]:
    """Descendant count (excluding itself) for *all* OrgUnits of an institution.

    A single recursive CTE instead of one per row -- avoids the N+1
    pattern that would arise if ``get_descendant_ids`` (one query per
    OrgUnit) were called per row in a list view. Missing IDs in the
    returned dict (no entry -> 0 descendants) are normal.
    """
    rows = db.execute(
        _DESCENDANT_COUNTS_SQL, {"institution_id": institution_id}
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def would_create_cycle(
    db: Session, org_unit_id: int, new_parent_id: int | None
) -> bool:
    """True if ``new_parent_id`` is a descendant (or ``org_unit_id`` itself).

    Prevents cycles when moving: a node must not be attached under one
    of its own descendants (or itself).
    """
    if new_parent_id is None:
        return False
    return new_parent_id in get_descendant_ids(db, org_unit_id)


def get_user_accessible_org_unit_ids(
    db: Session, user_id: int, institution_id: int
) -> set[int]:
    """All OrgUnits that ``user_id`` can access via membership + inheritance.

    Union of the descendant sets of all OrgUnits the user is directly
    assigned to (multiple memberships possible). Consumed by tier-1
    pilots to extend resource scoping to OrgUnit level -- not yet wired
    up anywhere in tier 0 (see Global Constraints).

    ``get_descendant_ids`` itself doesn't validate an institution -- this
    is uncritical today because ``create_org_unit``/``move_org_unit``
    already enforce the same institution on write. But since this
    function is the future permission-extension primitive for tier 1,
    we additionally filter on ``institution_id`` here as defense in
    depth, instead of implicitly relying on the write-path validation.
    """
    member_ids = {
        row[0]
        for row in db.query(UserOrgUnit.org_unit_id)
        .filter(UserOrgUnit.user_id == user_id)
        .all()
    }
    accessible: set[int] = set()
    for member_id in member_ids:
        accessible |= get_descendant_ids(db, member_id)

    if not accessible:
        return accessible

    scoped_ids = {
        row[0]
        for row in db.query(OrgUnit.id)
        .filter(OrgUnit.id.in_(accessible), OrgUnit.institution_id == institution_id)
        .all()
    }
    return scoped_ids


def validate_sibling_name_unique(
    db: Session,
    *,
    institution_id: int,
    parent_org_unit_id: int | None,
    name: str,
    exclude_id: int | None = None,
) -> None:
    query = db.query(OrgUnit).filter(
        OrgUnit.institution_id == institution_id,
        OrgUnit.parent_org_unit_id == parent_org_unit_id,
        OrgUnit.name == name,
    )
    if exclude_id is not None:
        query = query.filter(OrgUnit.id != exclude_id)
    if query.first() is not None:
        raise ValueError(f"OrgUnit '{name}' existiert bereits auf dieser Ebene")


def create_org_unit(
    db: Session,
    *,
    institution_id: int,
    unit_type: str,
    name: str,
    parent_org_unit_id: int | None,
    role_id: int | None = None,
) -> OrgUnit:
    if parent_org_unit_id is not None:
        parent = (
            db.query(OrgUnit)
            .filter(
                OrgUnit.id == parent_org_unit_id,
                OrgUnit.institution_id == institution_id,
            )
            .one_or_none()
        )
        if parent is None:
            raise ValueError(
                "Parent-OrgUnit nicht gefunden oder gehoert zu anderer Institution"
            )

    validate_sibling_name_unique(
        db,
        institution_id=institution_id,
        parent_org_unit_id=parent_org_unit_id,
        name=name,
    )

    org_unit = OrgUnit(
        institution_id=institution_id,
        unit_type=unit_type,
        name=name,
        parent_org_unit_id=parent_org_unit_id,
        role_id=role_id,
    )
    db.add(org_unit)
    try:
        db.commit()
    except IntegrityError as exc:
        # Race fallback: the sibling-name check above is SELECT-then-
        # INSERT, not atomic. The partial unique indexes from the
        # migration (ix_org_units_unique_sibling_name /
        # ix_org_units_unique_root_name) catch a concurrent duplicate
        # insert that bypassed the pre-check, instead of letting it
        # surface as a 500.
        #
        # TF-637 review fix: that used to be the only possible
        # IntegrityError cause, until role_id (FK to roles.id) was
        # added -- if a role is deleted between the role_id validation
        # check in the API and this commit (TOCTOU window), the INSERT
        # instead violates the FK constraint, not the sibling-name
        # unique index. Returning the same name-conflict text for that
        # would be misleading and hard to diagnose -- inspect the
        # constraint name + always log, as in delete_org_unit (same
        # principle, different FK).
        db.rollback()
        constraint_name = getattr(
            getattr(exc.orig, "diag", None), "constraint_name", None
        )
        logger.warning(
            "create_org_unit(name=%r, institution_id=%s) failed on "
            "IntegrityError (constraint=%s): %s",
            name,
            institution_id,
            constraint_name,
            exc,
            exc_info=True,
        )
        if constraint_name is not None and "role_id" in constraint_name.lower():
            raise ValueError(
                "Verliehene Rolle existiert nicht mehr -- bitte erneut waehlen"
            ) from exc
        raise ValueError(
            f"OrgUnit '{name}' existiert bereits auf dieser Ebene"
        ) from exc
    db.refresh(org_unit)
    return org_unit


def move_org_unit(
    db: Session, org_unit: OrgUnit, new_parent_org_unit_id: int | None
) -> OrgUnit:
    if new_parent_org_unit_id is not None:
        new_parent = (
            db.query(OrgUnit)
            .filter(
                OrgUnit.id == new_parent_org_unit_id,
                OrgUnit.institution_id == org_unit.institution_id,
            )
            .one_or_none()
        )
        if new_parent is None:
            raise ValueError(
                "Neuer Parent nicht gefunden oder gehoert zu anderer Institution"
            )

    if would_create_cycle(db, org_unit.id, new_parent_org_unit_id):
        raise ValueError("Verschieben wuerde einen Ring in der Hierarchie erzeugen")

    validate_sibling_name_unique(
        db,
        institution_id=org_unit.institution_id,
        parent_org_unit_id=new_parent_org_unit_id,
        name=org_unit.name,
        exclude_id=org_unit.id,
    )

    org_unit.parent_org_unit_id = new_parent_org_unit_id
    try:
        db.commit()
    except IntegrityError as exc:
        # Same race fallback as in create_org_unit -- including the same
        # TF-637 addendum: this commit can also co-commit an already
        # staged (but uncommitted) ``role_id`` value on ``org_unit``
        # from the caller (api/org_units.py::update_org_unit_endpoint)
        # if a reparent was requested at the same time -- so inspect
        # the same constraint name instead of assuming a sibling-name
        # conflict.
        db.rollback()
        constraint_name = getattr(
            getattr(exc.orig, "diag", None), "constraint_name", None
        )
        logger.warning(
            "move_org_unit(id=%s, name=%r) failed on IntegrityError "
            "(constraint=%s): %s",
            org_unit.id,
            org_unit.name,
            constraint_name,
            exc,
            exc_info=True,
        )
        if constraint_name is not None and "role_id" in constraint_name.lower():
            raise ValueError(
                "Verliehene Rolle existiert nicht mehr -- bitte erneut waehlen"
            ) from exc
        raise ValueError(
            f"OrgUnit '{org_unit.name}' existiert bereits auf dieser Ebene"
        ) from exc
    db.refresh(org_unit)
    return org_unit


def delete_org_unit(db: Session, org_unit: OrgUnit) -> int:
    """Deletes ``org_unit`` including all descendants (CASCADE).

    Returns the number of descendants deleted along with it (excluding
    itself). Note: this is the count *before* the delete -- so the UI
    warning must be shown and confirmed beforehand (via GET); this
    return value only serves for feedback/logging by the caller, not
    for the confirmation itself.

    Raises ``ValueError`` (-> 409 at the caller) if documents, prompts,
    questions, exams, or competency frameworks still reference this --
    or one of its descendant OrgUnits -- via ``visibility='team'``
    (TF-620/TF-641/TF-642/TF-643/TF-644): ``documents.org_unit_id``,
    ``prompts.org_unit_id``, ``question_reviews.org_unit_id``,
    ``exams.org_unit_id``, and ``competency_frameworks.org_unit_id`` all
    five deliberately have no ``ON DELETE CASCADE/SET NULL`` (see
    migrations ``tf620_doc_org_unit_scope``,
    ``tf641_prompt_org_unit_scope``, ``tf642_question_visibility``,
    ``tf643_exam_visibility``, and ``tf644_competency_visibility``
    respectively), so the DB-side FK fails here with an
    ``IntegrityError`` instead of silently deleting the referencing rows
    or leaving them in a constraint-violated state.
    """
    descendant_count = len(get_descendant_ids(db, org_unit.id)) - 1
    db.delete(org_unit)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # ``documents.org_unit_id``, ``prompts.org_unit_id``,
        # ``question_reviews.org_unit_id``, ``exams.org_unit_id`` and
        # ``competency_frameworks.org_unit_id`` are the only FKs onto
        # org_units without ON DELETE CASCADE/SET NULL today (see
        # docstring), so one of the five is the only thing that can raise
        # here in practice -- but don't just assume which: inspect the
        # actual constraint name so a future non-cascading FK onto org_units
        # doesn't get silently mislabeled with any of the specific messages
        # (TF-641 regression: the message stayed hardcoded to "Dokumente"
        # after prompts.org_unit_id was added, misleading admins about which
        # resource actually blocks the delete -- TF-642/TF-643/TF-644 repeat
        # the same risk for their own org_unit_id column if left unhandled),
        # and log the raw exception either way so a wrong guess is still
        # debuggable (409s are typically treated as expected client errors
        # and never reach error tracking) (TF-620/TF-641/TF-642/TF-643/TF-644).
        constraint_name = getattr(
            getattr(exc.orig, "diag", None), "constraint_name", None
        )
        logger.warning(
            "delete_org_unit(id=%s, name=%r) failed on IntegrityError "
            "(constraint=%s): %s",
            org_unit.id,
            org_unit.name,
            constraint_name,
            exc,
            exc_info=True,
        )
        if constraint_name is not None and "prompt" in constraint_name.lower():
            blocking_resource = "Prompts"
        elif constraint_name is not None and "document" in constraint_name.lower():
            blocking_resource = "Dokumente"
        elif constraint_name is not None and "question" in constraint_name.lower():
            blocking_resource = "Fragen"
        elif constraint_name is not None and "exam" in constraint_name.lower():
            blocking_resource = "Prüfungen"
        elif constraint_name is not None and "competency" in constraint_name.lower():
            blocking_resource = "Kompetenz-Frameworks"
        elif constraint_name is None or "org_unit_id" in constraint_name.lower():
            # Matches the FK but the naming convention doesn't tell us which
            # table -- name all five rather than guess and mislabel.
            blocking_resource = (
                "Dokumente, Prompts, Fragen, Prüfungen oder Kompetenz-Frameworks"
            )
        else:
            raise ValueError(
                f"OrgUnit '{org_unit.name}' kann nicht geloescht werden: "
                "wird noch von anderen Datensaetzen referenziert"
            ) from exc
        raise ValueError(
            f"OrgUnit '{org_unit.name}' kann nicht geloescht werden: "
            f"noch {blocking_resource} mit Team-Sichtbarkeit auf diese oder "
            "eine untergeordnete OrgUnit beschraenkt"
        ) from exc
    return descendant_count


def assign_user_to_org_unit(
    db: Session, *, user_id: int, org_unit_id: int, role: str | None = None
) -> UserOrgUnit:
    existing = (
        db.query(UserOrgUnit)
        .filter(UserOrgUnit.user_id == user_id, UserOrgUnit.org_unit_id == org_unit_id)
        .one_or_none()
    )
    if existing is not None:
        raise ValueError("User ist dieser OrgUnit bereits zugeordnet")

    membership = UserOrgUnit(user_id=user_id, org_unit_id=org_unit_id, role=role)
    db.add(membership)
    try:
        db.commit()
    except IntegrityError as exc:
        # Race fallback for the same SELECT-then-INSERT time window as
        # above: the composite PK (user_id, org_unit_id) catches a
        # concurrent duplicate insert on the DB side, instead of letting
        # an unhandled 500 surface.
        db.rollback()
        raise ValueError("User ist dieser OrgUnit bereits zugeordnet") from exc
    db.refresh(membership)
    return membership


def remove_user_from_org_unit(db: Session, *, user_id: int, org_unit_id: int) -> None:
    membership = (
        db.query(UserOrgUnit)
        .filter(UserOrgUnit.user_id == user_id, UserOrgUnit.org_unit_id == org_unit_id)
        .one_or_none()
    )
    if membership is None:
        raise ValueError("Mitgliedschaft nicht gefunden")
    db.delete(membership)
    db.commit()
