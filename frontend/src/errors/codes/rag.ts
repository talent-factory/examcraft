/**
 * Error codes of the premium RAG exam flow.
 *
 * Two groups share the `rag_` prefix and must not be confused.
 *
 * BACKEND CODES (TF-773 Teil D), texts verbatim from
 * `core/backend/locales/t.*.json` with `%{x}` rewritten to `{{x}}`. Raised by
 * `core/backend/api/rag_exams.py` since TF-773 PR #249 and PR 2d, but only
 * registered in Teil D — and only half of the job was the registration:
 * `RAGService` (premium/frontend) threw a fixed legacy code without reading
 * the body, so no `error_code` ever reached `selectCode()`. Teil D moved
 * `triggerGeneration`, `retryGeneration`, `retrieveContext` and
 * `getTaskResult` onto `appErrorFromResponse`. What a component can now
 * receive:
 *
 *   rag_context_retrieval_failed  500  retrieve-context (context preview)
 *   rag_document_not_found        404  generate-exam, retrieve-context — a
 *                                      selected document deleted meanwhile
 *   rag_document_not_processed    400  generate-exam — a document preselected
 *                                      from the exam list that is not processed
 *   rag_generation_failed         500  generate-exam, retry-generation
 *   rag_no_institution            403  generate-exam, retry-generation, and
 *                                      available-documents via DocumentService
 *   rag_retry_owner_unavailable   400  retry-generation — a superuser retrying
 *                                      another user's task
 *   rag_tag_archived {{name}}     422  generate-exam — a tag archived after it
 *                                      was picked, or a pending tag whose
 *                                      creation returned an archived one
 *   rag_tag_ids_invalid           422  generate-exam — a picked tag deleted
 *   rag_task_not_found            404  retry-generation, task result (get-task-result)
 *                                      — job row gone
 *   rag_task_queue_unavailable    503  generate-exam, retry-generation
 *
 * Deliberately NOT registered, because no call site can reach them:
 *
 *   rag_invalid_question_type    `validateRAGRequest` allows a strict subset of
 *                                the backend's types before anything is sent
 *   rag_retry_only_failed        the retry button exists only for FAILURE/
 *                                REVOKED tasks and is disabled while a retry
 *                                is in flight
 *   rag_retry_no_request_data    generate-exam always stores `request_data`
 *   rag_service_unhealthy        `RAGService.checkHealth` has no caller
 *
 * (`rag_get_documents_failed` predates both groups and lives in
 * `documents.ts`, because `DocumentService` is its only consumer.)
 *
 * FRONTEND-ONLY CODES (TF-772 PR 5): `rag_validation_*` come from
 * `RAGService.validateRAGRequest`, which checks the request in the browser
 * before anything is sent. No endpoint is involved and there is no backend
 * text to copy; the texts are the German literals the service used to
 * return. The `validation` infix keeps them apart from the backend group —
 * `rag_validation_invalid_question_types` reads like `rag_invalid_question_type`
 * but is a different sentence for a different failure.
 */
export const RAG_ERROR_CODES = [
  'rag_context_retrieval_failed',
  'rag_document_not_found',
  'rag_document_not_processed',
  'rag_generation_failed',
  'rag_no_institution',
  'rag_retry_owner_unavailable',
  'rag_tag_archived',
  'rag_tag_ids_invalid',
  'rag_task_not_found',
  'rag_task_queue_unavailable',
  'rag_validation_document_required',
  'rag_validation_invalid_difficulty',
  'rag_validation_invalid_language',
  'rag_validation_invalid_question_types',
  'rag_validation_question_count_range',
  'rag_validation_question_type_required',
  'rag_validation_topic_too_short',
] as const;
