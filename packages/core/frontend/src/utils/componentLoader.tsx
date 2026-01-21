/**
 * Runtime Component Loader for Premium/Enterprise Features
 *
 * Dynamically loads Premium/Enterprise components based on deployment mode.
 * Replaces static imports and volume mounts for cleaner deployment.
 */

import React, { lazy, Suspense, ComponentType } from 'react';
import { Box, Typography, CircularProgress } from '@mui/material';

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
 * Generic component loader with error handling
 * DEPRECATED: Use specific loader functions instead (loadRAGExamCreator, loadDocumentChat, etc.)
 * This function is kept for backward compatibility but should not be used for new code.
 */
export const loadComponent = <P extends object>(
  componentPath: string,
  componentName: string,
  FallbackComponent?: ComponentType<P>
): ComponentType<P> => {
  console.warn(`loadComponent is deprecated. Use specific loader functions instead.`);
  return (FallbackComponent || (() => <FeatureUnavailable featureName={componentName} />)) as ComponentType<P>;
};



/**
 * Load RAG Exam Creator (Premium Feature)
 * Uses @examcraft/premium package via Webpack alias
 */
export const loadRAGExamCreator = () => {
  const LazyComponent = lazy(() =>
    // @examcraft/premium resolves to ../../premium/frontend/src via craco.config.js
    import(/* webpackChunkName: "premium-rag-exam-creator" */ '@examcraft/premium')
      .then((module) => ({ default: module.RAGExamCreator || module.default }))
      .catch((error) => {
        console.error('Failed to load RAG Exam Creator:', error);
        return { default: () => <FeatureUnavailable featureName="RAG Exam Creator" /> };
      })
  );

  return (props: any) => (
    <Suspense fallback={<LoadingFallback componentName="RAG Exam Creator" />}>
      <LazyComponent {...props} />
    </Suspense>
  );
};

/**
 * Load Document Chat (Premium Feature)
 * Fallback: Returns unavailable component in Core deployment
 */
export const loadDocumentChat = () => {
  // Always return unavailable for now (Premium feature not implemented yet)
  return () => <FeatureUnavailable featureName="Document Chat" />;
};

/**
 * Load Prompt Management (Premium Feature)
 * Fallback: Returns unavailable component in Core deployment
 */
export const loadPromptManagement = () => {
  // Always return unavailable for now (Premium feature not implemented yet)
  return () => <FeatureUnavailable featureName="Prompt Management" />;
};

/**
 * Load Prompt Template Selector (Premium Feature)
 * Fallback: Returns unavailable component in Core deployment
 */
export const loadPromptTemplateSelector = () => {
  // Always return unavailable for now (Premium feature not implemented yet)
  return () => <FeatureUnavailable featureName="Prompt Template Selector" />;
};

/**
 * Load Prompt Library with Upload (Premium Feature)
 * Falls back to Core PromptLibrary if Premium not available
 */
export const loadPromptLibraryWithUpload = () => {
  // Import Core PromptLibrary as fallback
  const CorePromptLibrary = require('../pages/PromptLibrary').PromptLibrary;

  // Always return Core version for now (Premium feature not implemented yet)
  return CorePromptLibrary;
};

/**
 * Load Custom Branding (Enterprise Feature)
 * Fallback: Returns unavailable component in Core deployment
 */
export const loadCustomBranding = () => {
  // Always return unavailable for now (Enterprise feature not implemented yet)
  return () => <FeatureUnavailable featureName="Custom Branding" />;
};

/**
 * Load SSO Configuration (Enterprise Feature)
 * Fallback: Returns unavailable component in Core deployment
 */
export const loadSSOConfiguration = () => {
  // Always return unavailable for now (Enterprise feature not implemented yet)
  return () => <FeatureUnavailable featureName="SSO Configuration" />;
};
