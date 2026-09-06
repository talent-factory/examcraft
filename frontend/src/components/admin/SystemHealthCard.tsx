import React from 'react';
import { useTranslation } from 'react-i18next';
import { Box, Card, CardContent, Chip, Typography } from '@mui/material';
import { OpenInNew } from '@mui/icons-material';
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
 * optional deep-link to the component's specialist tool (Flower/RabbitMQ-UI/
 * Sentry). Never renders a history — the epic scoped that out of v1.
 */
const SystemHealthCard: React.FC<SystemHealthCardProps> = ({ componentKey, health }) => {
  const { t } = useTranslation();

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
      </CardContent>
    </Card>
  );
};

export default SystemHealthCard;
