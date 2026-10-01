/**
 * Fallback-only: `useFeatures` loading `GET /api/auth/features`.
 *
 * The endpoint raises no `error_code` of its own, and `useFeatures` builds its
 * `AppError` from the status alone rather than through `appErrorFromResponse`,
 * so this is the only code the hook's `error` ever carries. It was the TF-671
 * code `features.loadFailed` until TF-996 flattened it.
 *
 * SILENT TODAY (TF-996). No consumer renders it: the only one that reads
 * `error`, `TierGate` in `PortfolioGate.tsx`, logs it and lets the page
 * through (fail-open), and `withFeatureGate` does not read it at all. The
 * four-locale text exists because the hook translates the error into its
 * `error` field; a consumer that wants to show it can.
 */
export const FEATURES_ERROR_CODES = ['features_load_failed'] as const;
