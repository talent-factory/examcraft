/**
 * Error code for `auditService.fetchAuditLogs` (TF-772 PR 7), router
 * `core/backend/api/audit.py`.
 *
 * Fallback-only: the router raises two plain `HTTPException(400)`s, both
 * English and both about malformed filters the UI does not produce
 * («date_from must be <= date_to», an unknown category). `AuditLogView`
 * rendered their `message`; it now renders `audit_logs_load_failed`, whose text
 * is the view's existing `pages.admin.audit.loadError`. Found in the closeout
 * sweep of PR 7 — `auditService` sits on `httpClient` like the rest of the
 * family, but its only consumer is outside the Auswertungen pages.
 */
export const AUDIT_ERROR_CODES = ['audit_logs_load_failed'] as const;
