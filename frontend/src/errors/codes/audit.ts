/**
 * Error code for `auditService.fetchAuditLogs`, router
 * `core/backend/api/audit.py`.
 *
 * Fallback-only, and still so after TF-773 PR 2d. The router's two 400s are
 * now coded (`audit_invalid_date_range`, `audit_unknown_category`) but stay
 * English and untranslated under the TF-295 "developer errors stay English"
 * exemption: `AuditLogView` sends no date range at all and picks its category
 * from a select over the backend's own `_VALID_CATEGORIES`, so neither
 * sentence can be provoked from the UI. They are passthrough codes with no
 * `errors.*` key, so registering them would put two keys under the i18n guard
 * that no locale file can satisfy.
 *
 * `AuditLogView` therefore keeps rendering `audit_logs_load_failed`, whose
 * text is the view's existing `pages.admin.audit.loadError`.
 */
export const AUDIT_ERROR_CODES = ['audit_logs_load_failed'] as const;
