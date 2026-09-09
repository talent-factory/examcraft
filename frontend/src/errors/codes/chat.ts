/**
 * Error codes reachable through the premium `ChatService` (TF-772 PR 4).
 *
 * Frontend-only, for the same reason as `prompts.ts`: the chat router lives in
 * `premium/backend/api/v1/chat.py`, and the premium backend has no `locales/`
 * directory — there is no `chat_*` key to copy and no endpoint that can send an
 * `error_code`. The names follow the identity rule's shape (flat snake_case,
 * prefix = router) so they need no renaming when that changes.
 *
 * `chat.py` is the milder case of the two: eight of its twelve raises are a
 * generic "Fehler beim <Operation>" per endpoint, which is exactly what the
 * codes below say. Two are more specific and DO get lost — "Chat-Session nicht
 * gefunden" (404) and "Dokumente nicht gefunden: [ids]" (404) — and one is a
 * developer error the UI cannot reach ("Ungültiges Format. Erlaubt: markdown,
 * json"; `ChatService` and `ChatInterface` only ever send those two values).
 *
 * NOT LISTED, AND DELIBERATELY SO: `chat.downloadFailed` and
 * `chat.conversionFailed`, both thrown and translated inside `ChatInterface`
 * itself — the download there bypasses `ChatService` and calls `fetch`
 * directly, because it needs the Blob and the filename dialog. Only
 * `chat.downloadFailed` is a TF-671 dot-notation code registered in
 * `legacy.ts`; `chat.conversionFailed` is never constructed as an `AppError`
 * at all — it is only ever a plain `fallbackKey` string passed to
 * `translateError`, so it needs no registration in either file.
 * `chat_download_failed` below belongs to `ChatService.downloadChat`, a
 * different call site with no consumer today. Two codes for what reads like
 * one operation is the honest state; merging them would mean touching
 * `legacy.ts`, which is frozen until TF-775.
 */
export const CHAT_ERROR_CODES = [
  'chat_create_session_failed',
  'chat_delete_session_failed',
  'chat_download_failed',
  'chat_export_failed',
  'chat_history_load_failed',
  'chat_send_message_failed',
  'chat_session_load_failed',
  'chat_sessions_load_failed',
] as const;
