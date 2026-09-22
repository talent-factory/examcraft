/**
 * Error codes for `MoodleFeedbackPushService`, which hits
 * `core/backend/api/moodle_feedback_push.py`.
 *
 * BACKEND CODES (TF-773 PR 2d), texts verbatim from
 * `core/backend/locales/t.*.json`:
 *
 *   moodle_feedback_push_job_not_found       404, poll
 *   moodle_feedback_push_no_connection       412, start
 *   moodle_feedback_push_no_quiz_id          412, start
 *   moodle_feedback_push_queue_unavailable   503, broker down
 *
 * The 412 «Keine Moodle-Verbindung für diese Institution konfiguriert.» is the
 * loss TF-772 PR 7 recorded; it is back. The second 412 is the more useful of
 * the two, because it names the fix («Bitte zuerst die Moodle-Fragen-IDs
 * synchronisieren.») — `NotenexportPanel` starts the push and polls it inside
 * one `try` and branches on nothing, so every one of these reaches the screen.
 *
 * The router's 404 for a missing exam is `exams_not_found`, registered in
 * `exams.ts`; the registry is flat, so it resolves from here.
 *
 * `moodle_feedback_push_failed` stays as the operation fallback for a network
 * failure or a status with no code of its own.
 */
export const MOODLE_FEEDBACK_PUSH_ERROR_CODES = [
  'moodle_feedback_push_failed',
  'moodle_feedback_push_job_not_found',
  'moodle_feedback_push_no_connection',
  'moodle_feedback_push_no_quiz_id',
  'moodle_feedback_push_queue_unavailable',
] as const;
