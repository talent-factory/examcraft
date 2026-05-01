/**
 * Shared HTTP client helpers for the TF-336 service layer.
 *
 * The existing services (`submissionsService`, `statisticsService`,
 * `gradesService`, …) each carry their own thin wrappers around
 * ``fetch``. Rather than refactoring all of them in one go, this module
 * extracts just the behaviours we need for the new TF-336 services
 * (Klassen, Studi, Moodle-Connections, Moodle-Roundtrip): a
 * ``safeFetch``, an ``ensureOk`` that surfaces structured ``ApiError``
 * (kind/status/issues), an ``authHeaders`` helper, and a token-key
 * constant.
 *
 * ``ApiError`` is intentionally re-exported so existing code that
 * imports from ``submissionsService`` keeps working — the two modules
 * share the same identity.
 */

import { ApiError } from './submissionsService';
import type { ApiErrorKind } from '../types/submission';

export { ApiError };


export const API_BASE_URL =
  process.env.REACT_APP_API_URL || 'http://localhost:8000';
export const ACCESS_TOKEN_KEY = 'examcraft_access_token';


export function authHeaders(extra: HeadersInit = {}): HeadersInit {
  const token = localStorage.getItem(ACCESS_TOKEN_KEY);
  return {
    ...extra,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}


function statusToKind(status: number): ApiErrorKind {
  if (status === 401) return 'auth';
  if (status === 403) return 'permission';
  if (status === 404) return 'not_found';
  if (status === 413) return 'too_large';
  // 402 falls under "permission" semantically — the user lacks
  // *paid* access. The frontend's QuotaBanner reads ``status === 402``
  // explicitly, so this label is just for telemetry/grouping.
  if (status === 402) return 'permission';
  if (status === 422 || status === 400) return 'validation';
  if (status === 409) return 'validation';
  if (status >= 500) return 'server';
  return 'unknown';
}


async function readErrorBody(
  response: Response,
): Promise<{ message: string; detail: unknown; issues: string[] }> {
  let bodyText = '';
  try {
    bodyText = await response.text();
  } catch {
    return {
      message: `${response.status} ${response.statusText}`,
      detail: null,
      issues: [],
    };
  }
  let raw: unknown = null;
  if (bodyText) {
    try {
      raw = JSON.parse(bodyText);
    } catch {
      return {
        message: `${response.status} ${response.statusText}`,
        detail: bodyText,
        issues: [],
      };
    }
  }
  if (raw && typeof raw === 'object' && 'detail' in raw) {
    const detail = (raw as { detail: unknown }).detail;
    // Tier-Quota 402 + Validation 422 carry structured detail objects.
    if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
      const obj = detail as { message?: unknown; issues?: unknown };
      const message =
        typeof obj.message === 'string'
          ? obj.message
          : `${response.status} ${response.statusText}`;
      const issues = Array.isArray(obj.issues)
        ? (obj.issues.filter(
            (i): i is string => typeof i === 'string',
          ) as string[])
        : [];
      return { message, detail, issues };
    }
    return { message: String(detail), detail, issues: [] };
  }
  return {
    message: `${response.status} ${response.statusText}`,
    detail: raw,
    issues: [],
  };
}


export async function ensureOk(response: Response): Promise<Response> {
  if (response.ok) return response;
  const { message, detail, issues } = await readErrorBody(response);
  throw new ApiError({
    kind: statusToKind(response.status),
    status: response.status,
    message,
    detail,
    issues,
  });
}


export async function safeFetch(
  input: RequestInfo,
  init?: RequestInit,
): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (err) {
    if ((err as { name?: string })?.name === 'AbortError') {
      throw new ApiError({
        kind: 'network',
        status: 0,
        message: 'Anfrage abgebrochen',
      });
    }
    throw new ApiError({
      kind: 'network',
      status: 0,
      message:
        err instanceof Error ? `Netzwerkfehler: ${err.message}` : 'Netzwerkfehler',
    });
  }
}


export async function getJson<T>(path: string): Promise<T> {
  const response = await safeFetch(`${API_BASE_URL}${path}`, {
    method: 'GET',
    headers: authHeaders(),
  });
  await ensureOk(response);
  return (await response.json()) as T;
}


export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await safeFetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  });
  await ensureOk(response);
  return (await response.json()) as T;
}


export async function patchJson<T>(path: string, body: unknown): Promise<T> {
  const response = await safeFetch(`${API_BASE_URL}${path}`, {
    method: 'PATCH',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  });
  await ensureOk(response);
  return (await response.json()) as T;
}


export async function deleteVoid(path: string): Promise<void> {
  const response = await safeFetch(`${API_BASE_URL}${path}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  await ensureOk(response);
}
