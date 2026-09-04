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
import { useTranslation } from 'react-i18next';
import { isFullDeployment } from './deploymentMode';
import { withFeatureGate } from '../components/common/withFeatureGate';

/**
 * Feature unavailable component
 */
const FeatureUnavailable: React.FC<{ featureName: string }> = ({ featureName }) => {
  const { t } = useTranslation();
  return (
    <Box
      display="flex"
      flexDirection="column"
      justifyContent="center"
      alignItems="center"
      minHeight="200px"
      sx={{ p: 3 }}
    >
      <Typography variant="h6" color="textSecondary" gutterBottom>
        {t('components.featureUnavailable.title', { feature: featureName })}
      </Typography>
      <Typography variant="body2" color="textSecondary" align="center">
        {t('components.featureUnavailable.body')}
        <br />
        {t('components.featureUnavailable.hint')}
      </Typography>
    </Box>
  );
};

/**
 * Loading fallback component
 */
const LoadingFallback: React.FC<{ componentName?: string }> = ({ componentName }) => {
  const { t } = useTranslation();
  return (
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
          {t('components.componentLoader.loading', { component: componentName })}
        </Typography>
      )}
    </Box>
  );
};

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
          'components.featureGate.ragExamCreator.name',
          'components.featureGate.ragExamCreator.description'
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
 * 2. RBAC: User must have 'document_chatbot' feature (Professional tier)
 */
export const loadDocumentChat = () => {
  if (!isFullDeployment()) {
    console.warn('[componentLoader] Document Chat not available in Core deployment');
    return () => <FeatureUnavailable featureName="Document Chat" />;
  }

  const LazyComponent = lazy(() =>
    import('@examcraft/premium').then(module => ({ default: module.DocumentChatPage }))
  );

  return withFeatureGate(
    LazyComponent,
    'document_chatbot',
    'professional',
    'components.featureGate.documentChat.name',
    'components.featureGate.documentChat.description'
  );
};

/**
 * Load Prompt Management (Premium Feature)
 *
 * Checks:
 * 1. Deployment Mode: Must be Full deployment
 * 2. RBAC: User must have 'advanced_prompt_management' feature (Professional tier)
 */
export const loadPromptManagement = () => {
  if (!isFullDeployment()) {
    console.warn('[componentLoader] Prompt Management not available in Core deployment');
    return () => <FeatureUnavailable featureName="Prompt Management" />;
  }

  const LazyComponent = lazy(() =>
    import('@examcraft/premium').then(module => ({ default: module.PromptLibraryWithUpload }))
  );

  return withFeatureGate(
    LazyComponent,
    'advanced_prompt_management',
    'professional',
    'components.featureGate.promptManagement.name',
    'components.featureGate.promptManagement.description'
  );
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
          'components.featureGate.promptTemplateSelector.name',
          'components.featureGate.promptTemplateSelector.description'
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
          'components.featureGate.advancedPromptManagement.name',
          'components.featureGate.advancedPromptManagement.description'
        );
        return { default: ProtectedComponent };
      })
      .catch((error) => {
        console.error('[componentLoader] Failed to load Premium Prompt Library:', error);
        return { default: CorePromptLibrary };
      })
  );

  return (props: any) => (
    <div data-testid="prompts-content">
      <Suspense fallback={<LoadingFallback componentName="Prompt Library" />}>
        <LazyComponent {...props} />
      </Suspense>
    </div>
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

  // A CustomBranding component existed as an unwired placeholder but was
  // never lazy-loaded from here; it was removed as dead code in TF-671.
  // Implementing this feature means building the component from scratch.
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

  // An SSOConfiguration component existed as an unwired placeholder but was
  // never lazy-loaded from here; it was removed as dead code in TF-671.
  // Implementing this feature means building the component from scratch.
  return () => <FeatureUnavailable featureName="SSO Configuration" />;
};

/**
 * Loads the premium RAGService class for use by GenerationTasksContext.
 * Returns null in Core mode (no premium package available).
 */
export const loadRAGService = async (): Promise<any> => {
  if (!isFullDeployment()) return null;
  try {
    const module = await import(
      /* webpackChunkName: "rag-service" */
      '@examcraft/premium'
    );
    // TF-626: the fallback `|| module.default` that used to be here could
    // never trigger — premium/frontend/src/index.ts only has `export *`,
    // and that deliberately doesn't re-export a default. It was merely
    // invisible because this module was never typechecked.
    return module.RAGService;
  } catch (err) {
    console.error('[componentLoader] Failed to load premium RAGService:', err);
    return null;
  }
};
