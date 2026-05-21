/**
 * apiClient.test.ts
 *
 * Unit-Tests für core/frontend/src/api/apiClient.ts
 *
 * Strategie:
 *  - axios wird vollständig gemockt (jest.mock wird gehoisted, muss vor Imports stehen)
 *  - Die Fake-Instance ist per Closure zugänglich
 *  - Die Instance ist selbst callable (wegen `apiClient(originalRequest)` im Retry-Pfad)
 *  - Request- und Response-Interceptor-Handler werden direkt aufgerufen
 *  - Das module-level `refreshPromise` wird durch jest.resetModules() zwischen Tests isoliert
 */

// ─── Axios-Mock ──────────────────────────────────────────────────────────────
// MUSS vor allen Imports stehen – jest.mock() wird gehoisted
jest.mock('axios', () => {
  const requestHandlers: Array<(config: any) => any> = [];
  const responseHandlers: Array<[(res: any) => any, (err: any) => any]> = [];

  // The instance must also be callable because apiClient.ts does:
  //   return apiClient(originalRequest);
  // We implement it as a jest.fn() with the interceptors attached.
  const instance = jest.fn().mockResolvedValue({ data: 'retried' }) as any;
  instance.interceptors = {
    request: {
      use: jest.fn((handler: (config: any) => any) => {
        requestHandlers.push(handler);
      }),
    },
    response: {
      use: jest.fn((onFulfilled: (res: any) => any, onRejected: (err: any) => any) => {
        responseHandlers.push([onFulfilled, onRejected]);
      }),
    },
  };
  // Expose handler arrays so tests can invoke them
  instance._requestHandlers = requestHandlers;
  instance._responseHandlers = responseHandlers;

  return {
    __esModule: true,
    default: {
      create: jest.fn(() => instance),
      // Also expose via __instance for direct access
      __instance: instance,
    },
  };
});

// ─── Imports ─────────────────────────────────────────────────────────────────
// eslint-disable-next-line import/first
import axios from 'axios';
// eslint-disable-next-line import/first
import { setTokenRefreshCallback, setLogoutCallback } from '../apiClient';

// ─── Grab the fake instance ───────────────────────────────────────────────────
// `axios` is the default export, so (axios as any) is `{ create: jest.fn(), __instance: ... }`.
// The instance was created when apiClient module loaded (axios.create() call).
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const fakeAxios = axios as any;
const instance: any =
  fakeAxios.create?.mock?.results?.[0]?.value ??
  fakeAxios.__instance;

// ─── Helper accessors ─────────────────────────────────────────────────────────
function getRequestInterceptor(): (config: any) => any {
  return instance._requestHandlers[0];
}

function getResponseErrorHandler(): (error: any) => Promise<any> {
  return instance._responseHandlers[0]?.[1];
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('apiClient', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    // Reset callbacks to safe no-ops
    setTokenRefreshCallback(async () => {});
    setLogoutCallback(async () => {});
    // Restore the default retry mock after clearAllMocks
    instance.mockResolvedValue({ data: 'retried' });
  });

  // ── Request interceptor ───────────────────────────────────────────────────

  describe('request interceptor', () => {
    it('attaches Authorization header when token in localStorage', () => {
      localStorage.setItem('examcraft_access_token', 'my-token');
      const config = { headers: {} as Record<string, string> };

      const result = getRequestInterceptor()(config);

      expect(result.headers.Authorization).toBe('Bearer my-token');
    });

    it('does not set Authorization header when no token present', () => {
      const config = { headers: {} as Record<string, string> };

      const result = getRequestInterceptor()(config);

      expect(result.headers.Authorization).toBeUndefined();
    });
  });

  // ── Response interceptor – 401 handling ──────────────────────────────────

  describe('response interceptor — 401 handling', () => {
    it('passes through non-401 errors unchanged', async () => {
      const error = {
        response: { status: 500 },
        config: { url: '/api/v1/exams', headers: {} },
      };

      await expect(getResponseErrorHandler()(error)).rejects.toEqual(error);
    });

    it('passes through 401 on /api/auth/ endpoints without retry', async () => {
      const error = {
        response: { status: 401 },
        config: { url: '/api/auth/refresh', headers: {}, _retry: false },
      };

      await expect(getResponseErrorHandler()(error)).rejects.toEqual(error);
    });

    it('calls tokenRefreshCallback on 401 and retries the original request', async () => {
      const mockRefresh = jest.fn().mockResolvedValue(undefined);
      setTokenRefreshCallback(mockRefresh);
      localStorage.setItem('examcraft_access_token', 'new-token');

      const error = {
        response: { status: 401 },
        config: { url: '/api/v1/exams', headers: {}, _retry: false },
      };

      const result = await getResponseErrorHandler()(error);

      expect(mockRefresh).toHaveBeenCalledTimes(1);
      // After refresh the interceptor calls apiClient(originalRequest) – our mock returns { data: 'retried' }
      expect(result).toEqual({ data: 'retried' });
    });

    it('sets _retry flag so a second 401 on the same config is not retried again', async () => {
      const mockRefresh = jest.fn().mockResolvedValue(undefined);
      setTokenRefreshCallback(mockRefresh);
      localStorage.setItem('examcraft_access_token', 'new-token');

      const alreadyRetried = {
        response: { status: 401 },
        config: { url: '/api/v1/exams', headers: {}, _retry: true },
      };

      await expect(getResponseErrorHandler()(alreadyRetried)).rejects.toEqual(alreadyRetried);
      expect(mockRefresh).not.toHaveBeenCalled();
    });

    it('on second 401 (_retry=true) the logoutCallback is invoked', async () => {
      const mockLogout = jest.fn().mockResolvedValue(undefined);
      setLogoutCallback(mockLogout);

      const alreadyRetried = {
        response: { status: 401 },
        config: { url: '/api/v1/exams', headers: {}, _retry: true },
      };

      await expect(getResponseErrorHandler()(alreadyRetried)).rejects.toEqual(alreadyRetried);

      // logoutCallback is fire-and-forget — let the microtask queue drain.
      await Promise.resolve();
      expect(mockLogout).toHaveBeenCalledTimes(1);
    });

    it('on refresh failure: invokes logoutCallback and rejects with original error', async () => {
      const refreshErr = new Error('Refresh token expired');
      const mockRefresh = jest.fn().mockRejectedValue(refreshErr);
      const mockLogout = jest.fn().mockResolvedValue(undefined);
      setTokenRefreshCallback(mockRefresh);
      setLogoutCallback(mockLogout);

      const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      const orig401 = {
        response: { status: 401 },
        config: { url: '/api/v1/exams', headers: {}, _retry: false },
      };

      await expect(getResponseErrorHandler()(orig401)).rejects.toEqual(orig401);
      await Promise.resolve();
      expect(mockLogout).toHaveBeenCalledTimes(1);
      errorSpy.mockRestore();
    });

    it('attaches the refreshed token to the retried request headers', async () => {
      const mockRefresh = jest.fn().mockImplementation(async () => {
        localStorage.setItem('examcraft_access_token', 'rotated-token');
      });
      setTokenRefreshCallback(mockRefresh);

      const error = {
        response: { status: 401 },
        config: { url: '/api/v1/exams', headers: {} as Record<string, string>, _retry: false },
      };

      await getResponseErrorHandler()(error);

      // The interceptor mutates the original config's headers before calling
      // apiClient(originalRequest). Verify the rewrite happened.
      expect(error.config.headers.Authorization).toBe('Bearer rotated-token');
    });

    it('calls tokenRefreshCallback only once for parallel 401s (mutex)', async () => {
      // Use a manually-controlled promise to keep refreshPromise alive
      // long enough that the second 401 arrives while the first is still pending.
      let resolveRefresh!: () => void;
      const refreshPromiseExternal = new Promise<void>((res) => {
        resolveRefresh = res;
      });
      const mockRefresh = jest.fn().mockReturnValue(refreshPromiseExternal);
      setTokenRefreshCallback(mockRefresh);
      localStorage.setItem('examcraft_access_token', 'new-token');

      const handler = getResponseErrorHandler();

      const error1 = {
        response: { status: 401 },
        config: { url: '/api/v1/a', headers: {}, _retry: false },
      };
      const error2 = {
        response: { status: 401 },
        config: { url: '/api/v1/b', headers: {}, _retry: false },
      };

      // Fire both handlers without awaiting – both arrive before refresh resolves
      const p1 = handler(error1).catch(() => {});
      const p2 = handler(error2).catch(() => {});

      // Now let the refresh complete
      resolveRefresh();
      await Promise.all([p1, p2]);

      // Despite two concurrent 401s, the callback must have been invoked only once
      expect(mockRefresh).toHaveBeenCalledTimes(1);
    });
  });
});
