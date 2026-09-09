import { AppError, AppErrorCode, isAppError } from './AppError';
import { readParams, selectCode } from './errorBody';

/**
 * Third and last constructor: `ApiError` → `AppError` (TF-772 PR 4).
 *
 * `appErrorFromResponse` reads a `fetch` Response, `appErrorFromAxios` reads an
 * axios rejection — and this one reads what `httpClient.ensureOk` already
 * produced. It exists because `httpClient` is shared: `orgUnitsService`,
 * `studentClassesService`, `studentsService`, `auditService`, `rolesService`,
 * `moodleConnectionsService` and the two ops services all go through it, and
 * converting the helper itself would change the error type under seven
 * services that are not part of this package. So the conversion happens one
 * service up, where the operation is known and the blast radius is one file.
 *
 * `httpClient` carries `error_code` / `error_params` onto the `ApiError`
 * (TF-772) precisely so this function can prefer them over the fallback,
 * exactly like the other two constructors. TF-773 has since wired
 * `org_units.py` onto `api_error()`, so `orgUnitsService`'s calls already send
 * a real code where one exists (see `errors/codes/orgUnits.ts`); the other six
 * services this constructor also serves migrate onto specific codes as their
 * own routers do.
 *
 * `ApiError.message` survives as `AppError.detail` — log-only, never rendered.
 * That single move is the whole point: the text is still there when someone
 * reads the console, and gone from the screen.
 */
export function appErrorFromApiError(err: unknown, fallbackCode: AppErrorCode): AppError {
  if (isAppError(err)) return err;

  const api = apiErrorShape(err);
  if (!api) {
    return new AppError(fallbackCode, err instanceof Error ? err.message : undefined);
  }

  return new AppError(
    selectCode({ error_code: api.errorCode }, fallbackCode),
    api.message,
    // `httpClient` uses status 0 for a network failure; there is no HTTP status
    // to report, and 0 would read as one. `apiErrorShape` identifies its input
    // structurally (see below), so `status` is re-validated here the same way
    // `appErrorFromAxios` validates `response.status` — not assumed to be a
    // number just because the shape matched.
    typeof api.status === 'number' && api.status !== 0 ? api.status : undefined,
    readParams(api.errorParams),
  );
}

interface ApiErrorShape {
  message?: string;
  status?: unknown;
  errorCode?: string;
  errorParams?: unknown;
}

/**
 * Structural again, not `instanceof ApiError`: importing the class here would
 * point `errors/` at `services/`, and this module is part of the barrel that
 * `services/` imports from. `name === 'ApiError'` is set in that constructor
 * and is the one field that identifies it.
 */
function apiErrorShape(err: unknown): ApiErrorShape | null {
  if (!(err instanceof Error) || err.name !== 'ApiError') return null;
  return err as unknown as ApiErrorShape;
}
