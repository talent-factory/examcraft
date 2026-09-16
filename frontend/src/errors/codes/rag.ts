/**
 * Error codes of the premium RAG exam flow (TF-772 PR 5).
 *
 * Frontend-only by construction: `RAGService.validateRAGRequest` checks the
 * request in the browser before anything is sent, so no endpoint is involved
 * and there is no backend text to copy. The texts are the German literals the
 * service used to return, taken over verbatim.
 *
 * The `rag_validation_` prefix is deliberate. `core/backend/api/rag_exams.py`
 * already emits its own `rag_*` codes (TF-773, PR #249) that are not yet
 * registered in this frontend AppError registry — among them
 * `rag_invalid_question_type`, which reads like the client check below but is a
 * different sentence for a different failure. Those backend codes belong in
 * this file once they are registered; the prefix keeps the two groups from
 * colliding. (`rag_get_documents_failed` predates both and lives in
 * `documents.ts`, because `DocumentService` is its only consumer.)
 */
export const RAG_ERROR_CODES = [
  'rag_validation_document_required',
  'rag_validation_invalid_difficulty',
  'rag_validation_invalid_language',
  'rag_validation_invalid_question_types',
  'rag_validation_question_count_range',
  'rag_validation_question_type_required',
  'rag_validation_topic_too_short',
] as const;
