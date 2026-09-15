/**
 * Error codes reachable through `competencyFrameworksApi` on
 * `CompetencyFrameworkSettingsPage` (TF-772 PR 7), router
 * `core/backend/api/competency_frameworks.py`.
 *
 * The page rendered `response.data.detail` through a local
 * `extractApiDetail()` — the same leak `getErrorMessage()` had in the composer.
 * Found in the closeout sweep of PR 7.
 *
 * BACKEND CODES, texts verbatim from `core/backend/locales/t.*.json`:
 *
 *   create      competency_frameworks_duplicate_code ({{code}}),
 *               competency_frameworks_integrity_conflict, visibility_*
 *   update      competency_frameworks_access_denied, _integrity_conflict,
 *               _not_found, visibility_*
 *   (un)archive competency_frameworks_access_denied, _not_found
 *
 * The `visibility_*` codes are in `visibility.ts`.
 *
 * FRONTEND-ONLY FALLBACKS, texts of the page's `competencyFrameworks.error*`
 * keys: `competency_frameworks_archive_failed` (archive and unarchive share
 * one mutation and one sentence), `competency_frameworks_create_failed`,
 * `competency_frameworks_list_failed`, `competency_frameworks_update_failed`.
 */
export const COMPETENCY_FRAMEWORKS_ERROR_CODES = [
  'competency_frameworks_access_denied',
  'competency_frameworks_archive_failed',
  'competency_frameworks_create_failed',
  'competency_frameworks_duplicate_code',
  'competency_frameworks_integrity_conflict',
  'competency_frameworks_list_failed',
  'competency_frameworks_not_found',
  'competency_frameworks_update_failed',
] as const;
