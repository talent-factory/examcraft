import { ADMIN_ERROR_CODES } from './codes/admin';
import { AUTH_ERROR_CODES } from './codes/auth';
import { DOCUMENT_ERROR_CODES } from './codes/documents';
import { LEGACY_ERROR_CODES } from './codes/legacy';
import { RBAC_ERROR_CODES } from './codes/rbac';
import { RESERVED_ERROR_CODES } from './codes/reserved';
import { REVIEW_ERROR_CODES } from './codes/review';

/**
 * Closed registry of valid AppError codes.
 *
 * Why a registry and not a bare `string`: without it, `code` is exactly as
 * open as the `message: string` it replaces, and "the code is the contract"
 * (see AppError below) is enforced by nobody. Every domain's codes live here
 * so a typo or a code without a translation becomes a compile error instead
 * of a silent runtime fallback. `errors/__tests__/AppErrorCode.i18n.test.ts`
 * closes the other half of the loop: every code below must resolve to an
 * `errors.<code>` key in all four locales.
 *
 * The registry holds two kinds of code, and both really do exist at runtime:
 * the fallback codes a service constructs itself when the backend sends none,
 * and the backend codes `appErrorFromResponse()` is willing to adopt off the
 * wire. It is the accept-list for the second kind — an `error_code` that is not
 * registered here is logged and dropped in favour of the caller's fallback,
 * rather than reaching `translateError()` and rendering as a raw key. It is
 * still not a wishlist: a code belongs here only if some endpoint or call site
 * can actually produce it.
 *
 * The per-domain files under `codes/` are a merge-conflict measure, not
 * decoration — TF-772 has three branches appending codes at once. See
 * `codes/README.md` before adding a file.
 */
export const APP_ERROR_CODES = [
  ...LEGACY_ERROR_CODES,
  ...RESERVED_ERROR_CODES,
  ...ADMIN_ERROR_CODES,
  ...AUTH_ERROR_CODES,
  ...DOCUMENT_ERROR_CODES,
  ...RBAC_ERROR_CODES,
  ...REVIEW_ERROR_CODES,
] as const;

export type AppErrorCode = (typeof APP_ERROR_CODES)[number];

/**
 * Compile-time tripwire for the one way the registry above can silently
 * fail: if any `codes/*.ts` file forgets its `as const`, TypeScript widens
 * that array's spread element to plain `string`, and `AppErrorCode` widens
 * to `string` right along with it — with no error from `tsc`, ESLint, or
 * `AppErrorCode.i18n.test.ts` (which only checks length, not narrowness).
 * From that point on `isAppErrorCode`'s "closed accept-list" guarantee is
 * fiction: any string is assignable as a code.
 *
 * `AssertNoWideningToString<AppErrorCode>` collapses to `never` exactly when
 * that happens (`string extends AppErrorCode` only holds once `AppErrorCode`
 * itself IS `string`), and assigning `true` to `never` fails to compile —
 * turning the widening into a build break at the next `codes/` file TF-772
 * adds, instead of a silent, codebase-wide hole.
 */
type AssertNoWideningToString<T extends string> = string extends T ? never : true;
const _appErrorCodeStaysClosed: AssertNoWideningToString<AppErrorCode> = true;
void _appErrorCodeStaysClosed;

/**
 * Interpolation values for an error message, carried from the backend's
 * `error_params` (ADR 0005) into i18next.
 *
 * The two systems spell interpolation differently — the backend writes
 * `%{name}`, i18next writes `{{name}}` — so a text copied from
 * `core/backend/locales/` must be rewritten on the way into the frontend
 * locales. The *values* need no conversion, which is why this is a plain
 * record and not a wrapper type.
 */
export type ErrorParams = Record<string, string | number>;

/**
 * Application error carrying a stable, translatable code.
 *
 * Why: services used to throw `new Error('English text')` and components piped
 * `err.message` straight into the UI, which made every language switch a no-op
 * for error messages (TF-671). The code — not the text — is the contract now,
 * and `AppErrorCode` makes that a type-checked contract, not just a naming
 * convention: `new AppError('typo.doesNotExist', ...)` fails to compile.
 * `detail` keeps the raw backend/system text for logging; it must never be
 * rendered (see translateError). Not to be confused with the `apiDetail()`
 * helper (apiDetail.ts), which reads a different `detail` field off a plain
 * axios error and IS safe to render for the one API that answers in German.
 */
export class AppError extends Error {
  constructor(
    readonly code: AppErrorCode,
    readonly detail?: string,
    readonly status?: number,
    readonly params?: ErrorParams,
  ) {
    super(detail ?? code);
    this.name = 'AppError';
    // Required when targeting ES5-ish output so `instanceof` keeps working.
    // `new.target.prototype`, not `AppError.prototype`: a subclass
    // (DocumentFetchError) would otherwise have its own prototype overwritten
    // here and stop being an instance of itself.
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export function isAppError(e: unknown): e is AppError {
  return e instanceof AppError;
}

// Set, not Array.includes: `appErrorFromResponse` calls this on every failed
// response, and the registry grows with every TF-772 branch.
const CODE_SET: ReadonlySet<string> = new Set<string>(APP_ERROR_CODES);

/**
 * Is this string a code the frontend knows how to translate?
 *
 * The guard exists because `error_code` arrives as untyped JSON from the
 * network. Anything unrecognised — a code from a newer backend, a typo, a
 * proxy's error page — must not become an `AppErrorCode` by assertion, or the
 * compile-time guarantee behind `APP_ERROR_CODES` would be worth nothing.
 */
export function isAppErrorCode(value: unknown): value is AppErrorCode {
  return typeof value === 'string' && CODE_SET.has(value);
}
