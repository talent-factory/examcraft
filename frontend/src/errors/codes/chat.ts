/**
 * Error codes reachable through the premium `ChatService`.
 *
 * TF-772 PR 4 registered the eight operation fallbacks while `premium/backend/
 * api/v1/chat.py` still had no localized codes. Since TF-773 PR 2b the router
 * sends a code at every raise site (ADR 0006), and its generic 500s use exactly
 * these eight names, so each of them is now both a fallback and a backend
 * code. The two specific sentences TF-772 had to give up come back as
 * `chat_session_not_found` and `chat_documents_not_found` (with the missing
 * ids as `{{document_ids}}`); `chat_export_format_invalid` answers the
 * download endpoint's format check.
 *
 * `chat_export_render_failed` is deliberately absent: it belongs to
 * `POST /api/v1/chat/sessions/{id}/export`, which no frontend code calls —
 * registering it would put a permanently unreachable key under the i18n guard.
 * `chat_export_failed` is the `/to-document` endpoint, matching
 * `ChatService.exportToDocument`.
 *
 * `ChatInterface` downloads with its own `fetch` instead of
 * `ChatService.downloadChat`, but it hits the same endpoint, so it throws the
 * same `chat_download_failed`. Until TF-996 it had a TF-671 code of its own
 * (`chat.downloadFailed`), and its conversion fallback key was the nested
 * `errors.chat.conversionFailed`; that one is now `errors.chat_export_failed`,
 * which `ChatService.exportToDocument` already throws for the same request.
 */
export const CHAT_ERROR_CODES = [
  'chat_create_session_failed',
  'chat_delete_session_failed',
  'chat_documents_not_found',
  'chat_download_failed',
  'chat_export_failed',
  'chat_export_format_invalid',
  'chat_history_load_failed',
  'chat_send_message_failed',
  'chat_session_load_failed',
  'chat_session_not_found',
  'chat_sessions_load_failed',
] as const;
