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

/**
 * Every `error_code` `core/backend/services/auswertung_quotas.py::_http_402`
 * raises. Manually curated, not derived from the backend, the same tradeoff
 * `errors/codes/*.ts` makes for the ADR-0005 family — kept in sync by
 * `QuotaBanner.i18n.test.ts`, which fails if a code here has no
 * `auswertungen.tierBanner.<code>` translation in one of the four locales.
 *
 * `detail.error_code` itself stays `string` (see `QuotaErrorDetail` below):
 * this list exists for the i18n guard, not to close the type the way
 * `AppErrorCode` does, so a backend code added here without a frontend
 * release still renders the generic tier sentence instead of failing to
 * compile.
 */
export const QUOTA_ERROR_CODES = [
  'auswertung_class_history_enterprise_only',
  'auswertung_custom_grading_schemes_enterprise_only',
  'auswertung_driver_not_in_tier',
  'auswertung_exam_monthly_quota_exceeded',
  'auswertung_review_bulk_pro_only',
  'auswertung_submission_quota_exceeded',
] as const;

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

/**
 * The translated sentence for a tier-quota 402 (TF-772 PR 7).
 *
 * Extracted from the banner so `ImportDialog`, which shows import failures as
 * a plain alert rather than a banner, renders the same sentence. Before PR 7
 * both fell back to `error.message` — the backend's German `detail.message`
 * — whenever the key was missing, and `ImportDialog` rendered that text
 * unconditionally.
 *
 * This is the pre-ADR-0005 quota envelope (`detail.error_code`, nested, from
 * `services/auswertung_quotas.py::_http_402`), not the sibling `error_code`
 * that `appErrorFromApiError()` reads — hence its own lookup under
 * `auswertungen.tierBanner.*`. A quota code this build does not know yet gets
 * a generic tier sentence instead of the backend text.
 *
 * Missing-key detection is `translated !== key`, the same as `translateError`,
 * not i18next's `defaultValue`: the i18n mock in `setupTests.ts` ignores
 * `defaultValue`, so a test of that path would only have tested the mock.
 */
export function translateQuotaError(
  error: ApiError & { detail: QuotaErrorDetail },
  t: (key: string, options?: Record<string, unknown>) => string,
): string {
  const { detail } = error;
  const key = `auswertungen.tierBanner.${detail.error_code}`;
  const translated = t(key, {
    tier: detail.tier,
    limit: detail.limit,
    used: detail.used,
    driver: detail.driver,
  });
  return translated !== key ? translated : t('auswertungen.tierBanner.fallback');
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
        {t('auswertungen.tierBanner.fallback')}
      </Alert>
    );
  }

  const detail = error.detail;
  const message = translateQuotaError(error, t);

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
