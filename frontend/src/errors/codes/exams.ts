/**
 * Error codes reachable through `ComposerService` (TF-772 PR 7).
 *
 * `ComposerService` is axios, so these arrive through `appErrorFromAxios()`.
 * Two groups of consumers: the Auswertungen pages (`listExams`, `getExam`) and
 * the exam composer (`components/composer/*`), which until PR 7 rendered the
 * backend `detail` directly through `ComposerService.getErrorMessage()` — the
 * same leak class as the ApiError family, reached through axios instead.
 *
 * BACKEND CODES. Every code `core/backend/api/exams.py` raises from an
 * endpoint the frontend calls, texts verbatim from `core/backend/locales/`
 * (fr/it of `exams_export_internal_error` in the informal wording of TF-773
 * PR 2a). Reachability was derived per endpoint, including the helpers each
 * endpoint calls (`_get_exam_or_404`, `_require_draft`, `_auto_compose`, …).
 *
 * Six codes break the file-name-is-the-prefix rule, and are here because the
 * identity rule copies the backend verbatim (same exception as `review.ts`):
 * `approved_question_not_found`, `delete_exam_failed`,
 * `exam_archive_already_archived`, `exam_archive_failed`,
 * `exam_archive_not_archived`, `exam_restore_failed` — all raised by
 * `exams.py`, none prefixed `exams_`. The `visibility_*` codes the same router
 * raises live in `visibility.ts`, because `question_review.py` and
 * `competency_frameworks.py` raise them too.
 *
 * `delete_exam_failed`, `exam_archive_failed` and `exam_restore_failed` double
 * as the frontend fallback for their operation: the backend already names
 * that exact sentence, so inventing `exams_archive_failed` next to
 * `exam_archive_failed` would only add a near-duplicate.
 *
 * FRONTEND-ONLY FALLBACKS, one per operation a component renders a failure
 * for, texts copied from the component's existing `composer.*` /
 * `auswertungen.*` key:
 *
 *   exams_approved_question_load_failed, exams_approved_questions_load_failed,
 *   exams_auto_fill_failed, exams_compose_failed, exams_create_failed,
 *   exams_documents_load_failed, exams_export_failed, exams_finalize_failed,
 *   exams_list_failed, exams_load_failed, exams_question_add_failed,
 *   exams_question_generation_failed, exams_question_points_update_failed,
 *   exams_question_remove_failed, exams_questions_reorder_failed,
 *   exams_unfinalize_failed, exams_update_failed
 *
 * `exams_question_generation_failed` closes the one remaining `detail`/
 * `err.message` leak the PR 7 review found: `BasicExamCreator` had its own
 * inline `fetch` parser instead of going through the family. Its endpoint,
 * `POST /api/v1/questions/generate` in `main.py`, predates ADR 0005 and
 * raises a plain `HTTPException` with no `error_code`, so this is a
 * frontend-only fallback like the others above, not a registered backend
 * code.
 *
 * `exams_list_failed` and `exams_load_failed` belong to the Auswertungen pages;
 * `exams_load_failed` is new text, because `AuswertungenExam` had one sentence
 * for exam and submissions together (see `submissions.ts`).
 */
export const EXAMS_ERROR_CODES = [
  'approved_question_not_found',
  'delete_exam_failed',
  'exam_archive_already_archived',
  'exam_archive_failed',
  'exam_archive_not_archived',
  'exam_restore_failed',
  'exams_already_draft',
  'exams_approved_question_load_failed',
  'exams_approved_questions_load_failed',
  'exams_auto_fill_failed',
  'exams_cannot_export_empty',
  'exams_cannot_finalize_empty',
  'exams_compose_failed',
  'exams_composition_constraint_error',
  'exams_conflict',
  'exams_create_failed',
  'exams_db_error',
  'exams_distribution_invalid_keys',
  'exams_distribution_sum_invalid',
  'exams_documents_load_failed',
  'exams_exam_question_not_found',
  'exams_export_all_questions_unscoreable',
  'exams_export_failed',
  'exams_export_internal_error',
  'exams_finalize_failed',
  'exams_grading_scheme_invalid',
  'exams_list_failed',
  'exams_load_failed',
  'exams_must_be_draft',
  'exams_must_finalize_before_export',
  'exams_no_matching_questions',
  'exams_no_questions_fit_constraints',
  'exams_not_found',
  'exams_question_add_failed',
  'exams_question_generation_failed',
  'exams_question_not_approved',
  'exams_question_not_found',
  'exams_question_points_update_failed',
  'exams_question_remove_failed',
  'exams_questions_not_approved',
  'exams_questions_reorder_failed',
  'exams_tag_ids_invalid',
  'exams_unfinalize_failed',
  'exams_unsupported_format',
  'exams_update_failed',
] as const;
