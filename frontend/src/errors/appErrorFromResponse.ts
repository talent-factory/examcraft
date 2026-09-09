import { AppError, AppErrorCode } from './AppError';
import { ErrorBody, readDetail, readParams, selectCode } from './errorBody';

/**
 * Turn a failed `fetch` Response into an `AppError` carrying the backend's
 * error code (TF-772 / TF-773, ADR 0005).
 *
 * The backend answers a failure with three fields, of which only the first
 * existed before ADR 0005:
 *
 *     { "detail": "Ein Tag mit diesem Namen existiert bereits.",
 *       "error_code": "documents_tag_exists",
 *       "error_params": { "name": "Mathematik" } }
 *
 * `detail` is already prose in the user's language, and until TF-772 the
 * services threw it as `new Error(detail)` for the components to render. That
 * worked, and this helper must not lose what it did: the *reason* a request
 * failed is often more useful than the fact that it did ("four-eyes principle:
 * you cannot approve your own question" vs. "could not approve question"). So
 * the code is preferred over the text rather than over the meaning — the
 * frontend renders its own translation of the same code, which additionally
 * follows the UI language rather than whatever locale the request carried.
 *
 * Precedence:
 *
 *   1. A registered `error_code` from the body. Registered means listed in
 *      `APP_ERROR_CODES`; an unknown one is logged and ignored, because a code
 *      with no translation would render as the raw key `errors.foo_bar`.
 *   2. `fallbackCode` — the caller's per-operation code, for a body with no
 *      `error_code` at all: a framework 500, an HTML error page from a proxy,
 *      or an endpoint TF-773 has not reached yet.
 *
 * `detail` is kept on the AppError for logging only. `translateError()` never
 * renders it — that invariant is the whole reason TF-671 introduced AppError.
 *
 * Reads the body itself (once — `Response.json()` cannot be called twice), so
 * callers collapse to a single line:
 *
 *     if (!response.ok) {
 *       throw await appErrorFromResponse(response, 'documents_upload_failed');
 *     }
 *
 * The axios services use `appErrorFromAxios` instead; the two share their body
 * interpretation through `errorBody.ts`.
 */
export async function appErrorFromResponse(
  response: Response,
  fallbackCode: AppErrorCode,
): Promise<AppError> {
  const body = await readJsonBody(response);

  return new AppError(
    selectCode(body, fallbackCode),
    readDetail(body),
    response.status,
    readParams(body.error_params),
  );
}

/**
 * `.json()` rejects on an empty body, on HTML from a proxy, and on a 204 —
 * all of which are ordinary failure modes here, none of which should replace
 * the caller's error with a JSON parse error.
 */
async function readJsonBody(response: Response): Promise<ErrorBody> {
  try {
    const parsed = await response.json();
    return parsed && typeof parsed === 'object' ? (parsed as ErrorBody) : {};
  } catch {
    return {};
  }
}
