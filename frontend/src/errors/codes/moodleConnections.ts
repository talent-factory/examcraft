/**
 * Error codes reachable through `MoodleConnectionsService`'s connection CRUD.
 *
 * BACKEND CODES (TF-773 PR 2d). `core/backend/api/moodle_connections.py`
 * raised four plain `HTTPException`s with hand-written German; PR 2d put all
 * four on `api_error()`. Texts verbatim from `core/backend/locales/t.*.json`:
 *
 *   moodle_connections_already_exists           409, create
 *   moodle_connections_no_fields                400, update with an empty body
 *   moodle_connections_not_found                404, get / update / delete / test
 *   moodle_connections_token_decryption_failed  500, list / get / update / test
 *
 * The first two are the sentences TF-772 PR 7 recorded as lost («Es existiert
 * bereits eine Moodle-Verbindung für diese Institution.», «Mindestens ein Feld
 * (base_url, token) ist nötig.»); they are back, and now in four languages.
 *
 * `syncQuestionIds` lives in the same frontend service but hits
 * `moodle_roundtrip.py`, so its codes are in `moodleRoundtrip.ts`. The 500 has
 * a twin there (`moodle_roundtrip_token_decryption_failed`) with the same
 * text: same failure, two routers, one prefix each — the file-name-is-the-
 * prefix rule wins over de-duplicating a sentence.
 *
 * FRONTEND-ONLY FALLBACKS, one per operation `MoodleConnectionForm` and
 * `ImportDialog` render a failure for:
 *
 *   moodle_connections_delete_failed, moodle_connections_list_failed,
 *   moodle_connections_save_failed, moodle_connections_test_failed
 */
export const MOODLE_CONNECTIONS_ERROR_CODES = [
  'moodle_connections_already_exists',
  'moodle_connections_delete_failed',
  'moodle_connections_list_failed',
  'moodle_connections_no_fields',
  'moodle_connections_not_found',
  'moodle_connections_save_failed',
  'moodle_connections_test_failed',
  'moodle_connections_token_decryption_failed',
] as const;
