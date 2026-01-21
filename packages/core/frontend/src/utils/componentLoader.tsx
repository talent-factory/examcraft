/**
 * Runtime Component Loader for Premium/Enterprise Features
 *
 * Dynamically loads Premium/Enterprise components based on:
 * 1. Deployment Mode (Core vs Full)
 * 2. User Subscription Tier (RBAC)
 *
 * This ensures components are only loaded when:
 * - The deployment supports them (Full mode)
 * - The user has access to them (subscription tier)
 */

import React, { lazy, Suspense, ComponentType } from 'react';
import { Box, Typography, CircularProgress } from '@mui/material';
import { isFullDeployment } from './deploymentMode';
import { withFeatureGate } from '../components/common/withFeatureGate';

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
 *
 * Checks:
 * 1. Deployment Mode: Must be Full deployment
 * 2. RBAC: User must have 'rag_generation' feature (via withFeatureGate)
 *
 * Uses @examcraft/premium package via Webpack alias
 */
export const loadRAGExamCreator = () => {
  // Check deployment mode first
  if (!isFullDeployment()) {
    console.warn('[componentLoader] RAG Exam Creator not available in Core deployment');
    return () => <FeatureUnavailable featureName="RAG Exam Creator" />;
  }

  const LazyComponent = lazy(() =>
    // @examcraft/premium resolves to ../../premium/frontend/src via craco.config.js
    import(/* webpackChunkName: "premium-rag-exam-creator" */ '@examcraft/premium')
      .then((module) => {
        // Wrap with feature gate for RBAC check
        const ProtectedComponent = withFeatureGate(
          module.RAGExamCreator,
          'rag_generation',
          'starter',
          'RAG Exam Creator',
          'Generate exam questions using Retrieval-Augmented Generation with semantic search.'
        );
        return { default: ProtectedComponent };
      })
      .catch((error) => {
        console.error('[componentLoader] Failed to load RAG Exam Creator:', error);
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
 *
 * Checks:
 * 1. Deployment Mode: Must be Full deployment
 * 2. RBAC: User must have 'document_chatbot' feature (checked in component)
 */
export const loadDocumentChat = () => {
  if (!isFullDeployment()) {
    console.warn('[componentLoader] Document Chat not available in Core deployment');
    return () => <FeatureUnavailable featureName="Document Chat" />;
  }

  // TODO: Implement lazy loading when DocumentChat component is ready
  // const LazyComponent = lazy(() =>
  //   import('@examcraft/premium').then(module => ({ default: module.DocumentChat }))
  // );
  return () => <FeatureUnavailable featureName="Document Chat" />;
};

/**
 * Load Prompt Management (Premium Feature)
 *
 * Checks:
 * 1. Deployment Mode: Must be Full deployment
 * 2. RBAC: User must have 'advanced_prompt_management' feature (checked in component)
 */
export const loadPromptManagement = () => {
  if (!isFullDeployment()) {
    console.warn('[componentLoader] Prompt Management not available in Core deployment');
    return () => <FeatureUnavailable featureName="Prompt Management" />;
  }

  // TODO: Implement lazy loading when PromptManagement component is ready
  return () => <FeatureUnavailable featureName="Prompt Management" />;
};

/**
 * Load Prompt Template Selector (Premium Feature)
 *
 * Checks:
 * 1. Deployment Mode: Must be Full deployment
 * 2. RBAC: User must have 'prompt_templates' feature (via withFeatureGate)
 */
export const loadPromptTemplateSelector = () => {
  if (!isFullDeployment()) {
    console.warn('[componentLoader] Prompt Template Selector not available in Core deployment');
    return () => <FeatureUnavailable featureName="Prompt Template Selector" />;
  }

  const LazyComponent = lazy(() =>
    import(/* webpackChunkName: "premium-prompt-template-selector" */ '@examcraft/premium')
      .then((module) => {
        // Wrap with feature gate for RBAC check
        const ProtectedComponent = withFeatureGate(
          module.PromptTemplateSelector,
          'prompt_templates',
          'starter',
          'Prompt Template Selector',
          'Select and customize prompt templates for question generation.'
        );
        return { default: ProtectedComponent };
      })
      .catch((error) => {
        console.error('[componentLoader] Failed to load Prompt Template Selector:', error);
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
 *
 * Checks:
 * 1. Deployment Mode: Must be Full deployment for upload feature
 * 2. RBAC: User must have 'advanced_prompt_management' feature (via withFeatureGate)
 *
 * Falls back to Core PromptLibrary if Premium not available
 */
export const loadPromptLibraryWithUpload = () => {
  // Import Core PromptLibrary as fallback
  const CorePromptLibrary = require('../pages/PromptLibrary').PromptLibrary;

  if (!isFullDeployment()) {
    console.warn('[componentLoader] Prompt Library Upload not available in Core deployment');
    return CorePromptLibrary;
  }

  // Try to load Premium version with lazy loading
  const LazyComponent = lazy(() =>
    import(/* webpackChunkName: "premium-prompt-library" */ '@examcraft/premium')
      .then((module) => {
        // Wrap with feature gate for RBAC check
        const ProtectedComponent = withFeatureGate(
          module.PromptLibraryWithUpload,
          'advanced_prompt_management',
          'professional',
          'Advanced Prompt Management',
          'Upload and manage custom prompt templates with semantic search.'
        );
        return { default: ProtectedComponent };
      })
      .catch((error) => {
        console.error('[componentLoader] Failed to load Premium Prompt Library:', error);
        return { default: CorePromptLibrary };
      })
  );

  return (props: any) => (
    <Suspense fallback={<LoadingFallback componentName="Prompt Library" />}>
      <LazyComponent {...props} />
    </Suspense>
  );
};

/**
 * Load Custom Branding (Enterprise Feature)
 *
 * Checks:
 * 1. Deployment Mode: Must be Full deployment
 * 2. RBAC: User must have 'custom_branding' feature (checked in component)
 */
export const loadCustomBranding = () => {
  if (!isFullDeployment()) {
    console.warn('[componentLoader] Custom Branding not available in Core deployment');
    return () => <FeatureUnavailable featureName="Custom Branding" />;
  }

  // TODO: Implement lazy loading when CustomBranding component is ready
  // const LazyComponent = lazy(() =>
  //   import('@examcraft/enterprise').then(module => ({ default: module.CustomBranding }))
  // );
  return () => <FeatureUnavailable featureName="Custom Branding" />;
};

/**
 * Load SSO Configuration (Enterprise Feature)
 *
 * Checks:
 * 1. Deployment Mode: Must be Full deployment
 * 2. RBAC: User must have 'sso_integration' feature (checked in component)
 */
export const loadSSOConfiguration = () => {
  if (!isFullDeployment()) {
    console.warn('[componentLoader] SSO Configuration not available in Core deployment');
    return () => <FeatureUnavailable featureName="SSO Configuration" />;
  }

  // TODO: Implement lazy loading when SSOConfiguration component is ready
  // const LazyComponent = lazy(() =>
  //   import('@examcraft/enterprise').then(module => ({ default: module.SSOConfiguration }))
  // );
  return () => <FeatureUnavailable featureName="SSO Configuration" />;
};
