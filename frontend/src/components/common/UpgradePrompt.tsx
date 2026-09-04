/**
 * UpgradePrompt Component
 * Displays upgrade prompt when user tries to access a premium feature
 *
 * Shows:
 * - Feature name and description
 * - Current tier vs required tier
 * - Upgrade CTA button
 *
 * `featureNameKey`/`featureDescriptionKey` are i18n keys, not display text —
 * resolved via `t()` in here (TF-671 follow-up: the previous `featureName`/
 * `featureDescription` string props rendered whatever the caller passed
 * verbatim, and every real caller passed hardcoded English prose, so a
 * German-locale user saw translated chrome around untranslated content).
 *
 * @example
 * <UpgradePrompt
 *   featureNameKey="components.featureGate.documentChat.name"
 *   requiredTier="professional"
 *   currentTier="free"
 * />
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Box, Typography, Button, Paper, Chip, Stack } from '@mui/material';
import { Lock as LockIcon, ArrowForward as ArrowForwardIcon } from '@mui/icons-material';

// ============================================================================
// Types
// ============================================================================

export interface UpgradePromptProps {
  /** i18n key for the feature's display name, resolved via t() */
  featureNameKey: string;
  /** i18n key for the feature's description, resolved via t() (optional) */
  featureDescriptionKey?: string;
  /** Required subscription tier */
  requiredTier: 'starter' | 'professional' | 'enterprise';
  /** Current user's subscription tier */
  currentTier: 'free' | 'starter' | 'professional' | 'enterprise';
  /** Custom upgrade URL (optional) */
  upgradeUrl?: string;
  /** Callback when upgrade button is clicked (optional) */
  onUpgrade?: () => void;
}

// ============================================================================
// Tier Configuration
// ============================================================================

const TIER_CONFIG = {
  free: {
    label: 'Free',
    color: '#9e9e9e' as const,
  },
  starter: {
    label: 'Starter',
    color: '#2196f3' as const,
  },
  professional: {
    label: 'Professional',
    color: '#4caf50' as const,
  },
  enterprise: {
    label: 'Enterprise',
    color: '#ff9800' as const,
  },
};

// ============================================================================
// Component
// ============================================================================

export const UpgradePrompt: React.FC<UpgradePromptProps> = ({
  featureNameKey,
  featureDescriptionKey,
  requiredTier,
  currentTier,
  upgradeUrl = '/billing',
  onUpgrade,
}) => {
  const { t } = useTranslation();
  const currentConfig = TIER_CONFIG[currentTier];
  const requiredConfig = TIER_CONFIG[requiredTier];
  const featureName = t(featureNameKey);
  const featureDescription = featureDescriptionKey ? t(featureDescriptionKey) : undefined;

  const handleUpgrade = () => {
    if (onUpgrade) {
      onUpgrade();
    } else {
      window.location.href = upgradeUrl;
    }
  };

  return (
    <Paper
      elevation={3}
      sx={{
        p: 4,
        maxWidth: 600,
        mx: 'auto',
        mt: 4,
        textAlign: 'center',
        borderTop: `4px solid ${requiredConfig.color}`,
      }}
    >
      {/* Lock Icon */}
      <Box
        sx={{
          display: 'inline-flex',
          p: 2,
          borderRadius: '50%',
          bgcolor: `${requiredConfig.color}20`,
          mb: 2,
        }}
      >
        <LockIcon sx={{ fontSize: 48, color: requiredConfig.color }} />
      </Box>

      {/* Feature Name */}
      <Typography variant="h5" gutterBottom fontWeight="bold">
        {featureName}
      </Typography>

      {/* Feature Description */}
      {featureDescription && (
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          {featureDescription}
        </Typography>
      )}

      {/* Tier Comparison */}
      <Stack direction="row" spacing={2} justifyContent="center" sx={{ mb: 3 }}>
        <Box>
          <Typography variant="caption" color="text.secondary" display="block">
            {t('components.upgradePrompt.yourPlan')}
          </Typography>
          <Chip
            label={currentConfig.label}
            sx={{
              bgcolor: `${currentConfig.color}20`,
              color: currentConfig.color,
              fontWeight: 'bold',
            }}
          />
        </Box>

        <ArrowForwardIcon sx={{ alignSelf: 'center', color: 'text.secondary' }} />

        <Box>
          <Typography variant="caption" color="text.secondary" display="block">
            {t('components.upgradePrompt.requiredPlan')}
          </Typography>
          <Chip
            label={requiredConfig.label}
            sx={{
              bgcolor: `${requiredConfig.color}20`,
              color: requiredConfig.color,
              fontWeight: 'bold',
            }}
          />
        </Box>
      </Stack>

      {/* Upgrade line — no price here: the authoritative prices live on the
          in-app /billing page (BillingPage.tsx), which the default upgradeUrl
          below navigates to. TF-671: the hardcoded $29/$99 that used to be
          here contradicted BillingPage's CHF 9/CHF 49. */}
      <Typography variant="h6" color="text.secondary" sx={{ mb: 3 }}>
        {t('components.upgradePrompt.upgradeTo', { tier: requiredConfig.label })}
      </Typography>

      {/* Upgrade Button */}
      <Button
        variant="contained"
        size="large"
        onClick={handleUpgrade}
        sx={{
          bgcolor: requiredConfig.color,
          '&:hover': {
            bgcolor: requiredConfig.color,
            opacity: 0.9,
          },
        }}
      >
        {t('components.upgradePrompt.upgradeNow')}
      </Button>
    </Paper>
  );
};

export default UpgradePrompt;
