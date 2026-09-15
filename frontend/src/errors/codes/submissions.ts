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
 * `submissions.py` itself raises no `api_error()` yet — hand-written German and
 * `detail=str(exc)` throughout. TF-773 PR 2c migrates the four import
 * endpoints onto 10–15 distinct codes and waits for this file: those codes
 * belong here once they exist, next to the operation fallbacks below. Until
 * then an import failure shows the operation sentence where it used to show
 * the service text («Die Datei ist leer.»), the interim loss TF-772 accepted.
 *
 * FRONTEND-ONLY FALLBACKS, one per operation a component renders a failure
 * for:
 *
 *   submissions_detail_load_failed, submissions_grade_export_failed,
 *   submissions_import_commit_failed, submissions_import_delete_failed,
 *   submissions_import_preview_failed, submissions_import_summary_load_failed,
 *   submissions_list_failed
 *
 * TF-773 PR 2c should not reuse these names for a code with a different
 * meaning: `submissions_import_preview_failed` here means "the preview failed
 * for a reason the frontend cannot tell", and a backend code of that name
 * would be rendered with this sentence.
 *
 * Texts copied from the components' existing fallback keys
 * (`auswertungen.importDialog.*`, `auswertungen.deleteImportDialog.*`,
 * `auswertungen.exam.detailError`, `auswertungen.export.errorServer`).
 * `submissions_list_failed` is new: `AuswertungenExam` loads the exam and its
 * submissions in one `Promise.all` and had one sentence for both.
 */
export const SUBMISSIONS_ERROR_CODES = [
  'submissions_detail_load_failed',
  'submissions_grade_export_blocked_draft',
  'submissions_grade_export_blocked_pending_review',
  'submissions_grade_export_failed',
  'submissions_import_commit_failed',
  'submissions_import_delete_failed',
  'submissions_import_preview_failed',
  'submissions_import_summary_load_failed',
  'submissions_list_failed',
] as const;
