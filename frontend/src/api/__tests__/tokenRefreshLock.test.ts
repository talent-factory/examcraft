import {
  withTokenRefreshLock,
  TOKEN_REFRESH_LOCK_NAME,
  REFRESH_LEAD_MS,
  RefreshTrigger,
} from '../tokenRefreshLock';

const ACCESS_TOKEN_KEY = 'examcraft_access_token';

/** JWT-shaped token that expires in `lifetimeMs`. */
function makeToken(lifetimeMs: number): string {
  const exp = Math.floor((Date.now() + lifetimeMs) / 1000);
  const payload = btoa(JSON.stringify({ exp }))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
  return `eyJhbGciOiJIUzI1NiJ9.${payload}.sig`;
}

/** A token that has just come due for its proactive refresh. */
const dueToken = () => makeToken(REFRESH_LEAD_MS);

/** A token somebody else rotated moments ago — a full lifetime ahead. */
const freshToken = () => makeToken(30 * 60 * 1000);

/**
 * Minimal Web Locks stand-in: serializes callbacks per lock name, the one
 * property `withTokenRefreshLock` relies on. jsdom ships no LockManager.
 */
function installLockManagerMock(): jest.Mock {
  const queues = new Map<string, Promise<unknown>>();

  const request = jest.fn(async (name: string, callback: () => Promise<unknown>) => {
    const previous = queues.get(name) ?? Promise.resolve();
    const run = previous.then(() => callback(), () => callback());
    // Swallow rejections in the queue only — `run` itself still rejects for
    // the caller, so a failing holder must not block the next waiter.
    queues.set(name, run.then(() => undefined, () => undefined));
    return run;
  });

  Object.defineProperty(navigator, 'locks', {
    value: { request },
    configurable: true,
    writable: true,
  });

  return request;
}

function removeLockManagerMock(): void {
  Object.defineProperty(navigator, 'locks', {
    value: undefined,
    configurable: true,
    writable: true,
  });
}

describe('withTokenRefreshLock', () => {
  afterEach(() => {
    localStorage.clear();
    removeLockManagerMock();
    jest.clearAllMocks();
  });

  it('rotates while holding the named lock when no other tab interfered', async () => {
    const request = installLockManagerMock();
    localStorage.setItem(ACCESS_TOKEN_KEY, 'access-1');

    const rotate = jest.fn().mockResolvedValue(undefined);
    const adopt = jest.fn().mockResolvedValue(undefined);

    await withTokenRefreshLock(rotate, adopt);

    expect(request).toHaveBeenCalledWith(TOKEN_REFRESH_LOCK_NAME, expect.any(Function));
    expect(rotate).toHaveBeenCalledTimes(1);
    expect(adopt).not.toHaveBeenCalled();
  });

  it('lets only one of two concurrent tabs rotate; the other adopts the new token', async () => {
    installLockManagerMock();
    localStorage.setItem(ACCESS_TOKEN_KEY, 'access-1');

    const rotate = jest.fn(async () => {
      await Promise.resolve();
      localStorage.setItem(ACCESS_TOKEN_KEY, 'access-2');
    });
    const adopt = jest.fn().mockResolvedValue(undefined);

    await Promise.all([
      withTokenRefreshLock(rotate, adopt),
      withTokenRefreshLock(rotate, adopt),
    ]);

    // This is the TF-607 regression: without the lock both callers would send
    // the same refresh token and the backend would invalidate the loser.
    expect(rotate).toHaveBeenCalledTimes(1);
    expect(adopt).toHaveBeenCalledTimes(1);
    expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBe('access-2');
  });

  it('still rotates when the access token is unchanged, even under contention', async () => {
    installLockManagerMock();
    localStorage.setItem(ACCESS_TOKEN_KEY, 'access-1');

    // A 401 on a token that is not expired must still trigger a real refresh —
    // "unchanged" is the signal to rotate, not to adopt.
    const rotate = jest.fn().mockResolvedValue(undefined);
    const adopt = jest.fn().mockResolvedValue(undefined);

    await Promise.all([
      withTokenRefreshLock(rotate, adopt),
      withTokenRefreshLock(rotate, adopt),
    ]);

    expect(rotate).toHaveBeenCalledTimes(2);
    expect(adopt).not.toHaveBeenCalled();
  });

  it('falls back to a plain rotate when the browser has no Web Locks', async () => {
    removeLockManagerMock();
    localStorage.setItem(ACCESS_TOKEN_KEY, 'access-1');

    const rotate = jest.fn().mockResolvedValue(undefined);
    const adopt = jest.fn().mockResolvedValue(undefined);

    await withTokenRefreshLock(rotate, adopt);

    expect(rotate).toHaveBeenCalledTimes(1);
    expect(adopt).not.toHaveBeenCalled();
  });

  describe('late-firing timer (TF-607 follow-up)', () => {
    // Safari throttles timers in background tabs by hundreds of milliseconds.
    // Such a tab enters the lock *after* the winner finished, so it reads the
    // already-rotated token as its own baseline and the changed-token check
    // cannot see the rotation.

    it('adopts when the stored token is not due for refresh yet', async () => {
      installLockManagerMock();
      localStorage.setItem(ACCESS_TOKEN_KEY, freshToken());

      const rotate = jest.fn().mockResolvedValue(undefined);
      const adopt = jest.fn().mockResolvedValue(undefined);

      await withTokenRefreshLock(rotate, adopt, 'proactive-timer');

      expect(adopt).toHaveBeenCalledTimes(1);
      expect(rotate).not.toHaveBeenCalled();
    });

    it('rotates when the stored token really has come due', async () => {
      installLockManagerMock();
      localStorage.setItem(ACCESS_TOKEN_KEY, dueToken());

      const rotate = jest.fn().mockResolvedValue(undefined);
      const adopt = jest.fn().mockResolvedValue(undefined);

      await withTokenRefreshLock(rotate, adopt, 'proactive-timer');

      expect(rotate).toHaveBeenCalledTimes(1);
      expect(adopt).not.toHaveBeenCalled();
    });

    it.each<RefreshTrigger>(['axios-401', 'fetch-401', 'httpClient-401'])(
      'still rotates on %s even though the stored token looks fresh',
      async (trigger) => {
        installLockManagerMock();
        // The server rejected this token, so its `exp` proves nothing — the
        // session may have been revoked. Adopting here would loop: retry,
        // 401, adopt, retry.
        localStorage.setItem(ACCESS_TOKEN_KEY, freshToken());

        const rotate = jest.fn().mockResolvedValue(undefined);
        const adopt = jest.fn().mockResolvedValue(undefined);

        await withTokenRefreshLock(rotate, adopt, trigger);

        expect(rotate).toHaveBeenCalledTimes(1);
        expect(adopt).not.toHaveBeenCalled();
      },
    );

    it('rotates for an unrecognised trigger even though the token looks fresh', async () => {
      installLockManagerMock();
      localStorage.setItem(ACCESS_TOKEN_KEY, freshToken());

      const rotate = jest.fn().mockResolvedValue(undefined);
      const adopt = jest.fn().mockResolvedValue(undefined);

      // Remaining lifetime only means something for scheduled refreshes. A
      // future caller that forgets to name itself must land on the safe side,
      // because wrongly adopting on a reactive path loops forever. Cast past
      // the RefreshTrigger union deliberately: this simulates a call site
      // that bypasses the type (e.g. a raw string slipping through an `as
      // any`), which is exactly the failure mode PROACTIVE_TRIGGERS' allow-
      // list is meant to fail safe against.
      await withTokenRefreshLock(rotate, adopt, 'some-future-caller' as RefreshTrigger);

      expect(rotate).toHaveBeenCalledTimes(1);
      expect(adopt).not.toHaveBeenCalled();
    });

    it('rotates when the stored token cannot be parsed', async () => {
      installLockManagerMock();
      localStorage.setItem(ACCESS_TOKEN_KEY, 'not-a-jwt');

      const rotate = jest.fn().mockResolvedValue(undefined);
      const adopt = jest.fn().mockResolvedValue(undefined);

      await withTokenRefreshLock(rotate, adopt, 'proactive-timer');

      expect(rotate).toHaveBeenCalledTimes(1);
      expect(adopt).not.toHaveBeenCalled();
    });
  });

  it('propagates rotate failures to the caller', async () => {
    installLockManagerMock();
    localStorage.setItem(ACCESS_TOKEN_KEY, 'access-1');

    const rotate = jest.fn().mockRejectedValue(new Error('refresh failed'));

    await expect(
      withTokenRefreshLock(rotate, jest.fn().mockResolvedValue(undefined)),
    ).rejects.toThrow('refresh failed');
  });

  it('releases the lock after a failure so the next caller still runs', async () => {
    installLockManagerMock();
    localStorage.setItem(ACCESS_TOKEN_KEY, 'access-1');

    const failing = jest.fn().mockRejectedValue(new Error('refresh failed'));
    const succeeding = jest.fn().mockResolvedValue(undefined);

    await expect(
      withTokenRefreshLock(failing, jest.fn().mockResolvedValue(undefined)),
    ).rejects.toThrow('refresh failed');
    await withTokenRefreshLock(succeeding, jest.fn().mockResolvedValue(undefined));

    expect(succeeding).toHaveBeenCalledTimes(1);
  });

  it('propagates adopt failures to the caller without disturbing the winner', async () => {
    installLockManagerMock();
    localStorage.setItem(ACCESS_TOKEN_KEY, 'access-1');

    // Same setup as "lets only one of two concurrent tabs rotate": the first
    // caller through the lock rotates and changes the stored token, which is
    // exactly what makes the second caller's baseline look stale and take
    // the adopt branch. Here that adopt fails — e.g. the tokens vanished
    // (another tab logged out) between the lock granting "adopt" and the
    // callback actually running.
    const rotate = jest.fn(async () => {
      await Promise.resolve();
      localStorage.setItem(ACCESS_TOKEN_KEY, 'access-2');
    });
    const failingAdopt = jest.fn().mockRejectedValue(new Error('no stored tokens to adopt'));

    const winnerPromise = withTokenRefreshLock(rotate, jest.fn().mockResolvedValue(undefined));
    const loserPromise = withTokenRefreshLock(rotate, failingAdopt);

    await expect(winnerPromise).resolves.toBeUndefined();
    await expect(loserPromise).rejects.toThrow('no stored tokens to adopt');
    expect(rotate).toHaveBeenCalledTimes(1);
    expect(failingAdopt).toHaveBeenCalledTimes(1);
  });

  it('gives up on a stuck rotate and releases the lock instead of wedging every other tab', async () => {
    jest.useFakeTimers();
    try {
      installLockManagerMock();
      localStorage.setItem(ACCESS_TOKEN_KEY, 'access-1');

      // Simulates a hung fetch: a real refresh call that never settles
      // because the connection stalled or the tab was frozen/bfcached.
      const stuckRotate = jest.fn(() => new Promise<void>(() => {}));
      const promise = withTokenRefreshLock(stuckRotate, jest.fn().mockResolvedValue(undefined));

      // Jest 27's fake timers don't fake native Promise microtasks, so
      // `withTimeout`'s setTimeout is only registered after the lock mock's
      // own `.then()` chain runs. Interleave real microtask flushes with
      // simulated time in small steps rather than one big jump, so this
      // doesn't depend on guessing exact tick counts — 30 steps of 1s
      // simulated time comfortably clears both the queueing delay and the
      // lock-hold timeout, whatever its exact value.
      for (let i = 0; i < 30; i++) {
        await Promise.resolve();
        jest.advanceTimersByTime(1000);
      }

      await expect(promise).rejects.toThrow(/timed out/i);

      // The lock must actually have been released — a second, healthy
      // caller has to be able to proceed right after, not queue forever
      // behind the stuck first one.
      const healthyRotate = jest.fn().mockResolvedValue(undefined);
      await withTokenRefreshLock(healthyRotate, jest.fn().mockResolvedValue(undefined));
      expect(healthyRotate).toHaveBeenCalledTimes(1);
    } finally {
      jest.useRealTimers();
    }
  });
});
