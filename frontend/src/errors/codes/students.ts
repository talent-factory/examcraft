/**
 * Error codes reachable through `StudentsService` (TF-772 PR 7).
 *
 * Fallback-only. `core/backend/api/students.py` raises two plain
 * `HTTPException(404, detail="Studi nicht gefunden")` and no `api_error()`, so
 * there is no `error_code` to accept. What does arrive coded is the auth
 * dependency in front of it (`auth_permission_required`, see `auth.ts`).
 *
 * Known loss: the 404 on the history page used to show «Studi nicht gefunden»
 * via `err.message`; it now shows `students_history_load_failed`. Reported to
 * TF-773 as a router without a package, not worked around here.
 */
export const STUDENTS_ERROR_CODES = ['students_history_load_failed', 'students_list_failed'] as const;
