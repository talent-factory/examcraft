/**
 * Every parser of the ApiError family carries `error_code` / `error_params`
 * onto the error (TF-772 PR 7).
 *
 * Before PR 7 only `httpClient` did; the other six parsers dropped both fields
 * while reading the body, so `appErrorFromApiError()` never saw a code and each
 * backend message collapsed to the caller's fallback. The table below calls one
 * method per parser — not per service — because the parser is where the field
 * got lost. A new service on an existing parser needs no row; a new parser
 * does.
 */

import { readErrorEnvelope } from '../apiErrorBody';
import { SubmissionsService } from '../submissionsService';
import { StudentsService } from '../studentsService';
import { ActivityService } from '../activityService';
import { GradingSchemesService } from '../gradingSchemesService';
import { StatisticsService } from '../statisticsService';
import { GradeExportService } from '../gradeExportService';
import { MoodleFeedbackPushService } from '../moodleFeedbackPushService';

global.fetch = jest.fn();
const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

// 409, not 401: a 401 would send `httpClient` into its token-refresh retry.
const coded = (): Response => {
  const body = {
    detail: 'Klasse mit Namen «7a» existiert bereits',
    error_code: 'student_classes_name_exists',
    error_params: { name: '7a' },
  };
  return {
    ok: false,
    status: 409,
    statusText: 'Conflict',
    text: jest.fn().mockResolvedValue(JSON.stringify(body)),
    json: jest.fn().mockResolvedValue(body),
  } as unknown as Response;
};

const PARSERS: Array<[string, () => Promise<unknown>]> = [
  ['submissionsService.ensureOk', () => SubmissionsService.listForExam(1)],
  ['httpClient (via studentsService)', () => StudentsService.list({})],
  ['activityService.ensureOk', () => ActivityService.list()],
  ['gradingSchemesService.handleResponse', () => GradingSchemesService.list()],
  ['statisticsService.handleResponse', () => StatisticsService.getOverview(1)],
  ['gradeExportService.download', () => GradeExportService.download(1, 'csv')],
  ['moodleFeedbackPushService.parseJob', () => MoodleFeedbackPushService.start(1)],
];

describe('ApiError family: error_code survives parsing', () => {
  beforeEach(() => {
    mockFetch.mockReset();
    mockFetch.mockResolvedValue(coded());
  });

  it.each(PARSERS)('%s', async (_name, call) => {
    await expect(call()).rejects.toMatchObject({
      name: 'ApiError',
      status: 409,
      errorCode: 'student_classes_name_exists',
      errorParams: { name: '7a' },
    });
  });
});

describe('readErrorEnvelope', () => {
  it('reads both fields off a plain object', () => {
    expect(readErrorEnvelope({ error_code: 'x_y', error_params: { a: 1 } })).toEqual({
      errorCode: 'x_y',
      errorParams: { a: 1 },
    });
  });

  it.each([
    ['null', null],
    ['an array', [{ error_code: 'x_y' }]],
    ['a string', 'Bad Gateway'],
  ])('carries nothing for %s', (_label, raw) => {
    expect(readErrorEnvelope(raw)).toEqual({});
  });

  it('drops a non-string error_code instead of passing it on', () => {
    expect(readErrorEnvelope({ error_code: 42 }).errorCode).toBeUndefined();
  });
});
