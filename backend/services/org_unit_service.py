"""Rekursive Hierarchie-Traversal fuer OrgUnit (Composite-Pattern-Domain-Layer).

Adjacency-List-Speicherung (OrgUnit.parent_org_unit_id) + rekursive CTEs fuer
Vorfahren-/Nachfahren-Abfragen. Kapselt die "Blatt vs. Teilbaum ist egal"-
Eigenschaft aus dem Composite-Pattern in zwei Funktionen, die von Service- und
API-Schicht einheitlich genutzt werden.

Design: docs/superpowers/specs/2026-08-07-org-unit-hierarchie-design.md
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.org_unit import OrgUnit, UserOrgUnit

logger = logging.getLogger(__name__)

# Alle drei rekursiven CTEs tragen einen ``path``-Array-Guard
# (``NOT o.id = ANY(d.path)``), obwohl der Schreibpfad (``would_create_cycle``
# in ``move_org_unit``) Ringe bereits verhindert. Defense-in-depth: sollte der
# Check je umgangen werden (Race, zukuenftiger Aufrufer, manuelle DB-Aenderung),
# wuerde ein ungeguardeter ``UNION ALL`` hier sonst endlos rekursieren und die
# DB-Verbindung fuer jede Institution mit einem Datenring aufhaengen --
# insbesondere fatal, weil ``get_descendant_counts_for_institution`` bei jedem
# ``GET /org-units`` aufgerufen wird.
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
    """Alle Nachfahren von ``org_unit_id``, inkl. sich selbst."""
    rows = db.execute(_DESCENDANTS_SQL, {"org_unit_id": org_unit_id}).fetchall()
    return {row[0] for row in rows}


def get_ancestor_ids(db: Session, org_unit_id: int) -> set[int]:
    """Alle Vorfahren von ``org_unit_id``, inkl. sich selbst."""
    rows = db.execute(_ANCESTORS_SQL, {"org_unit_id": org_unit_id}).fetchall()
    return {row[0] for row in rows}


def get_descendant_counts_for_institution(
    db: Session, institution_id: int
) -> dict[int, int]:
    """Nachfahren-Anzahl (ohne sich selbst) fuer *alle* OrgUnits einer Institution.

    Eine einzelne rekursive CTE statt einer pro Zeile -- vermeidet das N+1-
    Muster, das entsteht, wenn ``get_descendant_ids`` (eine Abfrage pro
    OrgUnit) in einer Listen-Ansicht pro Zeile aufgerufen wird. Fehlende IDs im
    Rueckgabe-Dict (kein Eintrag -> 0 Nachfahren) sind normal.
    """
    rows = db.execute(
        _DESCENDANT_COUNTS_SQL, {"institution_id": institution_id}
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def would_create_cycle(
    db: Session, org_unit_id: int, new_parent_id: int | None
) -> bool:
    """True, wenn ``new_parent_id`` ein Nachfahre (oder ``org_unit_id`` selbst) ist.

    Verhindert Ringe beim Verschieben: ein Knoten darf nicht unter einem
    seiner eigenen Nachfahren (oder sich selbst) haengen.
    """
    if new_parent_id is None:
        return False
    return new_parent_id in get_descendant_ids(db, org_unit_id)


def get_user_accessible_org_unit_ids(
    db: Session, user_id: int, institution_id: int
) -> set[int]:
    """Alle OrgUnits, auf die ``user_id`` via Mitgliedschaft + Vererbung Zugriff hat.

    Vereinigung der Nachfahren-Mengen aller OrgUnits, denen der User direkt
    zugeordnet ist (Mehrfachmitgliedschaft moeglich). Wird von Stufe-1-Piloten
    konsumiert, um Ressourcen-Scoping um OrgUnit-Ebene zu erweitern -- in
    Stufe 0 noch nirgends verdrahtet (siehe Global Constraints).

    ``get_descendant_ids`` selbst validiert keine Institution -- das ist heute
    unkritisch, weil ``create_org_unit``/``move_org_unit`` gleiche Institution
    bereits beim Schreiben erzwingen. Da diese Funktion aber die zukuenftige
    Berechtigungs-Erweiterungs-Primitive fuer Stufe 1 ist, filtern wir hier
    zusaetzlich defense-in-depth auf ``institution_id``, statt uns implizit
    auf die Schreibpfad-Validierung zu verlassen.
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
    )
    db.add(org_unit)
    try:
        db.commit()
    except IntegrityError as exc:
        # Race-Fallback: der Sibling-Name-Check oben ist SELECT-dann-INSERT,
        # nicht atomar. Die partiellen Unique-Indizes aus der Migration
        # (ix_org_units_unique_sibling_name / ix_org_units_unique_root_name)
        # fangen einen gleichzeitigen Duplikat-Insert ab, der die Vor-Prüfung
        # umgangen hat, statt ihn als 500 durchschlagen zu lassen.
        db.rollback()
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
        # Gleicher Race-Fallback wie in create_org_unit.
        db.rollback()
        raise ValueError(
            f"OrgUnit '{org_unit.name}' existiert bereits auf dieser Ebene"
        ) from exc
    db.refresh(org_unit)
    return org_unit


def delete_org_unit(db: Session, org_unit: OrgUnit) -> int:
    """Loescht ``org_unit`` inkl. aller Nachfahren (CASCADE).

    Gibt die Anzahl der mitgeloeschten Nachfahren zurueck (ohne sich selbst).
    Hinweis: Das ist die Anzahl *vor* dem Loeschen -- die UI-Warnung muss
    also vorher (via GET) angezeigt und bestaetigt werden; dieser Rueckgabewert
    dient nur der Rueckmeldung/Protokollierung durch den Aufrufer, nicht der
    Bestaetigung selbst.

    Raises ``ValueError`` (-> 409 beim Aufrufer) wenn noch Dokumente auf diese
    -- oder eine ihrer Nachfahren-OrgUnits -- via ``visibility='team'``
    verweisen (TF-620): ``documents.org_unit_id`` hat bewusst kein
    ``ON DELETE CASCADE/SET NULL`` (siehe Migration
    ``tf620_doc_org_unit_scope``), also schlaegt der DB-seitige FK hier mit
    einem ``IntegrityError`` fehl statt Dokumente stillschweigend zu loeschen
    oder in einen Constraint-Verletzungs-Zustand zu bringen.
    """
    descendant_count = len(get_descendant_ids(db, org_unit.id)) - 1
    db.delete(org_unit)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # ``documents.org_unit_id`` is the only FK onto org_units without
        # ON DELETE CASCADE/SET NULL today (see docstring), so it's the only
        # thing that can raise here in practice -- but don't just assume
        # that's the cause: inspect the actual constraint name so a future
        # non-cascading FK onto org_units doesn't get silently mislabeled
        # with this specific message, and log the raw exception either way
        # so a wrong guess is still debuggable (409s are typically treated
        # as expected client errors and never reach error tracking) (TF-620).
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
        if constraint_name is None or "org_unit_id" in constraint_name.lower():
            raise ValueError(
                f"OrgUnit '{org_unit.name}' kann nicht geloescht werden: "
                "noch Dokumente mit Team-Sichtbarkeit auf diese oder eine "
                "untergeordnete OrgUnit beschraenkt"
            ) from exc
        raise ValueError(
            f"OrgUnit '{org_unit.name}' kann nicht geloescht werden: "
            "wird noch von anderen Datensaetzen referenziert"
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
        # Race-Fallback fuer den gleichen SELECT-dann-INSERT-Zeitfenster wie
        # oben: die Composite-PK (user_id, org_unit_id) fängt einen
        # gleichzeitigen Duplikat-Insert DB-seitig ab, statt einen
        # unbehandelten 500 durchschlagen zu lassen.
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
