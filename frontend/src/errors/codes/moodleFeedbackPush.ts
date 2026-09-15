/**
 * Error code for `MoodleFeedbackPushService` (TF-772 PR 7), which hits
 * `core/backend/api/moodle_feedback_push.py`.
 *
 * Fallback-only: the router raises plain `HTTPException`s. `NotenexportPanel`
 * starts the push and polls it inside one `try`, so one code covers both. Known
 * loss: the 412 «Keine Moodle-Verbindung für diese Institution konfiguriert.»
 * now renders as this fallback. The router has no TF-773 package yet —
 * reported.
 */
export const MOODLE_FEEDBACK_PUSH_ERROR_CODES = ['moodle_feedback_push_failed'] as const;
