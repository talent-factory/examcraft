/**
 * Error codes reachable through `GradesService` (TF-772 PR 4).
 *
 * `core/backend/api/grades.py` was frontend-fallback-only when this file was
 * first written — every failure was a hand-written `HTTPException(status,
 * detail="…")` in German, or `detail=str(exc)` from a `GradingService`
 * exception, with no `t(...)` and no `error_code`. TF-773 has since migrated
 * the router onto `api_error()`/`AppHTTPException`. Eight codes below are now
 * real backend codes, accepted off the wire the same way `documents_tag_exists`
 * is: `grades_exam_not_found`, `grades_not_found`,
 * `grades_confidence_range_invalid`, `grades_override_not_found`,
 * `grades_override_invalid`, `grades_bulk_approve_invalid`,
 * `grades_question_not_found`, `grades_regrade_failed`.
 *
 * The remaining four — `grades_approve_failed`, `grades_bulk_approve_failed`,
 * `grades_override_failed`, `grades_review_queue_load_failed` — are frontend-
 * only fallbacks, one per `GradesService` operation, for a network failure or a
 * 500 the backend raises without a specific code. `grades_approve_failed`
 * happens to double as a real backend code too (the router raises it verbatim
 * for `GradeNotFoundError` in `approve_grade`); the other three
 * (`grades_bulk_approve_failed`, `grades_override_failed`,
 * `grades_review_queue_load_failed`) stay purely frontend-side. Two of them
 * (`grades_override_failed`, `grades_bulk_approve_failed`) now sit next to a
 * backend code that is *more* specific than the operation-level fallback
 * (`grades_override_not_found`/`grades_override_invalid`,
 * `grades_bulk_approve_invalid`) — `selectCode()` always prefers the specific
 * backend code when the response carries one, so the fallback only fires when
 * it does not.
 */
export const GRADES_ERROR_CODES = [
  'grades_approve_failed',
  'grades_bulk_approve_failed',
  'grades_bulk_approve_invalid',
  'grades_confidence_range_invalid',
  'grades_exam_not_found',
  'grades_not_found',
  'grades_override_failed',
  'grades_override_invalid',
  'grades_override_not_found',
  'grades_question_not_found',
  'grades_regrade_failed',
  'grades_review_queue_load_failed',
] as const;
