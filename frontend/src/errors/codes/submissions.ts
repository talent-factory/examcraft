/**
 * Error codes reachable through `SubmissionsService` and `GradeExportService`
 * (TF-772 PR 7).
 *
 * One file for both because the backend prefix is one: `grade_export.py`
 * raises `submissions_grade_export_*`, not a prefix of its own.
 *
 * BACKEND CODES. Two, texts verbatim from `core/backend/locales/t.*.json`:
 *
 *   submissions_grade_export_blocked_draft           409
 *   submissions_grade_export_blocked_pending_review  409
 *
 * `NotenexportPanel` renders only the `conflict` kind from the response; auth,
 * permission, not-found and server errors get the panel's own
 * `auswertungen.export.*` sentences before any code is looked at. That is why
 * `submissions_grade_export_internal_error` (500) is absent — no call site can
 * reach it. The fr/it texts of the two 409s follow TF-773 PR 2a, which moved
 * them from «veuillez»/«si prega» to the informal register the project uses.
 *
 * REMAINING ROUTER CODES (TF-773 Teil D). The last four plain
 * `HTTPException`s in `submissions.py` now carry a code. Two are new:
 *
 *   submissions_import_job_not_found      404, import-job polling in
 *                                         `ImportDialog` — the job row goes
 *                                         when its exam is deleted mid-import
 *   submissions_delete_audit_unavailable  503, `DeleteImportDialog` — the
 *                                         audit write failed and the deletion
 *                                         was rolled back; «Löschen
 *                                         fehlgeschlagen.» hid that nothing
 *                                         was deleted. 503 (not 500): a
 *                                         transient, retryable dependency
 *                                         failure — the text itself says
 *                                         «Bitte versuche es später erneut.»
 *
 * The other two reuse existing names for the same fact: `exams_not_found`
 * (`exams.ts`) and `stats_submission_not_found` (`stats.ts`).
 *
 * IMPORT CODES (TF-773 PR 2c). The four import endpoints —
 * `/import/{preview,commit,api-preview,api-commit}` — answered with
 * `detail=str(exc)` until then, which is why the interim loss below existed:
 * the service sentence WAS the message, and the operation fallback replaced
 * «Die Datei ist leer.» with «Vorschau fehlgeschlagen.». The 21 codes below
 * end that. They are more than the 10–15 the ticket estimated because each
 * one leads to a different action by the teacher — «Moodle ist nicht
 * erreichbar» (wait), «Moodle hat den Zugriff verweigert» (ask the admin) and
 * «Das Moodle-Quiz 4242 wurde nicht gefunden» (check the ID) share a
 * transport but nothing else:
 *
 *   ..._attempt_without_user       ..._moodle_connection_invalid
 *   ..._driver_unknown             ..._moodle_connection_missing
 *   ..._enqueue_failed             ..._moodle_rate_limited
 *   ..._exam_mismatch {{count}}    ..._moodle_server_error {{status}}
 *   ..._exam_without_questions     ..._moodle_unexpected_response
 *   ..._file_empty                 ..._moodle_unreachable
 *   ..._file_not_json              ..._no_attempts
 *   ..._file_not_utf8              ..._question_mapping_failed
 *   ..._file_too_large {{max_mb}}  ..._question_texts_missing
 *   ..._internal_error             ..._quiz_not_found {{quiz_id}}
 *   ..._json_structure_invalid
 *   ..._moodle_auth_failed
 *
 * `submissions_import_driver_unknown` was unreachable via HTTP until the
 * TF-773 PR 2c review found that the multipart file-upload endpoints
 * (`/import/preview`, `/import/commit`) accepted `driver_name` as an
 * unvalidated string, letting `moodle_api` — meant only for the JSON-body
 * `/import/api-preview`/`/import/api-commit` pair — reach the driver with a
 * `quiz_id` that skipped `ApiImportIn`'s Pydantic guard. `submissions.py`'s
 * `_reject_driver_without_upload_body()` now rejects `moodle_api` on those
 * two endpoints with this code before the tier check runs, so it belongs
 * here rather than in the "unreachable" set below.
 *
 * The backend raises one more, deliberately absent here because no endpoint
 * can produce it — `ApiImportIn` rejects `quiz_id <= 0` with a 422
 * `validation_error` before the driver ever sees it:
 * `submissions_import_quiz_id_invalid`. Same rule as
 * `submissions_grade_export_internal_error` above. The contract test pins
 * that guard; if it goes away, the test fails and the code belongs here.
 *
 * Four carry parameters. Their texts are copied verbatim from
 * `core/backend/locales/t.*.json` with `%{x}` rewritten to `{{x}}` — the
 * backend sends both the rendered sentence and the parameters, and this file's
 * copy is what `translateError` actually renders.
 *
 * `..._internal_error` is deliberately here and deliberately vague: it covers
 * the programming and configuration errors whose original texts named classes
 * and tables («MoodleApiDriver braucht eine DB-Session …»). Those now go to
 * the log.
 *
 * FRONTEND-ONLY FALLBACKS, one per operation a component renders a failure
 * for:
 *
 *   submissions_detail_load_failed, submissions_grade_export_failed,
 *   submissions_import_commit_failed, submissions_import_delete_failed,
 *   submissions_import_preview_failed, submissions_import_summary_load_failed,
 *   submissions_list_failed
 *
 * The four import codes above are named so they cannot collide with these:
 * `submissions_import_preview_failed` means "the preview failed for a reason
 * the frontend cannot tell", and a backend code of that name would have been
 * rendered with this generic sentence instead of its own.
 *
 * Texts copied from the components' existing fallback keys
 * (`auswertungen.importDialog.*`, `auswertungen.deleteImportDialog.*`,
 * `auswertungen.exam.detailError`, `auswertungen.export.errorServer`).
 * `submissions_list_failed` is new: `AuswertungenExam` loads the exam and its
 * submissions in one `Promise.all` and had one sentence for both.
 */
export const SUBMISSIONS_ERROR_CODES = [
  'submissions_delete_audit_unavailable',
  'submissions_detail_load_failed',
  'submissions_grade_export_blocked_draft',
  'submissions_grade_export_blocked_pending_review',
  'submissions_grade_export_failed',
  'submissions_import_attempt_without_user',
  'submissions_import_commit_failed',
  'submissions_import_delete_failed',
  'submissions_import_driver_unknown',
  'submissions_import_enqueue_failed',
  'submissions_import_exam_mismatch',
  'submissions_import_exam_without_questions',
  'submissions_import_file_empty',
  'submissions_import_file_not_json',
  'submissions_import_file_not_utf8',
  'submissions_import_file_too_large',
  'submissions_import_internal_error',
  'submissions_import_job_not_found',
  'submissions_import_json_structure_invalid',
  'submissions_import_moodle_auth_failed',
  'submissions_import_moodle_connection_invalid',
  'submissions_import_moodle_connection_missing',
  'submissions_import_moodle_rate_limited',
  'submissions_import_moodle_server_error',
  'submissions_import_moodle_unexpected_response',
  'submissions_import_moodle_unreachable',
  'submissions_import_no_attempts',
  'submissions_import_preview_failed',
  'submissions_import_question_mapping_failed',
  'submissions_import_question_texts_missing',
  'submissions_import_quiz_not_found',
  'submissions_import_summary_load_failed',
  'submissions_list_failed',
] as const;
