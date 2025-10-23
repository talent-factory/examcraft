/**
 * Package Tier Badge Component
 * Displays current subscription tier (Core/Premium/Enterprise) in the navigation
 */

import React, { useEffect, useState } from 'react';
import { Chip, Tooltip, Box } from '@mui/material';
import {
  Layers as CoreIcon,
  Star as PremiumIcon,
  Business as EnterpriseIcon,
  Info as InfoIcon
} from '@mui/icons-material';

interface PackageTierInfo {
  tier: 'free' | 'starter' | 'professional' | 'enterprise';
  displayName: string;
  package: 'Core' | 'Premium' | 'Enterprise';
  features: string[];
}

const TIER_CONFIG: Record<string, PackageTierInfo> = {
  free: {
    tier: 'free',
    displayName: 'Free',
    package: 'Core',
    features: [
      'Document Upload',
      'Basic Question Generation',
      'Document Library',
      '5 Documents',
      '20 Questions/Month'
    ]
  },
  starter: {
    tier: 'starter',
    displayName: 'Starter',
    package: 'Premium',
    features: [
      'All Free Features',
      'RAG Generation',
      'Prompt Templates',
      'Batch Processing',
      '50 Documents',
      '200 Questions/Month'
    ]
  },
  professional: {
    tier: 'professional',
    displayName: 'Professional',
    package: 'Premium',
    features: [
      'All Starter Features',
      'Document ChatBot',
      'Advanced Prompt Management',
      'Analytics Dashboard',
      'Unlimited Documents',
      '1000 Questions/Month'
    ]
  },
  enterprise: {
    tier: 'enterprise',
    displayName: 'Enterprise',
    package: 'Enterprise',
    features: [
      'All Professional Features',
      'SSO Integration',
      'Custom Branding',
      'API Access',
      'Advanced Analytics',
      'Priority Support',
      'LDAP Integration',
      'Audit Logs'
    ]
  }
};

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
  const [tierInfo, setTierInfo] = useState<PackageTierInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    detectPackageTier();
  }, []);

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

      const response = await fetch(`${process.env.REACT_APP_API_URL}/api/v1/rbac/tiers/my`, {
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

  if (loading || !tierInfo) {
    return null;
  }

  const tooltipContent = (
    <Box sx={{ p: 1 }}>
      <Box sx={{ fontWeight: 'bold', mb: 1 }}>
        {tierInfo.package} Package - {tierInfo.displayName} Tier
      </Box>
      <Box sx={{ fontSize: '0.875rem' }}>
        <strong>Features:</strong>
        <ul style={{ margin: '4px 0', paddingLeft: '20px' }}>
          {tierInfo.features.map((feature, index) => (
            <li key={index}>{feature}</li>
          ))}
        </ul>
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
