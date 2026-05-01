/**
 * GradeExportService — wraps the grade-export download endpoint.
 *
 * Returns a Blob so the caller can trigger a browser download. The
 * 409 review-blocked case surfaces as an ApiError with kind
 * 'conflict' so the panel can show the i18n message
 * submissions_grade_export_blocked_pending_review.
 */

import { ApiError } from './submissionsService';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export type ExportFormat = 'csv' | 'moodle_csv' | 'pdf';

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export class GradeExportService {
  static async download(
    examId: number,
    format: ExportFormat,
  ): Promise<{ blob: Blob; filename: string }> {
    const url = `${API_BASE_URL}/api/v1/exams/${examId}/grades/export/${format}`;
    const response = await fetch(url, { headers: authHeaders() });

    if (!response.ok) {
      let detail: unknown;
      try {
        const body = await response.json();
        detail = body.detail;
      } catch {
        // Non-JSON error body — capture the raw text so we have *some*
        // signal in Sentry / the browser console. CDN error pages,
        // nginx 502s, fly.io health-check responses are all HTML.
        try {
          const text = await response.text();
          if (text) {
            detail = text.slice(0, 500);
            console.warn(
              '[GradeExportService] non-JSON error body for status',
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
            : response.status === 409
            ? 'conflict'
            : 'server',
        status: response.status,
        message:
          typeof detail === 'string'
            ? detail
            : `Export failed (${response.status})`,
        detail,
      });
    }

    const blob = await response.blob();
    const disposition = response.headers.get('Content-Disposition') ?? '';
    const filenameMatch = /filename="?([^";]+)"?/.exec(disposition);
    const fallback = format === 'pdf' ? 'pdf' : 'csv';
    const filename = filenameMatch?.[1] ?? `noten-${examId}.${fallback}`;
    return { blob, filename };
  }
}
