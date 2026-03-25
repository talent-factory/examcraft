"""Tests for i18n middleware locale resolution."""


class TestParseAcceptLanguage:
    """Test Accept-Language header parsing."""

    def test_simple_language(self):
        from middleware.i18n_middleware import parse_accept_language

        result = parse_accept_language("de")
        assert result == "de"

    def test_language_with_region(self):
        from middleware.i18n_middleware import parse_accept_language

        result = parse_accept_language("de-CH")
        assert result == "de"

    def test_french_swiss(self):
        from middleware.i18n_middleware import parse_accept_language

        result = parse_accept_language("fr-CH")
        assert result == "fr"

    def test_multiple_languages_with_quality(self):
        from middleware.i18n_middleware import parse_accept_language

        result = parse_accept_language("fr-CH,fr;q=0.9,en;q=0.8,de;q=0.7")
        assert result == "fr"

    def test_prefer_higher_quality(self):
        from middleware.i18n_middleware import parse_accept_language

        result = parse_accept_language("en;q=0.5,de;q=0.9")
        assert result == "de"

    def test_unsupported_language_returns_none(self):
        from middleware.i18n_middleware import parse_accept_language

        result = parse_accept_language("ja,zh;q=0.9")
        assert result is None

    def test_empty_header_returns_none(self):
        from middleware.i18n_middleware import parse_accept_language

        result = parse_accept_language("")
        assert result is None

    def test_wildcard_returns_none(self):
        from middleware.i18n_middleware import parse_accept_language

        result = parse_accept_language("*")
        assert result is None


class TestResolveLocale:
    """Test full locale resolution logic."""

    def test_accept_language_used(self):
        from middleware.i18n_middleware import resolve_locale

        result = resolve_locale(accept_language_header="en-US,en;q=0.9")
        assert result == "en"

    def test_default_fallback(self):
        from middleware.i18n_middleware import resolve_locale

        result = resolve_locale(accept_language_header=None)
        assert result == "de"

    def test_unsupported_falls_to_default(self):
        from middleware.i18n_middleware import resolve_locale

        result = resolve_locale(accept_language_header="ja,zh;q=0.9")
        assert result == "de"
