/**
 * Document Chat Page Component
 * Allows users to chat with documents using RAG
 *
 * Note: This component dynamically loads the Premium implementation
 * if the user has the required subscription tier.
 * Otherwise shows upgrade prompt.
 */

import React, { lazy, Suspense } from 'react';
import { Box, Typography, Alert, Button, CircularProgress } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { InfoOutlined } from '@mui/icons-material';
import { useAuth } from '../../contexts/AuthContext';
import { isFullDeployment } from '../../utils/deploymentMode';

// Lazy load Premium DocumentChat component
const PremiumDocumentChatPage = lazy(() =>
  import('../../../premium/components/DocumentChat/DocumentChatPage')
    .then(module => ({ default: module.DocumentChatPage }))
    .catch(() => {
      // Premium package not available - will show upgrade prompt
      return { default: UpgradePrompt };
    })
);

/**
 * Upgrade Prompt Component
 * Shown when user doesn't have access to Document Chat feature
 */
const UpgradePrompt: React.FC = () => {
  const navigate = useNavigate();

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        gap: 3,
        p: 2,
      }}
    >
      <Alert
        severity="info"
        icon={<InfoOutlined />}
        sx={{ maxWidth: 600 }}
      >
        <Typography variant="h6" sx={{ mb: 1 }}>
          Document Chat - Premium Feature
        </Typography>
        <Typography variant="body2" sx={{ mb: 2 }}>
          The Document Chat feature is available in the Premium package.
          This feature allows you to have interactive conversations with your documents using AI-powered RAG (Retrieval-Augmented Generation).
        </Typography>
        <Typography variant="body2" color="textSecondary">
          To access this feature, please upgrade to the Professional or Enterprise plan.
        </Typography>
      </Alert>

      <Box sx={{ display: 'flex', gap: 2 }}>
        <Button
          variant="contained"
          color="primary"
          onClick={() => navigate('/documents')}
        >
          Back to Documents
        </Button>
        <Button
          variant="outlined"
          color="primary"
          href="https://examcraft.ai/pricing"
          target="_blank"
        >
          View Premium Plans
        </Button>
      </Box>
    </Box>
  );
};

/**
 * Loading Fallback Component
 */
const LoadingFallback: React.FC = () => (
  <Box
    sx={{
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
    }}
  >
    <CircularProgress />
    <Typography variant="body2" color="textSecondary" sx={{ mt: 2 }}>
      Loading Document Chat...
    </Typography>
  </Box>
);

/**
 * Main Document Chat Page Component
 * Dynamically loads Premium version based on user permissions
 */
export const DocumentChatPage: React.FC = () => {
  const { hasPermission } = useAuth();

  // Check if user has document_chatbot feature (Professional/Enterprise tier)
  const hasDocumentChatAccess = hasPermission('document_chatbot');

  // Check if Full deployment (Premium/Enterprise packages available)
  const isFullMode = isFullDeployment();

  // If user has access AND Full deployment mode, load Premium component
  if (hasDocumentChatAccess && isFullMode) {
    return (
      <Suspense fallback={<LoadingFallback />}>
        <PremiumDocumentChatPage />
      </Suspense>
    );
  }

  // Otherwise show upgrade prompt
  return <UpgradePrompt />;
};
