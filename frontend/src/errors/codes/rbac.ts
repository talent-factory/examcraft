/**
 * Error codes reachable through `RBACService` (TF-772 PR 3).
 *
 * `core/backend/api/v1/rbac.py` is a read-only router — ten GET endpoints, no
 * writes — and raises exactly five codes. The other nine below are
 * frontend-only fallbacks, one per service method, for the case the backend
 * sends no code at all (network failure, framework 500, an endpoint TF-773 has
 * not reached yet):
 *
 *   rbac_feature_load_failed, rbac_features_load_failed,
 *   rbac_my_tier_load_failed, rbac_permission_check_failed,
 *   rbac_quota_check_failed, rbac_role_load_failed, rbac_roles_load_failed,
 *   rbac_tier_quotas_load_failed, rbac_tiers_load_failed
 *
 * The five backend codes are copied verbatim from `core/backend/locales/
 * t.*.json` (identity rule, ADR 0005). Two of them share an endpoint and must
 * not be collapsed: `GET /tiers/my` answers `rbac_institution_not_found` when
 * the user has no institution record and `rbac_tier_not_found` when the
 * institution has no tier — different problems with different fixes.
 *
 * `rbac_role_not_found` and `admin_role_not_found` are two distinct backend
 * codes with the same German text ("Rolle nicht gefunden"), raised by two
 * different routers. Both are registered under their own name rather than
 * folded into one: the identity rule maps a code to a key, not a text to a
 * key, and a shared key would break the grep from a backend log back to here.
 */
export const RBAC_ERROR_CODES = [
  'rbac_feature_load_failed',
  'rbac_feature_not_found',
  'rbac_features_load_failed',
  'rbac_institution_not_found',
  'rbac_my_tier_load_failed',
  'rbac_no_institution',
  'rbac_permission_check_failed',
  'rbac_quota_check_failed',
  'rbac_role_load_failed',
  'rbac_role_not_found',
  'rbac_roles_load_failed',
  'rbac_tier_not_found',
  'rbac_tier_quotas_load_failed',
  'rbac_tiers_load_failed',
] as const;
