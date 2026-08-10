"""Permission-Registry für ExamCraft (TF-603).

Einzige Quelle der Wahrheit für alle Permission-Strings, die aktuell in
``Role.permissions`` (System B, siehe ``models/auth.py``) vergeben werden
können. Vervollständigt am 2026-08-10 gegen die Union aller vier
Systemrollen-Permission-Listen in ``utils/seed_roles.py``.

19 Strings werden aktuell tatsächlich via ``require_permission()``/
``has_permission()`` geprüft; 11 sind seit jeher vergeben, aber nirgends
enforced (siehe Design-Doc, Abschnitt "Permission-Registry"). Beide Gruppen
sind hier bewusst gemeinsam aufgeführt: Ein Bearbeiten einer bestehenden
Rolle über das neue Admin-GUI darf ihr keine bereits vergebenen Rechte
unbemerkt entziehen.
"""

import json
from types import MappingProxyType
from typing import Any, List, Mapping, TypedDict


class PermissionMeta(TypedDict):
    """Shape of a single ``KNOWN_PERMISSIONS`` entry."""

    label: str
    category: str


_KNOWN_PERMISSIONS: dict[str, PermissionMeta] = {
    # Aktiv geprüft (19)
    "manage_org_units": {
        "label": "Organisationseinheiten verwalten",
        "category": "Organisation",
    },
    "manage_settings": {"label": "Systemeinstellungen verwalten", "category": "System"},
    "create_documents": {"label": "Dokumente erstellen", "category": "Dokumente"},
    "delete_documents": {"label": "Dokumente löschen", "category": "Dokumente"},
    "create_questions": {"label": "Fragen erstellen", "category": "Fragen"},
    "edit_questions": {"label": "Fragen bearbeiten", "category": "Fragen"},
    "delete_questions": {"label": "Fragen löschen", "category": "Fragen"},
    "review_questions": {"label": "Fragen begutachten", "category": "Fragen"},
    "create_exams": {"label": "Prüfungen erstellen", "category": "Prüfungen"},
    "delete_exams": {"label": "Prüfungen löschen", "category": "Prüfungen"},
    "grading_schemes:manage": {
        "label": "Notenschemata verwalten",
        "category": "Bewertung",
    },
    "submissions:read": {"label": "Abgaben einsehen", "category": "Bewertung"},
    "submissions:grade": {"label": "Abgaben bewerten", "category": "Bewertung"},
    "submissions:import": {"label": "Abgaben importieren", "category": "Bewertung"},
    "submissions:delete": {"label": "Abgaben löschen", "category": "Bewertung"},
    "submissions:moodle_feedback_push": {
        "label": "Moodle-Bewertungs-Rückexport",
        "category": "Bewertung",
    },
    "students:manage": {"label": "Studierende verwalten", "category": "Stammdaten"},
    "moodle:configure": {
        "label": "Moodle-Integration konfigurieren",
        "category": "Integration",
    },
    "prompt:create": {"label": "Prompts erstellen", "category": "Prompts"},
    # Seeded, aber aktuell nirgends enforced (11) — bewusst mitgeführt, siehe Docstring
    "manage_users": {"label": "Benutzer verwalten", "category": "System"},
    "manage_institutions": {"label": "Institutionen verwalten", "category": "System"},
    "manage_roles": {"label": "Rollen verwalten", "category": "System"},
    "edit_exams": {"label": "Prüfungen bearbeiten", "category": "Prüfungen"},
    "view_questions": {"label": "Fragen einsehen", "category": "Fragen"},
    "view_exams": {"label": "Prüfungen einsehen", "category": "Prüfungen"},
    "view_analytics": {"label": "Analysen einsehen", "category": "System"},
    "documents:read": {"label": "Dokumente einsehen", "category": "Dokumente"},
    "prompt:read": {"label": "Prompts einsehen", "category": "Prompts"},
    "prompt:update": {"label": "Prompts bearbeiten", "category": "Prompts"},
    "prompt:delete": {"label": "Prompts löschen", "category": "Prompts"},
}

# Read-only view: prevents accidental mutation of the single source of truth
# from anywhere other than this module (e.g. `KNOWN_PERMISSIONS.clear()`).
KNOWN_PERMISSIONS: Mapping[str, PermissionMeta] = MappingProxyType(_KNOWN_PERMISSIONS)


def parse_role_permissions(permissions: Any) -> List[str]:
    """Parse a ``Role.permissions`` value into a list of permission strings.

    Handles:
    - JSON string: ``["perm1", "perm2"]``
    - Postgres array literal (what a Python list becomes when assigned to a
      ``Column(Text)`` via psycopg2): ``{perm1,perm2,perm3}``
    - Python list: ``["perm1", "perm2"]``
    - Invalid/unexpected formats: returns ``[]``

    Shared by ``api/admin.py`` and ``models.auth.User.has_permission()`` so
    both call sites are guaranteed to agree on how a role's permissions are
    interpreted — do not re-implement this parsing elsewhere.
    """
    if not permissions:
        return []

    if isinstance(permissions, list):
        return permissions

    if not isinstance(permissions, str):
        return []

    # Try JSON first. Guard against `json.loads` succeeding on non-list JSON
    # (e.g. `json.loads("{}")` -> `{}`, a dict) — such values fall through to
    # the Postgres-array-literal branch below instead of being returned as-is.
    try:
        parsed = json.loads(permissions)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass

    # Try Postgres array literal format: {perm1,perm2,perm3}
    if permissions.startswith("{") and permissions.endswith("}"):
        perms_str = permissions[1:-1]
        return [p.strip() for p in perms_str.split(",") if p.strip()]

    # If all else fails, return empty list
    return []
