/**
 * usePortfolioAssessment — polling lifecycle (TF-987).
 *
 * Acceptance criterion: polling stops in the end state and on `failed`.
 */
import React from 'react';
import { act, renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  PORTFOLIO_POLL_INTERVAL_MS,
  portfolioAssessmentQueryKey,
  usePortfolioAssessment,
} from '../usePortfolioAssessment';
import { AppError } from '../../errors';
import { portfolioApi } from '../../api/portfolioApi';
import type {
  PortfolioAssessmentDetail,
  PortfolioAssessmentJob,
  PortfolioAssessmentStatus,
} from '../../types/portfolio';

jest.mock('../../api/portfolioApi', () => ({
  portfolioApi: { getAssessment: jest.fn() },
}));

const getAssessment = portfolioApi.getAssessment as jest.Mock;

function job(overrides: Partial<PortfolioAssessmentJob> = {}): PortfolioAssessmentJob {
  return {
    id: 'job-1',
    status: 'running',
    files_total: 10,
    files_done: 3,
    error_log: null,
    ...overrides,
  };
}

function assessment(
  status: PortfolioAssessmentStatus,
  latestJob: PortfolioAssessmentJob | null,
): PortfolioAssessmentDetail {
  return {
    id: 'a-1',
    template_id: 't-1',
    template_version: 1,
    student_id: 7,
    status,
    framework_conditions: null,
    source_repository_url: null,
    source_repository_ref: null,
    grading_scheme_id: null,
    review_status: 'pending_review',
    overall_points_awarded: null,
    overall_points_max: null,
    overall_percentage: null,
    job: latestJob,
    documents: [],
    phase_results: [],
    overall_grade: null,
  };
}

let client: QueryClient;

function renderWithClient(id: string | undefined) {
  client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return renderHook(() => usePortfolioAssessment(id), { wrapper });
}

async function advance(ms: number) {
  await act(async () => {
    jest.advanceTimersByTime(ms);
  });
}

const advancePoll = () => advance(PORTFOLIO_POLL_INTERVAL_MS);

beforeEach(() => {
  jest.useFakeTimers();
  getAssessment.mockReset();
});

afterEach(() => {
  jest.useRealTimers();
});

describe('usePortfolioAssessment', () => {
  it('pollt, solange der Job läuft, und hört im Endzustand auf', async () => {
    getAssessment
      .mockResolvedValueOnce(assessment('uploading', job({ status: 'queued' })))
      .mockResolvedValueOnce(assessment('uploading', job({ status: 'running' })))
      .mockResolvedValue(assessment('classifying', job({ status: 'completed' })));

    const { result } = renderWithClient('a-1');
    await waitFor(() => expect(result.current.assessment?.job?.status).toBe('queued'));
    expect(result.current.isPolling).toBe(true);

    await advancePoll();
    await waitFor(() => expect(result.current.assessment?.job?.status).toBe('running'));

    await advancePoll();
    await waitFor(() => expect(result.current.assessment?.job?.status).toBe('completed'));
    expect(result.current.isPolling).toBe(false);
    expect(getAssessment).toHaveBeenCalledTimes(3);

    await advancePoll();
    await advancePoll();
    expect(getAssessment).toHaveBeenCalledTimes(3);
  });

  it('hört bei einem fehlgeschlagenen Job auf', async () => {
    getAssessment
      .mockResolvedValueOnce(assessment('grading', job({ status: 'running' })))
      .mockResolvedValue(assessment('grading', job({ status: 'failed' })));

    const { result } = renderWithClient('a-1');
    await waitFor(() => expect(result.current.isPolling).toBe(true));

    await advancePoll();
    await waitFor(() => expect(result.current.assessment?.job?.status).toBe('failed'));
    expect(result.current.isPolling).toBe(false);

    await advancePoll();
    expect(getAssessment).toHaveBeenCalledTimes(2);
  });

  it('pollt nicht bei einem fehlgeschlagenen Assessment, auch wenn der Job noch aktiv gemeldet wird', async () => {
    getAssessment.mockResolvedValue(assessment('failed', job({ status: 'running' })));

    const { result } = renderWithClient('a-1');
    await waitFor(() => expect(result.current.assessment).toBeDefined());
    expect(result.current.isPolling).toBe(false);

    await advancePoll();
    expect(getAssessment).toHaveBeenCalledTimes(1);
  });

  it('pollt nicht ohne Job', async () => {
    getAssessment.mockResolvedValue(assessment('ready_to_grade', null));
    const { result } = renderWithClient('a-1');
    await waitFor(() => expect(result.current.assessment).toBeDefined());
    expect(result.current.isPolling).toBe(false);
    expect(result.current.runningSince).toBeNull();
  });

  it('pollt nicht, wenn schon das erste Laden scheitert', async () => {
    getAssessment.mockRejectedValue(new Error('network'));
    const { result } = renderWithClient('a-1');
    await waitFor(() => expect(result.current.error).toBeTruthy());
    expect(result.current.isPolling).toBe(false);
    await advancePoll();
    expect(getAssessment).toHaveBeenCalledTimes(1);
  });

  it('pollt nach einem 5xx während eines laufenden Jobs mit Backoff weiter', async () => {
    getAssessment
      .mockResolvedValueOnce(assessment('grading', job()))
      .mockRejectedValueOnce(new AppError('portfolio_assessment_load_failed', 'bad gateway', 502))
      .mockResolvedValue(assessment('grading', job({ status: 'completed' })));

    const { result } = renderWithClient('a-1');
    await waitFor(() => expect(result.current.isPolling).toBe(true));

    await advancePoll();
    await waitFor(() => expect(result.current.error).toBeTruthy());
    // Last known state stays, and polling goes on.
    expect(result.current.assessment?.job?.status).toBe('running');
    expect(result.current.isPolling).toBe(true);

    // Backoff: not after the normal interval …
    await advancePoll();
    expect(getAssessment).toHaveBeenCalledTimes(2);
    // … but after twice of it.
    await advance(PORTFOLIO_POLL_INTERVAL_MS);
    await waitFor(() => expect(result.current.assessment?.job?.status).toBe('completed'));
    expect(result.current.error).toBeNull();
    expect(result.current.isPolling).toBe(false);
  });

  it('hört nach einem 4xx während eines laufenden Jobs auf', async () => {
    getAssessment
      .mockResolvedValueOnce(assessment('grading', job()))
      .mockRejectedValue(new AppError('portfolio_assessment_not_found', 'gone', 404));

    const { result } = renderWithClient('a-1');
    await waitFor(() => expect(result.current.isPolling).toBe(true));

    await advancePoll();
    await waitFor(() => expect(result.current.error).toBeTruthy());
    expect(result.current.isPolling).toBe(false);
    expect(result.current.assessment).toBeDefined();

    await advance(PORTFOLIO_POLL_INTERVAL_MS * 20);
    expect(getAssessment).toHaveBeenCalledTimes(2);
  });

  it('startet das Polling nach einer Invalidierung neu (Muster für P3–P5)', async () => {
    getAssessment
      .mockResolvedValueOnce(assessment('ready_to_grade', job({ status: 'completed' })))
      .mockResolvedValue(assessment('grading', job({ id: 'job-2', status: 'queued' })));

    const { result } = renderWithClient('a-1');
    await waitFor(() => expect(result.current.assessment).toBeDefined());
    expect(result.current.isPolling).toBe(false);

    await act(async () => {
      await client.invalidateQueries({ queryKey: portfolioAssessmentQueryKey('a-1') });
    });
    await waitFor(() => expect(result.current.isPolling).toBe(true));

    await advancePoll();
    expect(getAssessment).toHaveBeenCalledTimes(3);
  });

  it('fragt ohne id nichts ab', async () => {
    const { result } = renderWithClient(undefined);
    await advancePoll();
    expect(getAssessment).not.toHaveBeenCalled();
    expect(result.current.isPolling).toBe(false);
  });

  describe('runningSince', () => {
    it('nimmt started_at vom Server, wenn vorhanden', async () => {
      getAssessment.mockResolvedValue(
        assessment('grading', job({ started_at: '2026-09-30T10:00:00Z' })),
      );
      const { result } = renderWithClient('a-1');
      await waitFor(() => expect(result.current.runningSince).not.toBeNull());
      expect(result.current.runningSince?.at.toISOString()).toBe('2026-09-30T10:00:00.000Z');
      expect(result.current.runningSince?.approximate).toBe(false);
    });

    it('fällt ohne Server-Zeitstempel auf den ersten Sichtkontakt zurück und bleibt dabei', async () => {
      jest.setSystemTime(new Date('2026-09-30T12:00:00Z'));
      getAssessment.mockResolvedValue(assessment('grading', job()));
      const { result } = renderWithClient('a-1');
      await waitFor(() => expect(result.current.runningSince).not.toBeNull());
      expect(result.current.runningSince?.approximate).toBe(true);
      const firstSeen = result.current.runningSince?.at.getTime();

      await advancePoll();
      await advancePoll();
      expect(result.current.runningSince?.at.getTime()).toBe(firstSeen);
    });

    it('beginnt bei einem neuen Job neu zu zählen', async () => {
      jest.setSystemTime(new Date('2026-09-30T12:00:00Z'));
      getAssessment
        .mockResolvedValueOnce(assessment('uploading', job({ id: 'job-1' })))
        .mockResolvedValue(assessment('classifying', job({ id: 'job-2' })));
      const { result } = renderWithClient('a-1');
      await waitFor(() => expect(result.current.runningSince).not.toBeNull());
      const first = result.current.runningSince?.at.getTime() as number;

      await advancePoll();
      await waitFor(() => expect(result.current.assessment?.job?.id).toBe('job-2'));
      expect(result.current.runningSince?.at.getTime()).toBeGreaterThan(first);
    });

    it('ist null, sobald kein Job mehr läuft', async () => {
      getAssessment.mockResolvedValue(assessment('grading', job({ status: 'failed' })));
      const { result } = renderWithClient('a-1');
      await waitFor(() => expect(result.current.assessment).toBeDefined());
      expect(result.current.runningSince).toBeNull();
    });
  });
});
