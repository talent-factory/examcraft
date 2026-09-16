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

import React, { lazy, Suspense } from 'react';
import { Box, Typography, CircularProgress } from '@mui/material';
import { useTranslation } from 'react-i18next';
import { isFullDeployment } from './deploymentMode';
import { withFeatureGate } from '../components/common/withFeatureGate';

/**
 * Feature unavailable component
 *
 * Takes an i18n key, not a display name: the loaders below run outside any
 * component body and cannot call `t()`, and the English literals they used to
 * pass ended up interpolated into an otherwise translated sentence
 * ("RAG Exam Creator ist nicht verfügbar").
 */
const FeatureUnavailable: React.FC<{ featureNameKey: string }> = ({ featureNameKey }) => {
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
        {t('components.featureUnavailable.title', { feature: t(featureNameKey) })}
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
 * Loading fallback component. `componentNameKey` is an i18n key, for the same
 * reason as `FeatureUnavailable`.
 */
const LoadingFallback: React.FC<{ componentNameKey?: string }> = ({ componentNameKey }) => {
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
      {componentNameKey && (
        <Typography variant="body2" color="textSecondary" sx={{ mt: 2 }}>
          {t('components.componentLoader.loading', { component: t(componentNameKey) })}
        </Typography>
      )}
    </Box>
  );
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
    return () => <FeatureUnavailable featureNameKey="components.featureGate.ragExamCreator.name" />;
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
        return {
          default: () => (
            <FeatureUnavailable featureNameKey="components.featureGate.ragExamCreator.name" />
          ),
        };
      })
  );

  return (props: any) => (
    <Suspense
      fallback={<LoadingFallback componentNameKey="components.featureGate.ragExamCreator.name" />}
    >
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
    return () => <FeatureUnavailable featureNameKey="components.featureGate.documentChat.name" />;
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
      <Suspense
        fallback={
          <LoadingFallback componentNameKey="components.featureGate.advancedPromptManagement.name" />
        }
      >
        <LazyComponent {...props} />
      </Suspense>
    </div>
  );
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
