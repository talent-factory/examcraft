# `errors/codes/` — one file per backend domain

`APP_ERROR_CODES` used to be a single flat array in `AppError.ts`. TF-772 splits
the frontend error path across parallel branches (PR 2 documents/review, PR 3
auth/admin/rbac, PR 4 prompts/chat, PR 5 premium RAG/exam-generation), and every
one of them appends to that registry — the same merge-conflict class the locale
files solve by alphabetical ordering, except a `readonly [...]` tuple has no
natural line-range separation.

So the registry is assembled from one file per backend domain prefix. A branch
that adds `auth_*` codes creates `auth.ts` and touches nothing else; the union
in `AppError.ts` grows by one import line.

## Rules

1. **The file name is the backend prefix.** `documents.ts` holds `documents_*`,
   `admin.ts` holds `admin_*`, `auth.ts` holds `auth_*`, `rbac.ts` holds
   `rbac_*`. Three files carry a documented, deliberate exception to that rule
   — the identity rule (below) copies the code verbatim, warts included, so an
   unprefixed backend code stays unprefixed here too:
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
   backend. See the `documents.ts` block comment for the current three.

## What belongs in the registry

Two kinds of code, and the distinction matters when reading `documents.ts`:

* **Fallback codes** the frontend constructs itself, one per service method, for
  when the backend sends no `error_code` (network failure, non-JSON 500, an
  endpoint not yet migrated).
* **Backend codes** `appErrorFromResponse()` accepts off the wire. The registry
  is the accept-list: a code that is not in it falls back to the caller's
  fallback code rather than reaching `translateError` untranslated.

`legacy.ts` holds the 22 dot-notation camelCase codes from TF-671. They predate
ADR 0005 and do not follow the identity rule. TF-775 decides whether they get
migrated; until then they are frozen — do not add to that file.
