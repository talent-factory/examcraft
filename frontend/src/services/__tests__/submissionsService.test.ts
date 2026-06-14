/**
 * Tests for SubmissionsService — the API client class for /api/v1/submissions/*.
 *
 * Covers:
 *  - HTTP success paths for preview / commit / listForExam / getDetail / getImportJob
 *  - ApiError mapping for auth/permission/validation/not_found/too_large/server
 *  - readErrorBody handles JSON, non-JSON (HTML proxy errors), empty bodies
 *  - Network failures + AbortSignal cancellation
 */

import {
  ApiError,
  SubmissionsService,
} from '../submissionsService';
import { ImportJob, ImportPreview, SubmissionDetail, SubmissionList } from '../../types/submission';

global.fetch = jest.fn();
const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

const json = (status: number, body: unknown, statusText = ''): Response =>
  ({
    ok: status >= 200 && status < 300,
    status,
    statusText,
    text: jest.fn().mockResolvedValue(JSON.stringify(body)),
    json: jest.fn().mockResolvedValue(body),
  }) as unknown as Response;

const text = (status: number, body: string, statusText = ''): Response =>
  ({
    ok: status >= 200 && status < 300,
    status,
    statusText,
    text: jest.fn().mockResolvedValue(body),
    json: jest.fn().mockRejectedValue(new SyntaxError('not json')),
  }) as unknown as Response;

const csvFile = new File(['email\nx@y.ch\n'], 'klasse.csv', { type: 'text/csv' });

const samplePreview: ImportPreview = {
  exam_id: 42,
  driver_name: 'moodle_csv',
  student_count: 1,
  attempt_count: 1,
  students: [{ external_id: 'x@y.ch', display_name: null }],
  attempts: [
    {
      student_external_id: 'x@y.ch',
      attempt_number: 1,
      started_at: null,
      submitted_at: null,
      answer_count: 0,
    },
  ],
  warnings: [],
  errors: [],
  source_metadata: {},
  truncated: false,
};

const sampleJob: ImportJob = {
  id: 7,
  exam_id: 42,
  driver_name: 'moodle_csv',
  status: 'succeeded',
  rows_processed: 1,
  rows_failed: 0,
  error_log: null,
  source_metadata: null,
  started_at: null,
  finished_at: null,
};

beforeEach(() => {
  jest.clearAllMocks();
  // localStorage default
  localStorage.clear();
});

describe('SubmissionsService', () => {
  // ----- preview ----------------------------------------------------------

  it('preview() POSTs FormData and returns the parsed payload', async () => {
    mockFetch.mockResolvedValueOnce(json(200, samplePreview));

    const result = await SubmissionsService.preview({
      examId: 42,
      file: csvFile,
      driverName: 'moodle_csv',
    });

    expect(result).toEqual(samplePreview);
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain('/api/v1/submissions/import/preview');
    expect((init as RequestInit).method).toBe('POST');
    expect((init as RequestInit).body).toBeInstanceOf(FormData);
  });

  it('preview() defaults driverName to moodle_csv', async () => {
    mockFetch.mockResolvedValueOnce(json(200, samplePreview));
    await SubmissionsService.preview({ examId: 1, file: csvFile });
    const init = mockFetch.mock.calls[0][1] as RequestInit;
    const fd = init.body as FormData;
    expect(fd.get('driver_name')).toBe('moodle_csv');
  });

  // ----- commit -----------------------------------------------------------

  it('commit() returns the persisted ImportJob', async () => {
    mockFetch.mockResolvedValueOnce(json(200, sampleJob));
    const job = await SubmissionsService.commit({ examId: 42, file: csvFile });
    expect(job).toEqual(sampleJob);
  });

  // ----- list / detail ----------------------------------------------------

  it('listForExam() builds the URL with exam_id query param', async () => {
    const list: SubmissionList = {
      items: [],
      total: 0,
      pending_count: 0,
      limit: 200,
      offset: 0,
    };
    mockFetch.mockResolvedValueOnce(json(200, list));

    const result = await SubmissionsService.listForExam(42);
    expect(result).toEqual(list);
    expect(mockFetch.mock.calls[0][0]).toContain('?exam_id=42');
  });

  it('getDetail() GETs /submissions/:id', async () => {
    const detail: SubmissionDetail = {
      id: 1,
      exam_id: 42,
      student_id: 9,
      student_external_id: 'x@y.ch',
      student_display_name: null,
      scoring_strategy: 'latest',
      graded_attempt_id: null,
      total_points_awarded: 0,
      total_points_max: 0,
      percentage: 0,
      grade_status: 'pending_review',
      attempts: [],
    };
    mockFetch.mockResolvedValueOnce(json(200, detail));

    const result = await SubmissionsService.getDetail(1);
    expect(result).toEqual(detail);
    expect(mockFetch.mock.calls[0][0]).toContain('/api/v1/submissions/1');
  });

  it('getImportJob() GETs /import-jobs/:id', async () => {
    mockFetch.mockResolvedValueOnce(json(200, sampleJob));
    const result = await SubmissionsService.getImportJob(7);
    expect(result).toEqual(sampleJob);
    expect(mockFetch.mock.calls[0][0]).toContain('/api/v1/submissions/import-jobs/7');
  });

  it('getImportSummary() GETs /import/summary with exam_id', async () => {
    const summary = {
      exam_id: 42,
      submission_count: 2,
      attempt_count: 3,
      student_count: 2,
      by_source: [{ source: 'moodle_csv', attempt_count: 3 }],
    };
    mockFetch.mockResolvedValueOnce(json(200, summary));
    const result = await SubmissionsService.getImportSummary(42);
    expect(result).toEqual(summary);
    expect(mockFetch.mock.calls[0][0]).toContain(
      '/api/v1/submissions/import/summary?exam_id=42',
    );
  });

  it('deleteImport() issues DELETE /import with exam_id', async () => {
    const summary = {
      exam_id: 42,
      submission_count: 2,
      attempt_count: 3,
      student_count: 2,
      by_source: [{ source: 'moodle_csv', attempt_count: 3 }],
    };
    mockFetch.mockResolvedValueOnce(json(200, summary));
    const result = await SubmissionsService.deleteImport(42);
    expect(result).toEqual(summary);
    expect(mockFetch.mock.calls[0][0]).toContain(
      '/api/v1/submissions/import?exam_id=42',
    );
    expect((mockFetch.mock.calls[0][1] as RequestInit).method).toBe('DELETE');
  });

  it('deleteImport() maps a 403 to an ApiError', async () => {
    mockFetch.mockResolvedValueOnce(json(403, { detail: 'forbidden' }));
    const err = await SubmissionsService.deleteImport(42).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.kind).toBe('permission');
  });

  // ----- auth header injection -------------------------------------------

  it('attaches Bearer token from localStorage when present', async () => {
    localStorage.setItem('examcraft_access_token', 'jwt-abc');
    mockFetch.mockResolvedValueOnce(json(200, sampleJob));
    await SubmissionsService.getImportJob(1);
    const init = mockFetch.mock.calls[0][1] as RequestInit;
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer jwt-abc');
  });

  it('omits Authorization when no token is stored', async () => {
    mockFetch.mockResolvedValueOnce(json(200, sampleJob));
    await SubmissionsService.getImportJob(1);
    const init = mockFetch.mock.calls[0][1] as RequestInit;
    expect((init.headers as Record<string, string>).Authorization).toBeUndefined();
  });

  // ----- error mapping ----------------------------------------------------

  it.each([
    [401, 'auth'],
    [403, 'permission'],
    [404, 'not_found'],
    [413, 'too_large'],
    [422, 'validation'],
    [400, 'validation'],
    [500, 'server'],
    [502, 'server'],
    [418, 'unknown'],
  ])('maps status %d to ApiError.kind=%s', async (status, expectedKind) => {
    mockFetch.mockResolvedValueOnce(
      json(status, { detail: 'message' }, 'Status'),
    );
    await expect(
      SubmissionsService.getImportJob(1),
    ).rejects.toMatchObject({ kind: expectedKind, status });
  });

  it('extracts structured detail with message + issues', async () => {
    mockFetch.mockResolvedValueOnce(
      json(422, {
        detail: {
          message: '3 Validierungs-Fehler',
          issues: ['issue 1', 'issue 2', 'issue 3'],
        },
      }),
    );
    const err = await SubmissionsService.getImportJob(1).catch(e => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toBe('3 Validierungs-Fehler');
    expect(err.issues).toEqual(['issue 1', 'issue 2', 'issue 3']);
  });

  it('falls back to status text when body is non-JSON (HTML proxy error)', async () => {
    const consoleWarn = jest.spyOn(console, 'warn').mockImplementation();
    mockFetch.mockResolvedValueOnce(
      text(502, '<html><body>Bad Gateway</body></html>', 'Bad Gateway'),
    );
    const err = await SubmissionsService.getImportJob(1).catch(e => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.kind).toBe('server');
    expect(err.message).toBe('502 Bad Gateway');
    // Raw text logged so devs can debug the actual error page contents
    expect(consoleWarn).toHaveBeenCalledWith(
      expect.stringContaining('non-JSON 502'),
      expect.stringContaining('Bad Gateway'),
    );
    consoleWarn.mockRestore();
  });

  it('handles empty error bodies (401 with no body)', async () => {
    mockFetch.mockResolvedValueOnce(text(401, '', 'Unauthorized'));
    const err = await SubmissionsService.getImportJob(1).catch(e => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.kind).toBe('auth');
    expect(err.message).toBe('401 Unauthorized');
  });

  // ----- network failures -------------------------------------------------

  it('wraps fetch network failures into ApiError(kind=network)', async () => {
    mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));
    const err = await SubmissionsService.getImportJob(1).catch(e => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.kind).toBe('network');
    expect(err.status).toBe(0);
    expect(err.message).toContain('Netzwerkfehler');
  });

  it('maps AbortError into ApiError(kind=network) with cancel-message', async () => {
    const abortErr = new Error('aborted');
    abortErr.name = 'AbortError';
    mockFetch.mockRejectedValueOnce(abortErr);
    const err = await SubmissionsService.getImportJob(1).catch(e => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.kind).toBe('network');
    expect(err.message).toMatch(/abgebrochen/i);
  });
});
