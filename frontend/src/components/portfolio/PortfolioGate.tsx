/**
 * Deployment and tier gate for every portfolio page (TF-987).
 *
 * Portfolio-Assessment is premium backend with its UI in core, so two things
 * have to hold before a page may talk to `/api/v1/portfolio-*`:
 *
 * 1. Full deployment. In core the routers do not exist; the gate renders the
 *    same "not available" notice as `componentLoader` and never mounts its
 *    children, so no request is issued at all.
 * 2. Tier `professional` or higher — what `_require_professional_tier` in the
 *    backend enforces on every mutation. The reads (list, detail, templates)
 *    are NOT tier-gated there, so this gate is the only thing keeping a lower
 *    tier off these pages. An unknown tier (`/api/auth/features` failed) lets
 *    the page through with a warning logged: the pages stay readable, and the
 *    first mutation (P3–P5) comes back as `portfolio_assessment_tier_insufficient`,
 *    which callers turn into the same prompt via `isPortfolioTierError`.
 *
 * Permissions are not checked here — the routes wrap this in `PermissionGuard`.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Box, CircularProgress, Typography } from '@mui/material';
import { useFeatures } from '../../hooks/useFeatures';
import { isFullDeployment } from '../../utils/deploymentMode';
import { isAppError } from '../../errors';
import { UpgradePrompt, UpgradePromptProps } from '../common/UpgradePrompt';

const REQUIRED_TIER = 'professional';
const TIER_RANK: Record<string, number> = { free: 0, starter: 1, professional: 2, enterprise: 3 };

type Tier = NonNullable<UpgradePromptProps['currentTier']>;

function isKnownTier(tier: string | null): tier is Tier {
  // hasOwnProperty, not `in`: `'constructor' in TIER_RANK` is true.
  return tier !== null && Object.prototype.hasOwnProperty.call(TIER_RANK, tier);
}

/** True for the backend's tier refusal, which pages render as `PortfolioUpgradePrompt`. */
export function isPortfolioTierError(err: unknown): boolean {
  return isAppError(err) && err.code === 'portfolio_assessment_tier_insufficient';
}

export const PortfolioUpgradePrompt: React.FC<{ currentTier: string | null }> = ({ currentTier }) => (
  <UpgradePrompt
    featureNameKey="pages.portfolio.gate.featureName"
    featureDescriptionKey="pages.portfolio.gate.featureDescription"
    requiredTier={REQUIRED_TIER}
    // Unknown tier: leave the "your plan" chip out rather than claim Free.
    currentTier={isKnownTier(currentTier) ? currentTier : undefined}
  />
);

const PortfolioUnavailable: React.FC = () => {
  const { t } = useTranslation();
  return (
    <Box display="flex" flexDirection="column" alignItems="center" sx={{ p: 3 }}>
      <Typography variant="h6" color="textSecondary" gutterBottom>
        {t('components.featureUnavailable.title', { feature: t('pages.portfolio.gate.featureName') })}
      </Typography>
      <Typography variant="body2" color="textSecondary" align="center">
        {t('components.featureUnavailable.body')}
      </Typography>
    </Box>
  );
};

const TierGate: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { tier, isLoading, error } = useFeatures();

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" sx={{ p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (isKnownTier(tier)) {
    if (TIER_RANK[tier] < TIER_RANK[REQUIRED_TIER]) {
      return <PortfolioUpgradePrompt currentTier={tier} />;
    }
  } else {
    console.warn('[PortfolioGate] Tier unknown, letting the page through:', tier, error);
  }

  return <>{children}</>;
};

export const PortfolioGate: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Checked before any hook that could fetch: in core nothing may be requested.
  if (!isFullDeployment()) {
    return <PortfolioUnavailable />;
  }
  return <TierGate>{children}</TierGate>;
};
