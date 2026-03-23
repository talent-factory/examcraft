/**
 * Package Tier Badge Component
 * Displays current subscription tier (Core/Premium/Enterprise) in the navigation
 */

import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Chip, Tooltip, Box } from '@mui/material';
import {
  Layers as CoreIcon,
  Star as PremiumIcon,
  Business as EnterpriseIcon,
} from '@mui/icons-material';

interface PackageTierInfo {
  tier: 'free' | 'starter' | 'professional' | 'enterprise';
  displayName: string;
  package: 'Core' | 'Premium' | 'Enterprise';
  features: string[];
}


const TIER_COLORS: Record<string, string> = {
  free: '#9E9E9E',      // Gray
  starter: '#2196F3',   // Blue
  professional: '#9C27B0', // Purple
  enterprise: '#FF9800'  // Orange
};

const TIER_ICONS: Record<string, React.ReactElement> = {
  free: <CoreIcon fontSize="small" />,
  starter: <PremiumIcon fontSize="small" />,
  professional: <PremiumIcon fontSize="small" />,
  enterprise: <EnterpriseIcon fontSize="small" />
};

export const PackageTierBadge: React.FC = () => {
  const { t } = useTranslation();
  const [tierInfo, setTierInfo] = useState<PackageTierInfo | null>(null);
  const [loading, setLoading] = useState(true);

  const TIER_CONFIG: Record<string, PackageTierInfo> = {
    free: {
      tier: 'free',
      displayName: t('layout.packageTier.displayName.free'),
      package: 'Core',
      features: [
        t('layout.packageTier.features.free.documentUpload'),
        t('layout.packageTier.features.free.basicQuestionGeneration'),
        t('layout.packageTier.features.free.documentLibrary'),
        t('layout.packageTier.features.free.fiveDocuments'),
        t('layout.packageTier.features.free.twentyQuestionsMonth'),
      ]
    },
    starter: {
      tier: 'starter',
      displayName: t('layout.packageTier.displayName.starter'),
      package: 'Premium',
      features: [
        t('layout.packageTier.features.starter.allFreeFeatures'),
        t('layout.packageTier.features.starter.ragGeneration'),
        t('layout.packageTier.features.starter.promptTemplates'),
        t('layout.packageTier.features.starter.batchProcessing'),
        t('layout.packageTier.features.starter.fiftyDocuments'),
        t('layout.packageTier.features.starter.twoHundredQuestionsMonth'),
      ]
    },
    professional: {
      tier: 'professional',
      displayName: t('layout.packageTier.displayName.professional'),
      package: 'Premium',
      features: [
        t('layout.packageTier.features.professional.allStarterFeatures'),
        t('layout.packageTier.features.professional.documentChatBot'),
        t('layout.packageTier.features.professional.advancedPromptManagement'),
        t('layout.packageTier.features.professional.analyticsDashboard'),
        t('layout.packageTier.features.professional.unlimitedDocuments'),
        t('layout.packageTier.features.professional.thousandQuestionsMonth'),
      ]
    },
    enterprise: {
      tier: 'enterprise',
      displayName: t('layout.packageTier.displayName.enterprise'),
      package: 'Enterprise',
      features: [
        t('layout.packageTier.features.enterprise.allProfessionalFeatures'),
        t('layout.packageTier.features.enterprise.ssoIntegration'),
        t('layout.packageTier.features.enterprise.customBranding'),
        t('layout.packageTier.features.enterprise.apiAccess'),
        t('layout.packageTier.features.enterprise.advancedAnalytics'),
        t('layout.packageTier.features.enterprise.prioritySupport'),
        t('layout.packageTier.features.enterprise.ldapIntegration'),
        t('layout.packageTier.features.enterprise.auditLogs'),
      ]
    }
  };

  const detectPackageTier = async () => {
    try {
      // Get authenticated user's institution tier from backend
      const token = localStorage.getItem('examcraft_access_token');

      if (!token) {
        // Not authenticated - fallback to free tier
        setTierInfo(TIER_CONFIG.free);
        setLoading(false);
        return;
      }

      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/rbac/tiers/my`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const currentTier = await response.json();

        // Map tier name to tier config
        const tierName = currentTier.name;

        if (tierName === 'enterprise') {
          setTierInfo(TIER_CONFIG.enterprise);
        } else if (tierName === 'professional') {
          setTierInfo(TIER_CONFIG.professional);
        } else if (tierName === 'starter') {
          setTierInfo(TIER_CONFIG.starter);
        } else {
          // free or unknown tier
          setTierInfo(TIER_CONFIG.free);
        }
      } else {
        // API call failed - fallback to free tier
        console.warn('Failed to fetch user tier from backend, falling back to Free');
        setTierInfo(TIER_CONFIG.free);
      }
    } catch (error) {
      console.error('Failed to detect package tier:', error);
      // Fallback to free tier
      setTierInfo(TIER_CONFIG.free);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    detectPackageTier();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading || !tierInfo) {
    return null;
  }

  const tooltipContent = (
    <Box sx={{ p: 1 }}>
      <Box sx={{ fontWeight: 'bold', mb: 1 }}>
        {t('layout.packageTier.tooltipTitle', { package: tierInfo.package, displayName: tierInfo.displayName })}
      </Box>
      <Box sx={{ fontSize: '0.875rem' }}>
        <strong>{t('layout.packageTier.featuresLabel')}</strong>
        <Box
          component="ul"
          sx={{ margin: '4px 0', paddingLeft: '20px' }}
        >
          {tierInfo.features.map((feature, index) => (
            <li key={index}>{feature}</li>
          ))}
        </Box>
      </Box>
    </Box>
  );

  return (
    <Tooltip title={tooltipContent} arrow placement="bottom">
      <Chip
        icon={TIER_ICONS[tierInfo.tier]}
        label={`${tierInfo.package} - ${tierInfo.displayName}`}
        size="small"
        sx={{
          backgroundColor: TIER_COLORS[tierInfo.tier],
          color: 'white',
          fontWeight: 'bold',
          cursor: 'help',
          '& .MuiChip-icon': {
            color: 'white'
          },
          '&:hover': {
            opacity: 0.9
          }
        }}
      />
    </Tooltip>
  );
};

export default PackageTierBadge;
