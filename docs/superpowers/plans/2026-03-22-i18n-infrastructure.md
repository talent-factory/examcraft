# i18n Infrastructure (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up end-to-end i18n infrastructure for ExamCraft with backend translation service, frontend react-i18next, language switcher, and user preference persistence — proven with 5-10 demo strings.

**Architecture:** Backend uses `python-i18n` with JSON locale files and Starlette middleware for Accept-Language resolution. Frontend uses `react-i18next` with nested JSON translation files and browser language detection. User language preference stored as dedicated DB column, synced between frontend and backend on login. Backend middleware resolves locale from Accept-Language header only; for authenticated endpoints, `current_user.preferred_language` is passed directly to the `t()` helper.

**Tech Stack:** python-i18n, react-i18next, i18next, i18next-browser-languagedetector, Alembic, FastAPI, React 18, TypeScript

**Spec:** `docs/superpowers/specs/2026-03-22-i18n-infrastructure-design.md`

> **Path convention:** All file paths are relative to `packages/core/` unless prefixed with `(root)`.

> **python-i18n note:** The library uses filename prefix as namespace and dots as key separators. Files are named `t.{locale}.json` with the locale as root JSON key. Keys use underscores: `auth_email_taken` not `auth.email_taken`. The wrapper `t()` function hides the namespace prefix.

---

### Task 1: Add python-i18n dependency

**Files:**
- Modify: `(root) pyproject.toml:7-24`

- [ ] **Step 1: Add python-i18n to dependencies**

In `pyproject.toml`, add `"python-i18n>=0.3.9"` to the `dependencies` list after the `redis` entry (line 23):

```toml
    "redis>=7.0.0",
    "python-i18n>=0.3.9",
```

- [ ] **Step 2: Verify import works**

```bash
cd packages/core/backend
pip install python-i18n
python -c "import i18n; print('python-i18n OK')"
```

Expected: `python-i18n OK`

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "feat(i18n): add python-i18n dependency"
```

---

### Task 2: Create backend translation service and locale files

**Files:**
- Create: `backend/services/translation_service.py`
- Create: `backend/locales/t.de.json`
- Create: `backend/locales/t.en.json`
- Create: `backend/locales/t.fr.json`
- Create: `backend/locales/t.it.json`
- Create: `backend/tests/test_translation_service.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_translation_service.py`:

```python
"""Tests for the i18n translation service."""

import pytest


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
        # Use a key that only exists in de, not in en
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd packages/core/backend
pytest tests/test_translation_service.py -v
```

Expected: FAIL -- `ModuleNotFoundError: No module named 'services.translation_service'`

- [ ] **Step 3: Create locale JSON files**

`python-i18n` requires: filename = `{namespace}.{locale}.json`, root key = locale code.

Create `backend/locales/t.de.json`:

```json
{
  "de": {
    "auth_email_taken": "E-Mail-Adresse ist bereits registriert",
    "auth_not_found": "Benutzer nicht gefunden",
    "auth_invalid_credentials": "Ung\u00fcltige Anmeldedaten",
    "auth_account_locked": "Konto gesperrt. Bitte warten Sie 30 Minuten.",
    "auth_unauthorized": "Authentifizierung erforderlich",
    "documents_upload_failed": "Upload fehlgeschlagen. Bitte erneut versuchen.",
    "documents_not_found": "Dokument nicht gefunden",
    "general_not_found": "Ressource nicht gefunden",
    "general_forbidden": "Zugriff verweigert",
    "general_server_error": "Interner Serverfehler",
    "test_only_in_de": "Nur auf Deutsch"
  }
}
```

Create `backend/locales/t.en.json`:

```json
{
  "en": {
    "auth_email_taken": "Email address is already registered",
    "auth_not_found": "User not found",
    "auth_invalid_credentials": "Invalid credentials",
    "auth_account_locked": "Account locked. Please wait 30 minutes.",
    "auth_unauthorized": "Authentication required",
    "documents_upload_failed": "Upload failed. Please try again.",
    "documents_not_found": "Document not found",
    "general_not_found": "Resource not found",
    "general_forbidden": "Access denied",
    "general_server_error": "Internal server error"
  }
}
```

Create `backend/locales/t.fr.json`:

```json
{
  "fr": {
    "auth_email_taken": "L'adresse e-mail est d\u00e9j\u00e0 enregistr\u00e9e",
    "auth_not_found": "Utilisateur introuvable",
    "auth_invalid_credentials": "Identifiants invalides",
    "auth_account_locked": "Compte verrouill\u00e9. Veuillez patienter 30 minutes.",
    "auth_unauthorized": "Authentification requise",
    "documents_upload_failed": "\u00c9chec du t\u00e9l\u00e9chargement. Veuillez r\u00e9essayer.",
    "documents_not_found": "Document introuvable",
    "general_not_found": "Ressource introuvable",
    "general_forbidden": "Acc\u00e8s refus\u00e9",
    "general_server_error": "Erreur interne du serveur"
  }
}
```

Create `backend/locales/t.it.json`:

```json
{
  "it": {
    "auth_email_taken": "L'indirizzo e-mail \u00e8 gi\u00e0 registrato",
    "auth_not_found": "Utente non trovato",
    "auth_invalid_credentials": "Credenziali non valide",
    "auth_account_locked": "Account bloccato. Attendere 30 minuti.",
    "auth_unauthorized": "Autenticazione richiesta",
    "documents_upload_failed": "Caricamento fallito. Riprovare.",
    "documents_not_found": "Documento non trovato",
    "general_not_found": "Risorsa non trovata",
    "general_forbidden": "Accesso negato",
    "general_server_error": "Errore interno del server"
  }
}
```

- [ ] **Step 4: Create translation service**

Create `backend/services/translation_service.py`:

```python
"""i18n translation service using python-i18n.

Provides locale-aware translation for user-facing API messages.
Log messages are NOT translated -- they stay in English.

python-i18n expects files named {namespace}.{locale}.json with the
locale as root key. We use namespace "t" so files are t.de.json etc.
Keys use underscores: t("auth_email_taken", locale="de").
"""

import os

import i18n

SUPPORTED_LOCALES = ["de", "en", "fr", "it"]
DEFAULT_LOCALE = "de"

_NAMESPACE = "t"


def init_translations() -> None:
    """Initialize python-i18n with JSON locale files."""
    locales_path = os.path.join(os.path.dirname(__file__), "..", "locales")
    i18n.set("load_path", [os.path.abspath(locales_path)])
    i18n.set("file_format", "json")
    i18n.set("fallback", DEFAULT_LOCALE)
    i18n.set("error_on_missing_translation", False)
    i18n.set("enable_memoization", True)


def t(key: str, locale: str = DEFAULT_LOCALE, **kwargs) -> str:
    """Translate a key for the given locale.

    The namespace prefix is added automatically.
    Usage: t("auth_email_taken", locale="de")

    Args:
        key: Translation key (e.g., "auth_email_taken")
        locale: Language code (de, en, fr, it)
        **kwargs: Interpolation variables

    Returns:
        Translated string, or fallback/key if not found.
    """
    if locale not in SUPPORTED_LOCALES:
        locale = DEFAULT_LOCALE
    return i18n.t(f"{_NAMESPACE}.{key}", locale=locale, **kwargs)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd packages/core/backend
pytest tests/test_translation_service.py -v
```

Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/services/translation_service.py backend/locales/ backend/tests/test_translation_service.py
git commit -m "feat(i18n): add translation service with locale files (de/en/fr/it)"
```

---

### Task 3: Create i18n middleware with Accept-Language parsing

**Files:**
- Create: `backend/middleware/i18n_middleware.py`
- Create: `backend/tests/test_i18n_middleware.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_i18n_middleware.py`:

```python
"""Tests for i18n middleware locale resolution."""

import pytest


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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd packages/core/backend
pytest tests/test_i18n_middleware.py -v
```

Expected: FAIL -- `ModuleNotFoundError`

- [ ] **Step 3: Implement i18n middleware**

Create `backend/middleware/i18n_middleware.py`:

```python
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
    """Resolve locale from Accept-Language header or default.

    For authenticated requests, endpoints pass current_user.preferred_language
    directly to t() instead of relying on middleware.

    Args:
        accept_language_header: Raw Accept-Language header value.

    Returns:
        Resolved locale code (de, en, fr, or it).
    """
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd packages/core/backend
pytest tests/test_i18n_middleware.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/middleware/i18n_middleware.py backend/tests/test_i18n_middleware.py
git commit -m "feat(i18n): add i18n middleware with Accept-Language parsing"
```

---

### Task 4: Add preferred_language column to User model + migration

**Files:**
- Modify: `backend/models/auth.py:295-336`
- Create: `backend/alembic/versions/f1a2b3c4d5e6_add_preferred_language.py`

- [ ] **Step 1: Add preferred_language column to User model**

In `backend/models/auth.py`, after line 295 (`preferences = Column(Text, nullable=True)`), add:

```python
    # Language Preference (i18n)
    preferred_language = Column(String(5), nullable=True, default=None)
```

- [ ] **Step 2: Add CheckConstraint to __table_args__**

In `backend/models/auth.py`, modify the `__table_args__` tuple (lines 331-336) to include the language constraint:

```python
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive', 'suspended', 'pending')",
            name="check_user_status",
        ),
        CheckConstraint(
            "preferred_language IN ('de', 'en', 'fr', 'it') OR preferred_language IS NULL",
            name="ck_user_preferred_language",
        ),
    )
```

- [ ] **Step 3: Create Alembic migration**

Create `backend/alembic/versions/f1a2b3c4d5e6_add_preferred_language.py`:

```python
"""add_preferred_language

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
Create Date: 2026-03-22

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "f1a2b3c4d5e6"  # pragma: allowlist secret
down_revision = "e1f2a3b4c5d6"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    """Check if a column already exists (idempotent migration support)."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c["name"] for c in inspector.get_columns(table)]
    return column in columns


def upgrade() -> None:
    if not _column_exists("users", "preferred_language"):
        op.add_column(
            "users",
            sa.Column("preferred_language", sa.String(5), nullable=True),
        )
        op.create_check_constraint(
            "ck_user_preferred_language",
            "users",
            "preferred_language IN ('de', 'en', 'fr', 'it') OR preferred_language IS NULL",
        )


def downgrade() -> None:
    op.drop_constraint("ck_user_preferred_language", "users", type_="check")
    op.drop_column("users", "preferred_language")
```

Note: Verify `down_revision` matches the latest migration:
```bash
ls packages/core/backend/alembic/versions/ | sort | tail -1
```
Adjust `down_revision` to match the revision ID in that file.

- [ ] **Step 4: Verify model loads without error**

```bash
cd packages/core/backend
python -c "from models.auth import User; print('User model OK, columns:', [c.name for c in User.__table__.columns if 'language' in c.name])"
```

Expected: `User model OK, columns: ['preferred_language']`

- [ ] **Step 5: Commit**

```bash
git add backend/models/auth.py backend/alembic/versions/f1a2b3c4d5e6_add_preferred_language.py
git commit -m "feat(i18n): add preferred_language column to User model"
```

---

### Task 5: Extend profile API to accept preferred_language

**Files:**
- Modify: `backend/api/auth.py:142-169, 557-582`
- Create: `backend/tests/test_profile_language.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_profile_language.py`:

```python
"""Tests for preferred_language in profile API."""

import pytest
from pydantic import ValidationError


class TestUserProfileUpdateModel:
    """Test that UserProfileUpdate accepts preferred_language."""

    def test_valid_language_de(self):
        from api.auth import UserProfileUpdate

        update = UserProfileUpdate(preferred_language="de")
        assert update.preferred_language == "de"

    def test_valid_language_en(self):
        from api.auth import UserProfileUpdate

        update = UserProfileUpdate(preferred_language="en")
        assert update.preferred_language == "en"

    def test_valid_language_fr(self):
        from api.auth import UserProfileUpdate

        update = UserProfileUpdate(preferred_language="fr")
        assert update.preferred_language == "fr"

    def test_valid_language_it(self):
        from api.auth import UserProfileUpdate

        update = UserProfileUpdate(preferred_language="it")
        assert update.preferred_language == "it"

    def test_none_language(self):
        from api.auth import UserProfileUpdate

        update = UserProfileUpdate()
        assert update.preferred_language is None

    def test_invalid_language_rejected(self):
        from api.auth import UserProfileUpdate

        with pytest.raises(ValidationError):
            UserProfileUpdate(preferred_language="ja")

    def test_invalid_language_empty_string_rejected(self):
        from api.auth import UserProfileUpdate

        with pytest.raises(ValidationError):
            UserProfileUpdate(preferred_language="")

    def test_language_in_model_dump(self):
        from api.auth import UserProfileUpdate

        update = UserProfileUpdate(preferred_language="fr")
        data = update.model_dump(exclude_unset=True)
        assert data["preferred_language"] == "fr"


class TestUserProfileResponseModel:
    """Test that UserProfileResponse includes preferred_language."""

    def test_response_has_language_field(self):
        from api.auth import UserProfileResponse

        fields = UserProfileResponse.model_fields
        assert "preferred_language" in fields
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd packages/core/backend
pytest tests/test_profile_language.py -v
```

Expected: FAIL -- `preferred_language` not in UserProfileUpdate

- [ ] **Step 3: Add preferred_language to Pydantic models**

In `backend/api/auth.py`:

Add to `UserProfileResponse` class (after line 155, `avatar_url`):

```python
    preferred_language: Optional[str] = None
```

Add to `UserProfileUpdate` class (after line 169, `avatar_url`):

```python
    preferred_language: Optional[str] = Field(None, pattern="^(de|en|fr|it)$")
```

- [ ] **Step 4: Add preferred_language handling in update endpoint**

In `backend/api/auth.py`, in the `update_current_user_profile` function, after the `avatar_url` block (after line 582), add:

```python
    if request.preferred_language is not None:
        current_user.preferred_language = request.preferred_language
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd packages/core/backend
pytest tests/test_profile_language.py -v
```

Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/api/auth.py backend/tests/test_profile_language.py
git commit -m "feat(i18n): add preferred_language to profile API"
```

---

### Task 6: Register i18n middleware and init translations in main.py

**Files:**
- Modify: `backend/main.py:401-416`

- [ ] **Step 1: Add translation init to startup**

In `backend/main.py`, in the lifespan/startup section (where other services are initialized), add:

```python
# Initialize i18n translations
from services.translation_service import init_translations
init_translations()
```

- [ ] **Step 2: Register I18nMiddleware**

In `backend/main.py`, after the RateLimitMiddleware registration (after line 416), add:

```python
# i18n Middleware - resolves locale from Accept-Language header
from middleware.i18n_middleware import I18nMiddleware  # noqa: E402

app.add_middleware(I18nMiddleware)
```

- [ ] **Step 3: Verify app starts without errors**

```bash
cd packages/core/backend
python -c "from main import app; print('App loaded OK')"
```

Expected: `App loaded OK` (no import errors)

- [ ] **Step 4: Commit**

```bash
git add backend/main.py
git commit -m "feat(i18n): register i18n middleware and init translations"
```

---

### Task 7: Install frontend i18next dependencies

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install dependencies**

```bash
cd packages/core/frontend
npm install i18next react-i18next i18next-browser-languagedetector
```

- [ ] **Step 2: Verify installation**

```bash
cd packages/core/frontend
node -e "require('i18next'); require('react-i18next'); require('i18next-browser-languagedetector'); console.log('i18next deps OK')"
```

Expected: `i18next deps OK`

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "feat(i18n): add i18next frontend dependencies"
```

---

### Task 8: Create frontend i18n config and locale files

**Files:**
- Create: `frontend/src/i18n.ts`
- Create: `frontend/src/locales/de/translation.json`
- Create: `frontend/src/locales/en/translation.json`
- Create: `frontend/src/locales/fr/translation.json`
- Create: `frontend/src/locales/it/translation.json`
- Modify: `frontend/src/index.tsx`

- [ ] **Step 1: Create locale JSON files**

Create `frontend/src/locales/de/translation.json`:

```json
{
  "nav": {
    "profile": "Profil",
    "settings": "Einstellungen",
    "logout": "Abmelden",
    "language": "Sprache"
  },
  "language": {
    "de": "Deutsch",
    "en": "English",
    "fr": "Fran\u00e7ais",
    "it": "Italiano"
  }
}
```

Create `frontend/src/locales/en/translation.json`:

```json
{
  "nav": {
    "profile": "Profile",
    "settings": "Settings",
    "logout": "Logout",
    "language": "Language"
  },
  "language": {
    "de": "Deutsch",
    "en": "English",
    "fr": "Fran\u00e7ais",
    "it": "Italiano"
  }
}
```

Create `frontend/src/locales/fr/translation.json`:

```json
{
  "nav": {
    "profile": "Profil",
    "settings": "Param\u00e8tres",
    "logout": "D\u00e9connexion",
    "language": "Langue"
  },
  "language": {
    "de": "Deutsch",
    "en": "English",
    "fr": "Fran\u00e7ais",
    "it": "Italiano"
  }
}
```

Create `frontend/src/locales/it/translation.json`:

```json
{
  "nav": {
    "profile": "Profilo",
    "settings": "Impostazioni",
    "logout": "Esci",
    "language": "Lingua"
  },
  "language": {
    "de": "Deutsch",
    "en": "English",
    "fr": "Fran\u00e7ais",
    "it": "Italiano"
  }
}
```

- [ ] **Step 2: Create i18n config**

Create `frontend/src/i18n.ts`:

```typescript
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import de from './locales/de/translation.json';
import en from './locales/en/translation.json';
import fr from './locales/fr/translation.json';
import it from './locales/it/translation.json';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      de: { translation: de },
      en: { translation: en },
      fr: { translation: fr },
      it: { translation: it },
    },
    fallbackLng: 'de',
    interpolation: {
      escapeValue: false, // React already escapes
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: 'examcraft_language',
    },
  });

export default i18n;
```

- [ ] **Step 3: Import i18n in app entry point**

In `frontend/src/index.tsx`, add after line 5 (after the sentry import):

```typescript
import './i18n'; // Initialize i18n before app render
```

- [ ] **Step 4: Verify app compiles**

```bash
cd packages/core/frontend
npx tsc --noEmit 2>&1 | head -20
```

Expected: No new errors related to i18n files

- [ ] **Step 5: Commit**

```bash
git add frontend/src/i18n.ts frontend/src/locales/ frontend/src/index.tsx
git commit -m "feat(i18n): add frontend i18n config with locale files"
```

---

### Task 9: Add preferred_language to frontend types

**Files:**
- Modify: `frontend/src/types/auth.ts:64-80, 162-166, 168-183`

- [ ] **Step 1: Add field to User interface**

In `frontend/src/types/auth.ts`, in the `User` interface, add after line 79 (`updated_at?: string;`):

```typescript
  preferred_language?: string;
```

- [ ] **Step 2: Add field to UpdateProfileRequest interface**

In `frontend/src/types/auth.ts`, in the `UpdateProfileRequest` interface (lines 162-166), add before closing brace:

```typescript
  preferred_language?: string;
```

- [ ] **Step 3: Add field to UserResponse interface**

In `frontend/src/types/auth.ts`, in the `UserResponse` interface (lines 168-183), add after line 182 (`created_at: string;`):

```typescript
  preferred_language?: string;
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/auth.ts
git commit -m "feat(i18n): add preferred_language to frontend auth types"
```

---

### Task 10: Add language switcher to NavigationBar

**Files:**
- Modify: `frontend/src/components/layout/NavigationBar.tsx`

- [ ] **Step 1: Add i18n imports**

In `NavigationBar.tsx`, add after line 8 (`import { useAuth } from ...`):

```typescript
import { useTranslation } from 'react-i18next';
import { AuthService } from '../../services/AuthService';
```

Note: Check the actual import path for AuthService -- it may be at `../../services/auth` or similar. Look at how other components import it.

- [ ] **Step 2: Add useTranslation hook**

Inside the component, after line 15 (`const [avatarError, setAvatarError] = useState(false);`), add:

```typescript
  const { t, i18n } = useTranslation();
```

- [ ] **Step 3: Add language change handler and options**

After the `getAvatarUrl` function (after line 32), add:

```typescript
  const handleLanguageChange = async (lng: string) => {
    await i18n.changeLanguage(lng);
    // Persist preference to backend if user is logged in
    const token = localStorage.getItem('examcraft_access_token');
    if (user && token) {
      try {
        await AuthService.updateProfile(token, { preferred_language: lng });
      } catch (error) {
        console.error('Failed to save language preference:', error);
      }
    }
  };

  const LANGUAGE_OPTIONS = [
    { code: 'de', label: 'Deutsch' },
    { code: 'en', label: 'English' },
    { code: 'fr', label: 'Fran\u00e7ais' },
    { code: 'it', label: 'Italiano' },
  ];
```

- [ ] **Step 4: Add language switcher to dropdown menu**

In the dropdown menu, between the Settings link (ends line 100) and the Logout button (starts line 101), add:

```tsx
                    <div className="border-t border-gray-100 my-1"></div>
                    <div className="px-4 py-1 text-xs text-gray-500">
                      {t('nav.language')}
                    </div>
                    {LANGUAGE_OPTIONS.map((lang) => (
                      <button
                        key={lang.code}
                        type="button"
                        onClick={() => {
                          handleLanguageChange(lang.code);
                          setShowUserMenu(false);
                        }}
                        className={`block w-full text-left px-4 py-1.5 text-sm hover:bg-gray-100 ${
                          i18n.language?.startsWith(lang.code)
                            ? 'text-primary-600 font-medium bg-primary-50'
                            : 'text-gray-700'
                        }`}
                      >
                        {lang.label}
                      </button>
                    ))}
```

- [ ] **Step 5: Replace hardcoded nav strings with t() calls**

Replace the three hardcoded menu items:

Line 92: Change `👤 Profile` to `{t('nav.profile')}`
Line 99: Change `⚙️ Settings` to `{t('nav.settings')}`
Line 106: Change `🚪 Logout` to `{t('nav.logout')}`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/layout/NavigationBar.tsx
git commit -m "feat(i18n): add language switcher to navigation bar"
```

---

### Task 11: Sync language preference on login in AuthContext

**Files:**
- Modify: `frontend/src/contexts/AuthContext.tsx`

- [ ] **Step 1: Add i18n import**

In `AuthContext.tsx`, add after the existing imports (around line 6):

```typescript
import i18n from '../i18n';
```

- [ ] **Step 2: Add language sync after login**

In the `login` callback, after line 179 (`const user = await AuthService.getProfile(tokens.access_token);`), add:

```typescript
      // Sync language preference from user profile
      if (user.preferred_language) {
        i18n.changeLanguage(user.preferred_language);
      }
```

- [ ] **Step 3: Add language sync after loginWithTokens (OAuth)**

In the `loginWithTokens` callback, after line 213 (`const user = await AuthService.getProfile(accessToken);`), add the same block:

```typescript
      if (user.preferred_language) {
        i18n.changeLanguage(user.preferred_language);
      }
```

- [ ] **Step 4: Add language sync after register**

In the `register` callback, after line 246 (`const user = await AuthService.getProfile(tokens.access_token);`), add the same block:

```typescript
      if (user.preferred_language) {
        i18n.changeLanguage(user.preferred_language);
      }
```

- [ ] **Step 5: Verify logout does NOT clear examcraft_language**

Check the logout function (lines 274-297). It removes `ACCESS_TOKEN_KEY`, `REFRESH_TOKEN_KEY`, and `USER_KEY` from localStorage. It does NOT remove `examcraft_language` -- this is correct. No changes needed.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/contexts/AuthContext.tsx
git commit -m "feat(i18n): sync language preference on login/register"
```

---

### Task 12: Run full test suite and verify integration

**Files:** (no new files)

- [ ] **Step 1: Run backend i18n tests**

```bash
cd packages/core/backend
pytest tests/test_translation_service.py tests/test_i18n_middleware.py tests/test_profile_language.py -v
```

Expected: All tests PASS

- [ ] **Step 2: Run full backend test suite for regressions**

```bash
cd packages/core/backend
pytest tests/ -v --tb=short 2>&1 | tail -30
```

Expected: No new failures from i18n changes

- [ ] **Step 3: Run frontend type check**

```bash
cd packages/core/frontend
npx tsc --noEmit 2>&1 | tail -10
```

Expected: No new type errors from i18n changes

- [ ] **Step 4: Run ruff linting on new Python files**

```bash
ruff check packages/core/backend/services/translation_service.py packages/core/backend/middleware/i18n_middleware.py
ruff format packages/core/backend/services/translation_service.py packages/core/backend/middleware/i18n_middleware.py
```

Expected: Clean or auto-fixed

- [ ] **Step 5: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix(i18n): address lint and test issues"
```

Only if fixes were needed.
