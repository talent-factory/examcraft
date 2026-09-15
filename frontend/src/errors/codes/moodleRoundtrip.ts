/**
 * Error code for `MoodleConnectionsService.syncQuestionIds` (TF-772 PR 7),
 * which hits `core/backend/api/moodle_roundtrip.py`.
 *
 * Fallback-only: the router raises plain `HTTPException`s. Some of what it
 * sends today is user-actionable («Diese Prüfung hat keine Fragen — Sync nicht
 * möglich.»), some is infrastructure («Token-Verschlüsselung defekt: {exc}»,
 * «Moodle-API HTTP 500»). Both now render as `moodle_roundtrip_sync_failed`;
 * the 404 keeps `SyncMoodleIdsDialog`'s own `notVisible` sentence. The router
 * has no TF-773 package yet — reported.
 */
export const MOODLE_ROUNDTRIP_ERROR_CODES = ['moodle_roundtrip_sync_failed'] as const;
