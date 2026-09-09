/**
 * Error codes reachable through `AuthService` (TF-772 PR 3).
 *
 * The backend codes below are copied verbatim from `core/backend/locales/
 * t.*.json`, where `core/backend/api/auth.py` raises them — the identity rule
 * from ADR 0005: the frontend key is `errors.` + the backend's `error_code`,
 * never a renamed variant.
 *
 * Registering the specific codes rather than one generic per method is the
 * point. A failed login has five distinct causes on the backend (account
 * locked, disabled, pending verification, wrong credentials, auth service
 * down) and answers each with its own localized sentence; a user who is told
 * "check your inbox" is being told something a generic "login failed" cannot
 * say. See `documents.ts` for the same argument at length.
 *
 * SCOPE. Only the endpoints `AuthService` (plus `ResendVerificationButton`,
 * which fetches `/api/auth/resend-verification` itself) actually calls are
 * represented. `auth.py` raises four further code families that no frontend
 * request can reach, and they are deliberately absent:
 *
 *   auth_oauth_state_missing / auth_oauth_state_invalid
 *                          GET /api/auth/oauth/{provider}/callback — a browser
 *                          redirect the backend answers directly, never a
 *                          fetch() from here.
 *   auth_verification_token_*  POST /api/auth/verify-email — called inline by
 *                          `pages/VerifyEmailPage.tsx`, which is not part of
 *                          this package (reported, not migrated).
 *   auth_avatar_*          GET /api/auth/avatar/{id} — used as an <img> src,
 *                          so its failures never become an AppError.
 *   auth_user_not_found    only reachable through those last two.
 *
 * FRONTEND-ONLY FALLBACKS. Unlike `documents.py`, `auth.py` has no generic
 * per-operation failure code — it raises only specific ones. So twelve of the
 * codes below have no backend counterpart and exist purely as the fallback for
 * one method, so that a network failure, a proxy error page or a bodyless 500
 * still produces a sentence about what the user was trying to do:
 *
 *   auth_login_failed, auth_logout_failed, auth_oauth_exchange_failed,
 *   auth_oauth_url_failed, auth_password_change_failed,
 *   auth_password_reset_failed, auth_password_reset_request_failed,
 *   auth_password_set_failed, auth_profile_load_failed,
 *   auth_profile_update_failed, auth_token_refresh_failed,
 *   auth_verification_resend_failed
 *
 * `auth_registration_failed` is the thirteenth fallback but a special case: the
 * key exists in the backend locales with exactly this meaning, yet nothing in
 * the backend ever raises it (reported as a dead key, along with
 * auth_insufficient_permissions, auth_logout_success, auth_session_expired,
 * auth_token_missing and auth_username_taken). Reusing the name rather than
 * inventing `auth_register_failed` keeps the identity rule intact for the day
 * TF-773 wires it up.
 */
export const AUTH_ERROR_CODES = [
  'auth_account_disabled',
  'auth_account_locked',
  'auth_account_pending',
  'auth_email_already_verified',
  'auth_email_taken',
  'auth_institution_not_found',
  'auth_invalid_credentials',
  'auth_login_failed',
  'auth_login_service_unavailable',
  'auth_logout_failed',
  'auth_oauth_code_invalid',
  'auth_oauth_exchange_failed',
  'auth_oauth_login_failed',
  'auth_oauth_provider_unsupported',
  'auth_oauth_token_read_failed',
  'auth_oauth_url_failed',
  'auth_password_already_set',
  'auth_password_change_failed',
  'auth_password_incorrect',
  'auth_password_reset_failed',
  'auth_password_reset_not_implemented',
  'auth_password_reset_request_failed',
  'auth_password_set_failed',
  'auth_profile_load_failed',
  'auth_profile_update_failed',
  'auth_registration_failed',
  'auth_service_unavailable',
  'auth_token_invalid',
  'auth_token_refresh_failed',
  'auth_verification_email_failed',
  'auth_verification_resend_failed',
] as const;
