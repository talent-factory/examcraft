/**
 * Error codes of `premium/backend/api/v1/vector_search.py` reachable from the
 * frontend (TF-773 PR 2b).
 *
 * Only one consumer exists: `DocumentService.reindexDocument` and
 * `DocumentService.getDocumentChunks`. Both endpoints answer their not-found
 * and generic-failure cases with names `documents.ts` already holds
 * (`documents_not_found`, `documents_chunks_load_failed`,
 * `documents_reindex_failed`) — the identity rule beats the router prefix, see
 * ADR 0006. What remains specific to this router is the one precondition the
 * user can act on.
 *
 * Caveat: `main.py` does not include the vector-search router today, so both
 * endpoints currently answer a bodyless 404 and the caller's fallback applies.
 * The code is registered for the day the router is mounted; the service
 * methods themselves have no component caller either.
 *
 * Not listed: `vector_search_failed`, `vector_search_stats_failed` and
 * `vector_search_delete_failed` — their endpoints (`/similarity`, `/stats`,
 * `DELETE …/vectors`) have no frontend caller.
 */
export const VECTOR_SEARCH_ERROR_CODES = ['vector_search_document_not_processed'] as const;
