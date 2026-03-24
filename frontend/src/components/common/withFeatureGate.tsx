/**
 * withFeatureGate Higher-Order Component
 *
 * Wraps a component with RBAC feature checking.
 * Shows UpgradePrompt if user doesn't have required feature.
 *
 * @example
 * const ProtectedComponent = withFeatureGate(
 *   MyComponent,
 *   'document_chatbot',
 *   'professional'
 * );
 */

import React, { ComponentType } from 'react';
import { Box, CircularProgress } from '@mui/material';
import { useFeatures } from '../../hooks/useFeatures';
import { UpgradePrompt } from './UpgradePrompt';

// ============================================================================
// Types
// ============================================================================

export interface WithFeatureGateOptions {
  /** Required feature name */
  requiredFeature: string;
  /** Required subscription tier */
  requiredTier: 'starter' | 'professional' | 'enterprise';
  /** Feature display name for upgrade prompt */
  featureName?: string;
  /** Feature description for upgrade prompt */
  featureDescription?: string;
}

// ============================================================================
// HOC Implementation
// ============================================================================

/**
 * Higher-Order Component that wraps a component with feature gate checking
 *
 * @param Component - Component to wrap
 * @param requiredFeature - Feature name required to access component
 * @param requiredTier - Subscription tier required
 * @param featureName - Display name for upgrade prompt (optional)
 * @param featureDescription - Description for upgrade prompt (optional)
 */
export function withFeatureGate<P extends object>(
  Component: ComponentType<P>,
  requiredFeature: string,
  requiredTier: 'starter' | 'professional' | 'enterprise',
  featureName?: string,
  featureDescription?: string
): ComponentType<P> {
  const WrappedComponent: React.FC<P> = (props) => {
    const { tier, hasFeature, isLoading } = useFeatures();

    // Show loading spinner while checking features
    if (isLoading) {
      return (
        <Box
          display="flex"
          justifyContent="center"
          alignItems="center"
          minHeight="200px"
        >
          <CircularProgress />
        </Box>
      );
    }

    // Check if user has required feature
    if (!hasFeature(requiredFeature)) {
      return (
        <UpgradePrompt
          featureName={featureName || requiredFeature}
          featureDescription={featureDescription}
          requiredTier={requiredTier}
          currentTier={tier as any || 'free'}
        />
      );
    }

    // User has access - render component
    return <Component {...props} />;
  };

  // Set display name for debugging
  WrappedComponent.displayName = `withFeatureGate(${Component.displayName || Component.name || 'Component'})`;

  return WrappedComponent;
}

export default withFeatureGate;
