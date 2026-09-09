import { AppErrorCode, ErrorParams, isAppErrorCode } from './AppError';

/**
 * The three fields ADR 0005 puts on a failed response, before any of them has
 * been validated. Every property is `unknown` on purpose: this is JSON off the
 * network, and the whole job of this module is to refuse to trust it.
 */
export interface ErrorBody {
  detail?: unknown;
  error_code?: unknown;
  error_params?: unknown;
}

/**
 * Body reading shared by the two `AppError` constructors (TF-772 PR 4).
 *
 * `appErrorFromResponse` (PR 2) handles the `fetch` services; `appErrorFromAxios`
 * handles the axios ones (`promptsApi` in both tiers, everything else built on
 * `api/apiClient.ts`). The two differ only in where the body comes from — a
 * `Response` that must be awaited versus an object already hanging off the
 * rejected error — so the parts that decide *what the body means* live here
 * rather than being written twice. Two copies of `readParams` would be two
 * places for the scalar filter to drift.
 */

/**
 * Pick the code to carry: a registered `error_code` from the body, else the
 * caller's per-operation fallback.
 *
 * Registered means listed in `APP_ERROR_CODES`. An unrecognised code is logged
 * and dropped rather than asserted into an `AppErrorCode`, because a code with
 * no translation renders as the raw key `errors.foo_bar` on screen.
 */
export function selectCode(body: ErrorBody, fallbackCode: AppErrorCode): AppErrorCode {
  if (isAppErrorCode(body.error_code)) return body.error_code;

  if (body.error_code != null) {
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
  return fallbackCode;
}

/**
 * i18next interpolates whatever it is handed. A nested object or an array
 * would reach the UI as "[object Object]", so only the scalar entries survive;
 * a missing one leaves its `{{placeholder}}` visible, which is a far more
 * legible failure than a rendered object.
 */
export function readParams(raw: unknown): ErrorParams | undefined {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return undefined;

  const params: ErrorParams = {};
  for (const [key, value] of Object.entries(raw as Record<string, unknown>)) {
    if (typeof value === 'string' || typeof value === 'number') {
      params[key] = value;
    }
  }
  return Object.keys(params).length > 0 ? params : undefined;
}

/** `detail` only when it is the string ADR 0005 promises; never a stringified object. */
export function readDetail(body: ErrorBody): string | undefined {
  return typeof body.detail === 'string' ? body.detail : undefined;
}
