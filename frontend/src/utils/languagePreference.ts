/**
 * Who owns the UI language.
 *
 * Two stores hold it and neither was the owner: `examcraft_language` (i18next's
 * own detector cache, written on every changeLanguage) and
 * `users.preferred_language` on the account. Whoever wrote last won, and that
 * was the server — AuthContext re-applies the account value on every profile
 * load. So a failed save used to drop the user back into the language they had
 * just left, with no message, and a reload would have done it again anyway.
 *
 * The rule now:
 *   - the account value is the CROSS-DEVICE DEFAULT, applied when this browser
 *     has no unsaved choice of its own;
 *   - an explicit choice made here wins for this browser until it reaches the
 *     account.
 *
 * This module holds the marker for "chosen here, not saved yet". It exists only
 * while the two disagree: a successful save clears it, so the account value
 * takes over again and a language set on another device still arrives here.
 */

import { SupportedLanguage } from '../types/auth';

const PENDING_KEY = 'examcraft_language_pending';

const SUPPORTED: readonly string[] = ['de', 'en', 'fr', 'it'];

function isSupported(value: string | null): value is SupportedLanguage {
  return value !== null && SUPPORTED.includes(value);
}

/**
 * The language chosen in this browser that the account does not know about yet,
 * or null. An unreadable/absent store means "no pending choice" — the account
 * value then applies, which is the safe direction.
 */
export function getPendingLanguage(): SupportedLanguage | null {
  try {
    const stored = window.localStorage.getItem(PENDING_KEY);
    return isSupported(stored) ? stored : null;
  } catch {
    return null;
  }
}

export function setPendingLanguage(language: string): void {
  try {
    window.localStorage.setItem(PENDING_KEY, language);
  } catch (err) {
    // private mode / quota: the language still applies for this page load,
    // but a reload right after would silently revert to the account value
    // with no trace anywhere that this happened — so at least log it.
    console.warn('Failed to persist the pending language choice:', err);
  }
}

export function clearPendingLanguage(): void {
  try {
    window.localStorage.removeItem(PENDING_KEY);
  } catch (err) {
    // Nothing to protect if we cannot write, but still worth a trace: an
    // account save that succeeded server-side while this fails would leave a
    // stale pending marker shadowing it locally.
    console.warn('Failed to clear the pending language choice:', err);
  }
}

/**
 * The language to apply when a profile arrives from the server.
 *
 * Used at every place that reacts to a loaded profile, so the account value can
 * never silently overwrite a choice this browser has not managed to save.
 */
export function resolveLanguageOnProfileLoad(
  accountLanguage?: string | null
): string | null {
  return getPendingLanguage() ?? (accountLanguage || null);
}
