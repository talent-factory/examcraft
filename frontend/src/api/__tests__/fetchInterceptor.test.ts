/**
 * fetchInterceptor.test.ts
 *
 * Unit-Tests für setupFetchInterceptor + executeTokenRefresh aus apiClient.ts.
 *
 * Strategie:
 *  - jest.resetModules() vor jedem Test isoliert die module-level State
 *    (fetchInterceptorInstalled, refreshPromise, callbacks).
 *  - Jeder Test importiert die Funktionen frisch via require() und patcht
 *    window.fetch mit einem jest.fn() bevor setupFetchInterceptor() läuft.
 *  - Axios wird nicht benötigt; trotzdem stub-mocken, damit der
 *    apiClient.ts-Top-Level-`axios.create()`-Call nicht crasht.
 */

jest.mock('axios', () => {
  const instance = jest.fn() as any;
  instance.interceptors = {
    request: { use: jest.fn() },
    response: { use: jest.fn() },
  };
  return {
    __esModule: true,
    default: { create: jest.fn(() => instance) },
  };
});

const ACCESS_TOKEN_KEY = 'examcraft_access_token';

type ApiClientModule = typeof import('../apiClient');

describe('setupFetchInterceptor', () => {
  let originalFetch: typeof window.fetch;
  let mockFetch: jest.Mock;
  let mod: ApiClientModule;

  beforeEach(() => {
    jest.resetModules();
    localStorage.clear();
    originalFetch = window.fetch;
    mockFetch = jest.fn();
    // Install our mock fetch BEFORE the interceptor reads it.
    (window as any).fetch = mockFetch;
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    mod = require('../apiClient');
  });

  afterEach(() => {
    (window as any).fetch = originalFetch;
  });

  function installWithCallbacks(refresh: () => Promise<void>, logout?: () => Promise<void>) {
    mod.setTokenRefreshCallback(refresh);
    if (logout) mod.setLogoutCallback(logout);
    mod.setupFetchInterceptor();
  }

  // ── Happy path ────────────────────────────────────────────────────────────

  it('passes non-401 responses through unchanged without refresh', async () => {
    const refresh = jest.fn().mockResolvedValue(undefined);
    installWithCallbacks(refresh);

    mockFetch.mockResolvedValueOnce({ status: 200, ok: true } as Response);

    const result = await window.fetch('/api/v1/something');

    expect(result.status).toBe(200);
    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(refresh).not.toHaveBeenCalled();
  });

  it('on 401: refreshes token, retries with new Authorization header, returns retried response', async () => {
    const refresh = jest.fn().mockImplementation(async () => {
      localStorage.setItem(ACCESS_TOKEN_KEY, 'new-token');
    });
    installWithCallbacks(refresh);

    mockFetch
      .mockResolvedValueOnce({ status: 401 } as Response)
      .mockResolvedValueOnce({ status: 200, ok: true } as Response);

    const result = await window.fetch('/api/v1/exams', {
      method: 'GET',
      headers: { 'X-Custom': 'yes' },
    });

    expect(result.status).toBe(200);
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(mockFetch).toHaveBeenCalledTimes(2);

    // The retry must carry the new Bearer token AND preserve original headers.
    const retryInit = mockFetch.mock.calls[1][1] as RequestInit;
    const retryHeaders = retryInit.headers as Headers;
    expect(retryHeaders.get('Authorization')).toBe('Bearer new-token');
    expect(retryHeaders.get('X-Custom')).toBe('yes');
  });

  // ── /api/auth/* short-circuit ────────────────────────────────────────────

  it('does NOT refresh on 401 from /api/auth/* endpoints (prevents recursion)', async () => {
    const refresh = jest.fn().mockResolvedValue(undefined);
    installWithCallbacks(refresh);

    mockFetch.mockResolvedValueOnce({ status: 401 } as Response);

    const result = await window.fetch('https://api/api/auth/refresh');

    expect(result.status).toBe(401);
    expect(refresh).not.toHaveBeenCalled();
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it('detects /api/auth/* path when input is a Request instance', async () => {
    const refresh = jest.fn().mockResolvedValue(undefined);
    installWithCallbacks(refresh);

    mockFetch.mockResolvedValueOnce({ status: 401 } as Response);

    const req = new Request('https://api/api/auth/login', { method: 'POST' });
    await window.fetch(req);

    expect(refresh).not.toHaveBeenCalled();
  });

  // ── Refresh failure → logout ────────────────────────────────────────────

  it('on refresh failure: calls logoutCallback and returns the original 401', async () => {
    const refresh = jest.fn().mockRejectedValue(new Error('Refresh token expired'));
    const logout = jest.fn().mockResolvedValue(undefined);
    installWithCallbacks(refresh, logout);

    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    const orig401 = { status: 401 } as Response;
    mockFetch.mockResolvedValueOnce(orig401);

    const result = await window.fetch('/api/v1/exams');

    expect(refresh).toHaveBeenCalledTimes(1);
    expect(logout).toHaveBeenCalledTimes(1);
    expect(result).toBe(orig401);
    // Original request fired once, no retry attempted after refresh failure.
    expect(mockFetch).toHaveBeenCalledTimes(1);
    errorSpy.mockRestore();
  });

  // ── Idempotency ─────────────────────────────────────────────────────────

  it('installing twice does not double-wrap window.fetch', async () => {
    const refresh = jest.fn().mockResolvedValue(undefined);
    mod.setTokenRefreshCallback(refresh);

    mod.setupFetchInterceptor();
    const afterFirst = window.fetch;
    mod.setupFetchInterceptor();
    const afterSecond = window.fetch;

    expect(afterFirst).toBe(afterSecond);
  });

  // ── Headers merge ───────────────────────────────────────────────────────

  it('merges Authorization header correctly when init.headers is undefined', async () => {
    const refresh = jest.fn().mockImplementation(async () => {
      localStorage.setItem(ACCESS_TOKEN_KEY, 'tok-2');
    });
    installWithCallbacks(refresh);

    mockFetch
      .mockResolvedValueOnce({ status: 401 } as Response)
      .mockResolvedValueOnce({ status: 200, ok: true } as Response);

    await window.fetch('/api/v1/exams');

    const retryInit = mockFetch.mock.calls[1][1] as RequestInit;
    const retryHeaders = retryInit.headers as Headers;
    expect(retryHeaders.get('Authorization')).toBe('Bearer tok-2');
  });

  it('merges Authorization header correctly when init.headers is a Headers instance', async () => {
    const refresh = jest.fn().mockImplementation(async () => {
      localStorage.setItem(ACCESS_TOKEN_KEY, 'tok-3');
    });
    installWithCallbacks(refresh);

    mockFetch
      .mockResolvedValueOnce({ status: 401 } as Response)
      .mockResolvedValueOnce({ status: 200, ok: true } as Response);

    const headers = new Headers();
    headers.set('Accept', 'application/json');
    await window.fetch('/api/v1/exams', { headers });

    const retryInit = mockFetch.mock.calls[1][1] as RequestInit;
    const retryHeaders = retryInit.headers as Headers;
    expect(retryHeaders.get('Accept')).toBe('application/json');
    expect(retryHeaders.get('Authorization')).toBe('Bearer tok-3');
  });
});

describe('executeTokenRefresh — cross-path mutex', () => {
  let mod: ApiClientModule;

  beforeEach(() => {
    jest.resetModules();
    localStorage.clear();
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    mod = require('../apiClient');
  });

  it('serialises parallel callers through the same refreshPromise', async () => {
    let resolveRefresh!: () => void;
    const refreshPromise = new Promise<void>((res) => { resolveRefresh = res; });
    const refresh = jest.fn().mockReturnValue(refreshPromise);
    mod.setTokenRefreshCallback(refresh);

    // Fire 5 callers concurrently before the refresh resolves.
    const callers = [0, 1, 2, 3, 4].map(() => mod.executeTokenRefresh());

    resolveRefresh();
    await Promise.all(callers);

    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it('throws when no refresh callback is registered (prevents silent no-op)', async () => {
    // No setTokenRefreshCallback() call — registry empty.
    await expect(mod.executeTokenRefresh()).rejects.toThrow(/No token refresh callback/);
  });

  it('resets refreshPromise after a failed refresh so the next caller can retry', async () => {
    const refresh = jest.fn()
      .mockRejectedValueOnce(new Error('temporary 500'))
      .mockResolvedValueOnce(undefined);
    mod.setTokenRefreshCallback(refresh);

    await expect(mod.executeTokenRefresh()).rejects.toThrow('temporary 500');
    await expect(mod.executeTokenRefresh()).resolves.toBeUndefined();

    expect(refresh).toHaveBeenCalledTimes(2);
  });
});
