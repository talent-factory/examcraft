/**
 * Error codes reachable through `AdminService` (TF-772 PR 3).
 *
 * The backend codes are copied verbatim from `core/backend/locales/t.*.json`,
 * where `core/backend/api/admin.py` and
 * `core/backend/services/user_institution_transfer_service.py` raise them.
 * Identity rule from ADR 0005 — no renaming on the way over.
 *
 * The `impersonation_*` codes have no `admin_` prefix. That is the backend's
 * spelling (`api/admin.py`, `utils/auth_utils.py`) and therefore the frontend
 * key, for the same reason `review.ts` keeps `archive_failed`: a code seen in
 * a backend log has to be greppable in the frontend locales.
 *
 * Two codes this service can produce live in `auth.ts` instead:
 * `auth_password_incorrect` and `auth_account_locked`. POST
 * `/users/{id}/impersonate` re-checks the admin's own password, so it answers
 * with the auth router's codes. They are registered once, in the file named
 * after their prefix — the registry is flat, so where a code is declared has
 * no effect on whether it is accepted.
 *
 * REGISTER, NOT A WISHLIST. `admin.py` also raises `admin_role_already_exists`,
 * `admin_role_has_users`, `admin_role_is_system` and `admin_unknown_permissions`
 * — all four from the role CRUD endpoints (POST/PATCH/DELETE `/roles`), which
 * `AdminService` does not call. It only reads `/roles`. They are left out until
 * something in the frontend can actually receive them.
 *
 * FRONTEND-ONLY FALLBACKS — thirteen of the codes below have no backend
 * counterpart, because `admin.py` (like `auth.py`, unlike `documents.py`)
 * raises only specific codes and has no generic per-operation failure:
 *
 *   admin_institution_create_failed, admin_institution_update_failed,
 *   admin_institutions_load_failed, admin_role_assign_failed,
 *   admin_role_remove_failed, admin_roles_load_failed, admin_transfer_failed,
 *   admin_transfer_preview_failed, admin_user_load_failed,
 *   admin_user_status_update_failed, admin_user_update_failed,
 *   admin_users_load_failed, impersonation_end_failed
 *
 * `impersonateUser` needs no such fallback: `impersonation_start_failed` is a
 * real backend code that already says exactly that.
 *
 * Two more frontend-only codes do not come from a service at all.
 * `AuthContext.startImpersonation` refuses locally in two situations —
 * no active admin session, and a recovery snapshot that could not be persisted
 * (`sessionStorage` full or restricted) — and both refusals are rendered by
 * `ImpersonationReasonDialog`, which catches the service call and the context
 * call together. They used to be English developer sentences on screen:
 *
 *   impersonation_no_admin_session, impersonation_snapshot_failed
 *
 * Its third refusal reuses the backend's `impersonation_already_active`, which
 * says the same thing.
 *
 * REGISTER-WORDING NOTE. `impersonation_no_password_set` and
 * `impersonation_rate_limit_exceeded` address the user formally ("Ihr Konto",
 * "Bitte versuchen Sie", "Veuillez") where every neighbouring string is
 * informal. Copied verbatim anyway — TF-772 transports existing texts, it does
 * not re-edit them, and changing them here would put the frontend and backend
 * wording out of sync for the same code.
 */
export const ADMIN_ERROR_CODES = [
  'admin_cannot_deactivate_self',
  'admin_cannot_remove_last_role',
  'admin_cross_institution_access_denied',
  'admin_email_already_in_use',
  'admin_institution_create_failed',
  'admin_institution_domain_exists',
  'admin_institution_not_found',
  'admin_institution_update_failed',
  'admin_institutions_load_failed',
  'admin_insufficient_permissions',
  'admin_invalid_grading_scheme',
  'admin_invalid_subscription_tier',
  'admin_role_assign_failed',
  'admin_role_not_found',
  'admin_role_remove_failed',
  'admin_roles_load_failed',
  'admin_transfer_audit_failed',
  'admin_transfer_failed',
  'admin_transfer_preview_failed',
  'admin_transfer_same_institution',
  'admin_transfer_self_forbidden',
  'admin_user_already_has_role',
  'admin_user_does_not_have_role',
  'admin_user_load_failed',
  'admin_user_not_found',
  'admin_user_status_update_failed',
  'admin_user_update_failed',
  'admin_users_load_failed',
  'impersonation_action_locked',
  'impersonation_already_active',
  'impersonation_end_failed',
  'impersonation_no_admin_session',
  'impersonation_no_password_set',
  'impersonation_not_active',
  'impersonation_rate_limit_exceeded',
  'impersonation_self_not_allowed',
  'impersonation_snapshot_failed',
  'impersonation_start_failed',
] as const;
