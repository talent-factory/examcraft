/**
 * Error codes reachable through the premium `WizardService` (TF-772 PR 4).
 *
 * Frontend-only, like `prompts.ts` and `chat.ts`: `premium/backend/api/v1/
 * wizard.py` sits outside the localized backend and sends no `error_code`.
 *
 * The loss is smallest here of the three. Every endpoint in `wizard.py` answers
 * a failure in one of exactly two ways: `HTTPException(400 | 404, detail=str(e))`
 * — a Python exception string, not written copy, and half the time English —
 * or the literal "Interner Serverfehler. Bitte versuche es spaeter erneut."
 * (sic, no umlaut) for the catch-all 500. Neither is text worth preserving, so
 * one code per operation is a strict improvement rather than a trade.
 */
export const WIZARD_ERROR_CODES = [
  'wizard_create_session_failed',
  'wizard_delete_session_failed',
  'wizard_generate_failed',
  'wizard_save_template_failed',
  'wizard_send_message_failed',
  'wizard_session_load_failed',
  'wizard_sessions_load_failed',
] as const;
