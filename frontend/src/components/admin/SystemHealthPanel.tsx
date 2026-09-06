import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Box, Button, CircularProgress, Grid, Typography } from '@mui/material';
import { fetchOpsHealth } from '../../services/opsHealthService';
import { OpsComponentKey, OpsHealthSnapshot } from '../../types/opsHealth';
import SystemHealthCard from './SystemHealthCard';

// Epic decision (TF-784, "System-Health-Panel"): 10–30s auto-refresh, no
// historical storage. 10s is the concrete choice for v1.
const POLL_INTERVAL_MS = 10000;

const COMPONENT_ORDER: OpsComponentKey[] = ['frontend', 'backend', 'db', 'rabbitmq', 'celery'];

/**
 * Ops-Dashboard "System Health" tab (TF-786). Polls the superuser-only
 * `/api/v1/ops/health` snapshot every 10s and renders one card per
 * component. Callers (Admin.tsx) are responsible for the superuser gate —
 * this component does not check permissions itself, matching how
 * `AuditLogView` receives its `isSuperuser` prop rather than re-deriving it.
 */
const SystemHealthPanel: React.FC = () => {
  const { t } = useTranslation();
  const [snapshot, setSnapshot] = useState<OpsHealthSnapshot | null>(null);
  const [hasError, setHasError] = useState(false);
  const [loading, setLoading] = useState(true);
  // Guards against setState after unmount and against a poll tick still
  // in flight when the component is torn down (fast tab switching).
  const cancelledRef = useRef(false);
  // The tick chain already serializes automatic polls against each other,
  // but the Retry button calls `load` directly, outside that chain — a
  // manual retry can still be in flight when the next scheduled tick fires
  // (or the user double-clicks Retry). This generation counter makes sure
  // only the most recently *started* request is ever allowed to apply its
  // result, regardless of which one resolves last.
  const requestIdRef = useRef(0);

  // Deliberately has no dependencies beyond the fetch itself: the UI always
  // shows the fixed, translated `loadError` copy (never the raw error
  // message), so `t` doesn't need to be a dependency here. Keeping `load`'s
  // identity stable across renders matters — it drives the poll effect
  // below, and a `t`-dependent callback would restart that effect (and
  // re-fetch) whenever the translation function's reference changes.
  const load = useCallback(async () => {
    const requestId = ++requestIdRef.current;
    const isCurrent = () => !cancelledRef.current && requestId === requestIdRef.current;
    setLoading(true);
    try {
      const result = await fetchOpsHealth();
      if (!isCurrent()) return;
      setSnapshot(result);
      setHasError(false);
    } catch (err) {
      if (!isCurrent()) return;
      // No dedicated error-tracking hook exists for this surface yet — log
      // to the console so a "health tab shows an error" report is at least
      // debuggable from the browser console (matches the pattern used in
      // OrgUnitAssignmentDialog/HelpFeedbackQueue).
      console.error('[SystemHealthPanel] fetchOpsHealth failed', err);
      setHasError(true);
    } finally {
      if (isCurrent()) setLoading(false);
    }
  }, []);

  useEffect(() => {
    cancelledRef.current = false;
    let timerId: ReturnType<typeof setTimeout>;

    // Self-rescheduling instead of setInterval: the next poll is only
    // scheduled once the current one has fully settled, so a slow request
    // (the backend probes Fly/RabbitMQ/DB/Celery and can take several
    // seconds) can never overlap with the next tick or have its response
    // land out of order against a newer one.
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
      <Box data-testid="system-health-error">
        <Alert severity="error" sx={{ mb: 2 }}>
          {t('pages.admin.systemHealth.loadError')}
        </Alert>
        <Button variant="outlined" onClick={load} disabled={loading}>
          {t('pages.admin.systemHealth.retry')}
        </Button>
      </Box>
    );
  }

  return (
    <Box data-testid="system-health-panel">
      <Typography variant="h6">{t('pages.admin.systemHealth.title')}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t('pages.admin.systemHealth.subtitle')}
      </Typography>

      {loading && !snapshot && <CircularProgress size={24} />}

      {/* A later poll can fail after an earlier one succeeded — keep
          showing the last known-good snapshot (better than blanking the
          screen) but surface that it's stale instead of staying silent. */}
      {hasError && snapshot && (
        <Alert severity="warning" sx={{ mb: 2 }} data-testid="system-health-stale-warning">
          {t('pages.admin.systemHealth.staleError')}
        </Alert>
      )}

      {snapshot && (
        <>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
            {t('pages.admin.systemHealth.lastUpdated', {
              time: new Date(snapshot.generated_at).toLocaleTimeString(),
            })}
          </Typography>
          <Grid container spacing={2}>
            {COMPONENT_ORDER.map((key) => (
              <Grid item xs={12} sm={6} md={4} key={key}>
                <SystemHealthCard componentKey={key} health={snapshot.components[key]} />
              </Grid>
            ))}
          </Grid>
        </>
      )}
    </Box>
  );
};

export default SystemHealthPanel;
