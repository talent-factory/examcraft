/**
 * Basic Exam Creator (Core Version)
 * Simple exam generation without RAG features
 */

import React, { useState } from 'react';
import {
  Box,
  Container,
  Typography,
  TextField,
  Button,
  Paper,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';

interface BasicExamCreatorProps {
  selectedDocuments?: any[];
  onExamGenerated?: (exam: any) => void;
  onBack?: () => void;
}

export const BasicExamCreator: React.FC<BasicExamCreatorProps> = ({
  selectedDocuments = [],
  onExamGenerated,
  onBack,
}) => {
  const { accessToken } = useAuth();
  const { t } = useTranslation();
  const [topic, setTopic] = useState('');
  const [questionCount, setQuestionCount] = useState(5);
  const [difficulty, setDifficulty] = useState('medium');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleGenerate = async () => {
    if (!topic.trim()) {
      setError(t('components.basicExamCreator.topicRequired'));
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(false);

    const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    try {
      const response = await fetch(`${apiUrl}/api/v1/questions/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          topic,
          num_questions: questionCount,
          difficulty,
          document_ids: selectedDocuments.map((doc) => doc.id),
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || t('components.basicExamCreator.generationError'));
      }

      const data = await response.json();
      setSuccess(true);

      if (onExamGenerated) {
        onExamGenerated(data);
      }
    } catch (err: any) {
      setError(err.message || t('components.basicExamCreator.generationError'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="md">
      <Paper sx={{ p: 4 }}>
        <Typography variant="h5" gutterBottom>
          {t('components.basicExamCreator.title')}
        </Typography>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          {t('components.basicExamCreator.subtitle')}
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess(false)}>
            {t('components.basicExamCreator.successMessage')}
          </Alert>
        )}

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          <TextField
            label={t('components.basicExamCreator.topicLabel')}
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder={t('components.basicExamCreator.topicPlaceholder')}
            fullWidth
            required
          />

          <TextField
            label={t('components.basicExamCreator.questionCountLabel')}
            type="number"
            value={questionCount}
            onChange={(e) => setQuestionCount(parseInt(e.target.value, 10))}
            inputProps={{ min: 1, max: 20 }}
            fullWidth
          />

          <FormControl fullWidth>
            <InputLabel>{t('components.basicExamCreator.difficultyLabel')}</InputLabel>
            <Select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
              label={t('components.basicExamCreator.difficultyLabel')}
            >
              <MenuItem value="easy">{t('components.basicExamCreator.difficultyEasy')}</MenuItem>
              <MenuItem value="medium">{t('components.basicExamCreator.difficultyMedium')}</MenuItem>
              <MenuItem value="hard">{t('components.basicExamCreator.difficultyHard')}</MenuItem>
            </Select>
          </FormControl>

          <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
            {onBack && (
              <Button onClick={onBack} disabled={loading}>
                {t('components.basicExamCreator.back')}
              </Button>
            )}
            <Button
              variant="contained"
              onClick={handleGenerate}
              disabled={loading || !topic.trim()}
            >
              {loading ? <CircularProgress size={24} /> : t('components.basicExamCreator.generate')}
            </Button>
          </Box>
        </Box>
      </Paper>
    </Container>
  );
};
