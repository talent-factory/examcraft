import React from 'react';
import { render, act, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../AuthContext';
import { readSessionSnapshot, writeSessionSnapshot } from '../../utils/sessionSnapshot';

jest.mock('../../services/AuthService', () => ({
  __esModule: true,
  default: {
    login: jest.fn(),
    refreshToken: jest.fn(),
    getProfile: jest.fn(),
    logout: jest.fn().mockResolvedValue(undefined),
    register: jest.fn(),
  },
}));

jest.mock('../../api/apiClient', () => ({
  setTokenRefreshCallback: jest.fn(),
  setLogoutCallback: jest.fn(),
  setAdoptStoredTokensCallback: jest.fn(),
  setupFetchInterceptor: jest.fn(),
  executeTokenRefresh: jest.fn().mockResolvedValue(undefined),
}));

jest.mock('../../i18n', () => ({
  __esModule: true,
  default: { changeLanguage: jest.fn().mockResolvedValue(undefined) },
}));

jest.mock('../../config/features', () => ({
  SubscriptionTier: {
    FREE: 'free',
    STARTER: 'starter',
    PROFESSIONAL: 'professional',
    ENTERPRISE: 'enterprise',
  },
  hasFeature: jest.fn().mockReturnValue(false),
  isFeatureName: jest.fn().mockReturnValue(false),
}));

// eslint-disable-next-line import/first
import AuthService from '../../services/AuthService';
// eslint-disable-next-line import/first
import {
  setTokenRefreshCallback,
  setLogoutCallback,
  setAdoptStoredTokensCallback,
} from '../../api/apiClient';

const ACCESS_TOKEN_KEY = 'examcraft_access_token';
const REFRESH_TOKEN_KEY = 'examcraft_refresh_token';
const LOGOUT_BROADCAST_KEY = 'examcraft_logout_broadcast';

const mockAuthService = AuthService as jest.Mocked<typeof AuthService>;

// Build a JWT-like token with given lifetime in seconds
function makeToken(lifetimeSeconds: number): string {
  const exp = Math.floor(Date.now() / 1000) + lifetimeSeconds;
  const payload = btoa(JSON.stringify({ exp, sub: 'user@test.com' }))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
  return `eyJhbGciOiJIUzI1NiJ9.${payload}.sig`;
}

const mockUser = {
  id: 1,
  email: 'user@test.com',
  first_name: 'Test',
  last_name: 'User',
  institution_id: 1,
  roles: [],
  status: 'active',
  is_superuser: false,
  is_email_verified: true,
  created_at: '2026-01-01T00:00:00Z',
  subscription_tier: null,
  institution: null,
};

function AuthConsumer({
  onContext,
}: {
  onContext: (auth: ReturnType<typeof useAuth>) => void;
}) {
  const auth = useAuth();
  React.useEffect(() => {
    onContext(auth);
  });
  return null;
}

describe('AuthContext — token refresh', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    jest.useFakeTimers();
    // Default logout mock
    (mockAuthService.logout as jest.Mock).mockResolvedValue(undefined);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('registers tokenRefreshCallback and logoutCallback on mount', async () => {
    render(<AuthProvider><div /></AuthProvider>);
    await act(async () => {
      await Promise.resolve();
    });

    expect(setTokenRefreshCallback).toHaveBeenCalledWith(expect.any(Function));
    expect(setLogoutCallback).toHaveBeenCalledWith(expect.any(Function));
  });

  it('schedules a refresh timer after login', async () => {
    const accessToken = makeToken(900); // 15 min
    (mockAuthService.login as jest.Mock).mockResolvedValue({
      access_token: accessToken,
      refresh_token: 'rt-1',
      token_type: 'bearer',
    });
    (mockAuthService.getProfile as jest.Mock).mockResolvedValue(mockUser as any);

    let capturedAuth: ReturnType<typeof useAuth> | null = null;
    render(
      <AuthProvider>
        <AuthConsumer onContext={(a) => { capturedAuth = a; }} />
      </AuthProvider>,
    );

    await act(async () => {
      await capturedAuth!.login('user@test.com', 'password');
    });

    // Timer should be set for ~13 min (900s - 120s buffer)
    expect(jest.getTimerCount()).toBeGreaterThanOrEqual(1);
  });

  it('cancels timer on logout', async () => {
    const accessToken = makeToken(900);
    (mockAuthService.login as jest.Mock).mockResolvedValue({
      access_token: accessToken,
      refresh_token: 'rt-1',
      token_type: 'bearer',
    });
    (mockAuthService.getProfile as jest.Mock).mockResolvedValue(mockUser as any);
    (mockAuthService.logout as jest.Mock).mockResolvedValue(undefined);

    let capturedAuth: ReturnType<typeof useAuth> | null = null;
    render(
      <AuthProvider>
        <AuthConsumer onContext={(a) => { capturedAuth = a; }} />
      </AuthProvider>,
    );

    await act(async () => {
      await capturedAuth!.login('user@test.com', 'pw');
    });
    expect(jest.getTimerCount()).toBeGreaterThanOrEqual(1);

    await act(async () => {
      await capturedAuth!.logout();
    });
    expect(jest.getTimerCount()).toBe(0);
  });

  it('clears wizard snapshots on logout (TF-608)', async () => {
    // sessionStorage überlebt den Benutzerwechsel im selben Tab, und der
    // Wizard-Snapshot enthält getippten Inhalt (Prüfungsthema). Auf einem
    // geteilten Rechner bekäme der nächste Nutzer sonst den Stand seines
    // Vorgängers zu sehen.
    writeSessionSnapshot('ragExamWizard', 1, { ragRequest: { topic: 'Vertraulich' } });
    expect(readSessionSnapshot('ragExamWizard', 1)).not.toBeNull();

    const accessToken = makeToken(900);
    (mockAuthService.login as jest.Mock).mockResolvedValue({
      access_token: accessToken,
      refresh_token: 'rt-1',
      token_type: 'bearer',
    });
    (mockAuthService.getProfile as jest.Mock).mockResolvedValue(mockUser as any);

    let capturedAuth: ReturnType<typeof useAuth> | null = null;
    render(
      <AuthProvider>
        <AuthConsumer onContext={(a) => { capturedAuth = a; }} />
      </AuthProvider>,
    );

    await act(async () => {
      await capturedAuth!.login('user@test.com', 'pw');
    });
    await act(async () => {
      await capturedAuth!.logout();
    });

    expect(readSessionSnapshot('ragExamWizard', 1)).toBeNull();
  });

  it('sets isAuthenticated to false when refresh token is expired', async () => {
    const accessToken = makeToken(900);
    (mockAuthService.login as jest.Mock).mockResolvedValue({
      access_token: accessToken,
      refresh_token: 'rt-1',
      token_type: 'bearer',
    });
    (mockAuthService.getProfile as jest.Mock).mockResolvedValue(mockUser as any);
    (mockAuthService.refreshToken as jest.Mock).mockRejectedValue(
      new Error('Refresh token expired'),
    );
    (mockAuthService.logout as jest.Mock).mockResolvedValue(undefined);

    let capturedAuth: ReturnType<typeof useAuth> | null = null;
    render(
      <AuthProvider>
        <AuthConsumer onContext={(a) => { capturedAuth = a; }} />
      </AuthProvider>,
    );

    await act(async () => {
      await capturedAuth!.login('user@test.com', 'pw');
    });

    // Invoke the tokenRefreshCallback that AuthContext registered with apiClient.
    // This triggers refreshAccessToken directly without going through the timer,
    // avoiding an unhandled rejection from the fire-and-forget setTimeout callback.
    const registeredCallback = (setTokenRefreshCallback as jest.Mock).mock.calls.at(-1)?.[0] as
      | (() => Promise<void>)
      | undefined;
    expect(registeredCallback).toBeDefined();

    // refreshAccessToken re-throws after calling clearLocalSession() — catch that here.
    await act(async () => {
      await registeredCallback!().catch(() => {
        // expected: refresh failed, local session was torn down (not a full logout)
      });
    });

    await waitFor(
      () => {
        expect(capturedAuth!.isAuthenticated).toBe(false);
      },
      { timeout: 3000 },
    );
  });

  it('clears wizard snapshots when a stale session is found expired on mount (TF-608)', async () => {
    // Der interessantere Fall als der explizite Logout-Klick oben: eine
    // abgelaufene Sitzung liegt bereits im localStorage eines offenen Tabs
    // (z. B. ein geteilter Rechner), und `loadAuthState`s Mount-Pfad in
    // AuthContext.tsx — nicht der `tokenRefreshCallback` — stellt das fest.
    // Genau der Fall, in dem jemand weggegangen ist und sich jemand anderes
    // an den Rechner setzt (siehe Kommentar an der Aufrufstelle).
    //
    // Echte Timer statt der Suite-weiten Fake-Timer: `isAuthenticated` ist
    // schon im Initial-State `false` — ein `waitFor` darauf würde beim
    // allerersten (synchronen) Poll grün werden, bevor die mehrstufige
    // async-Kette (getProfile → refreshToken → clearAllSessionSnapshots)
    // überhaupt einmal durchgelaufen ist. Ohne echte Timer bleibt unklar, ob
    // `waitFor`s Polling unter Fake-Timern zuverlässig mehrere
    // Promise-Hops abwartet.
    jest.useRealTimers();

    writeSessionSnapshot('ragExamWizard', 1, { ragRequest: { topic: 'Vertraulich' } });
    expect(readSessionSnapshot('ragExamWizard', 1)).not.toBeNull();

    localStorage.setItem('examcraft_access_token', makeToken(-60));
    localStorage.setItem('examcraft_refresh_token', 'stale-refresh-token');

    (mockAuthService.getProfile as jest.Mock).mockRejectedValue(new Error('401 Unauthorized'));
    (mockAuthService.refreshToken as jest.Mock).mockRejectedValue(
      new Error('Refresh token expired'),
    );

    let capturedAuth: ReturnType<typeof useAuth> | null = null;
    render(
      <AuthProvider>
        <AuthConsumer onContext={(a) => { capturedAuth = a; }} />
      </AuthProvider>,
    );

    // Zielgerichtet auf den eigentlich zu prüfenden Seiteneffekt warten,
    // nicht auf `isAuthenticated` — das ist schon vor der async-Kette
    // `false` und würde ein `waitFor` sofort (fälschlich) grün werden
    // lassen.
    await waitFor(
      () => {
        expect(readSessionSnapshot('ragExamWizard', 1)).toBeNull();
      },
      { timeout: 3000 },
    );

    expect(capturedAuth!.isAuthenticated).toBe(false);
  });
});

describe('AuthContext — cross-tab token sync (TF-607)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    jest.useFakeTimers();
    (mockAuthService.logout as jest.Mock).mockResolvedValue(undefined);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  /**
   * Mount one logged-in provider — the stand-in for a single browser tab —
   * and hand back a live handle on its auth context.
   */
  async function mountLoggedInTab(accessToken: string, refreshToken = 'rt-1') {
    (mockAuthService.login as jest.Mock).mockResolvedValue({
      access_token: accessToken,
      refresh_token: refreshToken,
      token_type: 'bearer',
    });
    (mockAuthService.getProfile as jest.Mock).mockResolvedValue(mockUser as any);

    const holder: { auth: ReturnType<typeof useAuth> | null } = { auth: null };
    render(
      <AuthProvider>
        <AuthConsumer onContext={(a) => { holder.auth = a; }} />
      </AuthProvider>,
    );

    await act(async () => {
      await holder.auth!.login('user@test.com', 'pw');
    });

    return holder;
  }

  /** Simulate the storage event another tab's write would deliver here. */
  function dispatchStorage(key: string | null, newValue: string | null, oldValue: string | null = null) {
    window.dispatchEvent(new StorageEvent('storage', { key, newValue, oldValue }));
  }

  it('refreshes under the cross-tab lock on mount instead of racing other tabs', async () => {
    const stale = makeToken(-10);
    const rotated = makeToken(1800);
    localStorage.setItem(ACCESS_TOKEN_KEY, stale);
    localStorage.setItem(REFRESH_TOKEN_KEY, 'rt-1');

    // The stale access token no longer authenticates; the rotated one does.
    (mockAuthService.getProfile as jest.Mock).mockImplementation(async (token: string) => {
      if (token === stale) throw new Error('401 Unauthorized');
      return mockUser;
    });

    // Web Locks stand-in in which another tab rotates while we queue.
    Object.defineProperty(navigator, 'locks', {
      value: {
        request: async (_name: string, callback: () => Promise<unknown>) => {
          localStorage.setItem(ACCESS_TOKEN_KEY, rotated);
          localStorage.setItem(REFRESH_TOKEN_KEY, 'rt-2');
          return callback();
        },
      },
      configurable: true,
      writable: true,
    });

    try {
      const tab: { auth: ReturnType<typeof useAuth> | null } = { auth: null };
      render(
        <AuthProvider>
          <AuthConsumer onContext={(a) => { tab.auth = a; }} />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(tab.auth!.isAuthenticated).toBe(true);
      });

      // Before TF-607 the mount path called AuthService.refreshToken directly,
      // outside the lock — three tabs opening together each burned the one
      // valid refresh token and all but one were rejected.
      expect(mockAuthService.refreshToken).not.toHaveBeenCalled();
      expect(tab.auth!.accessToken).toBe(rotated);
      expect(tab.auth!.refreshToken).toBe('rt-2');
    } finally {
      Object.defineProperty(navigator, 'locks', {
        value: undefined,
        configurable: true,
        writable: true,
      });
    }
  });

  it('refreshes successfully under the lock on mount when no other tab is contending', async () => {
    const stale = makeToken(-10);
    const rotated = makeToken(1800);
    localStorage.setItem(ACCESS_TOKEN_KEY, stale);
    localStorage.setItem(REFRESH_TOKEN_KEY, 'rt-1');

    (mockAuthService.getProfile as jest.Mock).mockImplementation(async (token: string) => {
      if (token === stale) throw new Error('401 Unauthorized');
      return mockUser;
    });
    (mockAuthService.refreshToken as jest.Mock).mockResolvedValue({
      access_token: rotated,
      refresh_token: 'rt-2',
    });

    // A plain passthrough lock — nobody else writes to localStorage while
    // this tab holds it, so the real tokenBeforeLock/tokenInsideLock
    // comparison inside withTokenRefreshLock finds nothing changed and this
    // tab takes the rotate branch itself, exercising the majority-case path
    // (a single tab refreshing its own expired token) through the actual
    // lock machinery rather than only its adopt/fallback branches.
    Object.defineProperty(navigator, 'locks', {
      value: {
        request: async (_name: string, callback: () => Promise<unknown>) => callback(),
      },
      configurable: true,
      writable: true,
    });

    try {
      const tab: { auth: ReturnType<typeof useAuth> | null } = { auth: null };
      render(
        <AuthProvider>
          <AuthConsumer onContext={(a) => { tab.auth = a; }} />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(tab.auth!.isAuthenticated).toBe(true);
      });

      expect(mockAuthService.refreshToken).toHaveBeenCalledTimes(1);
      expect(tab.auth!.accessToken).toBe(rotated);
      expect(tab.auth!.refreshToken).toBe('rt-2');
      expect(tab.auth!.user).toEqual(mockUser);
      expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBe(rotated);
      expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBe('rt-2');
    } finally {
      Object.defineProperty(navigator, 'locks', {
        value: undefined,
        configurable: true,
        writable: true,
      });
    }
  });

  it('registers the adopt-stored-tokens callback with the api client', async () => {
    render(<AuthProvider><div /></AuthProvider>);
    await act(async () => {
      await Promise.resolve();
    });

    expect(setAdoptStoredTokensCallback).toHaveBeenCalledWith(expect.any(Function));
  });

  it('adopts tokens that another tab rotated instead of refreshing again', async () => {
    const initial = makeToken(900);
    const holder = await mountLoggedInTab(initial);
    (mockAuthService.refreshToken as jest.Mock).mockClear();

    // Another tab won the refresh and wrote the rotated pair.
    const rotated = makeToken(1800);
    localStorage.setItem(ACCESS_TOKEN_KEY, rotated);
    localStorage.setItem(REFRESH_TOKEN_KEY, 'rt-2');

    await act(async () => {
      dispatchStorage(ACCESS_TOKEN_KEY, rotated, initial);
    });

    expect(holder.auth!.accessToken).toBe(rotated);
    expect(holder.auth!.refreshToken).toBe('rt-2');
    expect(holder.auth!.isAuthenticated).toBe(true);
    expect(mockAuthService.refreshToken).not.toHaveBeenCalled();
  });

  it('clears the local session when another tab broadcasts an intentional logout', async () => {
    const holder = await mountLoggedInTab(makeToken(900));

    // A real logout() writes the broadcast marker and then removes the
    // tokens — that combination is the one signal other tabs treat as proof
    // the backend already revoked every session (TF-607).
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    (mockAuthService.logout as jest.Mock).mockClear();

    await act(async () => {
      dispatchStorage(LOGOUT_BROADCAST_KEY, String(Date.now()), null);
    });

    expect(holder.auth!.isAuthenticated).toBe(false);
    // The other tab already talked to the backend — a second revoke-all from
    // here would be redundant and would race the other tab's fresh login.
    expect(mockAuthService.logout).not.toHaveBeenCalled();
  });

  it('clears the local session on a full localStorage.clear() from another tab', async () => {
    const holder = await mountLoggedInTab(makeToken(900));

    localStorage.clear();

    await act(async () => {
      dispatchStorage(null, null, null);
    });

    expect(holder.auth!.isAuthenticated).toBe(false);
  });

  it('keeps the session alive when another tab\'s own refresh merely failed', async () => {
    const accessToken = makeToken(900);
    const holder = await mountLoggedInTab(accessToken);

    // Another tab's own refresh attempt failed (network blip, lost race, a
    // timeout — none of which prove the backend session is dead) and tore
    // down *its* local session, which removed the shared tokens. No logout
    // broadcast was written.
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);

    await act(async () => {
      dispatchStorage(ACCESS_TOKEN_KEY, null, accessToken);
    });

    // This tab's own tokens still worked the last time it checked — a single
    // tab's failed refresh must not cascade into a logout here too, and this
    // tab should self-heal the evicted localStorage slot.
    expect(holder.auth!.isAuthenticated).toBe(true);
    expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBe(accessToken);
    expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBe('rt-1');
  });

  it('ignores storage events when this tab has no session', async () => {
    const holder: { auth: ReturnType<typeof useAuth> | null } = { auth: null };
    render(
      <AuthProvider>
        <AuthConsumer onContext={(a) => { holder.auth = a; }} />
      </AuthProvider>,
    );
    await act(async () => {
      await Promise.resolve();
    });
    expect(holder.auth!.isAuthenticated).toBe(false);

    await act(async () => {
      dispatchStorage(ACCESS_TOKEN_KEY, makeToken(900), null);
    });

    // No session to sync — must stay a no-op, not adopt credentials with no
    // loaded user behind them.
    expect(holder.auth!.isAuthenticated).toBe(false);
    expect(holder.auth!.accessToken).toBeNull();
  });

  it('does not revoke backend sessions when a refresh fails', async () => {
    const holder = await mountLoggedInTab(makeToken(900));
    (mockAuthService.refreshToken as jest.Mock).mockRejectedValue(new Error('Session not found'));
    (mockAuthService.logout as jest.Mock).mockClear();

    const refresh = (setTokenRefreshCallback as jest.Mock).mock.calls.at(-1)?.[0] as
      () => Promise<void>;

    await act(async () => {
      await refresh().catch(() => {
        // expected — the caller still learns the refresh failed
      });
    });

    // AuthService.logout hits /api/auth/logout, which revokes *every* session
    // of the user on the backend. One tab failing must not sign the user out
    // on their other tabs and devices.
    expect(mockAuthService.logout).not.toHaveBeenCalled();
    await waitFor(() => {
      expect(holder.auth!.isAuthenticated).toBe(false);
    });
  });

  it('adopts another tab\'s tokens when its own refresh lost the race', async () => {
    const initial = makeToken(900);
    const holder = await mountLoggedInTab(initial);

    const rotated = makeToken(1800);
    (mockAuthService.refreshToken as jest.Mock).mockImplementation(async () => {
      // Another tab rotated while our request was in flight — reachable on
      // browsers without Web Locks, where the lock cannot serialize us.
      localStorage.setItem(ACCESS_TOKEN_KEY, rotated);
      localStorage.setItem(REFRESH_TOKEN_KEY, 'rt-2');
      throw new Error('Session not found');
    });

    const refresh = (setTokenRefreshCallback as jest.Mock).mock.calls.at(-1)?.[0] as
      () => Promise<void>;

    await act(async () => {
      await refresh();
    });

    expect(holder.auth!.isAuthenticated).toBe(true);
    expect(holder.auth!.accessToken).toBe(rotated);
  });

  it('registers a local-only teardown as the api client logout callback', async () => {
    const holder = await mountLoggedInTab(makeToken(900));
    (mockAuthService.logout as jest.Mock).mockClear();

    const onAuthFailure = (setLogoutCallback as jest.Mock).mock.calls.at(-1)?.[0] as
      () => Promise<void> | void;

    await act(async () => {
      await onAuthFailure();
    });

    expect(holder.auth!.isAuthenticated).toBe(false);
    expect(mockAuthService.logout).not.toHaveBeenCalled();
  });
});
