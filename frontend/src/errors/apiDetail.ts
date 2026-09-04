/**
 * Read a backend-provided `detail` string from an axios-shaped error.
 *
 * Not to be confused with `AppError.detail` — a different field, on a
 * different error shape, with an opposite rendering rule: `AppError.detail`
 * is raw system/backend text meant only for logging (see AppError.ts) and
 * must never reach the UI, while what this function returns is raw text that
 * IS meant to be rendered, because it already answers in the user's language.
 *
 * Use this ONLY for endpoints that answer in the user's language. Today that
 * means the Tags API (core/backend/api/tags.py), which returns German prose
 * like "Tag wird noch von Fragen verwendet." — text that is strictly more
 * useful than a generic translated fallback. It is scoped narrower than "the
 * Tags API" in practice: `TagAutocomplete.tsx` hits the same endpoints but
 * deliberately shows a generic translated message instead, because its
 * compact inline UI has no room for a full backend sentence. This helper is
 * for the two admin surfaces (`TagCreateForm`, `TagSettingsPage`) where the
 * specific reason is worth the space.
 *
 * For every other endpoint use translateError() instead: most of the backend
 * still answers in English, and surfacing that raw is exactly what TF-671
 * removed. This helper becomes obsolete once the backend sends error codes
 * instead of prose.
 */
export function apiDetail(err: unknown): string | null {
  if (!err || typeof err !== 'object' || !('response' in err)) {
    return null;
  }

  const axiosError = err as { response?: { data?: { detail?: unknown } } };
  const detail = axiosError.response?.data?.detail;

  if (typeof detail !== 'string') {
    return null;
  }

  const trimmed = detail.trim();
  return trimmed ? trimmed : null;
}
