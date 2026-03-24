"""Translation service wrapping python-i18n for user-facing API messages.

Usage:
    from services.translation_service import init_translations, t, get_request_locale

    init_translations()  # Call once at startup (idempotent)
    message = t("auth_email_taken", locale="de")

    # In FastAPI endpoints:
    locale = get_request_locale(request, current_user)
    message = t("auth_email_taken", locale=locale)

Locale files live in packages/core/backend/locales/ using a project-specific
naming convention: t.{locale}.json with root key = locale code. This overrides
the python-i18n default ({locale}.{namespace}.{format}) via filename_format config.

Log messages stay in English — only user-facing response strings are translated.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

import i18n

if TYPE_CHECKING:
    from fastapi import Request
    from models.auth import User

logger = logging.getLogger(__name__)

DEFAULT_LOCALE = "de"
SUPPORTED_LOCALES = ["de", "en", "fr", "it"]

_FALLBACK_MESSAGES: dict[str, str] = {
    "de": "Ein Fehler ist aufgetreten",
    "en": "An error occurred",
    "fr": "Une erreur est survenue",
    "it": "Si è verificato un errore",
}

_initialized = False

_LOCALES_DIR = os.path.join(os.path.dirname(__file__), "..", "locales")


def init_translations() -> None:
    """Initialize python-i18n settings.

    Idempotent — safe to call multiple times (e.g. in tests).
    """
    global _initialized
    if _initialized:
        return

    locales_path = os.path.normpath(_LOCALES_DIR)
    i18n.set("load_path", [locales_path])
    i18n.set("file_format", "json")
    i18n.set("filename_format", "{namespace}.{locale}.{format}")
    i18n.set("fallback", DEFAULT_LOCALE)
    i18n.set("enable_memoization", True)
    i18n.set("error_on_missing_translation", False)

    _initialized = True
    logger.info("Translations initialized from %s", locales_path)


def t(key: str, locale: str = DEFAULT_LOCALE, **kwargs) -> str:
    """Translate a key for the given locale.

    Falls back to DEFAULT_LOCALE ("de") for:
    - Unsupported locales (enforced by this function)
    - Keys missing in the requested locale (via python-i18n's fallback config)

    Returns the key (with namespace prefix) if the key is unknown in all locales.

    Args:
        key: Translation key using underscores, e.g. "auth_email_taken".
             Do NOT include the "t." namespace prefix — this wrapper adds it.
        locale: BCP-47 locale code, e.g. "de", "en", "fr", "it".
        **kwargs: Optional interpolation variables passed to python-i18n.

    Returns:
        Translated string, or a generic fallback message if not found.
    """
    if not _initialized:
        init_translations()

    effective_locale = locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE
    namespaced_key = f"t.{key}"

    result = i18n.t(namespaced_key, locale=effective_locale, **kwargs)
    if result == namespaced_key:
        logger.warning(
            "Missing translation key '%s' for locale '%s'", key, effective_locale
        )
        return _FALLBACK_MESSAGES.get(
            effective_locale, _FALLBACK_MESSAGES[DEFAULT_LOCALE]
        )
    return result


def get_request_locale(
    request: Request | None = None,
    user: User | None = None,
) -> str:
    """Determine the effective locale for the current request.

    Resolution order:
    1. Authenticated user's preferred_language (if set)
    2. request.state.locale (set by I18nMiddleware from Accept-Language)
    3. DEFAULT_LOCALE ("de")
    """
    if user and getattr(user, "preferred_language", None):
        lang = user.preferred_language
        if lang in SUPPORTED_LOCALES:
            return lang

    if request and hasattr(request, "state") and hasattr(request.state, "locale"):
        return request.state.locale

    return DEFAULT_LOCALE
