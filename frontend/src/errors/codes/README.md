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

   `prompts.ts`, `chat.ts` and `wizard.ts` were fallback-only when TF-772 PR 4
   wrote them: the premium routers behind them had no `locales/` directory.
   TF-773 PR 2b added `premium/backend/locales/` (ADR 0006); all three files
   now mix backend codes — copied verbatim from `premium/backend/locales/
   t.*.json` — with the fallbacks, and the premium routers' generic 500s reuse
   the fallback names on purpose. `vectorSearch.ts` holds the one premium
   vector-search code a frontend service can receive. The MCP OAuth codes
   (`mcp_auth_*`) are not registered: no frontend code calls those endpoints.
   `dashboard.ts` is fallback-only because `dashboard.py` raises no
   `HTTPException` at all today.

   `rag.ts` holds two groups under one prefix. Its `rag_validation_*` codes
   are frontend-only: they come from `RAGService.validateRAGRequest`, a check
   that runs in the browser before any request is sent (TF-772 PR 5). The
   backend's own `rag_*` codes from `rag_exams.py` joined them in TF-773
   Teil D — the reachable ten, with the four unreachable ones named in the
   file's header. The `validation` infix keeps the two groups apart.

   `tags.ts` (TF-773 Teil D) replaced the `apiDetail()` special case: the two
   tag-management surfaces render the backend's codes like every other
   component instead of its raw German `detail`. `stats.ts` holds the one
   `stats_*` code a component can receive, which `submissions.py` reuses.

   `grades.ts`, `orgUnits.ts` and `help.ts` were fallback-only when TF-772 PR 4
   branched — `grades.py`, `org_units.py` and `core/backend/api/v1/help.py`
   hardcoded German sentences or `detail=str(exc)` instead of `t()` +
   `error_code`. TF-773 has since closed that gap for all three routers; each
   file's own comment now lists which of its codes are real backend codes
   (accepted off the wire) versus which remain frontend-only fallbacks for
   paths TF-773 did not reach (network failure, an endpoint with no specific
   code of its own).

   TF-772 PR 7 added one file per router whose consumers rendered the raw
   backend text — the ApiError family on `httpClient` and the other parsers
   (Auswertungen, admin, audit), and the axios pages that showed
   `response.data.detail` (composer, competency frameworks, subscription).
   `studentClasses.ts`, `submissions.ts`, `exams.ts`, `gradingSchemes.ts`,
   `competencyFrameworks.ts` and `billing.ts` mix real backend codes with
   operation fallbacks; `visibility.ts` holds only backend codes shared by
   several routers.

   The six files PR 7 created for routers that still raised plain
   `HTTPException`s were fallback-only at the time, and that is worth reading
   carefully before reusing one of their names: a backend code named after an
   operation fallback renders with the fallback's generic sentence, so sending
   it changes nothing on screen. TF-773 PR 2d migrated all six routers and
   split them by what the UI can actually show:

   * `moodleRoundtrip.ts`, `moodleConnections.ts`, `moodleFeedbackPush.ts` and
     `students.ts` now mix backend codes with their operation fallbacks — their
     consumers hand every failure to `translateError` without branching first,
     so a registered code reaches the screen.
   * `activity.ts` and `audit.ts` stay fallback-only *by decision*, not for
     lack of codes. Their routers' throw sites are either unreachable from the
     UI or a frontend bug, and the English ones are passthrough codes with no
     locale key at all. Each file states which, and why.

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
