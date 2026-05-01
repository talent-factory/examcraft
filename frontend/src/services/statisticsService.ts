/**
 * StatisticsService — read-only client for `/api/v1/exams/{id}/stats/*`
 * and `/api/v1/submissions/{id}/stats` (TF-335 Spec 8).
 */

import { ApiError } from './submissionsService';
import {
  OverviewStats,
  PerQuestionList,
  PerSubmissionStat,
} from '../types/statistics';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    return (await response.json()) as T;
  }
  let detail: unknown;
  try {
    const body = await response.json();
    detail = body.detail;
  } catch {
    // Non-JSON error body — keep raw text so an HTML error page
    // (CDN/nginx/fly health check) leaves a debuggable trace instead
    // of disappearing into a generic "Request failed (502)".
    try {
      const text = await response.text();
      if (text) {
        detail = text.slice(0, 500);
        console.warn(
          '[StatisticsService] non-JSON error body for status',
          response.status,
          text.slice(0, 200),
        );
      }
    } catch {
      /* body fully unavailable */
    }
  }
  throw new ApiError({
    kind:
      response.status === 401
        ? 'auth'
        : response.status === 403
        ? 'permission'
        : response.status === 404
        ? 'not_found'
        : 'server',
    status: response.status,
    message:
      typeof detail === 'string' ? detail : `Request failed (${response.status})`,
    detail,
  });
}

export class StatisticsService {
  static async getOverview(examId: number): Promise<OverviewStats> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/exams/${examId}/stats/overview`,
      { headers: authHeaders() },
    );
    return handleResponse<OverviewStats>(response);
  }

  static async getPerQuestion(examId: number): Promise<PerQuestionList> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/exams/${examId}/stats/per-question`,
      { headers: authHeaders() },
    );
    return handleResponse<PerQuestionList>(response);
  }

  static async getSubmissionStats(
    submissionId: number,
  ): Promise<PerSubmissionStat> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/submissions/${submissionId}/stats`,
      { headers: authHeaders() },
    );
    return handleResponse<PerSubmissionStat>(response);
  }
}
