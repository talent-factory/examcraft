/**
 * UpgradePrompt Component
 * Displays upgrade prompt when user tries to access a premium feature
 *
 * Shows:
 * - Feature name and description
 * - Current tier vs required tier
 * - Pricing comparison
 * - Upgrade CTA button
 *
 * @example
 * <UpgradePrompt
 *   featureName="Document Chatbot"
 *   requiredTier="professional"
 *   currentTier="free"
 * />
 */

import React from 'react';
import { Box, Typography, Button, Paper, Chip, Stack } from '@mui/material';
import { Lock as LockIcon, ArrowForward as ArrowForwardIcon } from '@mui/icons-material';

// ============================================================================
// Types
// ============================================================================

export interface UpgradePromptProps {
  /** Name of the feature requiring upgrade */
  featureName: string;
  /** Description of the feature (optional) */
  featureDescription?: string;
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
    price: '$0',
  },
  starter: {
    label: 'Starter',
    color: '#2196f3' as const,
    price: '$29/month',
  },
  professional: {
    label: 'Professional',
    color: '#4caf50' as const,
    price: '$99/month',
  },
  enterprise: {
    label: 'Enterprise',
    color: '#ff9800' as const,
    price: 'Contact Sales',
  },
};

// ============================================================================
// Component
// ============================================================================

export const UpgradePrompt: React.FC<UpgradePromptProps> = ({
  featureName,
  featureDescription,
  requiredTier,
  currentTier,
  upgradeUrl = '/pricing',
  onUpgrade,
}) => {
  const currentConfig = TIER_CONFIG[currentTier];
  const requiredConfig = TIER_CONFIG[requiredTier];

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
            Your Plan
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
            Required Plan
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

      {/* Pricing */}
      <Typography variant="h6" color="text.secondary" sx={{ mb: 3 }}>
        Upgrade to <strong>{requiredConfig.label}</strong> for {requiredConfig.price}
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
        Upgrade Now
      </Button>
    </Paper>
  );
};

export default UpgradePrompt;
