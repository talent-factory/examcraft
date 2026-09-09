/**
 * Error codes reachable through `DocumentService` (TF-772 PR 2).
 *
 * Almost all of them are copied verbatim from `core/backend/locales/t.*.json`,
 * where they are raised by `core/backend/api/documents.py` and
 * `core/backend/utils/document_tags.py`. That is the identity rule from
 * ADR 0005: the frontend key is `errors.` + the backend's `error_code`, so a
 * code that already exists on the backend is never renamed on the way over —
 * `documents_tag_exists` stays `documents_tag_exists`.
 *
 * Registering the specific codes and not just one generic per method is the
 * point of the exercise. Before TF-772 the services threw
 * `new Error(errorData.detail || '…')` and the components rendered
 * `err.message`, which already showed the backend's *localized* prose — the
 * backend has answered in the user's language since TF-670. Mapping every
 * failure of `approveQuestion` to a single "could not approve" would therefore
 * have been a regression, not a translation: the four-eyes message, the
 * owner-only message and the quota message would all have collapsed into one.
 *
 * FRONTEND-ONLY FALLBACKS — three codes below have no backend counterpart:
 *
 *   documents_reindex_failed          POST /api/v1/search/reindex/{id} lives in
 *                                     the premium vector-search router, which
 *                                     has no localized error codes at all.
 *   documents_tags_load_failed        GET /api/v1/documents/tags has no error
 *                                     handler; a failure arrives as a framework
 *                                     500, i.e. `internal_error`.
 *   documents_visibility_update_failed  PATCH /api/v1/documents/{id} answers a
 *                                     generic failure with
 *                                     `documents_rename_failed` ("could not be
 *                                     renamed") even when the request changed
 *                                     only the visibility. That text is wrong
 *                                     for a visibility flip, so the frontend
 *                                     registers its own fallback for it.
 *                                     Caveat: since `documents_rename_failed`
 *                                     is itself a registered code and
 *                                     `appErrorFromResponse` always prefers a
 *                                     registered backend code over the
 *                                     caller's fallback, this fallback is
 *                                     currently only reached for a genuinely
 *                                     codeless response on this endpoint
 *                                     (network failure, bodyless 500,
 *                                     non-JSON proxy body) — a *bodied* 500
 *                                     from `PATCH /documents/{id}` still
 *                                     surfaces "could not be renamed" today.
 *                                     Registering it anyway is still correct
 *                                     (it is used, just not on the path this
 *                                     comment originally implied); making it
 *                                     reachable for the bodied-500 case too
 *                                     needs a backend-side fix, not a
 *                                     frontend one.
 *
 * They exist so a network failure or a bodyless 500 still produces a sentence
 * about the operation the user actually attempted. If the backend later grows
 * real codes for these three, replace them here and drop the locale entries.
 *
 * Not included, deliberately: `documents_patch_no_fields`,
 * `documents_rename_invalid_chars` and `documents_rename_too_long` exist in the
 * backend locale files but are raised nowhere in the backend — dead keys, and
 * registering them here would put three permanently-unreachable codes under the
 * i18n test. Reported to TF-772 rather than fixed here (backend scope).
 */
export const DOCUMENT_ERROR_CODES = [
  'documents_access_denied',
  'documents_chunks_load_failed',
  'documents_content_load_failed',
  'documents_content_not_available',
  'documents_delete_failed',
  'documents_download_failed',
  'documents_download_storage_failed',
  'documents_file_not_found_disk',
  'documents_file_not_found_storage',
  'documents_invalid_filter',
  'documents_invalid_status',
  'documents_list_failed',
  'documents_load_failed',
  'documents_not_found',
  'documents_not_processed',
  'documents_page_out_of_range',
  'documents_preview_failed',
  'documents_processing_failed',
  'documents_reindex_failed',
  'documents_rename_failed',
  'documents_rename_owner_only',
  'documents_status_failed',
  'documents_storage_unavailable',
  'documents_tag_exists',
  'documents_tag_failed',
  'documents_tag_institution_admin_only',
  'documents_tag_institution_requires_shared',
  'documents_tag_not_found',
  'documents_tag_owner_only',
  'documents_tags_load_failed',
  'documents_upload_failed',
  'documents_visibility_invalid_org_unit',
  'documents_visibility_no_institution',
  'documents_visibility_owner_only',
  'documents_visibility_update_failed',
  // Not a `documents_*` code, but it is the code
  // GET /api/v1/rag/available-documents answers with, and that endpoint is
  // called by DocumentService.getAvailableDocuments — so it belongs to this
  // service's accept-list, not to the RAG package.
  'rag_get_documents_failed',
] as const;
