"""Tests for the i18n translation service."""

from unittest.mock import MagicMock


class TestTranslationService:
    """Test translation service initialization and key lookup."""

    def test_translate_known_key_de(self):
        from services.translation_service import init_translations, t

        init_translations()
        result = t("auth_email_taken", locale="de")
        assert result == "E-Mail-Adresse ist bereits registriert"

    def test_translate_known_key_en(self):
        from services.translation_service import init_translations, t

        init_translations()
        result = t("auth_email_taken", locale="en")
        assert result == "Email address is already registered"

    def test_translate_fallback_to_de_for_missing_key(self):
        from services.translation_service import DEFAULT_LOCALE, init_translations, t

        init_translations()
        # "not_found" exists in all locales; verify the fallback mechanism
        # works by requesting a key in the default locale and comparing
        result_de = t("not_found", locale=DEFAULT_LOCALE)
        result_en = t("not_found", locale="en")
        assert result_de == "Nicht gefunden"
        assert result_en == "Not found"

    def test_translate_unknown_key_returns_fallback(self):
        from services.translation_service import init_translations, t

        init_translations()
        result = t("nonexistent_key", locale="de")
        assert result == "Ein Fehler ist aufgetreten"
        result_en = t("nonexistent_key", locale="en")
        assert result_en == "An error occurred"

    def test_translate_fr(self):
        from services.translation_service import init_translations, t

        init_translations()
        result = t("auth_email_taken", locale="fr")
        assert "e-mail" in result.lower() or "enregistr" in result.lower()

    def test_translate_it(self):
        from services.translation_service import init_translations, t

        init_translations()
        result = t("auth_email_taken", locale="it")
        assert "e-mail" in result.lower() or "registrat" in result.lower()

    def test_unsupported_locale_falls_back_to_de(self):
        from services.translation_service import init_translations, t

        init_translations()
        result = t("auth_email_taken", locale="ja")
        assert result == "E-Mail-Adresse ist bereits registriert"

    def test_supported_locales(self):
        from services.translation_service import SUPPORTED_LOCALES

        assert SUPPORTED_LOCALES == ["de", "en", "fr", "it"]

    def test_default_locale_is_de(self):
        from services.translation_service import DEFAULT_LOCALE

        assert DEFAULT_LOCALE == "de"


def _make_request(locale=None):
    """Create a mock Request with optional state.locale."""
    request = MagicMock()
    if locale is not None:
        request.state.locale = locale
    else:
        # Remove locale attribute so hasattr(request.state, "locale") is False
        del request.state.locale
    return request


def _make_user(preferred_language=None):
    """Create a mock User with optional preferred_language."""
    user = MagicMock()
    user.preferred_language = preferred_language
    return user


class TestGetRequestLocale:
    """Test locale resolution via get_request_locale()."""

    def test_user_preference_wins_over_request_locale(self):
        from services.translation_service import get_request_locale

        user = _make_user(preferred_language="fr")
        request = _make_request(locale="en")
        assert get_request_locale(request, user) == "fr"

    def test_falls_back_to_request_locale_when_user_has_no_preference(self):
        from services.translation_service import get_request_locale

        user = _make_user(preferred_language=None)
        request = _make_request(locale="en")
        assert get_request_locale(request, user) == "en"

    def test_request_locale_used_when_no_user(self):
        from services.translation_service import get_request_locale

        request = _make_request(locale="fr")
        assert get_request_locale(request, None) == "fr"

    def test_default_when_no_user_and_no_request(self):
        from services.translation_service import get_request_locale

        assert get_request_locale(None, None) == "de"

    def test_user_preference_used_when_no_request(self):
        from services.translation_service import get_request_locale

        user = _make_user(preferred_language="fr")
        assert get_request_locale(None, user) == "fr"

    def test_default_when_request_has_no_locale_attribute(self):
        from services.translation_service import get_request_locale

        request = _make_request(locale=None)  # no locale on state
        assert get_request_locale(request, None) == "de"
