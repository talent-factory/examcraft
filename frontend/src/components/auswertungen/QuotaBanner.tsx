/**
 * QuotaBanner — translates a 402-Tier-Quota error into a friendly
 * upgrade banner (TF-336 Subarea E).
 *
 * The backend returns a structured ``detail`` with ``error_code``,
 * ``tier``, ``upgrade_to``, and quota counters. We pass them through
 * i18n so the same component can render every quota message
 * consistently.
 */

import React from 'react';
import { Alert, AlertTitle, Box, Button } from '@mui/material';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { ApiError } from '../../services/submissionsService';

export interface QuotaErrorDetail {
  error_code: string;
  tier?: string;
  upgrade_to?: string;
  limit?: number;
  used?: number;
  driver?: string;
  allowed_drivers?: string[];
}

export function isQuotaError(err: unknown): err is ApiError & {
  detail: QuotaErrorDetail;
} {
  if (!(err instanceof ApiError) || err.status !== 402) return false;
  const detail = err.detail as { error_code?: unknown } | null | undefined;
  return Boolean(
    detail && typeof detail === 'object' && typeof detail.error_code === 'string',
  );
}

interface Props {
  error: ApiError;
  onDismiss?: () => void;
  /** Custom data-testid prefix; defaults to ``quota-banner``. */
  testIdPrefix?: string;
}

const QuotaBanner: React.FC<Props> = ({ error, onDismiss, testIdPrefix }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  if (!isQuotaError(error)) {
    // Caller didn't check; render a generic alert anyway so the banner
    // is never *silent* on a 402.
    return (
      <Alert
        severity="warning"
        onClose={onDismiss}
        data-testid={`${testIdPrefix ?? 'quota-banner'}-fallback`}
      >
        {error.message}
      </Alert>
    );
  }

  const detail = error.detail as QuotaErrorDetail;
  // Look up the i18n message; fall back to the backend-provided plain
  // text if the key is missing — defence against a forgotten
  // translation key surfacing as the literal ``error_code`` to the
  // user.
  const i18nKey = `auswertungen.tierBanner.${detail.error_code}`;
  const fallback = error.message;
  const message = t(i18nKey, {
    defaultValue: fallback,
    tier: detail.tier,
    limit: detail.limit,
    used: detail.used,
    driver: detail.driver,
  });

  const upgradeTier = detail.upgrade_to;
  return (
    <Alert
      severity="warning"
      onClose={onDismiss}
      data-testid={`${testIdPrefix ?? 'quota-banner'}`}
      action={
        upgradeTier ? (
          <Button
            color="inherit"
            size="small"
            onClick={() => navigate('/billing')}
            data-testid={`${testIdPrefix ?? 'quota-banner'}-upgrade`}
          >
            {t('auswertungen.tierBanner.upgradeAction', {
              tier: upgradeTier,
              defaultValue: 'Upgrade',
            })}
          </Button>
        ) : undefined
      }
    >
      <AlertTitle>
        {t('auswertungen.tierBanner.title', {
          defaultValue: 'Tier-Limit erreicht',
        })}
      </AlertTitle>
      <Box>{message}</Box>
    </Alert>
  );
};

export default QuotaBanner;
