"""Institution-Admin read-all bypass permission registry (TF-639).

Design: docs/adr/0004-institution-admin-read-all-bypass-convention.md

Each of the five in-scope resources (documents, prompts, questions, exams,
competencies) gets its own ``<resource>:read_all`` permission string,
registered in ``utils.permissions.KNOWN_PERMISSIONS`` so it is seedable
(``utils.seed_roles``) and assignable to custom roles via the existing
Role-Permissions-Editor GUI (TF-603) without any further wiring — any string
present in ``KNOWN_PERMISSIONS`` is automatically listed and assignable
there.

This module is deliberately thin: it does *not* build a query filter or a
generic visibility abstraction. The actual filter shape (which visibility
enum, which team/org-unit column) differs per resource and is decided in
that resource's own ticket, following the ``utils/document_visibility.py``
pattern. Each resource's filter module calls ``has_read_all_bypass()`` from
within its own filter/visibility check instead of hardcoding the permission
string, so the naming convention lives in exactly one place.

Read-only bypass, never edit/delete (decided in TF-638). ``is_superuser``
needs no separate check here — ``User.has_permission()`` already
short-circuits to ``True`` for superusers before it ever looks at the
permission string.
"""

from types import MappingProxyType
from typing import Mapping

from models.auth import User

RESOURCE_READ_ALL_PERMISSIONS: Mapping[str, str] = MappingProxyType(
    {
        "documents": "documents:read_all",
        "prompts": "prompt:read_all",
        "questions": "questions:read_all",
        "exams": "exams:read_all",
        "competencies": "competencies:read_all",
    }
)


def has_read_all_bypass(user: User, resource: str) -> bool:
    """True if ``user`` may read every ``resource`` row institution-wide.

    ``resource`` must be a key of ``RESOURCE_READ_ALL_PERMISSIONS``
    (``"documents"``, ``"prompts"``, ``"questions"``, ``"exams"``,
    ``"competencies"``) — an unknown key raises ``KeyError`` rather than
    silently returning ``False``, so a typo'd resource name fails loudly
    instead of quietly denying the bypass.
    """
    permission = RESOURCE_READ_ALL_PERMISSIONS[resource]
    return user.has_permission(permission)
