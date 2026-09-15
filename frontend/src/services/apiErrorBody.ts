/**
 * Body reading for the `ApiError` family (TF-772 PR 7).
 *
 * Seven services build an `ApiError` from a failed response, and until PR 7
 * each carried its own parser. Only `httpClient` copied the backend's
 * `error_code` / `error_params` (ADR 0005) onto the error; the other six
 * dropped them while parsing, so `appErrorFromApiError()` never saw a code and
 * every backend message collapsed to the caller's fallback. The copies had
 * drifted in exactly the way copies do: the field was added to one and not
 * the other five.
 *
 * So the parts that decide what a body *means* live here once:
 *
 *   - `readErrorEnvelope` pulls the two ADR 0005 fields off an already-parsed
 *     body. The four services that parse with `response.json()` themselves
 *     (grading schemes, statistics, grade export, Moodle push) use only this.
 *   - `readErrorBody` reads the whole response for the services that parse
 *     text-first (`submissionsService`, `httpClient`, `activityService`).
 *
 * Deliberately free of the `ApiError` class: `activityService` has its own
 * `ApiError` (with an extra `aborted` kind), and both classes consume this.
 *
 * The fields stay untyped (`errorParams: unknown`) on purpose — validating
 * them is `errors/errorBody.ts`'s job when `appErrorFromApiError()` turns the
 * `ApiError` into an `AppError`. Doing it twice would be two places for the
 * scalar filter to drift.
 */

export interface ErrorEnvelope {
  /** The backend's `error_code`, when the body carried a string one. */
  errorCode?: string;
  /** The backend's `error_params`, unvalidated. */
  errorParams?: unknown;
}

export interface ErrorBodyParts extends ErrorEnvelope {
  /** Log-only text; never rendered (see `translateError`). */
  message: string;
  detail: unknown;
  issues: string[];
}

/**
 * The ADR 0005 sibling fields of a parsed error body. Anything that is not a
 * plain object — `null`, an array, a string from a proxy — carries no envelope.
 */
export function readErrorEnvelope(raw: unknown): ErrorEnvelope {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {};
  const body = raw as Record<string, unknown>;
  return {
    errorCode: typeof body.error_code === 'string' ? body.error_code : undefined,
    errorParams: body.error_params,
  };
}

/**
 * Read a failed response once, as text, so a non-JSON body (HTML proxy error
 * page, plain 502, empty 401) is observable to the developer rather than
 * swallowed by an opaque `${status} ${statusText}` message.
 *
 * `source` only prefixes the console warning, so a log line still says which
 * service saw the broken body.
 */
export async function readErrorBody(
  response: Response,
  source: string,
): Promise<ErrorBodyParts> {
  const statusMessage = `${response.status} ${response.statusText}`;

  let bodyText = '';
  try {
    bodyText = await response.text();
  } catch {
    return { message: statusMessage, detail: null, issues: [] };
  }

  let raw: unknown = null;
  if (bodyText) {
    try {
      raw = JSON.parse(bodyText);
    } catch {
      console.warn(
        `${source}: non-JSON ${response.status} response`,
        bodyText.slice(0, 500),
      );
      return { message: statusMessage, detail: bodyText, issues: [] };
    }
  }

  const envelope = readErrorEnvelope(raw);

  if (raw && typeof raw === 'object' && 'detail' in raw) {
    const detail = (raw as { detail: unknown }).detail;
    // Tier-Quota 402 + Validation 422 carry structured detail objects.
    if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
      const obj = detail as { message?: unknown; issues?: unknown };
      const message = typeof obj.message === 'string' ? obj.message : statusMessage;
      const issues = Array.isArray(obj.issues)
        ? obj.issues.filter((i): i is string => typeof i === 'string')
        : [];
      return { message, detail, issues, ...envelope };
    }
    return { message: String(detail), detail, issues: [], ...envelope };
  }
  return { message: statusMessage, detail: raw, issues: [], ...envelope };
}
