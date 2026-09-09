/**
 * Error codes reachable through `api/dashboard.ts` (TF-772 PR 4).
 *
 * Frontend-only, but for a different reason than the premium packages:
 * `core/backend/api/dashboard.py` is inside the localized backend and simply
 * raises nothing. It has no `HTTPException` at all — both endpoints either
 * answer 200 or fail as a framework 500 (`internal_error`) or an auth 401 the
 * fetch interceptor handles. So the two codes below exist to name the *thing
 * the user was looking at* when a network failure or a bodyless 500 arrives,
 * which "Es ist ein unerwarteter Fehler aufgetreten" cannot do.
 */
export const DASHBOARD_ERROR_CODES = [
  'dashboard_activity_load_failed',
  'dashboard_stats_load_failed',
] as const;
