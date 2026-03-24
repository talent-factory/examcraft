/**
 * RAG Exam Creator Component
 * Creates exams using RAG (Retrieval-Augmented Generation)
 *
 * This component checks the user's subscription tier and shows
 * an upgrade prompt for Free tier users.
 *
 * Note: The actual Premium implementation is mounted via Docker volume
 * in docker-compose.full.yml, which provides the full feature set.
 */

import React from 'react';
import { Box, Typography, Alert, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { InfoOutlined } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';

interface RAGExamCreatorProps {
  selectedDocuments?: number[];
  onExamGenerated?: (exam: any) => void;
  onBack?: () => void;
}

const RAGExamCreator: React.FC<RAGExamCreatorProps> = (props) => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  // This is the Core (Free) version - always shows upgrade prompt
  // The Premium version is mounted via Docker volume in docker-compose.full.yml
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
          {t('components.ragExamCreator.premiumTitle')}
        </Typography>
        <Typography variant="body2" sx={{ mb: 2 }}>
          {t('components.ragExamCreator.premiumDescription')}
        </Typography>
        <Typography variant="body2" color="textSecondary">
          {t('components.ragExamCreator.premiumUpgrade')}
        </Typography>
      </Alert>

      <Box sx={{ display: 'flex', gap: 2 }}>
        <Button
          variant="contained"
          color="primary"
          onClick={() => props.onBack ? props.onBack() : navigate('/exams')}
        >
          {t('components.ragExamCreator.back')}
        </Button>
        <Button
          variant="outlined"
          color="primary"
          href="https://examcraft.ai/pricing"
          target="_blank"
        >
          {t('components.ragExamCreator.viewPlans')}
        </Button>
      </Box>
    </Box>
  );
};

export default RAGExamCreator;
