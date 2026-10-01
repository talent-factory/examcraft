import React, { useState } from 'react';
import { Box, IconButton, Typography } from '@mui/material';
import { ThumbUpOutlined, ThumbDownOutlined } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { helpService } from '../../services/HelpService';
import { translateError } from '../../errors';

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
  const [error, setError] = useState<string | null>(null);

  // The thanks show optimistically, so a second click cannot send twice. On
  // failure they are taken back and the buttons return with the reason —
  // before TF-996 the rejection went unhandled and the rating was lost while
  // the widget said thanks.
  const handleFeedback = async (rating: 'up' | 'down') => {
    if (!accessToken || submitted) return;
    setSubmitted(rating);
    setError(null);
    try {
      await helpService.submitFeedback(accessToken, { question, answer, confidence, rating, route });
    } catch (err) {
      console.warn('Failed to submit help feedback:', err);
      setSubmitted(null);
      setError(translateError(err, t, 'errors.help_feedback_failed'));
    }
  };

  if (submitted) {
    return (
      <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
        {t('help.feedback.thanks')}
      </Typography>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
      <Typography variant="caption" color="text.secondary">
        {t('help.feedback.helpful')}
      </Typography>
      <IconButton size="small" onClick={() => handleFeedback('up')}>
        <ThumbUpOutlined fontSize="small" />
      </IconButton>
      <IconButton size="small" onClick={() => handleFeedback('down')}>
        <ThumbDownOutlined fontSize="small" />
      </IconButton>
      {error && (
        // Own line below the thumbs: the help panel is narrow, and squeezed
        // next to them the sentence would wrap word by word.
        <Typography
          variant="caption"
          color="error"
          role="alert"
          data-testid="help-feedback-error"
          sx={{ flexBasis: '100%' }}
        >
          {error}
        </Typography>
      )}
    </Box>
  );
};

export default HelpFeedback;
