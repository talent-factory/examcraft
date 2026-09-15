/**
 * Error codes reachable through `MoodleConnectionsService`'s connection CRUD
 * (TF-772 PR 7).
 *
 * Fallback-only. `core/backend/api/moodle_connections.py` raises plain
 * `HTTPException`s with hand-written German and no `api_error()`, so there is
 * no `error_code` to accept beyond the auth dependency (`auth.ts`).
 *
 * Known loss until that router is migrated: «Es existiert bereits eine
 * Moodle-Verbindung für diese Institution.» (409) and «Mindestens ein Feld
 * (base_url, token) ist nötig.» (400) now render as the save fallback. The
 * router has no TF-773 package yet — reported, not worked around.
 *
 * `syncQuestionIds` lives in the same frontend service but hits
 * `moodle_roundtrip.py`, so its code is in `moodleRoundtrip.ts`.
 *
 * `moodle_connections_list_failed` is new text: `MoodleConnectionForm` had a
 * hard-coded German literal, and `ImportDialog`'s probe a sentence about
 * "checking" the connection. The other three copy `admin.moodle.*Error`.
 */
export const MOODLE_CONNECTIONS_ERROR_CODES = [
  'moodle_connections_delete_failed',
  'moodle_connections_list_failed',
  'moodle_connections_save_failed',
  'moodle_connections_test_failed',
] as const;
