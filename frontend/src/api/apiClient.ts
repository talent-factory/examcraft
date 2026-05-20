import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';

const ACCESS_TOKEN_KEY = 'examcraft_access_token';
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

let refreshPromise: Promise<void> | null = null;
let tokenRefreshCallback: (() => Promise<void>) | null = null;
let logoutCallback: (() => Promise<void>) | null = null;

export function setTokenRefreshCallback(fn: () => Promise<void>): void {
  tokenRefreshCallback = fn;
}

export function setLogoutCallback(fn: () => Promise<void>): void {
  logoutCallback = fn;
}

// Single entry point for token refresh — all paths (axios interceptor,
// fetch interceptor, proactive timer) must go through this so concurrent
// callers share one inflight refresh instead of racing for a rotating
// refresh token.
export async function executeTokenRefresh(): Promise<void> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      if (!tokenRefreshCallback) {
        throw new Error('No token refresh callback registered');
      }
      await tokenRefreshCallback();
    })().finally(() => { refreshPromise = null; });
  }
  return refreshPromise;
}

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
      await executeTokenRefresh();
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
      await executeTokenRefresh();
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
