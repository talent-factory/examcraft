/**
 * SubmissionsService — API client for `/api/v1/submissions/*`.
 *
 * Mirrors `core/backend/api/submissions.py`. Auth-token handling
 * matches the project's other service classes (Bearer from
 * localStorage). All errors raise an `ApiError` with `kind`/`status`
 * so callers can branch on intent (network vs auth vs validation vs
 * server).
 */

import {
  ApiErrorKind,
  DriverName,
  ImportJob,
  ImportPreview,
  SubmissionDetail,
  SubmissionList,
} from '../types/submission';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const ROOT = '/api/v1/submissions';

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

function statusToKind(status: number): ApiErrorKind {
  if (status === 401) return 'auth';
  if (status === 403) return 'permission';
  if (status === 404) return 'not_found';
  if (status === 413) return 'too_large';
  if (status === 422 || status === 400) return 'validation';
  if (status >= 500) return 'server';
  return 'unknown';
}

async function readErrorBody(
  response: Response,
): Promise<{ message: string; detail: unknown; issues: string[] }> {
  // Read once as text so a non-JSON body (HTML proxy error page, plain
  // 502, empty 401) is observable to the developer rather than getting
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
        `SubmissionsService: non-JSON ${response.status} response`,
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

function authHeaders(extra: HeadersInit = {}): HeadersInit {
  const token = localStorage.getItem('examcraft_access_token');
  return {
    ...extra,
    ...(token && { Authorization: `Bearer ${token}` }),
  };
}

async function safeFetch(
  input: RequestInfo,
  init?: RequestInit,
): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (err) {
    // Network failures (offline, CORS, DNS) surface here.
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
        err instanceof Error
          ? `Netzwerkfehler: ${err.message}`
          : 'Netzwerkfehler',
    });
  }
}

export class SubmissionsService {
  static async preview(params: {
    examId: number;
    file: File;
    driverName?: DriverName;
    signal?: AbortSignal;
  }): Promise<ImportPreview> {
    const formData = new FormData();
    formData.append('exam_id', String(params.examId));
    formData.append('driver_name', params.driverName ?? 'moodle_csv');
    formData.append('file', params.file);

    const response = await safeFetch(`${API_BASE_URL}${ROOT}/import/preview`, {
      method: 'POST',
      headers: authHeaders(),
      body: formData,
      signal: params.signal,
    });
    await ensureOk(response);
    return (await response.json()) as ImportPreview;
  }

  static async commit(params: {
    examId: number;
    file: File;
    driverName?: DriverName;
    signal?: AbortSignal;
  }): Promise<ImportJob> {
    const formData = new FormData();
    formData.append('exam_id', String(params.examId));
    formData.append('driver_name', params.driverName ?? 'moodle_csv');
    formData.append('file', params.file);

    const response = await safeFetch(`${API_BASE_URL}${ROOT}/import/commit`, {
      method: 'POST',
      headers: authHeaders(),
      body: formData,
      signal: params.signal,
    });
    await ensureOk(response);
    return (await response.json()) as ImportJob;
  }

  static async getImportJob(jobId: number): Promise<ImportJob> {
    const response = await safeFetch(
      `${API_BASE_URL}${ROOT}/import-jobs/${jobId}`,
      { method: 'GET', headers: authHeaders() },
    );
    await ensureOk(response);
    return (await response.json()) as ImportJob;
  }

  static async listForExam(examId: number): Promise<SubmissionList> {
    const url = `${API_BASE_URL}${ROOT}?exam_id=${examId}`;
    const response = await safeFetch(url, {
      method: 'GET',
      headers: authHeaders(),
    });
    await ensureOk(response);
    return (await response.json()) as SubmissionList;
  }

  static async getDetail(submissionId: number): Promise<SubmissionDetail> {
    const response = await safeFetch(
      `${API_BASE_URL}${ROOT}/${submissionId}`,
      { method: 'GET', headers: authHeaders() },
    );
    await ensureOk(response);
    return (await response.json()) as SubmissionDetail;
  }

  /**
   * TF-336: Moodle-API-Import (Pro+ only). Backend wirft 402 wenn der
   * Tier den ``moodle_api``-Driver nicht freischaltet — der Caller
   * unterscheidet das via ``ApiError.status``.
   */
  static async apiPreview(params: {
    examId: number;
    quizId: number;
    signal?: AbortSignal;
  }): Promise<ImportPreview> {
    const response = await safeFetch(
      `${API_BASE_URL}${ROOT}/import/api-preview`,
      {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          exam_id: params.examId,
          quiz_id: params.quizId,
        }),
        signal: params.signal,
      },
    );
    await ensureOk(response);
    return (await response.json()) as ImportPreview;
  }

  static async apiCommit(params: {
    examId: number;
    quizId: number;
    signal?: AbortSignal;
  }): Promise<ImportJob> {
    const response = await safeFetch(
      `${API_BASE_URL}${ROOT}/import/api-commit`,
      {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          exam_id: params.examId,
          quiz_id: params.quizId,
        }),
        signal: params.signal,
      },
    );
    await ensureOk(response);
    return (await response.json()) as ImportJob;
  }
}
