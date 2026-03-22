"""Tests for the i18n translation service."""


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
        from services.translation_service import init_translations, t

        init_translations()
        result = t("test_only_in_de", locale="en")
        assert result == "Nur auf Deutsch"

    def test_translate_unknown_key_returns_key(self):
        from services.translation_service import init_translations, t

        init_translations()
        result = t("nonexistent_key", locale="de")
        assert "nonexistent_key" in result

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
