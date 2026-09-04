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
 * Add a code here when — and only when — a call site actually constructs
 * `new AppError(code, ...)`. This list is not a wishlist of translatable
 * error states; it is the exhaustive set that exists at runtime.
 */
export const APP_ERROR_CODES = [
  'rag.examGenerationFailed',
  'rag.connectionLost',
  'rag.statusFailed',
  'rag.retryFailed',
  'rag.activeTasksFailed',
  'rag.taskResultFailed',
  'rag.contextRetrievalFailed',
  'rag.questionTypesFailed',
  'rag.healthCheckFailed',
  'rag.contextPreviewFailed',
  'rag.notAvailableInCore',
  'help.statusFailed',
  'help.onboardingStatusFailed',
  'help.onboardingStepFailed',
  'help.onboardingSkipFailed',
  'help.contextHintFailed',
  'help.hintDismissFailed',
  'help.messageFailed',
  'help.feedbackFailed',
  'features.loadFailed',
  'chat.downloadFailed',
  'compliance.loadFailed',
] as const;

export type AppErrorCode = (typeof APP_ERROR_CODES)[number];

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
  ) {
    super(detail ?? code);
    this.name = 'AppError';
    // Required when targeting ES5-ish output so `instanceof` keeps working.
    Object.setPrototypeOf(this, AppError.prototype);
  }
}

export function isAppError(e: unknown): e is AppError {
  return e instanceof AppError;
}
