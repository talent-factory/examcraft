/**
 * Live status surface for background result imports (TF-428).
 *
 * Polls the import-jobs list for an exam and renders a banner for every
 * running/queued import with live "n/total graded" progress. The import no
 * longer needs to hold a modal-spinner open — the user can close the dialog
 * and watch progress here instead. When a previously-active job reaches a
 * terminal status, ``onCompleted`` fires so the parent can refresh the
 * submissions list to show the freshly imported results.
 */

import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Box, CircularProgress, LinearProgress } from '@mui/material';

import { SubmissionsService } from '../../services/submissionsService';
import { ImportJob } from '../../types/submission';

const ACTIVE_POLL_MS = 2500;
const IDLE_POLL_MS = 10000;

const isActive = (job: ImportJob): boolean =>
  job.status === 'queued' || job.status === 'running';

interface ImportStatusBannerProps {
  examId: number;
  /** Bump to force an immediate re-poll (e.g. after closing the import dialog). */
  pollKey?: number;
  /** Called when a job that was active becomes terminal — refresh results. */
  onCompleted: () => void;
  /**
   * Override the poll cadence (ms) for both the active and idle paths. Exposed
   * so tests can poll fast without fake timers; production uses the
   * active/idle defaults.
   */
  pollIntervalMs?: number;
}

const ImportStatusBanner: React.FC<ImportStatusBannerProps> = ({
  examId,
  pollKey,
  onCompleted,
  pollIntervalMs,
}) => {
  const { t } = useTranslation();
  const [active, setActive] = useState<ImportJob[]>([]);
  const prevActiveIds = useRef<Set<number>>(new Set());
  // Keep the latest callback without retriggering the polling effect.
  const onCompletedRef = useRef(onCompleted);
  useEffect(() => {
    onCompletedRef.current = onCompleted;
  }, [onCompleted]);

  useEffect(() => {
    if (!examId) return undefined;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const tick = async (): Promise<void> => {
      let nextDelay = pollIntervalMs ?? IDLE_POLL_MS;
      try {
        const res = await SubmissionsService.listImportJobs(examId, 5);
        if (cancelled) return;
        const running = res.items.filter(isActive);
        setActive(running);
        const activeIds = new Set(running.map((job) => job.id));
        // A job that was active last tick and is no longer active finished —
        // pull the new results into the list.
        let finished = false;
        prevActiveIds.current.forEach((id) => {
          if (!activeIds.has(id)) finished = true;
        });
        prevActiveIds.current = activeIds;
        if (finished) onCompletedRef.current();
        if (activeIds.size > 0) nextDelay = pollIntervalMs ?? ACTIVE_POLL_MS;
      } catch {
        // Transient error (auth refresh, blip) — keep polling at idle cadence.
      } finally {
        if (!cancelled) timer = setTimeout(tick, nextDelay);
      }
    };

    void tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [examId, pollKey, pollIntervalMs]);

  if (active.length === 0) return null;

  return (
    <Box sx={{ mb: 2 }}>
      {active.map((job) => {
        const hasProgress =
          job.graded_total != null && job.graded_total > 0;
        const percent = hasProgress
          ? Math.min(
              100,
              Math.round((job.graded_done / (job.graded_total as number)) * 100),
            )
          : 0;
        return (
          <Alert
            key={job.id}
            severity="info"
            icon={<CircularProgress size={18} />}
            sx={{ mb: 1, '& .MuiAlert-message': { width: '100%' } }}
          >
            {hasProgress
              ? t('auswertungen.importStatus.running', {
                  done: job.graded_done,
                  total: job.graded_total,
                })
              : t(
                  job.status === 'queued'
                    ? 'auswertungen.importStatus.queued'
                    : 'auswertungen.importStatus.runningIndeterminate',
                )}
            {hasProgress && (
              <LinearProgress
                variant="determinate"
                value={percent}
                sx={{ mt: 1 }}
              />
            )}
          </Alert>
        );
      })}
    </Box>
  );
};

export default ImportStatusBanner;
