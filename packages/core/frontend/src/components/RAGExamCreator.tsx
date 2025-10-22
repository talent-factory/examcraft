/**
 * RAG Exam Creator Component
 * Creates exams using RAG (Retrieval-Augmented Generation)
 * 
 * Note: This is a placeholder component for the Core package.
 * Full implementation is available in the Premium package.
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

const RAGExamCreator: React.FC<RAGExamCreatorProps> = ({
  onBack,
}) => {
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
          RAG Exam Creator - Premium Feature
        </Typography>
        <Typography variant="body2" sx={{ mb: 2 }}>
          The RAG Exam Creator feature is available in the Premium package.
          This feature allows you to automatically generate exam questions from your documents using AI-powered RAG (Retrieval-Augmented Generation).
        </Typography>
        <Typography variant="body2" color="textSecondary">
          To access this feature, please upgrade to the Premium plan.
        </Typography>
      </Alert>

      <Box sx={{ display: 'flex', gap: 2 }}>
        <Button
          variant="contained"
          color="primary"
          onClick={() => onBack ? onBack() : navigate('/exams')}
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

