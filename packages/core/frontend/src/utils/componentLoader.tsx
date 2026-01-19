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
 * Uses @examcraft/premium package in workspace
 */
export const loadRAGExamCreator = () => {
  if (!isFullDeployment()) {
    return () => <FeatureUnavailable featureName="RAG Exam Creator" />;
  }

  const LazyComponent = lazy(() =>
    import('@examcraft/premium')
      .then((module) => ({ default: module.RAGExamCreator }))
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
 */
export const loadDocumentChat = () => {
  if (!isFullDeployment()) {
    return () => <FeatureUnavailable featureName="Document Chat" />;
  }

  const LazyComponent = lazy(() =>
    import('@examcraft/premium')
      .then((module) => ({ default: module.DocumentChatPage }))
      .catch((error) => {
        console.error('Failed to load Document Chat:', error);
        return { default: () => <FeatureUnavailable featureName="Document Chat" /> };
      })
  );

  return (props: any) => (
    <Suspense fallback={<LoadingFallback componentName="Document Chat" />}>
      <LazyComponent {...props} />
    </Suspense>
  );
};

/**
 * Load Prompt Management (Premium Feature)
 */
export const loadPromptManagement = () => {
  if (!isFullDeployment()) {
    return () => <FeatureUnavailable featureName="Prompt Management" />;
  }

  const LazyComponent = lazy(() =>
    import('@examcraft/premium')
      .then((module) => ({ default: module.PromptLibraryWithUpload }))
      .catch((error) => {
        console.error('Failed to load Prompt Management:', error);
        return { default: () => <FeatureUnavailable featureName="Prompt Management" /> };
      })
  );

  return (props: any) => (
    <Suspense fallback={<LoadingFallback componentName="Prompt Management" />}>
      <LazyComponent {...props} />
    </Suspense>
  );
};

/**
 * Load Prompt Template Selector (Premium Feature)
 */
export const loadPromptTemplateSelector = () => {
  if (!isFullDeployment()) {
    return () => <FeatureUnavailable featureName="Prompt Template Selector" />;
  }

  const LazyComponent = lazy(() =>
    import('@examcraft/premium')
      .then((module) => ({ default: module.PromptTemplateSelector }))
      .catch((error) => {
        console.error('Failed to load Prompt Template Selector:', error);
        return { default: () => <FeatureUnavailable featureName="Prompt Template Selector" /> };
      })
  );

  return (props: any) => (
    <Suspense fallback={<LoadingFallback componentName="Prompt Template Selector" />}>
      <LazyComponent {...props} />
    </Suspense>
  );
};

/**
 * Load Prompt Library with Upload (Premium Feature)
 * Falls back to Core PromptLibrary if Premium not available
 */
export const loadPromptLibraryWithUpload = () => {
  if (!isFullDeployment()) {
    return () => <FeatureUnavailable featureName="Prompt Library with Upload" />;
  }

  const LazyComponent = lazy(() =>
    import('@examcraft/premium')
      .then((module) => ({ default: module.PromptLibraryWithUpload }))
      .catch((error) => {
        console.error('Failed to load Prompt Library with Upload:', error);
        return { default: () => <FeatureUnavailable featureName="Prompt Library with Upload" /> };
      })
  );

  return (props: any) => (
    <Suspense fallback={<LoadingFallback componentName="Prompt Library with Upload" />}>
      <LazyComponent {...props} />
    </Suspense>
  );
};

/**
 * Load Custom Branding (Enterprise Feature)
 */
export const loadCustomBranding = () => {
  if (!isFullDeployment()) {
    return () => <FeatureUnavailable featureName="Custom Branding" />;
  }

  const LazyComponent = lazy(() =>
    import('@examcraft/enterprise')
      .then((module) => ({ default: module.CustomBranding }))
      .catch((error) => {
        console.error('Failed to load Custom Branding:', error);
        return { default: () => <FeatureUnavailable featureName="Custom Branding" /> };
      })
  );

  return (props: any) => (
    <Suspense fallback={<LoadingFallback componentName="Custom Branding" />}>
      <LazyComponent {...props} />
    </Suspense>
  );
};

/**
 * Load SSO Configuration (Enterprise Feature)
 */
export const loadSSOConfiguration = () => {
  if (!isFullDeployment()) {
    return () => <FeatureUnavailable featureName="SSO Configuration" />;
  }

  const LazyComponent = lazy(() =>
    import('@examcraft/enterprise')
      .then((module) => ({ default: module.SSOConfiguration }))
      .catch((error) => {
        console.error('Failed to load SSO Configuration:', error);
        return { default: () => <FeatureUnavailable featureName="SSO Configuration" /> };
      })
  );

  return (props: any) => (
    <Suspense fallback={<LoadingFallback componentName="SSO Configuration" />}>
      <LazyComponent {...props} />
    </Suspense>
  );
};
