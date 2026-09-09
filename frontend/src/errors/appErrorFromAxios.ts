import { AppError, AppErrorCode, isAppError } from './AppError';
import { ErrorBody, readDetail, readParams, selectCode } from './errorBody';

/**
 * `appErrorFromResponse` for the axios services (TF-772 PR 4).
 *
 * Why a second constructor rather than one shared helper: the two clients hand
 * over a failure in incompatible shapes. `fetch` resolves with a `Response`
 * whose body still has to be awaited — so `appErrorFromResponse` is `async` and
 * is called at the `if (!response.ok)` site. Axios *rejects*, with the parsed
 * body already sitting on `err.response.data` — so this one is synchronous and
 * is called from a `catch`. Everything after "what does this body mean" is
 * identical, and that part lives in `errorBody.ts`.
 *
 *     try {
 *       const { data } = await apiClient.get('/api/v1/prompts');
 *       return data;
 *     } catch (err) {
 *       throw appErrorFromAxios(err, 'prompts_list_failed');
 *     }
 *
 * Three cases, all of which produce an AppError and none of which throw:
 *
 *   1. `err` is already an AppError — returned unchanged. Services layer
 *      (`promptsApi` calls into `apiClient`, whose interceptor may itself throw
 *      one), and re-wrapping would bury the specific code under a generic
 *      fallback at every level it passes.
 *   2. A response with a body — the ADR 0005 path: registered `error_code`,
 *      `detail` for the log, `error_params` for the interpolation.
 *   3. No response at all — a network failure, a CORS rejection, a timeout.
 *      There is no body and no status, so the caller's fallback code is all
 *      there is; the axios message is kept as `detail` for the log line.
 */
export function appErrorFromAxios(err: unknown, fallbackCode: AppErrorCode): AppError {
  if (isAppError(err)) return err;

  const response = axiosResponseOf(err);
  if (!response) {
    return new AppError(
      fallbackCode,
      err instanceof Error ? err.message : undefined,
    );
  }

  const body: ErrorBody =
    response.data && typeof response.data === 'object' && !Array.isArray(response.data)
      ? (response.data as ErrorBody)
      : {};

  return new AppError(
    selectCode(body, fallbackCode),
    readDetail(body),
    typeof response.status === 'number' ? response.status : undefined,
    readParams(body.error_params),
  );
}

interface AxiosLikeResponse {
  status?: unknown;
  data?: unknown;
}

/**
 * The `response` of an axios-shaped rejection, or null.
 *
 * Structural rather than `axios.isAxiosError`: this module is imported by the
 * public `errors` barrel and therefore by premium code, and a type-only shape
 * check keeps axios out of that dependency edge. It also keeps the helper
 * usable from tests that reject with a hand-built `{ response: … }` instead of
 * a real AxiosError — which is how every axios service in this codebase is
 * already tested.
 */
function axiosResponseOf(err: unknown): AxiosLikeResponse | null {
  if (!err || typeof err !== 'object' || !('response' in err)) return null;

  const response = (err as { response?: unknown }).response;
  if (!response || typeof response !== 'object') return null;

  return response as AxiosLikeResponse;
}
