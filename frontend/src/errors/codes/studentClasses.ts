/**
 * Error codes reachable through `StudentClassesService` (TF-772 PR 7).
 *
 * File name `studentClasses.ts`, codes `student_classes_*` — the backend router
 * is `core/backend/api/student_classes.py`; same camelCase-file rule as
 * `orgUnits.ts`.
 *
 * The service sits on `httpClient` and keeps throwing `ApiError`: its
 * consumers branch on `status` (402 → QuotaBanner, 409 → "duplicate") before
 * they render anything, and `AppError` carries no `kind` or quota `detail`.
 * The conversion happens in the component, via `appErrorFromApiError()`, at
 * the moment a message is rendered.
 *
 * BACKEND CODES. `student_classes.py` raises five codes through `api_error()`.
 * Three are registered, texts verbatim from `core/backend/locales/t.*.json`:
 *
 *   student_classes_not_found             404, get / rename / delete / members / stats
 *   student_classes_student_not_found     404, add member
 *   student_classes_membership_not_found  404, remove member
 *
 * The other two are 409s that no converted call site can reach, and are
 * deliberately absent: `student_classes_name_exists` (create/rename) and
 * `student_classes_already_member` (add member). `CreateClassDialog` and
 * `AssignStudentDialog` intercept `status === 409` with their own "duplicate"
 * sentence before the conversion runs — the same meaning, so nothing is lost,
 * and registering the codes would put two unreachable keys under the i18n
 * guard.
 *
 * FRONTEND-ONLY FALLBACKS, one per operation a component renders a failure
 * for — a network failure, a proxy page, or a 403/500 without a registered
 * code lands here:
 *
 *   student_classes_add_member_failed, student_classes_create_failed,
 *   student_classes_delete_failed, student_classes_history_load_failed,
 *   student_classes_list_failed, student_classes_load_failed,
 *   student_classes_remove_member_failed, student_classes_rename_failed
 *
 * Where the component already had a fallback sentence for the operation
 * (`auswertungen.klassen.*`), the code's text is that sentence, copied. Rename,
 * delete, history and remove-member had none: rename borrowed "Klasse konnte
 * nicht angelegt werden." and the other three rendered nothing but
 * `err.message`.
 */
export const STUDENT_CLASSES_ERROR_CODES = [
  'student_classes_add_member_failed',
  'student_classes_create_failed',
  'student_classes_delete_failed',
  'student_classes_history_load_failed',
  'student_classes_list_failed',
  'student_classes_load_failed',
  'student_classes_membership_not_found',
  'student_classes_not_found',
  'student_classes_remove_member_failed',
  'student_classes_rename_failed',
  'student_classes_student_not_found',
] as const;
