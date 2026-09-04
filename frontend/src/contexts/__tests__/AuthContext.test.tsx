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

jest.mock('../../services/AdminService', () => ({
  __esModule: true,
  default: {
    endImpersonation: jest.fn().mockResolvedValue(undefined),
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
import AdminService from '../../services/AdminService';
// eslint-disable-next-line import/first
import {
  setTokenRefreshCallback,
  setLogoutCallback,
  setAdoptStoredTokensCallback,
} from '../../api/apiClient';
// eslint-disable-next-line import/first
import i18n from '../../i18n';
// eslint-disable-next-line import/first
import { setPendingLanguage } from '../../utils/languagePreference';

const ACCESS_TOKEN_KEY = 'examcraft_access_token';
const REFRESH_TOKEN_KEY = 'examcraft_refresh_token';
const LOGOUT_BROADCAST_KEY = 'examcraft_logout_broadcast';

const mockAuthService = AuthService as jest.Mocked<typeof AuthService>;
const mockAdminService = AdminService as jest.Mocked<typeof AdminService>;

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
    // sessionStorage survives a user switch within the same tab, and the
    // wizard snapshot contains typed content (exam topic). On a shared
    // machine, the next user would otherwise see their predecessor's state.
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
    // The more interesting case than the explicit logout click above: an
    // expired session already sits in an open tab's localStorage (e.g. a
    // shared machine), and `loadAuthState`'s mount path in AuthContext.tsx —
    // not the `tokenRefreshCallback` — is the one that detects it. Exactly
    // the case where someone walked away and someone else sits down at the
    // machine (see the comment at the call site).
    //
    // Real timers instead of the suite-wide fake timers: `isAuthenticated` is
    // already `false` in the initial state — a `waitFor` on it would pass on
    // the very first (synchronous) poll, before the multi-step async chain
    // (getProfile → refreshToken → clearAllSessionSnapshots) has run even
    // once. Without real timers it stays unclear whether `waitFor`'s polling
    // reliably waits out several promise hops under fake timers.
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

    // Wait specifically for the side effect actually under test, not for
    // `isAuthenticated` — that is already `false` before the async chain
    // runs and would make a `waitFor` on it pass immediately (falsely).
    await waitFor(
      () => {
        expect(readSessionSnapshot('ragExamWizard', 1)).toBeNull();
      },
      { timeout: 3000 },
    );

    expect(capturedAuth!.isAuthenticated).toBe(false);
  });
});

// resolveLanguageOnProfileLoad itself is unit-tested in
// languagePreference.test.ts, and the write side (setPendingLanguage /
// clearPendingLanguage on save success/failure) in
// ProfileView.language.test.tsx. Neither proves the only production caller —
// AuthContext, which routes every profile load through it instead of the raw
// account value — actually applies the pending choice. A regression here
// (e.g. "simplifying" back to `i18n.changeLanguage(profile.preferred_language)`)
// would not be caught anywhere else.
describe('AuthContext — pending language preference precedence', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  it('applies the pending browser choice instead of the account language on login', async () => {
    const accessToken = makeToken(900);
    (mockAuthService.login as jest.Mock).mockResolvedValue({
      access_token: accessToken,
      refresh_token: 'rt-1',
      token_type: 'bearer',
    });
    (mockAuthService.getProfile as jest.Mock).mockResolvedValue({
      ...mockUser,
      preferred_language: 'en',
    } as any);

    // A choice made in this browser, not yet saved to the account.
    setPendingLanguage('fr');

    let capturedAuth: ReturnType<typeof useAuth> | null = null;
    render(
      <AuthProvider>
        <AuthConsumer onContext={(a) => { capturedAuth = a; }} />
      </AuthProvider>,
    );

    await act(async () => {
      await capturedAuth!.login('user@test.com', 'password');
    });

    expect(i18n.changeLanguage).toHaveBeenCalledWith('fr');
    expect(i18n.changeLanguage).not.toHaveBeenCalledWith('en');
  });

  it('falls back to the account language when there is no pending choice', async () => {
    const accessToken = makeToken(900);
    (mockAuthService.login as jest.Mock).mockResolvedValue({
      access_token: accessToken,
      refresh_token: 'rt-1',
      token_type: 'bearer',
    });
    (mockAuthService.getProfile as jest.Mock).mockResolvedValue({
      ...mockUser,
      preferred_language: 'en',
    } as any);

    let capturedAuth: ReturnType<typeof useAuth> | null = null;
    render(
      <AuthProvider>
        <AuthConsumer onContext={(a) => { capturedAuth = a; }} />
      </AuthProvider>,
    );

    await act(async () => {
      await capturedAuth!.login('user@test.com', 'password');
    });

    expect(i18n.changeLanguage).toHaveBeenCalledWith('en');
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

  it("does not clobber another tab's impersonation handoff when the storage read to detect it fails (TF-743)", async () => {
    const holder = await mountLoggedInTab(makeToken(900));
    const ourAccessToken = holder.auth!.accessToken!;

    // Another tab started impersonating: access token present, no refresh
    // token (TF-743's impersonation token shape) — this is what handleStorage
    // must recognise as a handoff and leave alone.
    const otherTabImpersonationToken = makeToken(1800);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.setItem(ACCESS_TOKEN_KEY, otherTabImpersonationToken);

    let callCount = 0;
    const realGetItem = window.localStorage.getItem.bind(window.localStorage);
    // Let adoptStoredTokens()'s own two reads through untouched (it correctly
    // concludes "not a full pair, nothing to adopt" on real data); only the
    // isImpersonationHandoff detection reads that follow are made to fail.
    window.localStorage.getItem = jest.fn((key: string) => {
      callCount += 1;
      if (callCount > 2) throw new Error('storage access blocked');
      return realGetItem(key);
    });

    try {
      await act(async () => {
        dispatchStorage(ACCESS_TOKEN_KEY, otherTabImpersonationToken, null);
      });
    } finally {
      window.localStorage.getItem = realGetItem;
    }

    // Safe default: on a storage read failure here, assume this MIGHT be a
    // handoff and do nothing — never clobber what the other tab just wrote.
    expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBe(otherTabImpersonationToken);
    expect(holder.auth!.accessToken).toBe(ourAccessToken);
  });

  it("ignores another tab's ordinary token rotation entirely while this tab is impersonating (TF-743)", async () => {
    const holder = await mountLoggedInTab(makeToken(900));

    const impersonationToken = makeToken(1800);
    (mockAuthService.getProfile as jest.Mock).mockResolvedValue({ ...mockUser, id: 2 } as any);
    await act(async () => {
      await holder.auth!.startImpersonation({ accessToken: impersonationToken, expiresIn: 1800 });
    });
    expect(holder.auth!.isImpersonating).toBe(true);

    // A sibling tab of the same admin does its own, entirely unrelated,
    // ordinary token rotation — writes a fresh admin access+refresh pair.
    const siblingAdminAccessToken = makeToken(900);
    localStorage.setItem(ACCESS_TOKEN_KEY, siblingAdminAccessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, 'sibling-admin-rt');

    await act(async () => {
      dispatchStorage(ACCESS_TOKEN_KEY, siblingAdminAccessToken, impersonationToken);
    });

    // Still impersonating the original target under the original token — the
    // sibling tab's rotation must not silently swap this tab's identity
    // while the banner keeps claiming to impersonate someone else.
    expect(holder.auth!.isImpersonating).toBe(true);
    expect(holder.auth!.accessToken).toBe(impersonationToken);
  });
});

describe('AuthContext impersonation (TF-743)', () => {
  const adminUser = { ...mockUser, id: 1, email: 'admin@test.com', is_superuser: true };
  const targetUser = { ...mockUser, id: 2, email: 'target@test.com', is_superuser: false };

  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    (mockAuthService.logout as jest.Mock).mockResolvedValue(undefined);
  });

  async function mountAsAdmin(adminAccessToken: string, adminRefreshToken = 'admin-rt-1') {
    (mockAuthService.login as jest.Mock).mockResolvedValue({
      access_token: adminAccessToken,
      refresh_token: adminRefreshToken,
      token_type: 'bearer',
    });
    (mockAuthService.getProfile as jest.Mock).mockResolvedValue(adminUser as any);

    const holder: { auth: ReturnType<typeof useAuth> | null } = { auth: null };
    render(
      <AuthProvider>
        <AuthConsumer onContext={(a) => { holder.auth = a; }} />
      </AuthProvider>,
    );
    await act(async () => {
      await holder.auth!.login('admin@test.com', 'pw');
    });
    return holder;
  }

  it('swaps the active session to the target user, drops the refresh token, and stashes the admin session', async () => {
    const adminAccessToken = makeToken(900);
    const holder = await mountAsAdmin(adminAccessToken);

    const impersonationToken = makeToken(1800);
    (mockAuthService.getProfile as jest.Mock).mockResolvedValue(targetUser as any);

    await act(async () => {
      await holder.auth!.startImpersonation({ accessToken: impersonationToken, expiresIn: 1800 });
    });

    expect(holder.auth!.user).toEqual(targetUser);
    expect(holder.auth!.accessToken).toBe(impersonationToken);
    expect(holder.auth!.refreshToken).toBeNull();
    expect(holder.auth!.isImpersonating).toBe(true);
    expect(holder.auth!.impersonationExpiresAt).not.toBeNull();
    expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBe(impersonationToken);
    expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBeNull();

    const stashed = readSessionSnapshot<{ accessToken: string; refreshToken: string; user: unknown }>(
      'impersonation.adminSession',
      1,
    );
    expect(stashed?.accessToken).toBe(adminAccessToken);
    expect(stashed?.refreshToken).toBe('admin-rt-1');
    expect(stashed?.user).toEqual(adminUser);
  });

  it('endImpersonation restores the stashed admin session with a freshly refreshed token pair', async () => {
    const adminAccessToken = makeToken(900);
    const holder = await mountAsAdmin(adminAccessToken);

    (mockAuthService.getProfile as jest.Mock).mockResolvedValue(targetUser as any);
    await act(async () => {
      await holder.auth!.startImpersonation({ accessToken: makeToken(1800), expiresIn: 1800 });
    });
    expect(holder.auth!.isImpersonating).toBe(true);

    const rotatedAdminAccessToken = makeToken(901); // distinct lifetime so the token string differs from adminAccessToken even within the same test-run second
    (mockAuthService.refreshToken as jest.Mock).mockResolvedValue({
      access_token: rotatedAdminAccessToken,
      refresh_token: 'admin-rt-2',
      token_type: 'bearer',
    });

    await act(async () => {
      await holder.auth!.endImpersonation();
    });

    expect(mockAuthService.refreshToken).toHaveBeenCalledWith({ refresh_token: 'admin-rt-1' });
    expect(holder.auth!.user).toEqual(adminUser);
    expect(holder.auth!.accessToken).toBe(rotatedAdminAccessToken);
    expect(holder.auth!.refreshToken).toBe('admin-rt-2');
    expect(holder.auth!.isImpersonating).toBe(false);
    expect(holder.auth!.impersonationExpiresAt).toBeNull();
    expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBe(rotatedAdminAccessToken);
    expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBe('admin-rt-2');
    expect(readSessionSnapshot('impersonation.adminSession', 1)).toBeNull();
  });

  it('endImpersonation is a no-op when nothing was stashed (already restored, e.g. by the automatic fallback)', async () => {
    const holder = await mountAsAdmin(makeToken(900));

    await act(async () => {
      await holder.auth!.endImpersonation();
    });

    expect(mockAuthService.refreshToken).not.toHaveBeenCalled();
    expect(holder.auth!.isAuthenticated).toBe(true);
    expect(holder.auth!.user).toEqual(adminUser);
  });

  it('routes a 401/proactive-refresh during impersonation (no refresh token) to restoring the admin session instead of logging out', async () => {
    const adminAccessToken = makeToken(900);
    const holder = await mountAsAdmin(adminAccessToken);

    (mockAuthService.getProfile as jest.Mock).mockResolvedValue(targetUser as any);
    await act(async () => {
      await holder.auth!.startImpersonation({ accessToken: makeToken(1800), expiresIn: 1800 });
    });

    const rotatedAdminAccessToken = makeToken(901); // distinct lifetime so the token string differs from adminAccessToken even within the same test-run second
    (mockAuthService.refreshToken as jest.Mock).mockResolvedValue({
      access_token: rotatedAdminAccessToken,
      refresh_token: 'admin-rt-2',
      token_type: 'bearer',
    });

    // Simulate what apiClient's 401/proactive-timer path does: call the
    // registered tokenRefreshCallback directly (executeTokenRefresh is
    // mocked out in this file — see the top-level apiClient mock).
    const tokenRefreshCallback = (setTokenRefreshCallback as jest.Mock).mock.calls.at(-1)?.[0] as
      () => Promise<void>;

    await act(async () => {
      // refreshAccessToken throws ImpersonationEndedError after a
      // successful restore, precisely so apiClient's interceptors know not
      // to retry the original request under the admin's identity — state
      // is already updated by the time it throws, so assert on that below.
      await tokenRefreshCallback().catch(() => {
        // expected: see ImpersonationEndedError in tokenRefreshLock.ts
      });
    });

    expect(mockAuthService.logout).not.toHaveBeenCalled();
    expect(mockAdminService.endImpersonation).toHaveBeenCalledWith();
    expect(holder.auth!.isAuthenticated).toBe(true);
    expect(holder.auth!.isImpersonating).toBe(false);
    expect(holder.auth!.user).toEqual(adminUser);
    expect(holder.auth!.accessToken).toBe(rotatedAdminAccessToken);
  });

  it('falls back to a full logout when the refresh token is missing and nothing was stashed (not impersonating)', async () => {
    const holder = await mountAsAdmin(makeToken(900));
    // No impersonation ever started, so there is no stashed admin session —
    // simulate a session that lost its refresh token some other way.
    localStorage.removeItem(REFRESH_TOKEN_KEY);

    const tokenRefreshCallback = (setTokenRefreshCallback as jest.Mock).mock.calls.at(-1)?.[0] as
      () => Promise<void>;

    // refreshAccessToken re-throws after calling clearLocalSession() — catch that here
    // (same pattern as the pre-existing "sets isAuthenticated to false when refresh
    // token is expired" test above) rather than asserting on the rejection directly,
    // so the state update from clearLocalSession() is flushed before we read it.
    await act(async () => {
      await tokenRefreshCallback().catch(() => {
        // expected: no refresh token and nothing to restore, session torn down
      });
    });

    await waitFor(() => {
      expect(holder.auth!.isAuthenticated).toBe(false);
    });
  });

  it('refuses to start a second impersonation while one is already active', async () => {
    const holder = await mountAsAdmin(makeToken(900));
    (mockAuthService.getProfile as jest.Mock).mockResolvedValue(targetUser as any);

    await act(async () => {
      await holder.auth!.startImpersonation({ accessToken: makeToken(1800), expiresIn: 1800 });
    });
    expect(holder.auth!.isImpersonating).toBe(true);

    await expect(
      holder.auth!.startImpersonation({ accessToken: makeToken(1800), expiresIn: 1800 }),
    ).rejects.toThrow(/already impersonating/i);

    // The original impersonation session is untouched by the rejected attempt.
    expect(holder.auth!.isImpersonating).toBe(true);
  });

  it('refuses to start impersonation when the recovery snapshot cannot be saved', async () => {
    const adminAccessToken = makeToken(900);
    const holder = await mountAsAdmin(adminAccessToken);

    const realSetItem = window.sessionStorage.setItem.bind(window.sessionStorage);
    window.sessionStorage.setItem = jest.fn(() => {
      throw new Error('QuotaExceededError');
    });

    try {
      await expect(
        holder.auth!.startImpersonation({ accessToken: makeToken(1800), expiresIn: 1800 }),
      ).rejects.toThrow(/snapshot/i);
    } finally {
      window.sessionStorage.setItem = realSetItem;
    }

    // Refused before touching anything — still the admin's own session.
    expect(holder.auth!.isImpersonating).toBe(false);
    expect(holder.auth!.accessToken).toBe(adminAccessToken);
    expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBe(adminAccessToken);
  });

  it('rolls back and best-effort closes the orphaned session when starting impersonation fails after the backend already created it', async () => {
    const adminAccessToken = makeToken(900);
    const holder = await mountAsAdmin(adminAccessToken);
    const impersonationToken = makeToken(1800);
    (mockAuthService.getProfile as jest.Mock).mockRejectedValueOnce(new Error('network error'));

    await expect(
      holder.auth!.startImpersonation({ accessToken: impersonationToken, expiresIn: 1800 }),
    ).rejects.toThrow('network error');

    // Rolled all the way back: admin session intact, no orphaned snapshot.
    expect(holder.auth!.isImpersonating).toBe(false);
    expect(holder.auth!.isAuthenticated).toBe(true);
    expect(holder.auth!.accessToken).toBe(adminAccessToken);
    expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBe(adminAccessToken);
    expect(
      readSessionSnapshot<{ accessToken: string; refreshToken: string; user: unknown }>(
        'impersonation.adminSession',
        1,
      ),
    ).toBeNull();

    // The backend already created the impersonation session before this
    // failure (AdminService.impersonateUser succeeded); it must be told the
    // swap was abandoned rather than left open until the reaper reclaims it.
    // localStorage still holds the admin's own token, so the just-issued
    // target token has to be passed explicitly.
    expect(mockAdminService.endImpersonation).toHaveBeenCalledWith(impersonationToken);
  });

  it('falls back to the stashed (unrefreshed) admin token when refreshing the admin session on restore also fails', async () => {
    const adminAccessToken = makeToken(900);
    const holder = await mountAsAdmin(adminAccessToken);
    (mockAuthService.getProfile as jest.Mock).mockResolvedValue(targetUser as any);

    await act(async () => {
      await holder.auth!.startImpersonation({ accessToken: makeToken(1800), expiresIn: 1800 });
    });
    expect(holder.auth!.isImpersonating).toBe(true);

    (mockAuthService.refreshToken as jest.Mock).mockRejectedValueOnce(
      new Error('admin session also expired'),
    );

    await act(async () => {
      await holder.auth!.endImpersonation();
    });

    // The admin is not logged out purely because their own token also came
    // due while they happened to be impersonating — the stashed (unrefreshed)
    // pair is restored as a last resort instead.
    expect(holder.auth!.isImpersonating).toBe(false);
    expect(holder.auth!.isAuthenticated).toBe(true);
    expect(holder.auth!.accessToken).toBe(adminAccessToken);
    expect(holder.auth!.refreshToken).toBe('admin-rt-1');
  });

  it('logout while impersonating only ends the impersonation, without broadcasting a full logout or wiping other tabs', async () => {
    const holder = await mountAsAdmin(makeToken(900));
    (mockAuthService.getProfile as jest.Mock).mockResolvedValue(targetUser as any);

    await act(async () => {
      await holder.auth!.startImpersonation({ accessToken: makeToken(1800), expiresIn: 1800 });
    });
    expect(holder.auth!.isImpersonating).toBe(true);

    const rotatedAdminAccessToken = makeToken(901);
    (mockAuthService.refreshToken as jest.Mock).mockResolvedValue({
      access_token: rotatedAdminAccessToken,
      refresh_token: 'admin-rt-2',
      token_type: 'bearer',
    });

    await act(async () => {
      await holder.auth!.logout();
    });

    // Mirrors the backend (auth.py's logout endpoint treats
    // logout-while-impersonating the same as ending the impersonation):
    // this must not revoke every session of the admin's account, nor
    // broadcast a cross-tab logout that would sign the admin out everywhere.
    expect(mockAuthService.logout).not.toHaveBeenCalled();
    expect(localStorage.getItem(LOGOUT_BROADCAST_KEY)).toBeNull();
    expect(holder.auth!.isAuthenticated).toBe(true);
    expect(holder.auth!.isImpersonating).toBe(false);
    expect(holder.auth!.user).toEqual(adminUser);
  });

  it('reload while impersonating (access token but no refresh token) restores the stashed admin session instead of logging out entirely', async () => {
    const adminAccessToken = makeToken(900);
    const impersonationAccessToken = makeToken(1800);

    // Simulate the state left behind by startImpersonation right before a
    // reload: localStorage has only the impersonation access token (no
    // refresh token, by design — TF-741's hard cap, no renewal), and the
    // admin's own session is stashed in sessionStorage.
    localStorage.setItem(ACCESS_TOKEN_KEY, impersonationAccessToken);
    writeSessionSnapshot<{ accessToken: string; refreshToken: string; user: unknown }>(
      'impersonation.adminSession',
      1,
      { accessToken: adminAccessToken, refreshToken: 'admin-rt-1', user: adminUser },
    );

    (mockAuthService.refreshToken as jest.Mock).mockResolvedValue({
      access_token: makeToken(901),
      refresh_token: 'admin-rt-2',
      token_type: 'bearer',
    });

    let capturedAuth: ReturnType<typeof useAuth> | null = null;
    render(
      <AuthProvider>
        <AuthConsumer onContext={(a) => { capturedAuth = a; }} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(capturedAuth!.isLoading).toBe(false);
    });

    // The admin lands back on their own session instead of being logged out
    // entirely, which was the previous behavior on any reload mid-impersonation.
    expect(capturedAuth!.isAuthenticated).toBe(true);
    expect(capturedAuth!.isImpersonating).toBe(false);
    expect(capturedAuth!.user).toEqual(adminUser);
  });
});
