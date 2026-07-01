"""TF-504: contract test — every audit *action* must be reachable (emitted at a
real call site, directly or via a convenience wrapper) or explicitly reserved
with a reason. Covers both ``AuditService.ACTION_*`` constants and the raw
action strings listed in ``ACTIONS_BY_CATEGORY``.

This prevents the class of gap TF-504 closed: an action that is defined (and
even categorised in ``ACTIONS_BY_CATEGORY``) but emitted nowhere — e.g. the
question-edit action, which was defined and categorised yet written by no code
path until TF-504 wired it.

Detection scans the call-site layers (``api`` / ``services`` / ``tasks`` /
``middleware``), excluding ``audit_service.py`` itself: there the constants are
defined AND referenced by the taxonomy + the convenience wrappers, and neither
of those is an *emission*. An action emitted only through a convenience wrapper
(``log_login`` → ``ACTION_LOGIN``) counts as reachable when that wrapper is
called at a scanned call site.

Comments are stripped before scanning and constant references are matched in
their qualified ``AuditService.ACTION_X`` form, so a mere *mention* of a
constant name in prose (a comment or docstring) can no longer make a
never-emitted action look reachable.

Pure filesystem + import — no DB required.
"""

import io
import re
import tokenize
from pathlib import Path

from services.audit_service import ACTIONS_BY_CATEGORY, AuditService

_BACKEND = Path(__file__).resolve().parents[1]
_SCAN_DIRS = ("api", "services", "tasks", "middleware")

# Actions whose ``action=`` lives inside a convenience wrapper in
# audit_service.py; reachable when the wrapper is called at a call site.
_CONVENIENCE_EMITTERS = {
    "ACTION_LOGIN": "log_login",
    "ACTION_LOGOUT": "log_logout",
    "ACTION_REGISTER": "log_register",
    "ACTION_PASSWORD_CHANGE": "log_password_change",
    "ACTION_RATE_LIMIT_EXCEEDED": "log_rate_limit_exceeded",
    "ACTION_SUPERUSER_BYPASS": "log_superuser_bypass",
    "ACTION_ADMIN_CROSS_OWNER": "log_admin_cross_owner",
}

# Constants defined but intentionally NOT emitted on develop — each with a
# justification. Trim an entry once a merge makes the action reachable
# (``test_reserved_actions_are_not_reachable`` enforces that trimming).
_RESERVED_ACTIONS = {
    "ACTION_PROCESS_DOCUMENT": (
        "document processing is a system/background step, not a user-facing audit event"
    ),
    "ACTION_CREATE_USER": (
        "no admin user-create endpoint on develop; enterprise OAuth signup "
        "audits creation in TF-503"
    ),
    "ACTION_DELETE_USER": "no user-delete endpoint exists yet",
    "ACTION_ASSIGN_ROLE": (
        "emitted by admin.py in TF-502 (#159); reserved until that merges"
    ),
    "ACTION_REMOVE_ROLE": (
        "emitted by admin.py in TF-502 (#159); reserved until that merges"
    ),
    "ACTION_OAUTH_LOGIN": (
        "core OAuth callback audit not yet wired (separate follow-up)"
    ),
    "ACTION_TOKEN_REFRESH": (
        "token rotation is high-frequency and lacks a clean user_id at the "
        "endpoint; the session is bound at login/logout"
    ),
    "ACTION_PASSWORD_RESET": (
        "the /password-reset endpoints are stubs (request is a no-op TODO, "
        "confirm raises 501); wire audit when implemented"
    ),
    "ACTION_API_ACCESS": (
        "generic per-request API-access logging is not wired; auditing is "
        "done per mutating endpoint instead"
    ),
    "ACTION_PERMISSION_DENIED": (
        "AuditService.log_permission_denied is unused; permission denials are "
        "recorded in permission_audit_log via RBACService (separate table)"
    ),
}

# Raw action *values* (categorised but not backed by an ``ACTION_*`` constant)
# that are intentionally unemitted. Empty today — every categorised raw string
# is emitted. Add ``"value": "reason"`` here if that ever changes.
_RESERVED_ACTION_VALUES: dict[str, str] = {}


def _strip_comments(src: str) -> str:
    """Blank out ``#`` comments so a constant mentioned in prose does not count
    as an emission. Falls back to the raw text if a file will not tokenise."""
    try:
        comments = [
            (tok.start, tok.end)
            for tok in tokenize.generate_tokens(io.StringIO(src).readline)
            if tok.type == tokenize.COMMENT
        ]
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return src
    lines = src.split("\n")
    for (srow, scol), (_erow, ecol) in comments:  # COMMENT tokens are single-line
        line = lines[srow - 1]
        lines[srow - 1] = line[:scol] + " " * (ecol - scol) + line[ecol:]
    return "\n".join(lines)


def _call_site_source() -> str:
    parts = []
    for name in _SCAN_DIRS:
        root = _BACKEND / name
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if path.name == "audit_service.py":
                continue
            parts.append(_strip_comments(path.read_text(encoding="utf-8")))
    return "\n".join(parts)


def _action_constants() -> dict[str, str]:
    return {
        name: getattr(AuditService, name)
        for name in dir(AuditService)
        if name.startswith("ACTION_")
    }


def _emitted_as_raw_action(value: str, sources: str) -> bool:
    """``action="value"`` / ``action='value'`` appears at a call site."""
    return bool(re.search(rf"""action\s*=\s*["']{re.escape(value)}["']""", sources))


def _is_reachable(name: str, value: str, sources: str) -> bool:
    # Referenced in its qualified ``AuditService.ACTION_X`` form at a call site.
    # (Bare-name matching is deliberately avoided: a prose mention of the
    # constant name must not count as an emission.)
    if re.search(rf"AuditService\s*\.\s*{re.escape(name)}\b", sources):
        return True
    # Emitted as a raw string ``action="value"`` at a call site.
    if _emitted_as_raw_action(value, sources):
        return True
    # Emitted only through a convenience wrapper that is called at a call site.
    wrapper = _CONVENIENCE_EMITTERS.get(name)
    return bool(wrapper and wrapper in sources)


def test_every_audit_action_is_reachable_or_reserved():
    sources = _call_site_source()
    orphaned = [
        (name, value)
        for name, value in _action_constants().items()
        if name not in _RESERVED_ACTIONS and not _is_reachable(name, value, sources)
    ]
    assert not orphaned, (
        "Audit ACTION_* constants defined but never emitted at a call site "
        f"(and not RESERVED): {orphaned}. Either emit them via AuditService, or "
        "add them to _RESERVED_ACTIONS with a justification."
    )


def test_categorised_actions_are_reachable_or_reserved():
    """Every action string in ``ACTIONS_BY_CATEGORY`` must be emitted somewhere
    (or reserved). This extends the contract to the raw-string exam actions
    (``"update_exam"`` etc.) that are categorised but not backed by an
    ``ACTION_*`` constant, so they cannot silently become dead entries."""
    sources = _call_site_source()
    value_to_name = {value: name for name, value in _action_constants().items()}
    orphaned = []
    for actions in ACTIONS_BY_CATEGORY.values():
        for value in actions:
            name = value_to_name.get(value)
            if name is not None:
                # Backed by a constant — covered by the constant-level contract.
                if name not in _RESERVED_ACTIONS and not _is_reachable(
                    name, value, sources
                ):
                    orphaned.append(value)
            elif value not in _RESERVED_ACTION_VALUES and not _emitted_as_raw_action(
                value, sources
            ):
                orphaned.append(value)
    assert not orphaned, (
        "Actions categorised in ACTIONS_BY_CATEGORY but never emitted at a call "
        f"site: {sorted(set(orphaned))}. Emit them via AuditService, or add "
        "raw values to _RESERVED_ACTION_VALUES with a justification."
    )


def test_reserved_actions_are_not_reachable():
    """A reserved action that has since been wired should be un-reserved, not
    left masking real coverage. Fail once a RESERVED action is actually emitted
    (e.g. after TF-502 merges and admin.py starts emitting the role actions)."""
    sources = _call_site_source()
    constants = _action_constants()
    now_reachable = sorted(
        name
        for name in _RESERVED_ACTIONS
        if name in constants and _is_reachable(name, constants[name], sources)
    )
    assert not now_reachable, (
        "These actions are RESERVED but now emitted at a call site — remove them "
        f"from _RESERVED_ACTIONS so the reachability contract covers them: {now_reachable}"
    )


def test_reserved_actions_are_real_constants():
    """Guard the allowlist against typos / stale entries after a rename."""
    unknown = sorted(set(_RESERVED_ACTIONS) - set(_action_constants()))
    assert not unknown, f"_RESERVED_ACTIONS references unknown constants: {unknown}"
