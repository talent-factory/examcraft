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

interface RAGExamCreatorProps {
  selectedDocuments?: number[];
  onExamGenerated?: (exam: any) => void;
  onBack?: () => void;
}

const RAGExamCreator: React.FC<RAGExamCreatorProps> = (props) => {
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
          RAG Exam Creator - Premium Feature
        </Typography>
        <Typography variant="body2" sx={{ mb: 2 }}>
          The RAG Exam Creator feature is available in the Premium package.
          This feature allows you to automatically generate exam questions from your documents using AI-powered RAG (Retrieval-Augmented Generation).
        </Typography>
        <Typography variant="body2" color="textSecondary">
          To access this feature, please upgrade to the Starter, Professional, or Enterprise plan.
        </Typography>
      </Alert>

      <Box sx={{ display: 'flex', gap: 2 }}>
        <Button
          variant="contained"
          color="primary"
          onClick={() => props.onBack ? props.onBack() : navigate('/exams')}
        >
          Back
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

export default RAGExamCreator;
