/**
 * Error codes reachable through the premium `WizardService`.
 *
 * Until TF-773 PR 2b every endpoint in `premium/backend/api/v1/wizard.py`
 * answered with `detail=str(e)` — a mix of German and English exception text —
 * or "Interner Serverfehler. Bitte versuche es spaeter erneut." for the 500, so
 * TF-772 PR 4 registered one fallback per operation and lost nothing worth
 * keeping. The service now raises `WizardServiceError(code, …)` with its own
 * HTTP status, and the router's 500s reuse the seven operation names below;
 * the nine specific codes (AI unavailable, invalid AI response, session not
 * found / not active, template already saved / not generated, author missing /
 * without institution, malformed reference prompt id) are the sentences the
 * user can now actually act on.
 */
export const WIZARD_ERROR_CODES = [
  'wizard_ai_invalid_response',
  'wizard_ai_unavailable',
  'wizard_create_session_failed',
  'wizard_delete_session_failed',
  'wizard_generate_failed',
  'wizard_no_institution',
  'wizard_reference_prompt_invalid',
  'wizard_save_template_failed',
  'wizard_send_message_failed',
  'wizard_session_load_failed',
  'wizard_session_not_active',
  'wizard_session_not_found',
  'wizard_sessions_load_failed',
  'wizard_template_already_saved',
  'wizard_template_not_generated',
  'wizard_user_not_found',
] as const;
