import React from 'react';
import { render, act, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../AuthContext';

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
  setupFetchInterceptor: jest.fn(),
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
import { setTokenRefreshCallback, setLogoutCallback } from '../../api/apiClient';

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

    // refreshAccessToken re-throws after calling logout() — catch that here.
    await act(async () => {
      await registeredCallback!().catch(() => {
        // expected: refresh failed, logout was called internally
      });
    });

    await waitFor(
      () => {
        expect(capturedAuth!.isAuthenticated).toBe(false);
      },
      { timeout: 3000 },
    );
  });
});
