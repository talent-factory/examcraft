/**
 * Latest job of a portfolio assessment: status, file progress, «läuft seit …»
 * and the translated `error_log` (TF-987). Shared by every step of the detail
 * page, which is why P3–P5 do not need their own job display.
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Box, Chip, LinearProgress, Paper, Stack, Typography } from '@mui/material';
import type { Translate } from '../../errors';
import type { PortfolioAssessmentJob, PortfolioJobStatus } from '../../types/portfolio';
import type { PortfolioRunningSince } from '../../hooks/usePortfolioAssessment';
import { describePortfolioJobEntry, portfolioJobEntryFiles } from './portfolioJobMessages';
import { JOB_STATUSES, portfolioLabel } from './portfolioLabels';

/**
 * From here on the panel says the job may be stuck. The ingest and classify
 * watchdogs reap far later; the grade job has none (TF-946), so this hint is
 * the only signal a teacher gets.
 */
export const PORTFOLIO_JOB_STALLED_AFTER_MS = 20 * 60 * 1000;

const STATUS_COLOR: Record<PortfolioJobStatus, 'default' | 'info' | 'success' | 'error'> = {
  queued: 'default',
  running: 'info',
  completed: 'success',
  failed: 'error',
};

export function formatElapsed(ms: number, t: Translate): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  if (totalSeconds < 60) {
    return t('pages.portfolio.job.elapsedSeconds', { seconds: totalSeconds });
  }
  const totalMinutes = Math.floor(totalSeconds / 60);
  if (totalMinutes < 60) {
    return t('pages.portfolio.job.elapsedMinutes', { minutes: totalMinutes });
  }
  return t('pages.portfolio.job.elapsedHours', {
    hours: Math.floor(totalMinutes / 60),
    minutes: totalMinutes % 60,
  });
}

/** Current time, re-rendered every second while `active`. */
function useNow(active: boolean): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return undefined;
    setNow(Date.now());
    const handle = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(handle);
  }, [active]);
  return now;
}

interface PortfolioJobPanelProps {
  job: PortfolioAssessmentJob;
  runningSince: PortfolioRunningSince | null;
}

export const PortfolioJobPanel: React.FC<PortfolioJobPanelProps> = ({
  job,
  runningSince,
}) => {
  const { t } = useTranslation();
  const now = useNow(runningSince !== null);
  const elapsedMs = runningSince ? now - runningSince.at.getTime() : 0;
  const entries = job.error_log ?? [];
  const hasProgress = typeof job.files_total === 'number' && job.files_total > 0;

  return (
    <Paper variant="outlined" sx={{ p: 2 }} data-testid="portfolio-job-status">
      <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
        <Typography variant="subtitle2">{t('pages.portfolio.job.title')}</Typography>
        <Chip
          size="small"
          color={STATUS_COLOR[job.status] ?? 'default'}
          label={portfolioLabel(t, 'job.status', job.status, JOB_STATUSES)}
        />
        {runningSince && (
          <Typography variant="body2" color="textSecondary">
            {t(
              runningSince.approximate
                ? 'pages.portfolio.job.runningSinceApproximate'
                : 'pages.portfolio.job.runningSince',
              { elapsed: formatElapsed(elapsedMs, t) },
            )}
          </Typography>
        )}
        {hasProgress && (
          <Typography variant="body2" color="textSecondary">
            {t('pages.portfolio.job.progress', { done: job.files_done, total: job.files_total })}
          </Typography>
        )}
      </Stack>

      {runningSince && hasProgress && (
        <LinearProgress
          sx={{ mt: 1.5 }}
          variant="determinate"
          value={Math.min(100, (job.files_done / (job.files_total as number)) * 100)}
        />
      )}

      {runningSince && elapsedMs >= PORTFOLIO_JOB_STALLED_AFTER_MS && (
        <Alert severity="warning" sx={{ mt: 1.5 }}>
          {t('pages.portfolio.job.stalled')}
        </Alert>
      )}

      {entries.length > 0 && (
        <Box sx={{ mt: 1.5 }}>
          <Typography variant="body2" fontWeight={600} gutterBottom>
            {t('pages.portfolio.job.messages')}
          </Typography>
          <Stack spacing={1}>
            {entries.map((entry, index) => {
              const files = portfolioJobEntryFiles(entry);
              return (
                <Alert key={index} severity={job.status === 'failed' ? 'error' : 'warning'}>
                  {describePortfolioJobEntry(entry, t)}
                  {files.length > 0 && (
                    <Box component="ul" sx={{ m: 0, mt: 0.5, pl: 2.5 }}>
                      {files.map((file) => (
                        <li key={file}>
                          <Typography variant="body2" component="span" sx={{ fontFamily: 'monospace' }}>
                            {file}
                          </Typography>
                        </li>
                      ))}
                    </Box>
                  )}
                </Alert>
              );
            })}
          </Stack>
        </Box>
      )}
    </Paper>
  );
};
