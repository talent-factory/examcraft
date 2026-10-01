/**
 * Fallback-only: `ComplianceService.getContent`, the public AVV/TOM content.
 * It was the TF-671 code `compliance.loadFailed` until TF-996 flattened it.
 *
 * SILENT ON PURPOSE (TF-996). `CompliancePage` never hands this to
 * `translateError`: it logs the error, reports it via `reportHandledError`
 * (client error reporting, Specula) and shows its own
 * generic "please try again later" text. The page is public and
 * unauthenticated, so the cause stays out of the user-facing message; there
 * is nothing the reader could do with a more specific sentence. The code
 * still needs its four-locale text, because the service throws it.
 */
export const COMPLIANCE_ERROR_CODES = ['compliance_load_failed'] as const;
