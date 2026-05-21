"""Shared helper to extract a human-readable title from ``AuditLog.additional_data``.

Tolerant of corrupt rows:

* Missing/empty ``additional_data`` → fallback.
* JSON parse failure → fallback (logged at ERROR — corrupt audit data
  is a security-relevant signal that should reach Sentry).
* JSON whose top-level isn't an object → fallback.
* Recognized keys missing → fallback.
"""

from __future__ import annotations

import json
import logging

from models.auth import AuditLog


logger = logging.getLogger(__name__)


def extract_audit_title(
    log: AuditLog,
    fallback_title: str,
    preferred_keys: tuple[str, ...],
) -> str:
    """Return the first non-empty value found under ``preferred_keys``.

    Args:
        log: An ``AuditLog`` row with ``additional_data`` (JSON string).
        fallback_title: Returned when the JSON is missing/malformed or
            none of the preferred keys yield a truthy value.
        preferred_keys: Ordered list of keys to try; the first
            populated key wins.
    """
    if not log.additional_data:
        return fallback_title
    try:
        data = json.loads(log.additional_data)
    except (json.JSONDecodeError, TypeError):
        # ERROR-level so Sentry catches the corruption: a row that
        # passed AuditService.log_action's serializer should always
        # be parseable; if it isn't, something upstream is writing
        # malformed JSON and we want to know early.
        logger.error(
            "Corrupt additional_data in audit log id=%s action=%s — "
            "rendering fallback title",
            log.id,
            log.action,
        )
        return fallback_title
    if not isinstance(data, dict):
        return fallback_title
    for key in preferred_keys:
        value = data.get(key)
        if value:
            return str(value)
    return fallback_title
