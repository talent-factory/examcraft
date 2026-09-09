/**
 * The two codes `RESERVED_ERROR_CODES` in `core/backend/errors.py` names.
 *
 * They come from the framework-level handlers in `main.py` — a Pydantic
 * validation failure and the catch-all 500 — and are never thrown by endpoint
 * code, which is why no domain owns them. PR 1 created their translations
 * (`errors.internal_error`, `errors.validation_error`) in all four locales for
 * exactly that reason; registering them here is the other half, and it only
 * became necessary once `appErrorFromResponse()` started accepting codes off
 * the wire: without them a 422 would fall back to the caller's generic
 * "operation failed" instead of "check your input".
 */
export const RESERVED_ERROR_CODES = ['internal_error', 'validation_error'] as const;
