# Design Specification: i18n Infrastructure (Phase 1)

**Task:** TF-295 — Mehrsprachigkeit (i18n)
**Phase:** 1 of 5 (Infrastructure only)
**Date:** 2026-03-22
**Languages:** de (fallback), en, fr, it

> **Path convention:** All file paths in this spec are relative to `packages/core/`.

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
| Frontend JSON structure | Nested objects matching dot-separated keys |
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

1. Check `request.state.preferred_language` (set by RBAC middleware, if present)
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

1. `request.state.preferred_language` (set by RBAC middleware which already loads user data — extend it to also set this field)
2. Best match from `Accept-Language` header against `SUPPORTED_LOCALES`
3. `DEFAULT_LOCALE` ("de")

**Accept-Language parsing:** Strip region subtags to match base language (e.g., `de-CH` maps to `de`, `fr-CH` maps to `fr`). Parse quality weights and select the highest-weighted match against `SUPPORTED_LOCALES`. Implement as a utility function in the middleware module — no external library needed for this simple matching.

**Middleware registration order:** In `main.py`, register `I18nMiddleware` via `app.add_middleware(I18nMiddleware)` **before** the RBAC middleware registration (so it executes **after** RBAC in Starlette's reversed execution order). This ensures `request.state.preferred_language` is available when `I18nMiddleware.dispatch` runs.

### RBAC Middleware Extension

**File:** `backend/middleware/rbac_middleware.py`

The existing RBAC middleware already loads user data and sets `request.state.user_id` and `request.state.institution_id`. Extend it to also set:

```python
request.state.preferred_language = user.preferred_language  # may be None
```

This allows the i18n middleware to access the user's language preference without an additional DB query.

### User Model Extension

**File:** `backend/models/auth.py`

Add column to User model:

```python
preferred_language = Column(
    String(5),
    nullable=True,
    default=None,
)
```

Add a `CheckConstraint` to the model's `__table_args__`:

```python
CheckConstraint(
    "preferred_language IN ('de', 'en', 'fr', 'it') OR preferred_language IS NULL",
    name="ck_user_preferred_language",
)
```

- `NULL` means "use browser locale / Accept-Language"
- Valid values: `"de"`, `"en"`, `"fr"`, `"it"`

Alembic migration adds the column with no default (nullable) and the check constraint.

### Profile API Extension

**File:** `backend/api/auth.py`

Extend `PATCH /api/auth/profile`:

- Add `preferred_language: Optional[str] = None` to the `UserProfileUpdate` Pydantic model
- Validate against `SUPPORTED_LOCALES` (reject invalid values with 422)
- Store in User model
- Return updated profile with language field

### Main App Registration

**File:** `backend/main.py`

- Call `init_translations()` at startup
- Register `I18nMiddleware` before RBAC middleware (executes after RBAC due to Starlette's reversed order)

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

Note: `react-i18next` uses `"."` as `keySeparator` by default, so keys like `"nav.profile"` resolve to nested JSON paths `{ "nav": { "profile": "..." } }`. The translation files must use nested structure to match.

### Translation Files

**Location:** `frontend/src/locales/{de,en,fr,it}/translation.json`

Nested JSON structure matching dot-separated key convention:

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
    "fr": "Francais",
    "it": "Italiano"
  }
}
```

Phase 1: 5-10 demo keys (nav items, language switcher labels) in de + en. FR + IT with same structure, translated.

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

**Note:** The `examcraft_language` localStorage key is a browser-level preference and must NOT be cleared on logout. Only session-related keys (`examcraft_access_token`, `examcraft_refresh_token`, `examcraft_user`) should be cleared.

### Type Extensions

**File:** `frontend/src/types/auth.ts`

Add to `User` interface:

```typescript
preferred_language?: string;
```

Add to `UpdateProfileRequest` interface (or equivalent profile update type):

```typescript
preferred_language?: string;
```

## Fallback Chain

```
Authenticated user:  user.preferred_language -> Accept-Language -> "de"
Anonymous user:      localStorage -> navigator.language -> "de"
```

## Files Changed (Phase 1)

> All paths relative to `packages/core/`.

| Action | File |
|--------|------|
| Create | `backend/locales/de.json` |
| Create | `backend/locales/en.json` |
| Create | `backend/locales/fr.json` |
| Create | `backend/locales/it.json` |
| Create | `backend/services/translation_service.py` |
| Create | `backend/middleware/i18n_middleware.py` |
| Modify | `backend/middleware/rbac_middleware.py` — set `preferred_language` on request state |
| Modify | `backend/models/auth.py` — add `preferred_language` column + CheckConstraint |
| Modify | `backend/api/auth.py` — add `preferred_language` to `UserProfileUpdate`, accept in profile endpoint |
| Modify | `backend/main.py` — register i18n middleware, init translations |
| Create | `backend/alembic/versions/xxx_add_preferred_language.py` |
| Modify | `pyproject.toml` (root) — add `python-i18n` dependency |
| Create | `frontend/src/i18n.ts` |
| Create | `frontend/src/locales/de/translation.json` |
| Create | `frontend/src/locales/en/translation.json` |
| Create | `frontend/src/locales/fr/translation.json` |
| Create | `frontend/src/locales/it/translation.json` |
| Modify | `frontend/src/index.tsx` — import i18n |
| Modify | `frontend/src/components/layout/NavigationBar.tsx` — language switcher |
| Modify | `frontend/src/contexts/AuthContext.tsx` — sync language on login |
| Modify | `frontend/src/types/auth.ts` — add `preferred_language` to User + UpdateProfileRequest |
| Modify | `frontend/package.json` — add i18next dependencies |

## Phase 1 Tests

Minimal test coverage to verify infrastructure works:

1. **Translation service unit test** — `t("auth.email_taken", locale="de")` returns German string, `t("auth.email_taken", locale="en")` returns English, unknown key returns fallback
2. **Middleware locale resolution test** — verify Accept-Language parsing (de-CH -> de, fr;q=0.9 -> fr), fallback to "de" when no match
3. **Profile API test** — PATCH with valid `preferred_language` persists, PATCH with invalid value returns 422
4. **Frontend language switcher test** — component renders, clicking a language option calls `i18n.changeLanguage`

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
