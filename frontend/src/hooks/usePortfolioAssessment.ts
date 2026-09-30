/**
 * Polls one portfolio assessment while its latest job is working (TF-987).
 *
 * `refetchInterval` is on only while the job is `queued`/`running`; a job that
 * reached `completed` or `failed` or an assessment in `failed` switches it off.
 * The next mutation in P3–P5 restarts polling simply by invalidating
 * `portfolioAssessmentQueryKey(id)`.
 *
 * A failed poll does not stop a busy assessment's polling unless it is a 4xx
 * (403 permission, 404 deleted — asking again cannot help). A 5xx or network
 * error, e.g. during a deploy, keeps polling with exponential backoff: a job
 * runs for minutes, and a frozen «läuft» would hide exactly the stalled-job
 * hint this hook exists for. `refetch` lets the page offer a manual retry.
 *
 * `runningSince` makes a hung job distinguishable from a slow one. It is the
 * job's `started_at`, or `created_at` while the job still waits in the queue
 * (TF-986). Only if the backend sends neither does the hook fall back to the
 * moment it first saw the job active and flag that with
 * `runningSince.approximate` — the real start can only be earlier.
 */
import { useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { portfolioApi } from '../api/portfolioApi';
import { isAppError } from '../errors';
import type { PortfolioAssessmentDetail, PortfolioAssessmentJob } from '../types/portfolio';

export const PORTFOLIO_POLL_INTERVAL_MS = 2500;
export const PORTFOLIO_POLL_MAX_BACKOFF_MS = 30_000;

export const portfolioAssessmentQueryKey = (id: string) => ['portfolioAssessment', id] as const;
/** Prefix of every list page (filters and paging are appended). */
export const portfolioAssessmentsQueryKey = ['portfolioAssessments'] as const;

export function isPortfolioJobActive(job: PortfolioAssessmentJob | null | undefined): boolean {
  return job?.status === 'queued' || job?.status === 'running';
}

/** A 4xx will not heal by asking again; anything else (5xx, network) may. */
function isPermanentError(error: unknown): boolean {
  const status = isAppError(error) ? error.status : undefined;
  return status !== undefined && status >= 400 && status < 500;
}

/** Whether the assessment still has work in flight, i.e. whether to keep polling. */
export function isPortfolioAssessmentBusy(assessment: PortfolioAssessmentDetail | undefined): boolean {
  return !!assessment && assessment.status !== 'failed' && isPortfolioJobActive(assessment.job);
}

export interface PortfolioRunningSince {
  at: Date;
  approximate: boolean;
}

export interface UsePortfolioAssessmentResult {
  assessment: PortfolioAssessmentDetail | undefined;
  isLoading: boolean;
  error: unknown;
  /** True while the hook refetches on an interval. */
  isPolling: boolean;
  /** Manual reload, e.g. for a «try again» button after a failed poll. */
  refetch: () => void;
  /**
   * Start of the active job, `null` when no job is active. `approximate` is
   * true when `at` is only when this hook first saw the job active.
   */
  runningSince: PortfolioRunningSince | null;
}

export function usePortfolioAssessment(id: string | undefined): UsePortfolioAssessmentResult {
  const query = useQuery({
    queryKey: portfolioAssessmentQueryKey(id ?? ''),
    queryFn: () => portfolioApi.getAssessment(id as string),
    enabled: !!id,
    staleTime: 0,
    refetchInterval: (q) => {
      if (!isPortfolioAssessmentBusy(q.state.data)) return false;
      if (q.state.status !== 'error') return PORTFOLIO_POLL_INTERVAL_MS;
      if (isPermanentError(q.state.error)) return false;
      return Math.min(
        PORTFOLIO_POLL_MAX_BACKOFF_MS,
        // fetchFailureCount resets on the next success, errorUpdateCount never.
        PORTFOLIO_POLL_INTERVAL_MS * 2 ** q.state.fetchFailureCount,
      );
    },
  });

  const assessment = query.data;
  const isPolling =
    isPortfolioAssessmentBusy(assessment) && !(query.isError && isPermanentError(query.error));
  const job = assessment?.job ?? null;

  // Per job id, so a new job (e.g. classify after ingest) restarts the clock.
  const firstSeenRef = useRef<{ jobId: string; at: number } | null>(null);
  if (isPolling && job && firstSeenRef.current?.jobId !== job.id) {
    firstSeenRef.current = { jobId: job.id, at: Date.now() };
  }

  let runningSince: PortfolioRunningSince | null = null;
  if (isPolling && job) {
    const serverStart = job.started_at ?? job.created_at;
    if (serverStart) {
      runningSince = { at: new Date(serverStart), approximate: false };
    } else if (firstSeenRef.current) {
      runningSince = { at: new Date(firstSeenRef.current.at), approximate: true };
    }
  }

  return {
    assessment,
    isLoading: query.isLoading,
    error: query.error,
    isPolling,
    refetch: () => {
      void query.refetch();
    },
    runningSince,
  };
}
