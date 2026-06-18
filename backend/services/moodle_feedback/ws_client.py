"""Thin Moodle REST helper for the feedback push (TF-435).

Reuses the conventions from services/import_drivers/moodle_api_driver.py:
POST to <base>/webservice/rest/server.php with wstoken in the body, and
treat the HTTP-200 ``{"exception": ...}`` envelope as an error.
"""

from __future__ import annotations

from typing import Any

import httpx

DEFAULT_TIMEOUT_SECONDS = 30.0


class MoodleWsError(Exception):
    """A Moodle Web Service call failed (transport or Moodle exception)."""


def flatten_moodle_params(value: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten nested dict/list params into Moodle's bracket notation.

    {"a": [{"b": 1}]} -> {"a[0][b]": 1}. Scalars pass through unchanged.

    Callers always pass a dict at the top level; a bare scalar would land in
    ``out[""]`` (empty key), but that branch is only reached via recursion with
    a non-empty prefix, so the empty-key case never occurs in practice.
    """
    out: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, val in value.items():
            child = f"{prefix}[{key}]" if prefix else str(key)
            out.update(flatten_moodle_params(val, child))
    elif isinstance(value, (list, tuple)):
        for idx, val in enumerate(value):
            out.update(flatten_moodle_params(val, f"{prefix}[{idx}]"))
    else:
        out[prefix] = value
    return out


def call_moodle(
    base_url: str,
    token: str,
    function: str,
    params: dict[str, Any],
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> Any:
    """POST one WS call and unwrap Moodle's canonical error envelope."""
    endpoint = base_url.rstrip("/") + "/webservice/rest/server.php"
    data = {
        "wstoken": token,
        "moodlewsrestformat": "json",
        "wsfunction": function,
        **flatten_moodle_params(params),
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(endpoint, data=data)
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise MoodleWsError(f"Moodle-WS nicht erreichbar ({function}): {exc}") from exc
    except ValueError as exc:
        # A 200 with a non-JSON body (proxy/WAF/captive-portal HTML page).
        # json.JSONDecodeError is a ValueError; funnel it through the same
        # canonical wrapper so every call site sees a MoodleWsError, not a
        # raw decode error.
        raise MoodleWsError(
            f"Moodle-WS lieferte kein JSON ({function}): {exc}"
        ) from exc

    if isinstance(payload, dict) and payload.get("exception"):
        raise MoodleWsError(
            f"Moodle-WS Fehler ({function}): "
            f"{payload.get('errorcode')} — {payload.get('message')}"
        )
    return payload
