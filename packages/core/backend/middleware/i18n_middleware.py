"""i18n middleware for locale resolution from Accept-Language header.

Resolves the request locale and stores it in request.state.locale.
For authenticated endpoints, the caller can override with
current_user.preferred_language when calling t().

Resolution order:
1. Accept-Language header (best match against supported locales)
2. Default locale ("de")
"""

import re
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from services.translation_service import DEFAULT_LOCALE, SUPPORTED_LOCALES


def parse_accept_language(header: Optional[str]) -> Optional[str]:
    """Parse Accept-Language header and return best matching supported locale.

    Handles quality weights and region subtags.
    E.g., "de-CH,de;q=0.9,en;q=0.8" -> "de"

    Returns None if no supported locale matches.
    """
    if not header or header.strip() == "*":
        return None

    entries = []
    for part in header.split(","):
        part = part.strip()
        if not part:
            continue

        match = re.match(r"^([a-zA-Z*-]+)(?:;q=([0-9.]+))?$", part)
        if not match:
            continue

        lang = match.group(1)
        if lang == "*":
            continue

        quality = float(match.group(2)) if match.group(2) else 1.0

        # Strip region subtag (e.g., de-CH -> de, fr-CH -> fr)
        base_lang = lang.split("-")[0].lower()

        if base_lang in SUPPORTED_LOCALES:
            entries.append((base_lang, quality))

    if not entries:
        return None

    entries.sort(key=lambda x: x[1], reverse=True)
    return entries[0][0]


def resolve_locale(accept_language_header: Optional[str] = None) -> str:
    """Resolve locale from Accept-Language header or default."""
    from_header = parse_accept_language(accept_language_header)
    if from_header:
        return from_header
    return DEFAULT_LOCALE


class I18nMiddleware(BaseHTTPMiddleware):
    """Middleware that resolves request locale and sets request.state.locale."""

    async def dispatch(self, request: Request, call_next) -> Response:
        accept_language = request.headers.get("accept-language")
        locale = resolve_locale(accept_language_header=accept_language)
        request.state.locale = locale

        response = await call_next(request)
        response.headers["Content-Language"] = locale
        return response
