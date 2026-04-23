import React, { useState } from 'react';
import { Box, IconButton, Typography } from '@mui/material';
import { ThumbUpOutlined, ThumbDownOutlined } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { helpService } from '../../services/HelpService';

interface HelpFeedbackProps {
  question: string;
  answer: string;
  confidence: number;
  route: string;
}

const HelpFeedback: React.FC<HelpFeedbackProps> = ({ question, answer, confidence, route }) => {
  const { t } = useTranslation();
  const { accessToken } = useAuth();
  const [submitted, setSubmitted] = useState<'up' | 'down' | null>(null);

  const handleFeedback = async (rating: 'up' | 'down') => {
    if (!accessToken || submitted) return;
    setSubmitted(rating);
    await helpService.submitFeedback(accessToken, { question, answer, confidence, rating, route });
  };

  if (submitted) {
    return (
      <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
        {t('help.feedback.thanks')}
      </Typography>
    );
  }

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
      <Typography variant="caption" color="text.secondary">
        {t('help.feedback.helpful')}
      </Typography>
      <IconButton size="small" onClick={() => handleFeedback('up')}>
        <ThumbUpOutlined fontSize="small" />
      </IconButton>
      <IconButton size="small" onClick={() => handleFeedback('down')}>
        <ThumbDownOutlined fontSize="small" />
      </IconButton>
    </Box>
  );
};

export default HelpFeedback;
