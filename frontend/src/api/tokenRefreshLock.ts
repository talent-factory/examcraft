/**
 * Cross-tab coordination for the rotating refresh token (TF-607).
 *
 * The backend rotates both JTIs onto a single session row on every refresh,
 * so the previous refresh token dies immediately. Every tab schedules its
 * proactive refresh from the `exp` of the *same* stored access token, which
 * means all open tabs wake up within milliseconds of each other and would
 * each send that one refresh token. Exactly one wins; the losers get a 401
 * and tear the session down.
 *
 * Web Locks turn that stampede into a queue: the first tab rotates, the
 * others wait and then find a changed access token in localStorage, which is
 * the signal that someone else already did the work and they only need to
 * adopt the result.
 */

export const ACCESS_TOKEN_KEY = 'examcraft_access_token';

export const TOKEN_REFRESH_LOCK_NAME = 'examcraft-token-refresh';

/**
 * How long before expiry the proactive refresh fires. Single source of truth —
 * AuthContext schedules its timer from this, and the lock uses it to recognise
 * a token that is not due yet.
 */
export const REFRESH_LEAD_MS = 2 * 60 * 1000;

/**
 * Headroom above REFRESH_LEAD_MS before a stored token counts as "somebody
 * else's fresh rotation". Safari throttles timers in background tabs by
 * hundreds of milliseconds, so a timer meant to fire right at the lead
 * window can enter the lock noticeably late; without this margin that delay
 * alone could decide between rotating and adopting.
 */
const FRESHNESS_MARGIN_MS = 30 * 1000;

/**
 * Safety bound on how long the cross-tab lock may be held. If `rotate` (or
 * `adopt`) hangs — a stalled fetch, a frozen/bfcached tab — we give up on it
 * and let the lock release rather than wedging every other tab's refresh
 * attempts indefinitely. Throwing inside the Web Locks callback rejects and
 * releases the lock per spec even though the underlying call may still be
 * running; its eventual result is simply discarded. Generous relative to the
 * 5s inner timeouts callers already use around their own network calls.
 */
const LOCK_HOLD_TIMEOUT_MS = 20 * 1000;

/**
 * Triggers where an incorrectly-adopted token fails safe: nobody has claimed
 * the token is invalid, so a token with plenty of life left is very likely
 * someone else's fresh rotation, and being wrong just costs one extra
 * profile fetch. `proactive-timer` fires on a schedule; `mount` fires from a
 * rejection handler but the worst case of misjudging it is the same.
 *
 * Listed as an allow-list on purpose. Anything reactive — a 401 from the
 * server — must rotate, because a revoked session still carries a perfectly
 * healthy-looking `exp`, and adopting there would loop: retry, 401, adopt,
 * retry. An unrecognised trigger therefore falls on the rotate side.
 */
const PROACTIVE_TRIGGERS: ReadonlySet<RefreshTrigger> = new Set(['proactive-timer', 'mount']);

/**
 * Every distinct reason `withTokenRefreshLock` gets called. Kept as a closed
 * union (rather than `string`) so a new call site — or a typo in an existing
 * one — is a compile error instead of silently missing PROACTIVE_TRIGGERS
 * and always falling on the safe-but-wasteful "rotate" side.
 */
export type RefreshTrigger =
  | 'proactive-timer'
  | 'mount'
  | 'axios-401'
  | 'fetch-401'
  | 'httpClient-401'
  | 'unknown';

/** Milliseconds until the token expires, or null if it cannot be read. */
export function getTokenRemainingMs(token: string): number | null {
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const { exp } = JSON.parse(atob(base64));
    if (typeof exp !== 'number') return null;
    return exp * 1000 - Date.now();
  } catch (err) {
    console.error('[TokenRefreshLock] Failed to parse JWT:', err);
    return null;
  }
}

/**
 * Race `promise` against a timeout. If the timeout wins, `promise` is left
 * running — its `.catch` is pre-armed so a later rejection does not surface
 * as an unhandled rejection — and its eventual result is discarded.
 */
async function withTimeout<T>(promise: Promise<T>, ms: number, message: string): Promise<T> {
  promise.catch(() => {});
  let timer: ReturnType<typeof setTimeout>;
  try {
    return await Promise.race([
      promise,
      new Promise<never>((_, reject) => {
        timer = setTimeout(() => reject(new Error(message)), ms);
      }),
    ]);
  } finally {
    clearTimeout(timer!);
  }
}

/**
 * Run `rotate` under the cross-tab refresh lock.
 *
 * If another tab rotated the tokens while we waited for the lock, `adopt` is
 * called instead — the fresh tokens are already in localStorage and rotating
 * again would needlessly burn the one we just received. `adopt` signals its
 * own failure by throwing, the same contract `rotate` already has.
 *
 * For reactive triggers (a 401 from the server), an unchanged access token
 * always means rotate, never adopt: a 401 on a token that has not expired
 * yet still needs a real refresh. For triggers in PROACTIVE_TRIGGERS, an
 * unchanged-but-fresh-looking token can still mean adopt — see the
 * remaining-lifetime check below.
 *
 * Browsers without Web Locks (Safari < 15.4) fall back to rotating directly,
 * i.e. the pre-TF-607 behaviour.
 */
export async function withTokenRefreshLock(
  rotate: () => Promise<void>,
  adopt: () => Promise<void>,
  trigger: RefreshTrigger = 'unknown',
): Promise<void> {
  const locks = navigator.locks;

  if (!locks || typeof locks.request !== 'function') {
    await rotate();
    return;
  }

  const tokenBeforeLock = localStorage.getItem(ACCESS_TOKEN_KEY);

  await locks.request(TOKEN_REFRESH_LOCK_NAME, async () => {
    const tokenInsideLock = localStorage.getItem(ACCESS_TOKEN_KEY);

    if (tokenInsideLock && tokenInsideLock !== tokenBeforeLock) {
      await withTimeout(adopt(), LOCK_HOLD_TIMEOUT_MS, 'Timed out adopting another tab\'s tokens');
      return;
    }

    // The comparison above only catches tabs that were already queued when the
    // winner rotated. A timer firing late — Safari throttles background tabs by
    // hundreds of milliseconds — enters the lock afterwards and reads the
    // *new* token as its own baseline, so nothing looks changed. Remaining
    // lifetime still gives it away: a token this fresh cannot be the one this
    // tab set out to replace.
    if (tokenInsideLock && PROACTIVE_TRIGGERS.has(trigger)) {
      const remaining = getTokenRemainingMs(tokenInsideLock);
      if (remaining !== null && remaining > REFRESH_LEAD_MS + FRESHNESS_MARGIN_MS) {
        await withTimeout(adopt(), LOCK_HOLD_TIMEOUT_MS, 'Timed out adopting another tab\'s tokens');
        return;
      }
    }

    await withTimeout(rotate(), LOCK_HOLD_TIMEOUT_MS, 'Timed out rotating the token while holding the cross-tab lock');
  });
}
