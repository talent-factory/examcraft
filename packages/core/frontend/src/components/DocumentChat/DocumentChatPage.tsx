/**
 * Document Chat Page Component
 * Allows users to chat with documents using RAG
 *
 * Note: This is a placeholder component for the Core package.
 * The Premium implementation is mounted via Docker volume in docker-compose.premium.yml
 */

import React from 'react';
import { Box, Typography, Alert, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { InfoOutlined } from '@mui/icons-material';

export const DocumentChatPage: React.FC = () => {
  const navigate = useNavigate();

  // This is the Core (Free) version - always shows upgrade prompt
  // The Premium version is mounted via Docker volume in docker-compose.premium.yml
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

