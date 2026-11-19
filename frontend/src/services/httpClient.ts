/**
 * Shared HTTP client helpers for the TF-336 service layer.
 *
 * The existing services (`submissionsService`, `statisticsService`,
 * `gradesService`, …) each carry their own thin wrappers around
 * ``fetch``. Rather than refactoring all of them in one go, this module
 * extracts just the behaviours we need for the new TF-336 services
 * (Klassen, Studi, Moodle-Connections, Moodle-Roundtrip): a
 * ``safeFetch``, an ``ensureOk`` that surfaces structured ``ApiError``
 * (kind/status/issues), and an ``authHeaders`` helper (the
 * session cookie itself is sent by the global fetch interceptor).
 *
 * ``ApiError`` is intentionally re-exported so existing code that
 * imports from ``submissionsService`` keeps working — the two modules
 * share the same identity. ``safeFetch`` is re-exported from there too:
 * this module used to carry identical copies of it and of ``ensureOk``,
 * and the copies drifted (only one learned to keep ``error_code``,
 * TF-772).
 *
 * ``ensureOk`` is wrapped, not re-exported as-is: ``submissionsService``'s
 * version labels a non-JSON error body with its own name in the console
 * warning. Eight services hang off this module (orgUnits, studentClasses,
 * students, audit, roles, moodleConnections, both ops services), and a
 * broken body from any of them should say ``httpClient``, not
 * ``SubmissionsService``, so an incident log points at the right module.
 */

import { ApiError, ensureOk as ensureOkWith, safeFetch } from './submissionsService';

export { ApiError, safeFetch };

export const ensureOk = (response: Response): Promise<Response> =>
  ensureOkWith(response, 'httpClient');


export const API_BASE_URL =
  process.env.REACT_APP_API_URL || 'http://localhost:8000';


// Die Anmeldung ist ein httpOnly-Session-Cookie (EXAMCRAFT-126); der globale
// fetch-Interceptor sendet es mit und baut bei einem 401 die Session lokal ab.
// Header gibt es nur noch für Content-Type & Co.
export function authHeaders(extra: HeadersInit = {}): HeadersInit {
  return { ...extra };
}


export async function getJson<T>(path: string): Promise<T> {
  const response = await safeFetch(`${API_BASE_URL}${path}`, { method: 'GET', headers: authHeaders() });
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


export async function postVoid(
  path: string,
  body: unknown,
): Promise<void> {
  const response = await safeFetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  });
  await ensureOk(response);
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
  const response = await safeFetch(`${API_BASE_URL}${path}`, { method: 'DELETE', headers: authHeaders() });
  await ensureOk(response);
}
