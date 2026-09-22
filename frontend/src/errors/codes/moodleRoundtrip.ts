/**
 * Error codes reachable through `MoodleConnectionsService.syncQuestionIds`,
 * which hits `core/backend/api/moodle_roundtrip.py`.
 *
 * BACKEND CODES (TF-773 PR 2d). The router raised eleven plain
 * `HTTPException`s until PR 2d put every one of them on `api_error()`; eight
 * are registered here, texts verbatim from `core/backend/locales/t.*.json`:
 *
 *   moodle_roundtrip_api_error                    502, Moodle answered 5xx
 *   moodle_roundtrip_api_exception                400, Moodle sent an errorcode
 *   moodle_roundtrip_api_invalid_response         502, non-JSON / not an object
 *   moodle_roundtrip_api_rejected                 502, Moodle answered 4xx
 *   moodle_roundtrip_api_unreachable              502, transport failure
 *   moodle_roundtrip_exam_has_no_questions        400, nothing to sync
 *   moodle_roundtrip_question_ids_count_mismatch  400, list length != questions
 *   moodle_roundtrip_token_decryption_failed      500, key rotation fallout
 *
 * The three 502s and the 500 used to interpolate the exception text or the
 * upstream status into `detail` («Token-Verschlüsselung defekt: {exc}»,
 * «Moodle-API HTTP 500»). PR 2d moved that to the server log and left the
 * response a generic, translated sentence per failure class — which is why
 * four codes exist where one fallback used to be: the operator still learns
 * whether Moodle was unreachable, rejected the token, or replied with
 * nonsense.
 *
 * Two codes the router raises are deliberately absent:
 *
 * - `exams_not_found` (404) — registered in `exams.ts`; the registry is flat,
 *   so it resolves from here. Unreachable anyway, see below.
 * - `moodle_roundtrip_quiz_not_visible` (404) — `SyncMoodleIdsDialog`
 *   intercepts `status === 404` with its own `auswertungen.moodleSync
 *   .notVisible` sentence, which carries the same meaning and interpolates
 *   the quiz id the user just typed. Registering it would add a key the i18n
 *   guard covers and no call site can ever render, the same call
 *   `studentClasses.ts` makes for its two 409s.
 *
 * `moodle_roundtrip_sync_failed` stays as the operation fallback for a
 * network failure or a status with no code of its own.
 */
export const MOODLE_ROUNDTRIP_ERROR_CODES = [
  'moodle_roundtrip_api_error',
  'moodle_roundtrip_api_exception',
  'moodle_roundtrip_api_invalid_response',
  'moodle_roundtrip_api_rejected',
  'moodle_roundtrip_api_unreachable',
  'moodle_roundtrip_exam_has_no_questions',
  'moodle_roundtrip_question_ids_count_mismatch',
  'moodle_roundtrip_sync_failed',
  'moodle_roundtrip_token_decryption_failed',
] as const;
