/**
 * Error code for `ActivityService`, router `core/backend/api/activity.py`.
 *
 * Fallback-only, and deliberately still so after TF-773 PR 2d gave the
 * router's two throw sites codes. Neither belongs on a screen:
 *
 * - `activity_unknown_type` (422) fires when the `types` CSV holds a token the
 *   backend does not know. `Aktivitaeten.tsx` builds that CSV itself from a
 *   fixed list, so reaching it means the frontend has a bug — and «Unbekannter
 *   Activity-Type: exam_frobnicated» is a sentence for the console, not for a
 *   user. PR 2d still gave it a real code and a real translation, because the
 *   code is the API contract even where the UI declines to render it; the
 *   unknown and supported token lists ride along in `error_params`.
 * - `activity_scope_institution_forbidden` (403) is a contract assertion that
 *   is unreachable while `User.institution_id` stays NOT NULL, and stays
 *   English under the TF-295 exemption. It has no `errors.*` key by design —
 *   it is a passthrough code, so registering it would put a key under the i18n
 *   guard that no locale file can satisfy.
 *
 * Both therefore land on `activity_list_failed`, the operation fallback, which
 * is the right sentence for a user in both cases.
 *
 * `activityService` keeps its own `ApiError` class for the `aborted` kind;
 * `appErrorFromApiError()` identifies it by name like the other one.
 */
export const ACTIVITY_ERROR_CODES = ['activity_list_failed'] as const;
