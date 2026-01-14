/**
 * Runtime Component Loader for Premium/Enterprise Features
 *
 * Dynamically loads Premium/Enterprise components based on deployment mode.
 * Replaces static imports and volume mounts for cleaner deployment.
 */

import React, { lazy, Suspense, ComponentType } from 'react';
import { CircularProgress, Box, Typography } from '@mui/material';
import { isFullDeployment } from './deploymentMode';

/**
 * Loading fallback component
 */
const LoadingFallback: React.FC<{ componentName?: string }> = ({ componentName }) => (
  <Box
    display="flex"
    flexDirection="column"
    justifyContent="center"
    alignItems="center"
    minHeight="200px"
  >
    <CircularProgress />
    {componentName && (
      <Typography variant="body2" color="textSecondary" sx={{ mt: 2 }}>
        Loading {componentName}...
      </Typography>
    )}
  </Box>
);

/**
 * Feature unavailable component
 */
const FeatureUnavailable: React.FC<{ featureName: string }> = ({ featureName }) => (
  <Box
    display="flex"
    flexDirection="column"
    justifyContent="center"
    alignItems="center"
    minHeight="200px"
    sx={{ p: 3 }}
  >
    <Typography variant="h6" color="textSecondary" gutterBottom>
      {featureName} Not Available
    </Typography>
    <Typography variant="body2" color="textSecondary" align="center">
      This feature is only available in the Full deployment (Premium/Enterprise).
      <br />
      Please upgrade your subscription or contact your administrator.
    </Typography>
  </Box>
);

/**
 * Generic component loader with error handling
 */
export const loadComponent = <P extends object>(
  componentPath: string,
  componentName: string,
  FallbackComponent?: ComponentType<P>
): ComponentType<P> => {
  // Check deployment mode
  if (!isFullDeployment()) {
    return (FallbackComponent || (() => <FeatureUnavailable featureName={componentName} />)) as ComponentType<P>;
  }

  // Lazy load the component
  const LazyComponent = lazy(() =>
    import(`../${componentPath}`)
      .then((module) => ({ default: module.default || module }))
      .catch((error) => {
        console.error(`Failed to load ${componentName}:`, error);
        // Return fallback or unavailable component
        if (FallbackComponent) {
          return { default: FallbackComponent };
        }
        return { default: () => <FeatureUnavailable featureName={componentName} /> };
      })
  );

  // Wrap in Suspense
  return ((props: P) => (
    <Suspense fallback={<LoadingFallback componentName={componentName} />}>
      <LazyComponent {...props} />
    </Suspense>
  )) as ComponentType<P>;
};

/**
 * Load RAG Exam Creator (Premium Feature)
 */
export const loadRAGExamCreator = () =>
  loadComponent(
    'premium/components/RAGExamCreator',
    'RAG Exam Creator'
  );

/**
 * Load Document Chat (Premium Feature)
 */
export const loadDocumentChat = () =>
  loadComponent(
    'premium/components/DocumentChat/DocumentChat',
    'Document Chat'
  );

/**
 * Load Prompt Management (Premium Feature)
 */
export const loadPromptManagement = () =>
  loadComponent(
    'premium/components/prompts/PromptManagement',
    'Prompt Management'
  );

/**
 * Load Prompt Template Selector (Premium Feature)
 */
export const loadPromptTemplateSelector = () =>
  loadComponent(
    'premium/components/prompts/PromptTemplateSelector',
    'Prompt Template Selector'
  );

/**
 * Load Prompt Library with Upload (Premium Feature)
 * Falls back to Core PromptLibrary if Premium not available
 */
export const loadPromptLibraryWithUpload = () => {
  // Import Core PromptLibrary as fallback
  const CorePromptLibrary = require('../pages/PromptLibrary').PromptLibrary;

  return loadComponent(
    'premium/components/prompts/PromptLibraryWithUpload',
    'Prompt Library with Upload',
    CorePromptLibrary
  );
};

/**
 * Load Custom Branding (Enterprise Feature)
 */
export const loadCustomBranding = () =>
  loadComponent(
    'enterprise/components/CustomBranding',
    'Custom Branding'
  );

/**
 * Load SSO Configuration (Enterprise Feature)
 */
export const loadSSOConfiguration = () =>
  loadComponent(
    'enterprise/components/SSOConfiguration',
    'SSO Configuration'
  );
