import { isAppError } from './AppError';

/**
 * Minimal structural type for i18next's `t`. Deliberately not `TFunction`:
 * i18next v25's overloaded signature is awkward to satisfy from call sites,
 * and all we need is key -> string.
 */
export type Translate = (key: string) => string;

const ERROR_KEY_PREFIX = 'errors.';

/**
 * Resolve a thrown value into a translated, user-facing message.
 *
 * Order: `errors.<code>` for an AppError whose key exists, otherwise the
 * caller's `fallbackKey`. The raw message/detail is logged, never returned —
 * that invariant is what keeps untranslated text out of the UI.
 *
 * Missing-key detection relies on i18next (and the react-i18next mock in
 * setupTests.ts) returning the key itself when it cannot resolve it. Using
 * `i18n.exists()` instead would break every component test, because the mock
 * does not provide it.
 */
// String(plainObject) degrades to "[object Object]", which throws away the
// one thing the raw-text log line exists to preserve. JSON.stringify keeps
// the actual shape when the value has one; a circular/unserializable value
// falls back to String() rather than throwing out of a logging helper.
function describeUnknown(value: unknown): string {
  try {
    const json = JSON.stringify(value);
    if (json !== undefined) return json;
  } catch {
    // fall through to String()
  }
  return String(value);
}

export function translateError(err: unknown, t: Translate, fallbackKey: string): string {
  const raw = isAppError(err)
    ? (err.detail ?? err.code)
    : err instanceof Error
      ? err.message
      : describeUnknown(err);

  if (isAppError(err)) {
    const key = `${ERROR_KEY_PREFIX}${err.code}`;
    const translated = t(key);
    if (translated !== key) {
      // Expected, fully-handled path — code resolved to a translation. Not a
      // problem to warn about; debug-level keeps it out of normal noise while
      // still leaving a trail for local debugging.
      console.debug('[i18n] AppError surfaced:', err.code, '- raw:', raw);
      return translated;
    }
    console.warn('[i18n] AppError without translation key:', key, '- raw:', raw);
    return t(fallbackKey);
  }

  console.warn('[i18n] Untyped error surfaced, using fallback key:', fallbackKey, '- raw:', raw);
  return t(fallbackKey);
}
