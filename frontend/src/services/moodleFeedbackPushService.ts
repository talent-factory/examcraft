/**
 * MoodleFeedbackPushService — TF-435.
 *
 * Triggers the feedback push (points + per-question comments) back to
 * Moodle and polls the resulting job. Mirrors the auth-header + ApiError
 * conventions of GradeExportService.
 */

import { ApiError } from './submissionsService';
import { ApiErrorKind } from '../types/submission';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Mirrors the backend MoodleFeedbackPushStatus / FeedbackTransportName enums
// so the status comparisons in NotenexportPanel are checked at compile time.
export type PushJobStatus = 'queued' | 'processing' | 'completed' | 'failed';
export type PushTransport = 'plugin' | 'gradebook';

export interface PushJob {
  id: number;
  status: PushJobStatus;
  transport: PushTransport | null;
  students_total: number;
  students_pushed: number;
  students_skipped: number;
  students_failed: number;
  error_log: unknown[] | null;
}

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function kindForStatus(status: number): ApiErrorKind {
  if (status === 401) return 'auth';
  if (status === 403) return 'permission';
  if (status === 404) return 'not_found';
  if (status === 400 || status === 412 || status === 422) return 'validation';
  if (status >= 500) return 'server';
  return 'unknown';
}

async function parseJob(response: Response, action: string): Promise<PushJob> {
  if (!response.ok) {
    let detail: unknown;
    try {
      const body = await response.json();
      detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError({
      kind: kindForStatus(response.status),
      status: response.status,
      message:
        typeof detail === 'string'
          ? detail
          : `${action} fehlgeschlagen (${response.status})`,
      detail,
    });
  }
  return (await response.json()) as PushJob;
}

export class MoodleFeedbackPushService {
  static async start(examId: number): Promise<PushJob> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/exams/${examId}/moodle/push-feedback`,
      { method: 'POST', headers: authHeaders() },
    );
    return parseJob(response, 'Push');
  }

  static async poll(examId: number, jobId: number): Promise<PushJob> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/exams/${examId}/moodle/push-feedback/${jobId}`,
      { headers: authHeaders() },
    );
    return parseJob(response, 'Status-Abfrage');
  }
}

export default MoodleFeedbackPushService;
