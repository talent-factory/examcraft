# `errors/codes/` — one file per backend domain

`APP_ERROR_CODES` used to be a single flat array in `AppError.ts`. TF-772 splits
the frontend error path across parallel branches (PR 2 documents/review, PR 3
auth/admin/rbac, PR 4 prompts/chat/wizard/grades/org-units/dashboard/help, PR 5
premium RAG/exam-generation), and every one of them appends to that registry —
the same merge-conflict class the locale files solve by alphabetical ordering,
except a `readonly [...]` tuple has no natural line-range separation.

So the registry is assembled from one file per backend domain prefix. A branch
that adds `auth_*` codes creates `auth.ts` and touches nothing else; the union
in `AppError.ts` grows by one import line.

## Rules

1. **The file name is the backend prefix.** `documents.ts` holds `documents_*`,
   `admin.ts` holds `admin_*`, `auth.ts` holds `auth_*`, `rbac.ts` holds
   `rbac_*`. Where the prefix has an underscore the file name keeps the
   camelCase spelling every other module in `src/` uses — `orgUnits.ts` holds
   `org_units_*`, matching `services/orgUnitsService.ts` and `types/orgUnit.ts`.
   Three files carry a documented, deliberate exception to the file-name-is-
   the-prefix rule — the identity rule (below) copies the code verbatim, warts
   included, so an unprefixed backend code stays unprefixed here too:
   - `review.ts` also holds the review router's unprefixed codes
     (`archive_failed`, `delete_failed`, `restore_failed`) — the backend
     really does emit them without a `review_` prefix.
   - `admin.ts` also holds the impersonation router's `impersonation_*`
     codes — a separate backend router with its own prefix, not `admin_*`.
   - `reserved.ts` holds framework-level codes with no prefix at all
     (`internal_error`, `validation_error`) — they are not scoped to any one
     backend domain by construction.
2. **Alphabetical within the file.** Same reason as the locale files.
3. **Every code needs `errors.<code>` in all four locales.**
   `errors/__tests__/AppErrorCode.i18n.test.ts` fails the build otherwise.
4. **Mark codes with no backend counterpart.** A frontend-only fallback code is
   legitimate — a network failure produces no `error_code` at all, and some
   endpoints have no generic 500 code — but it must be visible as such, because
   it is the one kind of code that can silently drift out of sync with the
   backend. See the `documents.ts` block comment for the original three.

   `prompts.ts`, `chat.ts` and `wizard.ts` are fallback-only end to end: the
   premium routers behind them (`prompts.py`, `chat.py`, `wizard.py`) sit
   outside the localized backend entirely and have no `locales/` directory, so
   there is no `error_code` to accept — only the operation-level fallback.
   `dashboard.ts` is fallback-only for the same reason `dashboard.py` raises no
   `HTTPException` at all today.

   `grades.ts`, `orgUnits.ts` and `help.ts` were fallback-only when TF-772 PR 4
   branched — `grades.py`, `org_units.py` and `core/backend/api/v1/help.py`
   hardcoded German sentences or `detail=str(exc)` instead of `t()` +
   `error_code`. TF-773 has since closed that gap for all three routers; each
   file's own comment now lists which of its codes are real backend codes
   (accepted off the wire) versus which remain frontend-only fallbacks for
   paths TF-773 did not reach (network failure, an endpoint with no specific
   code of its own).

## What belongs in the registry

Two kinds of code, and the distinction matters when reading `documents.ts`:

* **Fallback codes** the frontend constructs itself, one per service method, for
  when the backend sends no `error_code` (network failure, non-JSON 500, an
  endpoint not yet migrated).
* **Backend codes** the three constructors accept off the wire —
  `appErrorFromResponse()` for `fetch`, `appErrorFromAxios()` for `apiClient`,
  `appErrorFromApiError()` for the services built on `httpClient`. The registry
  is the accept-list for all three: a code that is not in it falls back to the
  caller's fallback code rather than reaching `translateError` untranslated.

`legacy.ts` holds the 22 dot-notation camelCase codes from TF-671. They predate
ADR 0005 and do not follow the identity rule. TF-775 decides whether they get
migrated; until then they are frozen — do not add to that file.
