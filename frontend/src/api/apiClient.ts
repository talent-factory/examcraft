import axios, { AxiosInstance } from 'axios';

// EXAMCRAFT-126: Die Anmeldung ist eine serverseitige Session (BFF). Der
// Browser hält nur ein opakes httpOnly-Cookie und sendet es bei jedem
// Request mit; es gibt weder Tokens im Browser noch einen Refresh.
//
// Ausnahmen vom automatischen 401-Logout:
// - `/api/auth/me` und `/api/v1/auth/` (Login-Flow) beantwortet der
//   AuthContext selbst: ein 401 heisst dort schlicht "nicht angemeldet".
// - `/api/admin/impersonate/end` (TF-743) läuft unter der aktuellen Identität;
//   ein 401 darf die Admin-Session nicht lokal abräumen.
const AUTH_EXCLUDED_URL_PATTERNS = ['/api/auth/me', '/api/v1/auth/', '/api/admin/impersonate/end'];
const isAuthExcluded = (url: string | undefined): boolean =>
  !!url && AUTH_EXCLUDED_URL_PATTERNS.some((pattern) => url.includes(pattern));

export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

let logoutCallback: (() => Promise<void>) | null = null;

export function setLogoutCallback(fn: () => Promise<void>): void {
  logoutCallback = fn;
}

// Lokaler Abbau der Session (State leeren, zur Anmeldung leiten). Beendet die
// Server-Session nicht: das Cookie ist bei einem 401 ohnehin ungültig.
export function triggerAuthLogout(): void {
  if (logoutCallback) {
    logoutCallback().catch((err) => {
      console.error('[apiClient] Logout failed:', err);
    });
  }
}

const isApiRequest = (url: string): boolean =>
  url.startsWith(API_BASE_URL) || url.startsWith('/api/') || url.startsWith('/ws/');

let fetchInterceptorInstalled = false;

/**
 * Sorgt dafür, dass jeder fetch() an die API das Session-Cookie mitschickt
 * (`credentials: 'include'`), und baut bei einem 401 die lokale Session ab.
 * So müssen die Services weder Tokens noch Header kennen.
 */
export function setupFetchInterceptor(): void {
  if (fetchInterceptorInstalled) return;
  fetchInterceptorInstalled = true;

  const originalFetch = window.fetch.bind(window);

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = input instanceof Request ? input.url : String(input);
    const apiRequest = isApiRequest(url);
    const response = await originalFetch(
      input,
      apiRequest ? { credentials: 'include', ...init } : init,
    );

    if (apiRequest && response.status === 401 && !isAuthExcluded(url)) {
      triggerAuthLogout();
    }
    return response;
  };
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !isAuthExcluded(error.config?.url)) {
      triggerAuthLogout();
    }
    return Promise.reject(error);
  },
);
