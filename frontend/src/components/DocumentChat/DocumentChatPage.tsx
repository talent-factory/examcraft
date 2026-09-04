/**
 * Document Chat Page Component
 * Allows users to chat with documents using RAG
 *
 * Note: This is the Core version that shows an upgrade prompt.
 * The Premium version is loaded dynamically in Full deployment mode.
 */

import React from 'react';
import { Box, Typography, Alert, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { InfoOutlined } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';


/**
 * Upgrade Prompt Component
 * Shown when user doesn't have access to Document Chat feature
 */
const UpgradePrompt: React.FC = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();

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
          {t('components.documentChatPage.title')}
        </Typography>
        <Typography variant="body2" sx={{ mb: 2 }}>
          {t('components.documentChatPage.description')}
        </Typography>
        <Typography variant="body2" color="textSecondary">
          {t('components.documentChatPage.upgradeHint')}
        </Typography>
      </Alert>

      <Box sx={{ display: 'flex', gap: 2 }}>
        <Button
          variant="contained"
          color="primary"
          onClick={() => navigate('/documents')}
        >
          {t('components.documentChatPage.backToDocuments')}
        </Button>
        <Button
          variant="outlined"
          color="primary"
          href="https://examcraft.ai/pricing"
          target="_blank"
        >
          {t('components.documentChatPage.viewPlans')}
        </Button>
      </Box>
    </Box>
  );
};

/**
 * Main Document Chat Page Component
 * Shows upgrade prompt in Core deployment mode
 */
export const DocumentChatPage: React.FC = () => {
  // In Core deployment, always show upgrade prompt
  return <UpgradePrompt />;
};
