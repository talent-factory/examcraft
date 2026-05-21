/**
 * Tests for ActivityService — the API client for /api/v1/activity (TF-337).
 *
 * Mirrors the coverage in submissionsService.test.ts so the two
 * paginated-API clients share the same error-mapping shape:
 *   - HTTP success path with all query params (scope/types/limit/offset).
 *   - Auth header injection via the localStorage token.
 *   - Status → ApiErrorKind mapping (auth/permission/validation/...).
 *   - readErrorBody: structured detail, non-JSON body, empty body.
 *   - Network failures + AbortError mapping.
 */

import {
  ApiError,
  ActivityService,
} from '../activityService';
import { ActivityListResponse } from '../../types/activity';

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

const sampleResponse: ActivityListResponse = {
  items: [
    {
      id: 'audit_1',
      type: 'document_uploaded',
      title: 'doc.pdf',
      timestamp: '2026-05-01T10:00:00Z',
      actor_user_id: null,
    },
  ],
  total: 1,
  limit: 25,
  offset: 0,
  has_more: false,
};

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
});

describe('ActivityService.list', () => {
  it('GETs the activity endpoint and returns the parsed payload', async () => {
    mockFetch.mockResolvedValueOnce(json(200, sampleResponse));

    const result = await ActivityService.list();

    expect(result).toEqual(sampleResponse);
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain('/api/v1/activity');
    expect((init as RequestInit).method).toBe('GET');
  });

  it('omits all query params when no params are passed', async () => {
    mockFetch.mockResolvedValueOnce(json(200, sampleResponse));
    await ActivityService.list();
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).not.toContain('?');
  });

  it('serialises scope, limit and offset as query params', async () => {
    mockFetch.mockResolvedValueOnce(json(200, sampleResponse));
    await ActivityService.list({
      scope: 'institution',
      limit: 50,
      offset: 25,
    });
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain('scope=institution');
    expect(url).toContain('limit=50');
    expect(url).toContain('offset=25');
  });

  it('joins types into a single comma-separated value (matching the backend signature)', async () => {
    mockFetch.mockResolvedValueOnce(json(200, sampleResponse));
    await ActivityService.list({
      types: ['question_approved', 'question_rejected'],
    });
    const url = mockFetch.mock.calls[0][0] as string;
    // URLSearchParams encodes commas as %2C.
    expect(url).toMatch(/types=question_approved%2Cquestion_rejected/);
  });

  it('omits types entirely when the array is empty (no spurious ?types=)', async () => {
    mockFetch.mockResolvedValueOnce(json(200, sampleResponse));
    await ActivityService.list({ types: [] });
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).not.toContain('types=');
  });

  it('forwards the AbortSignal to fetch', async () => {
    mockFetch.mockResolvedValueOnce(json(200, sampleResponse));
    const controller = new AbortController();
    await ActivityService.list({ signal: controller.signal });
    const init = mockFetch.mock.calls[0][1] as RequestInit;
    expect(init.signal).toBe(controller.signal);
  });
});

describe('ActivityService — auth header', () => {
  it('attaches Bearer token from localStorage when present', async () => {
    localStorage.setItem('examcraft_access_token', 'jwt-abc');
    mockFetch.mockResolvedValueOnce(json(200, sampleResponse));
    await ActivityService.list();
    const init = mockFetch.mock.calls[0][1] as RequestInit;
    expect((init.headers as Record<string, string>).Authorization).toBe(
      'Bearer jwt-abc',
    );
  });

  it('omits Authorization when no token is stored', async () => {
    mockFetch.mockResolvedValueOnce(json(200, sampleResponse));
    await ActivityService.list();
    const init = mockFetch.mock.calls[0][1] as RequestInit;
    expect((init.headers as Record<string, string>).Authorization).toBeUndefined();
  });
});

describe('ActivityService — error mapping', () => {
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
    await expect(ActivityService.list()).rejects.toMatchObject({
      kind: expectedKind,
      status,
    });
  });

  it('extracts structured detail with message + issues', async () => {
    mockFetch.mockResolvedValueOnce(
      json(422, {
        detail: {
          message: 'Unbekannter Activity-Type',
          issues: ['does_not_exist'],
        },
      }),
    );
    const err = await ActivityService.list().catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toBe('Unbekannter Activity-Type');
    expect(err.issues).toEqual(['does_not_exist']);
  });

  it('falls back to status text when body is non-JSON (HTML proxy error)', async () => {
    const consoleWarn = jest.spyOn(console, 'warn').mockImplementation();
    mockFetch.mockResolvedValueOnce(
      text(502, '<html><body>Bad Gateway</body></html>', 'Bad Gateway'),
    );
    const err = await ActivityService.list().catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.kind).toBe('server');
    expect(err.message).toBe('502 Bad Gateway');
    expect(consoleWarn).toHaveBeenCalledWith(
      expect.stringContaining('non-JSON 502'),
      expect.stringContaining('Bad Gateway'),
    );
    consoleWarn.mockRestore();
  });

  it('handles empty error bodies (401 with no body)', async () => {
    mockFetch.mockResolvedValueOnce(text(401, '', 'Unauthorized'));
    const err = await ActivityService.list().catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.kind).toBe('auth');
    expect(err.message).toBe('401 Unauthorized');
  });
});

describe('ActivityService — network', () => {
  it('wraps fetch network failures into ApiError(kind=network)', async () => {
    mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));
    const err = await ActivityService.list().catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.kind).toBe('network');
    expect(err.status).toBe(0);
    expect(err.message).toContain('Netzwerkfehler');
  });

  it('maps AbortError into ApiError(kind=aborted) — discriminates from real network errors', async () => {
    const abortErr = new Error('aborted');
    abortErr.name = 'AbortError';
    mockFetch.mockRejectedValueOnce(abortErr);
    const err = await ActivityService.list().catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    // ``aborted`` is a dedicated kind so callers can suppress the
    // alert without string-matching translated messages.
    expect(err.kind).toBe('aborted');
    expect(err.message).toMatch(/abgebrochen/i);
  });
});
