import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { withTokenRefreshLock, ACCESS_TOKEN_KEY, RefreshTrigger } from './tokenRefreshLock';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

let refreshPromise: Promise<void> | null = null;
let tokenRefreshCallback: (() => Promise<void>) | null = null;
let logoutCallback: (() => Promise<void>) | null = null;
let adoptStoredTokensCallback: (() => Promise<void>) | null = null;

export function setTokenRefreshCallback(fn: () => Promise<void>): void {
  tokenRefreshCallback = fn;
}

export function setLogoutCallback(fn: () => Promise<void>): void {
  logoutCallback = fn;
}

// Called when another tab won the refresh race — the fresh tokens are already
// in localStorage and only need to be pulled into this tab's auth state.
// Must throw if nothing usable was adopted (mirrors the `rotate` contract
// below) rather than resolving silently, or a lost adoption looks like a
// successful refresh to every caller of executeTokenRefresh.
export function setAdoptStoredTokensCallback(fn: () => Promise<void>): void {
  adoptStoredTokensCallback = fn;
}

// Single entry point for token refresh — all interceptor/timer paths (axios
// interceptor, fetch interceptor, proactive timer) must go through this so
// concurrent callers share one inflight refresh instead of racing for a
// rotating refresh token. `refreshPromise` deduplicates within this tab, the
// Web Lock inside withTokenRefreshLock deduplicates across tabs (TF-607).
// The one exception is AuthContext's mount-time flow, which calls
// withTokenRefreshLock directly — safe because it only runs once, before the
// timer or either interceptor has anything to race against.
export async function executeTokenRefresh(trigger: RefreshTrigger = 'unknown'): Promise<void> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = withTokenRefreshLock(
    async () => {
      if (!tokenRefreshCallback) {
        throw new Error('No token refresh callback registered');
      }
      await tokenRefreshCallback();
    },
    async () => {
      if (!adoptStoredTokensCallback) {
        throw new Error('No adopt-stored-tokens callback registered');
      }
      await adoptStoredTokensCallback();
    },
    trigger,
  ).finally(() => { refreshPromise = null; });

  return refreshPromise;
}

// Local-only teardown by design (TF-607): AuthContext registers this as
// `clearLocalSession`, not `logout` — `logout` calls AuthService.logout(),
// which revokes *every* session of the user on the backend. Escalating a
// single request's auth failure to a full server-side revoke would sign the
// user out of every open tab and device, not just recover this one.
export function triggerAuthLogout(): void {
  if (logoutCallback) {
    logoutCallback().catch((err) => {
      console.error('[apiClient] Logout failed:', err);
    });
  }
}

let fetchInterceptorInstalled = false;

export function setupFetchInterceptor(): void {
  if (fetchInterceptorInstalled) return;
  fetchInterceptorInstalled = true;

  const originalFetch = window.fetch.bind(window);

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const response = await originalFetch(input, init);

    if (response.status !== 401) return response;

    const url = input instanceof Request ? input.url : String(input);
    if (url.includes('/api/auth/')) return response;

    try {
      await executeTokenRefresh('fetch-401');
    } catch (err) {
      console.error('[apiClient] Fetch refresh failed:', err);
      triggerAuthLogout();
      return response;
    }

    const newToken = localStorage.getItem(ACCESS_TOKEN_KEY);
    const newHeaders = new Headers(init?.headers);
    if (newToken) newHeaders.set('Authorization', `Bearer ${newToken}`);

    return originalFetch(input, { ...init, headers: newHeaders });
  };
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem(ACCESS_TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (
      !originalRequest ||
      error.response?.status !== 401 ||
      originalRequest.url?.includes('/api/auth/')
    ) {
      return Promise.reject(error);
    }

    if (originalRequest._retry) {
      triggerAuthLogout();
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      await executeTokenRefresh('axios-401');
    } catch (refreshErr) {
      console.error('[apiClient] Axios refresh failed:', refreshErr);
      triggerAuthLogout();
      return Promise.reject(error);
    }

    const newToken = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (newToken) {
      originalRequest.headers.Authorization = `Bearer ${newToken}`;
    }
    return apiClient(originalRequest);
  }
);
