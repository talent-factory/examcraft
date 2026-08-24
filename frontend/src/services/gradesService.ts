/**
 * GradesService — API client for /api/v1/grades/* + review-queue.
 *
 * Mirrors `core/backend/api/grades.py`. Reuses the ApiError shape and
 * fetch helpers from SubmissionsService, but lives in a separate
 * module so the bundle splits cleanly between import-flow and
 * review-flow code paths.
 */

import { ApiError, statusToKind } from './submissionsService';
import {
  BulkApproveResult,
  GradeAction,
  ReviewQueue,
  ReviewQueueFilter,
} from '../types/submission';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// TF-626-Review: `statusToKind` used to be documented here as a local
// copy ("trivial and stable enough to copy") — that exact copy therefore
// didn't know about `409 → 'conflict'`, even though `gradingSchemesService`
// already threw it at runtime. `ApiError` is already imported from
// `submissionsService` anyway (see above), so the cross-import already
// exists; `statusToKind` now follows that same path instead of keeping
// its own copy.

async function readErrorBody(response: Response): Promise<{ message: string }> {
  try {
    const text = await response.text();
    if (!text) {
      return { message: `${response.status} ${response.statusText}` };
    }
    try {
      const raw = JSON.parse(text);
      if (raw && typeof raw === 'object' && 'detail' in raw) {
        const detail = (raw as { detail: unknown }).detail;
        if (typeof detail === 'string') return { message: detail };
        if (
          detail &&
          typeof detail === 'object' &&
          'message' in detail &&
          typeof (detail as { message?: unknown }).message === 'string'
        ) {
          return { message: (detail as { message: string }).message };
        }
      }
    } catch {
      // fall through
    }
    return { message: text || `${response.status} ${response.statusText}` };
  } catch {
    return { message: `${response.status} ${response.statusText}` };
  }
}

async function ensureOk(response: Response): Promise<Response> {
  if (response.ok) return response;
  const { message } = await readErrorBody(response);
  throw new ApiError({
    kind: statusToKind(response.status),
    status: response.status,
    message,
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

function buildQuery(filter: ReviewQueueFilter): string {
  const params = new URLSearchParams();
  if (filter.confidence_min !== undefined)
    params.set('confidence_min', String(filter.confidence_min));
  if (filter.confidence_max !== undefined)
    params.set('confidence_max', String(filter.confidence_max));
  if (filter.question_id !== undefined)
    params.set('question_id', String(filter.question_id));
  if (filter.student_id !== undefined)
    params.set('student_id', String(filter.student_id));
  if (filter.limit !== undefined) params.set('limit', String(filter.limit));
  if (filter.offset !== undefined) params.set('offset', String(filter.offset));
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export class GradesService {
  static async getReviewQueue(
    examId: number,
    filter: ReviewQueueFilter = {},
  ): Promise<ReviewQueue> {
    const url = `${API_BASE_URL}/api/v1/exams/${examId}/review-queue${buildQuery(
      filter,
    )}`;
    const response = await safeFetch(url, {
      method: 'GET',
      headers: authHeaders(),
    });
    await ensureOk(response);
    return (await response.json()) as ReviewQueue;
  }

  static async approve(gradeId: number): Promise<GradeAction> {
    const response = await safeFetch(
      `${API_BASE_URL}/api/v1/grades/${gradeId}/approve`,
      { method: 'POST', headers: authHeaders() },
    );
    await ensureOk(response);
    return (await response.json()) as GradeAction;
  }

  static async override(
    gradeId: number,
    body: { points_awarded: number; reviewer_note?: string | null },
  ): Promise<GradeAction> {
    const response = await safeFetch(
      `${API_BASE_URL}/api/v1/grades/${gradeId}/override`,
      {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(body),
      },
    );
    await ensureOk(response);
    return (await response.json()) as GradeAction;
  }

  static async bulkApprove(params: {
    examId: number;
    confidenceMin?: number;
    gradeIds?: number[];
  }): Promise<BulkApproveResult> {
    const body: Record<string, unknown> = { exam_id: params.examId };
    if (params.confidenceMin !== undefined)
      body.confidence_min = params.confidenceMin;
    if (params.gradeIds !== undefined) body.grade_ids = params.gradeIds;

    const response = await safeFetch(
      `${API_BASE_URL}/api/v1/grades/bulk-approve`,
      {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(body),
      },
    );
    await ensureOk(response);
    return (await response.json()) as BulkApproveResult;
  }
}
