# Design Specification: i18n Infrastructure (Phase 1)

**Task:** TF-295 — Mehrsprachigkeit (i18n)
**Phase:** 1 of 5 (Infrastructure only)
**Date:** 2026-03-22
**Languages:** de (fallback), en, fr, it

## Context

ExamCraft has no i18n infrastructure. The backend contains ~175 user-facing messages (95% EN, 5% DE, mixed inconsistently). The frontend has ~619 hardcoded strings across ~79 components (60% DE, 40% EN). This phase sets up the translation infrastructure end-to-end without extracting all strings — subsequent phases handle bulk extraction and translation.

## Architecture Decisions

| Decision | Result |
|----------|--------|
| Translation scope | Backend + Frontend separately |
| Language preference | Browser locale before login, profile setting after login |
| Fallback language | German (de) |
| Backend library | `python-i18n` |
| Frontend library | `react-i18next` + `i18next` + `i18next-browser-languagedetector` |
| Frontend namespaces | Single namespace per language (one `translation.json`) |
| Language switcher | Inside user dropdown menu in NavigationBar |
| Live switch | Yes, without page reload (native react-i18next) |
| Log language | Always English (not translated) |

## Backend Design

### Translation Service

**File:** `backend/services/translation_service.py`

Thin wrapper around `python-i18n`:

```python
import i18n

SUPPORTED_LOCALES = ["de", "en", "fr", "it"]
DEFAULT_LOCALE = "de"

def init_translations():
    i18n.set("load_path", ["locales"])
    i18n.set("file_format", "json")
    i18n.set("fallback", DEFAULT_LOCALE)

def t(key: str, locale: str = DEFAULT_LOCALE, **kwargs) -> str:
    return i18n.t(key, locale=locale, **kwargs)
```

### Locale Files

**Location:** `backend/locales/{de,en,fr,it}.json`

Flat key structure organized by domain prefix:

```json
{
  "auth.email_taken": "E-Mail bereits registriert",
  "auth.not_found": "Benutzer nicht gefunden",
  "documents.upload_failed": "Upload fehlgeschlagen"
}
```

Phase 1 includes only 5-10 demo keys per language (de + en filled, fr + it skeleton).

### i18n Middleware

**File:** `backend/middleware/i18n_middleware.py`

Starlette middleware that resolves the request locale:

1. Check authenticated user's `preferred_language` (if available)
2. Parse `Accept-Language` header
3. Fall back to `"de"`
4. Store resolved locale in `request.state.locale`

```python
from starlette.middleware.base import BaseHTTPMiddleware

class I18nMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        locale = resolve_locale(request)
        request.state.locale = locale
        response = await call_next(request)
        response.headers["Content-Language"] = locale
        return response
```

**Locale resolution order:**
1. `request.state.user.preferred_language` (set by auth middleware, if present)
2. Best match from `Accept-Language` header against `SUPPORTED_LOCALES`
3. `DEFAULT_LOCALE` ("de")

### User Model Extension

**File:** `backend/models/auth.py`

Add column to User model:

```python
preferred_language = Column(String(5), nullable=True, default=None)
```

- `NULL` means "use browser locale / Accept-Language"
- Valid values: `"de"`, `"en"`, `"fr"`, `"it"`

Alembic migration adds the column with no default (nullable).

### Profile API Extension

**File:** `backend/api/auth.py`

Extend `PATCH /api/auth/profile` to accept and validate `preferred_language`:

- Validate against `SUPPORTED_LOCALES`
- Store in User model
- Return updated profile with language field

### Main App Registration

**File:** `backend/main.py`

- Call `init_translations()` at startup
- Register `I18nMiddleware` (after auth middleware so user is available)

### Usage Pattern (for subsequent phases)

```python
# In any API endpoint:
from services.translation_service import t

@router.post("/login")
async def login(request: Request, ...):
    locale = request.state.locale
    raise HTTPException(status_code=400, detail=t("auth.email_taken", locale=locale))
```

## Frontend Design

### i18next Configuration

**File:** `frontend/src/i18n.ts`

```typescript
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import de from "./locales/de/translation.json";
import en from "./locales/en/translation.json";
import fr from "./locales/fr/translation.json";
import it from "./locales/it/translation.json";

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
    fallbackLng: "de",
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
      lookupLocalStorage: "examcraft_language",
    },
  });

export default i18n;
```

### Translation Files

**Location:** `frontend/src/locales/{de,en,fr,it}/translation.json`

Single flat namespace with dot-separated keys:

```json
{
  "nav.profile": "Profil",
  "nav.settings": "Einstellungen",
  "nav.logout": "Abmelden",
  "nav.language": "Sprache"
}
```

Phase 1: 5-10 demo keys (nav items, language switcher labels) in de + en. FR + IT skeleton.

### App Entry Point

**File:** `frontend/src/index.tsx`

Add `import "./i18n";` before app render to initialize i18next.

### Language Switcher

**File:** `frontend/src/components/layout/NavigationBar.tsx`

Add a language selector item inside the existing user dropdown menu:

- Shows current language label (e.g., "Deutsch")
- Clicking opens a submenu or inline list with all 4 languages
- On selection: calls `i18n.changeLanguage(lng)` for immediate UI switch
- If user is authenticated: also calls `PATCH /api/auth/profile` with `preferred_language`

### Auth Context Sync

**File:** `frontend/src/contexts/AuthContext.tsx`

After successful login/profile fetch:

```typescript
if (user.preferred_language) {
  i18n.changeLanguage(user.preferred_language);
}
```

This ensures the UI language matches the user's stored preference after login.

### Type Extension

**File:** `frontend/src/types/auth.ts`

Add to `User` interface:

```typescript
preferred_language?: string;
```

## Fallback Chain

```
Authenticated user:  user.preferred_language → Accept-Language → "de"
Anonymous user:      localStorage → navigator.language → "de"
```

## Files Changed (Phase 1)

| Action | File |
|--------|------|
| Create | `backend/locales/de.json` |
| Create | `backend/locales/en.json` |
| Create | `backend/locales/fr.json` |
| Create | `backend/locales/it.json` |
| Create | `backend/services/translation_service.py` |
| Create | `backend/middleware/i18n_middleware.py` |
| Modify | `backend/models/auth.py` — add `preferred_language` column |
| Modify | `backend/api/auth.py` — accept `preferred_language` in profile update |
| Modify | `backend/main.py` — register middleware, init translations |
| Create | `backend/alembic/versions/xxx_add_preferred_language.py` |
| Modify | `pyproject.toml` — add `python-i18n[YAML]` dependency |
| Create | `frontend/src/i18n.ts` |
| Create | `frontend/src/locales/de/translation.json` |
| Create | `frontend/src/locales/en/translation.json` |
| Create | `frontend/src/locales/fr/translation.json` |
| Create | `frontend/src/locales/it/translation.json` |
| Modify | `frontend/src/index.tsx` — import i18n |
| Modify | `frontend/src/components/layout/NavigationBar.tsx` — language switcher |
| Modify | `frontend/src/contexts/AuthContext.tsx` — sync language on login |
| Modify | `frontend/src/types/auth.ts` — add `preferred_language` |
| Modify | `frontend/package.json` — add i18next dependencies |

## Out of Scope (Phase 1)

- Bulk string extraction (~794 strings) — Phase 2+3
- FR/IT translations — Phase 4
- Log audit (English enforcement) — Phase 4
- Comprehensive i18n test suite — Phase 5

## Success Criteria (Phase 1)

1. Language switcher visible in user menu, switches UI language live
2. 5-10 demo strings render correctly in de and en
3. `preferred_language` persists in user profile and loads on login
4. Backend resolves locale from Accept-Language header
5. Backend `t()` helper returns translated string for a demo endpoint
6. Anonymous users get browser locale, authenticated users get profile preference
