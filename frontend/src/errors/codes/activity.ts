/**
 * Error code for `ActivityService` (TF-772 PR 7), router
 * `core/backend/api/activity.py`.
 *
 * Fallback-only: the router raises plain `HTTPException`s — a 422 with a dict
 * `detail` for unknown type filters (a frontend bug, not a user error) and a
 * 403 whose `detail` is English («scope=institution requires institution
 * membership»). Neither was worth showing; both now render
 * `activity_list_failed`. What does arrive coded is the auth dependency
 * (`get_current_active_user`, see `auth.ts`).
 *
 * `activityService` keeps its own `ApiError` class for the `aborted` kind;
 * `appErrorFromApiError()` identifies it by name like the other one.
 */
export const ACTIVITY_ERROR_CODES = ['activity_list_failed'] as const;
