/**
 * TierLockedHint — inline upgrade notice next to an evaluation action the
 * current tier does not include (TF-1055).
 *
 * The limits come from `useFeatures().evaluationLimits`; callers disable the
 * action and render this hint instead of hiding it. Unknown limits (loading,
 * request failed) never lock anything: the backend's 402 and `QuotaBanner`
 * stay the fallback.
 */

import React from 'react';
import { Alert, Box, Button, Chip } from '@mui/material';
import { Lock as LockIcon } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { TIER_CONFIG, UpgradePromptProps } from '../common/UpgradePrompt';

export type UpgradeTier = UpgradePromptProps['requiredTier'];

/**
 * Target tier per gated evaluation action — the same `upgrade_to` the
 * matching `assert_*` in `services/auswertung_quotas.py` puts on its 402.
 */
export const EVALUATION_UPGRADE_TIER = {
  review_bulk: 'professional',
  custom_grading_schemes: 'enterprise',
  class_history_stats: 'enterprise',
  moodle_api: 'professional',
} as const satisfies Record<string, UpgradeTier>;

type CurrentTier = NonNullable<UpgradePromptProps['currentTier']>;

/** `tier` if UpgradePrompt can show it as "your plan", else undefined. */
export function knownTier(tier: string | undefined): CurrentTier | undefined {
  // hasOwnProperty, not `in`: `'constructor' in TIER_CONFIG` is true.
  return tier !== undefined && Object.prototype.hasOwnProperty.call(TIER_CONFIG, tier)
    ? (tier as CurrentTier)
    : undefined;
}

/** Display label of a tier, e.g. «Professional». */
export function tierLabel(tier: UpgradeTier): string {
  return TIER_CONFIG[tier].label;
}

/**
 * The target tier as the same coloured chip `UpgradePrompt` uses, so a tier
 * looks alike on every page (Professional green, Enterprise orange).
 * `locked` adds a lock for places with no other lock nearby; inside
 * `TierLockedHint` the alert icon already is the lock.
 */
export const TierChip: React.FC<{
  tier: UpgradeTier;
  /** Chip text; defaults to the tier label */
  label?: string;
  locked?: boolean;
  testId?: string;
}> = ({ tier, label, locked = false, testId }) => {
  const { color } = TIER_CONFIG[tier];
  return (
    <Chip
      icon={locked ? <LockIcon /> : undefined}
      label={label ?? tierLabel(tier)}
      size="small"
      data-testid={testId}
      sx={{
        bgcolor: `${color}20`,
        color,
        fontWeight: 'bold',
        '& .MuiChip-icon': { color },
      }}
    />
  );
};

interface Props {
  /** i18n key of the sentence; receives `{{tier}}` (target tier label) */
  messageKey: string;
  requiredTier: UpgradeTier;
  testId: string;
}

const TierLockedHint: React.FC<Props> = ({ messageKey, requiredTier, testId }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const label = tierLabel(requiredTier);
  const { color } = TIER_CONFIG[requiredTier];

  return (
    // Outlined in the tier colour instead of the blue info severity, which
    // read as the Starter colour next to an orange Enterprise UpgradePrompt.
    <Alert
      variant="outlined"
      icon={<LockIcon fontSize="inherit" />}
      data-testid={testId}
      sx={{ borderColor: color, color: 'text.primary', '& .MuiAlert-icon': { color } }}
      action={
        // Filled in the tier colour, like UpgradePrompt's upgrade button.
        <Button
          variant="contained"
          size="small"
          disableElevation
          onClick={() => navigate('/billing')}
          data-testid={`${testId}-upgrade`}
          sx={{ bgcolor: color, '&:hover': { bgcolor: color, opacity: 0.9 } }}
        >
          {t('auswertungen.tierBanner.upgradeAction', { tier: label })}
        </Button>
      }
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
        <TierChip tier={requiredTier} />
        <span>{t(messageKey, { tier: label })}</span>
      </Box>
    </Alert>
  );
};

export default TierLockedHint;
