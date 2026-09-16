import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Box, Button, CircularProgress, Grid, Typography } from '@mui/material';
import { fetchLiveActivity } from '../../services/liveActivityService';
import { ActivityBucketId, LiveActivitySnapshot } from '../../types/liveActivity';
import LiveActivityCard from './LiveActivityCard';

// TF-838 (TF-827 decision): identical 10s auto-refresh cadence to
// SystemHealthPanel.
const POLL_INTERVAL_MS = 10000;

// Fixed frontend order (TF-827 decision) — never derived from the JSON
// response's key order, so tiles don't reshuffle between polls.
const BUCKET_ORDER: ActivityBucketId[] = [
  'documents_upload',
  'questions_generate_rag',
  'questions_review',
  'exam_compose',
  'exam_results_import',
  'prompt_template_edit',
  'prompt_wizard_chat',
  'document_chat_session',
  'admin_reference_data_edit',
];

/**
 * Ops-Dashboard "Live Activity" tab (TF-838). Polls the superuser-only
 * `/api/v1/ops/activity` snapshot every 10s and renders one tile per bucket
 * in `BUCKET_ORDER`. Callers (Admin.tsx) are responsible for the superuser +
 * Full-deployment gate — this component does not check permissions itself,
 * matching `SystemHealthPanel`.
 */
const LiveActivityPanel: React.FC = () => {
  const { t } = useTranslation();
  const [snapshot, setSnapshot] = useState<LiveActivitySnapshot | null>(null);
  const [hasError, setHasError] = useState(false);
  const [loading, setLoading] = useState(true);
  // Guards against setState after unmount and against a poll tick still in
  // flight when the component is torn down (fast tab switching).
  const cancelledRef = useRef(false);
  // The tick chain already serializes automatic polls against each other,
  // but the Retry button calls `load` directly, outside that chain — this
  // generation counter makes sure only the most recently *started* request
  // is ever allowed to apply its result, regardless of which one resolves
  // last (mirrors SystemHealthPanel).
  const requestIdRef = useRef(0);

  const load = useCallback(async () => {
    const requestId = ++requestIdRef.current;
    const isCurrent = () => !cancelledRef.current && requestId === requestIdRef.current;
    setLoading(true);
    try {
      const result = await fetchLiveActivity();
      if (!isCurrent()) return;
      setSnapshot(result);
      setHasError(false);
    } catch (err) {
      if (!isCurrent()) return;
      console.error('[LiveActivityPanel] fetchLiveActivity failed', err);
      setHasError(true);
    } finally {
      if (isCurrent()) setLoading(false);
    }
  }, []);

  useEffect(() => {
    cancelledRef.current = false;
    let timerId: ReturnType<typeof setTimeout>;

    // Self-rescheduling instead of setInterval, matching SystemHealthPanel:
    // the next poll is only scheduled once the current one has settled.
    const tick = async () => {
      await load();
      if (!cancelledRef.current) {
        timerId = setTimeout(tick, POLL_INTERVAL_MS);
      }
    };
    tick();

    return () => {
      cancelledRef.current = true;
      clearTimeout(timerId);
    };
  }, [load]);

  if (hasError && !snapshot) {
    return (
      <Box data-testid="live-activity-error">
        <Alert severity="error" sx={{ mb: 2 }}>
          {t('pages.admin.liveActivity.loadError')}
        </Alert>
        <Button variant="outlined" onClick={load} disabled={loading}>
          {t('pages.admin.liveActivity.retry')}
        </Button>
      </Box>
    );
  }

  return (
    <Box data-testid="live-activity-panel">
      <Typography variant="h6">{t('pages.admin.liveActivity.title')}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t('pages.admin.liveActivity.subtitle')}
      </Typography>

      {loading && !snapshot && <CircularProgress size={24} />}

      {/* A later poll can fail after an earlier one succeeded — keep
          showing the last known-good snapshot but surface that it's stale. */}
      {hasError && snapshot && (
        <Alert severity="warning" sx={{ mb: 2 }} data-testid="live-activity-stale-warning">
          {t('pages.admin.liveActivity.staleError')}
        </Alert>
      )}

      {snapshot && (
        <>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
            {t('pages.admin.liveActivity.lastUpdated', {
              time: new Date(snapshot.generated_at).toLocaleTimeString(),
            })}
          </Typography>
          <Grid container spacing={2}>
            {BUCKET_ORDER.map((bucketId) => (
              <Grid item xs={12} sm={6} md={4} key={bucketId}>
                <LiveActivityCard bucketId={bucketId} bucket={snapshot.buckets[bucketId]} />
              </Grid>
            ))}
          </Grid>
        </>
      )}
    </Box>
  );
};

export default LiveActivityPanel;
