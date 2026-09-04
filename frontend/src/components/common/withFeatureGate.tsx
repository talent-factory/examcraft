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
  /** i18n key for the feature's display name shown on the upgrade prompt */
  featureNameKey?: string;
  /** i18n key for the feature's description shown on the upgrade prompt */
  featureDescriptionKey?: string;
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
 * @param featureNameKey - i18n key for the upgrade prompt's display name (optional)
 * @param featureDescriptionKey - i18n key for the upgrade prompt's description (optional)
 */
export function withFeatureGate<P extends object>(
  Component: ComponentType<P>,
  requiredFeature: string,
  requiredTier: 'starter' | 'professional' | 'enterprise',
  featureNameKey?: string,
  featureDescriptionKey?: string
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
          // Falls back to the raw RBAC feature id (e.g. "rag_generation") if
          // no key was given — not a translation key, but react-i18next's t()
          // returns an unresolvable key verbatim, so this degrades to the
          // same "show something" behavior the old string fallback had.
          featureNameKey={featureNameKey || requiredFeature}
          featureDescriptionKey={featureDescriptionKey}
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
