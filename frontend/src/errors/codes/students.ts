/**
 * Error codes reachable through `StudentsService`.
 *
 * BACKEND CODE (TF-773 PR 2d). `core/backend/api/students.py` raised two plain
 * `HTTPException(404, detail="Studi nicht gefunden")` — the detail page's and
 * the history endpoint's — and PR 2d put both on one `api_error()`:
 *
 *   students_not_found  404, get student / get history
 *
 * One code for both because the sentence is the same statement about the same
 * row; nothing distinguishes them for a reader. That restores the «Studi nicht
 * gefunden» TF-772 PR 7 recorded as lost on the history page, in four
 * languages instead of one.
 *
 * Note the near-twin in `studentClasses.ts`: `student_classes_student_not_found`
 * has the identical German text but belongs to `student_classes.py`'s
 * add-member endpoint. Same sentence, two routers, one prefix each.
 *
 * FRONTEND-ONLY FALLBACKS, one per operation:
 *
 *   students_history_load_failed, students_list_failed
 */
export const STUDENTS_ERROR_CODES = [
  'students_history_load_failed',
  'students_list_failed',
  'students_not_found',
] as const;
