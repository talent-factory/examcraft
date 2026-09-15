/**
 * Error codes reachable through `GradingSchemesService` on the admin pages
 * (TF-772 PR 7).
 *
 * File `gradingSchemes.ts`, codes `grading_schemes_*`, router
 * `core/backend/api/grading_schemes.py`.
 *
 * BACKEND CODES. Nine of the router's ten, texts verbatim from
 * `core/backend/locales/t.*.json`:
 *
 *   create (GradingSchemeEditor)   institution_required 400, name_exists 409,
 *                                  database_error 500
 *   update (GradingSchemeEditor)   not_found 404, system_not_editable 403,
 *                                  uniqueness_violated 409, database_error 500
 *   delete (AdminGradingSchemes)   not_found, system_not_editable,
 *                                  is_institution_default 409, referenced 409,
 *                                  referenced_by_exam 409, database_error
 *
 * Absent: `grading_schemes_cross_institution_superadmin_only` (403), raised by
 * `list` only when an `institution_id` is passed. `AdminGradingSchemes` never
 * passes one; `InstitutionEditDialog` does, but renders no error text.
 *
 * WHY THE DELETE 409s MATTER. `AdminGradingSchemes` used to answer every
 * `kind === 'conflict'` with `admin.gradingSchemes.deleteInUse` («… wird von
 * mindestens einer Prüfung verwendet …»). The router has three distinct 409s,
 * and for `is_institution_default` that sentence is wrong — the fix is to pick
 * another default, not to remove the scheme from an exam. The page now lets a
 * registered code win and keeps `deleteInUse` only for a 409 without one.
 *
 * FRONTEND-ONLY FALLBACKS, one per operation: `grading_schemes_create_failed`,
 * `grading_schemes_delete_failed`, `grading_schemes_list_failed`,
 * `grading_schemes_update_failed` — texts copied from
 * `admin.gradingSchemes.failed*`.
 */
export const GRADING_SCHEMES_ERROR_CODES = [
  'grading_schemes_create_failed',
  'grading_schemes_database_error',
  'grading_schemes_delete_failed',
  'grading_schemes_institution_required',
  'grading_schemes_is_institution_default',
  'grading_schemes_list_failed',
  'grading_schemes_name_exists',
  'grading_schemes_not_found',
  'grading_schemes_referenced',
  'grading_schemes_referenced_by_exam',
  'grading_schemes_system_not_editable',
  'grading_schemes_uniqueness_violated',
  'grading_schemes_update_failed',
] as const;
