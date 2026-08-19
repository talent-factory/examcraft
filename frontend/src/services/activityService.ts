/**
 * ActivityService — API client for `/api/v1/activity`.
 */

import {
  ActivityListResponse,
  ActivityScope,
  ActivityType,
} from '../types/activity';
import { ApiErrorKind } from '../types/submission';
import { statusToKind } from './submissionsService';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const ROOT = '/api/v1/activity';

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number;
  readonly detail: unknown;
  readonly issues: string[];

  constructor(params: {
    kind: ApiErrorKind;
    status: number;
    message: string;
    detail?: unknown;
    issues?: string[];
  }) {
    super(params.message);
    this.name = 'ApiError';
    this.kind = params.kind;
    this.status = params.status;
    this.detail = params.detail;
    this.issues = params.issues ?? [];
  }
}

async function readErrorBody(
  response: Response,
): Promise<{ message: string; detail: unknown; issues: string[] }> {
  // Read once as text so a non-JSON body (HTML proxy error page,
  // empty 401) is observable to the developer rather than getting
  // swallowed by an opaque `${status} ${statusText}` message.
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
      console.warn(
        `ActivityService: non-JSON ${response.status} response`,
        bodyText.slice(0, 500),
      );
      return {
        message: `${response.status} ${response.statusText}`,
        detail: bodyText,
        issues: [],
      };
    }
  }

  if (raw && typeof raw === 'object' && 'detail' in raw) {
    const detail = (raw as { detail: unknown }).detail;
    if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
      const obj = detail as { message?: unknown; issues?: unknown };
      const message =
        typeof obj.message === 'string'
          ? obj.message
          : `${response.status} ${response.statusText}`;
      const issues = Array.isArray(obj.issues)
        ? (obj.issues.filter((i): i is string => typeof i === 'string') as string[])
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

async function ensureOk(response: Response): Promise<Response> {
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

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('examcraft_access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function safeFetch(
  input: RequestInfo,
  init?: RequestInit,
): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (err) {
    // Network failures (offline, CORS, DNS) and AbortError land here.
    if ((err as { name?: string })?.name === 'AbortError') {
      // Discriminate aborts via a dedicated kind so callers can
      // suppress them without string-matching translated messages.
      throw new ApiError({
        kind: 'aborted',
        status: 0,
        message: 'Anfrage abgebrochen',
      });
    }
    // Preserve the original error name (e.g. SecurityError, TypeError)
    // so a misconfigured CSP / invalid URL doesn't masquerade as a
    // network problem when support is debugging.
    const errName = (err as { name?: string })?.name;
    const baseMessage = err instanceof Error ? err.message : 'Netzwerkfehler';
    const message =
      errName && errName !== 'Error'
        ? `Netzwerkfehler (${errName}): ${baseMessage}`
        : `Netzwerkfehler: ${baseMessage}`;
    throw new ApiError({
      kind: 'network',
      status: 0,
      message,
      detail: { name: errName, message: baseMessage },
    });
  }
}

export class ActivityService {
  static async list(params: {
    scope?: ActivityScope;
    types?: ActivityType[];
    limit?: number;
    offset?: number;
    signal?: AbortSignal;
  } = {}): Promise<ActivityListResponse> {
    const search = new URLSearchParams();
    if (params.scope) search.set('scope', params.scope);
    if (params.types && params.types.length > 0) {
      // Backend accepts a single CSV (not repeated keys) — match the
      // Pydantic ``types: str | None`` signature.
      search.set('types', params.types.join(','));
    }
    if (params.limit !== undefined) search.set('limit', String(params.limit));
    if (params.offset !== undefined) search.set('offset', String(params.offset));

    const query = search.toString();
    const url = `${API_BASE_URL}${ROOT}${query ? `?${query}` : ''}`;
    const response = await safeFetch(url, {
      method: 'GET',
      headers: authHeaders(),
      signal: params.signal,
    });
    await ensureOk(response);
    return (await response.json()) as ActivityListResponse;
  }
}
