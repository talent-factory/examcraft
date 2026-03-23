"""Tests ensuring all backend locale files have identical key sets."""

import json
from pathlib import Path

LOCALES_DIR = Path(__file__).parent.parent / "locales"
SUPPORTED_LOCALES = ["de", "en", "fr", "it"]


class TestLocaleKeyParity:
    """Verify that every supported locale file exists and shares the same keys."""

    def _load_keys(self, locale: str) -> set:
        path = LOCALES_DIR / f"t.{locale}.json"
        with open(path) as f:
            data = json.load(f)
        # Locale files use { "<locale>": { ...keys... } } structure
        inner = data.get(locale, data)
        return set(inner.keys())

    def test_all_locale_files_exist(self):
        for locale in SUPPORTED_LOCALES:
            path = LOCALES_DIR / f"t.{locale}.json"
            assert path.exists(), f"Missing locale file: {path}"

    def test_all_locales_have_same_keys(self):
        keys_by_locale = {loc: self._load_keys(loc) for loc in SUPPORTED_LOCALES}
        reference = keys_by_locale["de"]
        for locale, keys in keys_by_locale.items():
            missing = reference - keys
            extra = keys - reference
            assert not missing, f"Locale '{locale}' is missing keys: {missing}"
            assert not extra, f"Locale '{locale}' has extra keys: {extra}"
