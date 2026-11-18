/**
 * Error codes reachable through `AuthService` (TF-772 PR 3).
 *
 * The backend codes below are copied verbatim from `core/backend/locales/
 * t.*.json` — the identity rule from ADR 0005: the frontend key is `errors.` +
 * the backend's `error_code`, never a renamed variant. They are raised by
 * `api/auth.py`, `api/auth_oidc.py`, `api/admin.py` and
 * `utils/auth_utils.py`.
 *
 * SCOPE. Only the endpoints `AuthService` actually calls are represented.
 * `GET /api/auth/avatar/{id}` (`auth_avatar_*`) is deliberately absent: it is
 * used as an <img> src, so its failures never become an AppError.
 *
 * EXAMCRAFT-126/139: the OIDC-BFF login removed the password, verification,
 * reset and OAuth endpoints, so their codes (and the `auth_login_failed`,
 * `auth_token_refresh_failed` etc. fallbacks) are gone from this registry and
 * the locales. A few legacy entries (e.g. `auth_email_taken`) stay registered
 * because tests still use them. Login failures arrive as `/login?error=…` and
 * are rendered by `LoginPage` from `auth.loginError.*`, not through AppError.
 *
 * FRONTEND-ONLY FALLBACKS. `auth.py` has no generic per-operation failure code,
 * so these exist purely as the fallback of one `AuthService` method, so that a
 * network failure, a proxy error page or a bodyless 500 still produces a
 * sentence about what the user was trying to do:
 *
 *   auth_logout_failed, auth_profile_load_failed, auth_profile_update_failed
 *
 * AUTH DEPENDENCIES (TF-772 PR 7). Four codes below come not from `auth.py` but
 * from the FastAPI dependencies in `core/backend/utils/auth_utils.py`, which
 * every protected endpoint runs before its own body:
 *
 *   auth_permission_required     403, `require_permission(...)`, %{permission}
 *   auth_account_status_invalid  403, `get_current_user`, %{status}
 *   auth_account_not_active      403, `get_current_active_user`
 *   auth_token_user_not_found    401, `get_current_user`
 *
 * They became reachable once the ApiError family started carrying
 * `error_code`: every endpoint it calls sits behind `require_permission`,
 * `get_current_active_user`, `get_current_superuser` (role CRUD) or plain
 * `get_current_user` (audit, role list) — all four build on
 * `get_current_user`. Before, a teacher without
 * `students:manage` read «Berechtigung «students:manage» erforderlich» off
 * `err.message`; without these registered the same 403 would collapse to the
 * operation's generic fallback. The 401s normally end in a token refresh and a
 * retry, but a refresh that succeeds and still meets a revoked token surfaces
 * them to the caller.
 */
export const AUTH_ERROR_CODES = [
  'auth_account_locked',
  'auth_account_not_active',
  'auth_account_status_invalid',
  'auth_email_taken',
  'auth_logout_failed',
  'auth_password_incorrect',
  'auth_permission_required',
  'auth_profile_load_failed',
  'auth_profile_update_failed',
  'auth_reauth_required',
  'auth_token_invalid',
  'auth_token_user_not_found',
  'auth_user_not_found',
] as const;
