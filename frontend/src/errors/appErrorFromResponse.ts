import { AppError, AppErrorCode, ErrorParams, isAppErrorCode } from './AppError';

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
 */
export async function appErrorFromResponse(
  response: Response,
  fallbackCode: AppErrorCode,
): Promise<AppError> {
  const body = await readJsonBody(response);

  const code = isAppErrorCode(body.error_code) ? body.error_code : fallbackCode;
  if (body.error_code != null && !isAppErrorCode(body.error_code)) {
    // Not console.error: an unrecognised code is a survivable mismatch (the
    // user still gets the fallback sentence), but it means the backend knows
    // something this build does not — worth a breadcrumb when someone asks why
    // the message is vague.
    console.warn(
      '[i18n] Unknown error_code from backend, using fallback:',
      body.error_code,
      '->',
      fallbackCode,
    );
  }

  return new AppError(
    code,
    typeof body.detail === 'string' ? body.detail : undefined,
    response.status,
    readParams(body.error_params),
  );
}

interface ErrorBody {
  detail?: unknown;
  error_code?: unknown;
  error_params?: unknown;
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

/**
 * i18next interpolates whatever it is handed. A nested object or an array
 * would reach the UI as "[object Object]", so only the scalar entries survive;
 * a missing one leaves its `{{placeholder}}` visible, which is a far more
 * legible failure than a rendered object.
 */
function readParams(raw: unknown): ErrorParams | undefined {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return undefined;

  const params: ErrorParams = {};
  for (const [key, value] of Object.entries(raw as Record<string, unknown>)) {
    if (typeof value === 'string' || typeof value === 'number') {
      params[key] = value;
    }
  }
  return Object.keys(params).length > 0 ? params : undefined;
}
