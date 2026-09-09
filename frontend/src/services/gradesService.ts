/**
 * GradesService — API client for /api/v1/grades/* + review-queue.
 *
 * Mirrors `core/backend/api/grades.py`.
 *
 * TF-772: this module used to share `ApiError` and the fetch helpers with
 * `submissionsService`, and its two consumers rendered `err.message` — which
 * is the backend's `detail`, hardcoded German in `grades.py` regardless of the
 * user's locale. It now throws `AppError` with a code per operation instead;
 * see `errors/codes/grades.ts` for what that costs and why the fix belongs in
 * the backend. The shared helpers stayed behind with the services that still
 * use them: nothing here needs `ApiErrorKind` any more, because the consumers
 * distinguish failures by code, not by kind.
 */

import { AppError, AppErrorCode, appErrorFromResponse } from '../errors';
import {
  BulkApproveResult,
  GradeAction,
  ReviewQueue,
  ReviewQueueFilter,
} from '../types/submission';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function authHeaders(extra: HeadersInit = {}): HeadersInit {
  const token = localStorage.getItem('examcraft_access_token');
  return {
    ...extra,
    ...(token && { Authorization: `Bearer ${token}` }),
  };
}

/**
 * One grades request, with the failing operation's code.
 *
 * `fetch` rejects only on a network-level failure — no response, so no body and
 * no status. That is the one branch `appErrorFromResponse` cannot serve, and it
 * still has to end as an `AppError`: an untyped rejection would reach
 * `translateError` and be answered with the caller's fallback key rather than
 * this code's sentence.
 */
async function request(
  code: AppErrorCode,
  url: string,
  init: RequestInit,
): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(url, init);
  } catch (err) {
    throw new AppError(code, err instanceof Error ? err.message : undefined);
  }

  if (!response.ok) {
    throw await appErrorFromResponse(response, code);
  }
  return response;
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
    const response = await request('grades_review_queue_load_failed', url, {
      method: 'GET',
      headers: authHeaders(),
    });
    return (await response.json()) as ReviewQueue;
  }

  static async approve(gradeId: number): Promise<GradeAction> {
    const response = await request(
      'grades_approve_failed',
      `${API_BASE_URL}/api/v1/grades/${gradeId}/approve`,
      { method: 'POST', headers: authHeaders() },
    );
    return (await response.json()) as GradeAction;
  }

  static async override(
    gradeId: number,
    body: { points_awarded: number; reviewer_note?: string | null },
  ): Promise<GradeAction> {
    const response = await request(
      'grades_override_failed',
      `${API_BASE_URL}/api/v1/grades/${gradeId}/override`,
      {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(body),
      },
    );
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

    const response = await request(
      'grades_bulk_approve_failed',
      `${API_BASE_URL}/api/v1/grades/bulk-approve`,
      {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(body),
      },
    );
    return (await response.json()) as BulkApproveResult;
  }
}
