/**
 * MoodleFeedbackPushService — TF-435.
 *
 * Triggers the feedback push (points + per-question comments) back to
 * Moodle and polls the resulting job. Mirrors the auth-header + ApiError
 * conventions of GradeExportService.
 */

import { ApiError, statusToKind } from './submissionsService';
import { ErrorEnvelope, readErrorEnvelope } from './apiErrorBody';

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

async function parseJob(response: Response, action: string): Promise<PushJob> {
  if (!response.ok) {
    let detail: unknown;
    let envelope: ErrorEnvelope = {};
    try {
      const body = await response.json();
      envelope = readErrorEnvelope(body);
      detail = body.detail;
    } catch {
      // Non-JSON error body — keep raw text so an HTML error page
      // (CDN/nginx/fly health check) leaves a debuggable trace instead
      // of disappearing into a generic "Push fehlgeschlagen (502)".
      try {
        const text = await response.text();
        if (text) {
          detail = text.slice(0, 500);
          console.warn(
            '[MoodleFeedbackPushService] non-JSON error body for status',
            response.status,
            text.slice(0, 200),
          );
        }
      } catch {
        /* body fully unavailable */
      }
    }
    throw new ApiError({
      kind: statusToKind(response.status),
      status: response.status,
      message:
        typeof detail === 'string'
          ? detail
          : `${action} fehlgeschlagen (${response.status})`,
      detail,
      ...envelope,
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
