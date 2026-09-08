"""Machine-readable API errors (TF-773).

The wire format is *additive*: ``detail`` keeps its existing meaning — a
human-readable string in the caller's language — and the machine-readable
code arrives as a sibling field next to it::

    HTTP 409
    {
      "detail": "Ein Tag mit diesem Namen existiert bereits.",
      "error_code": "documents_tag_exists",
      "error_params": {"name": "Mathematik"}
    }

Why a sibling and not ``detail: {code, message}``: 89 call sites across the
three frontend tiers read ``response.data.detail`` as a string (DocumentService
20, ReviewService 16, AdminService 14, RBACService 11, ChatService 8, …).
Nesting the code inside ``detail`` turns every one of them into a *silent*
regression — they would fall through to a generic fallback rather than raise,
so nothing fails loudly. The sibling field costs one exception handler and
breaks nothing. See docs/adr/0005-backend-fehlercodes-als-geschwisterfeld.md.

``error_code`` is, verbatim, the key in ``core/backend/locales/t.{de,en,fr,it}
.json`` — not a parallel naming scheme. That identity is what lets the contract
test in ``tests/test_error_codes_contract.py`` be an exact set comparison
instead of a mapping table, and it means the 265 sites that already call
``t()`` need no key renaming at all.

Usage — the short form covers almost every case::

    from errors import api_error
    from services.translation_service import get_request_locale

    locale = get_request_locale(request, current_user)
    raise api_error(409, "documents_tag_exists", locale)

    # with interpolation — params go to t() *and* into error_params,
    # so a client can re-render the message in its own wording:
    raise api_error(422, "admin_unknown_permissions", locale, permissions=", ".join(unknown))

Use ``AppHTTPException`` directly only when the message must NOT come from the
locale files (e.g. it echoes back a service-layer exception's own text).
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from services.translation_service import DEFAULT_LOCALE, t

#: Reserved codes that are not raised from endpoint code. They are produced by
#: the framework-level handlers in ``main.py`` and still have to resolve in all
#: four locales, so the contract test knows about them. Both
#: ``AppHTTPException`` and ``api_error()`` refuse to construct with one of
#: these (see below), so a hand-written call site can't silently impersonate a
#: framework response shape — e.g. a business 500 that skips the guaranteed
#: ``logger.exception`` in ``main.py``'s unhandled-exception handler.
RESERVED_ERROR_CODES = (
    "validation_error",
    "internal_error",
)

#: Names an interpolation kwarg to ``api_error()`` must not use. They don't
#: collide with ``api_error()`` itself — that class of collision was closed by
#: making its own parameters positional-only, below — but with
#: ``t(key, locale=..., **kwargs)`` further down the call chain, whose
#: signature this module doesn't control and which ~265 pre-existing call
#: sites already depend on. Caught eagerly so the failure is a clear
#: ``TypeError`` at the call site instead of a cryptic "t() got multiple
#: values for argument 'locale'" several frames down.
_RESERVED_INTERPOLATION_NAMES = frozenset({"key", "locale"})


class AppHTTPException(HTTPException):
    """``HTTPException`` that also carries a stable, machine-readable code.

    Nothing about ``detail`` changes — subclassing keeps every existing
    ``except HTTPException`` handler, every ``raise`` from a dependency and
    FastAPI's own routing working unchanged. The extra attributes are read by
    the handler registered in ``main.py``; if that handler were ever removed,
    responses would silently degrade to today's format rather than break.

    ``detail`` must be a plain string: the whole point of the sibling-field
    design (see module docstring) is that the 89 existing frontend call sites
    can keep reading ``response.data.detail`` as a string forever. A dict or
    list here would silently reproduce that exact regression for whichever
    endpoint does it, so it's rejected at construction time rather than left
    for a client to discover via its generic fallback. The one legitimate
    dict-``detail`` shape in this codebase
    (``services/auswertung_quotas.py::_http_402``, kept for
    ``QuotaBanner.tsx``) predates this module and raises a plain
    ``fastapi.HTTPException`` directly, not ``AppHTTPException``.
    """

    def __init__(
        self,
        status_code: int,
        detail: str,
        *,
        error_code: str,
        error_params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        if error_code in RESERVED_ERROR_CODES:
            raise ValueError(
                f"error_code={error_code!r} is reserved for the "
                "framework-level handlers in main.py (validation_error / "
                "internal_error) and must not be raised from endpoint code "
                "— see RESERVED_ERROR_CODES."
            )
        if not isinstance(detail, str):
            raise TypeError(
                f"AppHTTPException.detail must be a str, got "
                f"{type(detail).__name__}. The additive envelope depends on "
                "every response's `detail` staying a string for the 89 "
                "existing frontend call sites (see module docstring)."
            )
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code
        # Normalise {} to None so the handler can omit the field entirely
        # rather than serialising an empty object on every error response.
        self.error_params = error_params or None


def api_error(
    status_code: int,
    code: str,
    locale: str = DEFAULT_LOCALE,
    headers: dict[str, str] | None = None,
    /,
    **params: Any,
) -> AppHTTPException:
    """Build a translated, coded HTTP error.

    ``code`` is both the ``error_code`` on the wire and the translation key —
    they are the same string by construction, which is the invariant the
    contract test relies on.

    ``**params`` are passed to ``t()`` for interpolation *and* surfaced as
    ``error_params``, so a client that prefers its own wording can rebuild the
    sentence without parsing the rendered one.

    The first four parameters (``status_code``, ``code``, ``locale``,
    ``headers``) are positional-only (``/``) so that an interpolation
    variable may be named any of them without colliding. That is not
    hypothetical: ``competency_frameworks_duplicate_code`` interpolates
    ``%{code}``, and before ``code`` was made positional-only that call raised
    "got multiple values for argument 'code'" at runtime rather than being
    caught early. ``headers`` used to be keyword-only, which looked safe but
    wasn't: a ``%{headers}`` interpolation value passed as ``headers=...`` was
    silently captured by the *real* HTTP-headers parameter instead of
    reaching ``params`` — the message would render the literal placeholder
    text, and the response would carry a nonsense header value, with no error
    at all. Positional-only converts that into the same loud, immediate
    ``TypeError`` as the ``code`` collision (see the guard below for the two
    names positional-only can't help with).

    ``key`` and ``locale`` remain genuinely reserved even after this: they are
    ``t()``'s own named parameters, and ``t()`` is called by ~265 other
    pre-existing sites this module can't make positional-only on their
    behalf. A message needing a ``%{key}`` or ``%{locale}`` variable has to
    build ``AppHTTPException`` directly instead — attempting it here raises a
    ``TypeError`` immediately rather than failing deep inside ``t()``.
    """
    collision = _RESERVED_INTERPOLATION_NAMES.intersection(params)
    if collision:
        raise TypeError(
            "api_error() interpolation params must not use the reserved "
            f"name(s) {sorted(collision)} — they collide with t()'s own "
            "parameters. Build AppHTTPException directly if a message "
            "genuinely needs one of these as a %{...} variable."
        )
    return AppHTTPException(
        status_code=status_code,
        detail=t(code, locale, **params),
        error_code=code,
        error_params=params or None,
        headers=headers,
    )
