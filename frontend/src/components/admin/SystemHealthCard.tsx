import React from 'react';
import { useTranslation } from 'react-i18next';
import { Box, Card, CardContent, Chip, IconButton, Tooltip, Typography } from '@mui/material';
import { ContentCopy, OpenInNew } from '@mui/icons-material';
import { OpsComponentHealth, OpsComponentKey } from '../../types/opsHealth';

interface SystemHealthCardProps {
  componentKey: OpsComponentKey;
  health: OpsComponentHealth;
}

const STATUS_COLOR: Record<OpsComponentHealth['status'], 'success' | 'warning' | 'error'> = {
  green: 'success',
  yellow: 'warning',
  red: 'error',
};

/**
 * One Ops-Dashboard card (TF-786): traffic-light status + headline metric +
 * either an optional deep-link to the component's specialist tool
 * (Flower/Specula, and RabbitMQ in local dev — TF-800) or, where no working
 * deep-link exists (RabbitMQ in prod — TF-817, no public IP), a copyable
 * CLI-fallback command. Never renders a history — the epic scoped that out
 * of v1.
 */
const SystemHealthCard: React.FC<SystemHealthCardProps> = ({ componentKey, health }) => {
  const { t } = useTranslation();
  const [copyState, setCopyState] = React.useState<'idle' | 'copied' | 'failed'>('idle');
  const resetTimerRef = React.useRef<number>();

  // Clears any pending "reset to idle" timer so two quick clicks (or an
  // unmount) can't have a stale timeout clobber a newer copyState.
  React.useEffect(() => {
    return () => window.clearTimeout(resetTimerRef.current);
  }, []);

  const handleCopyCliHint = async () => {
    if (!health.cli_hint) return;
    window.clearTimeout(resetTimerRef.current);
    try {
      await navigator.clipboard.writeText(health.cli_hint);
      setCopyState('copied');
    } catch (err) {
      // Clipboard API unavailable/blocked (e.g. insecure context, no user
      // activation, permission denied) — the command stays visible and
      // selectable, so this isn't a hard failure, just no copy shortcut.
      // Still surfaced in the UI (not just this log) so an admin isn't left
      // wondering whether their click registered at all.
      console.warn('[SystemHealthCard] clipboard write failed', err);
      setCopyState('failed');
    }
    resetTimerRef.current = window.setTimeout(() => setCopyState('idle'), 2000);
  };

  return (
    <Card data-testid={`system-health-card-${componentKey}`} variant="outlined">
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Typography variant="h6">{t(`pages.admin.systemHealth.component.${componentKey}`)}</Typography>
          <Chip
            data-testid={`system-health-card-status-${componentKey}`}
            size="small"
            color={STATUS_COLOR[health.status]}
            label={t(`pages.admin.systemHealth.status.${health.status}`)}
          />
        </Box>
        <Typography variant="body2" color="text.secondary">
          {t(`pages.admin.systemHealth.metricLabel.${health.metric_label}`)}
        </Typography>
        <Typography variant="h5">{health.metric_value ?? '—'}</Typography>
        {health.detail && (
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
            {health.detail}
          </Typography>
        )}
        {(componentKey === 'backend' || componentKey === 'frontend') &&
          health.specula?.configured &&
          health.specula.error_count_5m != null && (
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
              {t('pages.admin.systemHealth.speculaErrorCount', {
                count: health.specula.error_count_5m,
              })}
            </Typography>
          )}
        {health.deep_link && (
          <Box sx={{ mt: 1 }}>
            <a
              data-testid={`system-health-card-link-${componentKey}`}
              href={health.deep_link}
              target="_blank"
              rel="noreferrer"
              style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}
            >
              {t('pages.admin.systemHealth.openTool')}
              <OpenInNew fontSize="inherit" />
            </a>
          </Box>
        )}
        {!health.deep_link && health.cli_hint && (
          <Box sx={{ mt: 1 }}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              {t('pages.admin.systemHealth.cliHintLabel')}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Typography
                component="code"
                variant="body2"
                data-testid={`system-health-card-cli-hint-${componentKey}`}
                sx={{
                  fontFamily: 'monospace',
                  bgcolor: 'action.hover',
                  px: 1,
                  py: 0.5,
                  borderRadius: 1,
                }}
              >
                {health.cli_hint}
              </Typography>
              <Tooltip title={t('pages.admin.systemHealth.copyCommand')}>
                <IconButton
                  size="small"
                  aria-label={t('pages.admin.systemHealth.copyCommand')}
                  data-testid={`system-health-card-copy-${componentKey}`}
                  onClick={handleCopyCliHint}
                >
                  <ContentCopy fontSize="inherit" />
                </IconButton>
              </Tooltip>
              {copyState === 'copied' && (
                <Typography variant="caption" color="success.main">
                  {t('pages.admin.systemHealth.copied')}
                </Typography>
              )}
              {copyState === 'failed' && (
                <Typography variant="caption" color="error.main">
                  {t('pages.admin.systemHealth.copyFailed')}
                </Typography>
              )}
            </Box>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default SystemHealthCard;
