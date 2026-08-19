/**
 * GradingSchemesService — API client for `/api/v1/grading-schemes/*`.
 *
 * Mirrors the backend in `core/backend/api/grading_schemes.py`. Auth-
 * token handling matches the project's other service classes (Bearer
 * from localStorage). All errors raise an `ApiError` with a `kind`
 * field so callers can branch on intent without re-parsing status
 * codes.
 */

import { ApiError, statusToKind } from './submissionsService';
import {
  GradingSchemeCreate,
  GradingSchemeListOut,
  GradingSchemeOut,
  GradingSchemeUpdate,
} from '../types/gradingScheme';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const ROOT = '/api/v1/grading-schemes';

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    if (response.status === 204) {
      return undefined as unknown as T;
    }
    return (await response.json()) as T;
  }

  let detail: unknown;
  let issues: string[] = [];
  try {
    const body = await response.json();
    detail = body.detail;
    if (Array.isArray(body.detail)) {
      issues = (body.detail as Array<{ msg?: string }>)
        .map((d) => d?.msg)
        .filter((m): m is string => typeof m === 'string');
    }
  } catch {
    // Non-JSON error body — capture raw text for Sentry/console so an
    // upstream HTML error page (CDN/nginx/fly health check) doesn't
    // disappear without trace.
    try {
      const text = await response.text();
      if (text) {
        detail = text.slice(0, 500);
        console.warn(
          '[GradingSchemesService] non-JSON error body for status',
          response.status,
          text.slice(0, 200),
        );
      }
    } catch {
      /* body fully unavailable */
    }
  }
  const message =
    typeof detail === 'string'
      ? detail
      : `Request failed (${response.status})`;
  throw new ApiError({
    // TF-626-Review: vorher eine inline-Ternary, die nur einen Teil der
    // Codes kannte und alles Unbekannte auf 'server' abbildete (statt
    // 'unknown' wie ueberall sonst) — jetzt dasselbe kanonische Mapping wie
    // jeder andere Service, siehe submissionsService.ts.
    kind: statusToKind(response.status),
    status: response.status,
    message,
    detail,
    issues,
  });
}

export class GradingSchemesService {
  /**
   * List grading schemes. By default returns system schemes plus the
   * caller's own institution schemes. A SuperAdmin may pass
   * ``institutionId`` to scope institution-owned schemes to a *target*
   * institution instead (TF-431 admin institution editor).
   */
  static async list(
    includeSystem = true,
    institutionId?: number | null,
  ): Promise<GradingSchemeListOut> {
    let url = `${API_BASE_URL}${ROOT}?include_system=${includeSystem}`;
    if (institutionId != null) {
      url += `&institution_id=${institutionId}`;
    }
    const response = await fetch(url, { headers: authHeaders() });
    return handleResponse<GradingSchemeListOut>(response);
  }

  static async get(id: number): Promise<GradingSchemeOut> {
    const response = await fetch(`${API_BASE_URL}${ROOT}/${id}`, {
      headers: authHeaders(),
    });
    return handleResponse<GradingSchemeOut>(response);
  }

  static async create(payload: GradingSchemeCreate): Promise<GradingSchemeOut> {
    const response = await fetch(`${API_BASE_URL}${ROOT}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(payload),
    });
    return handleResponse<GradingSchemeOut>(response);
  }

  static async update(
    id: number,
    payload: GradingSchemeUpdate,
  ): Promise<GradingSchemeOut> {
    const response = await fetch(`${API_BASE_URL}${ROOT}/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(payload),
    });
    return handleResponse<GradingSchemeOut>(response);
  }

  static async delete(id: number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}${ROOT}/${id}`, {
      method: 'DELETE',
      headers: authHeaders(),
    });
    return handleResponse<void>(response);
  }
}
