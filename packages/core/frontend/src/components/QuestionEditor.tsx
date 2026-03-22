/**
 * QuestionEditor Component
 * Inline editing form for questions
 */

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
  Typography,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Alert,
  Stack,
} from '@mui/material';
import {
  Close,
  Add,
  Delete,
  Save,
  Cancel as CancelIcon,
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { QuestionReview, QuestionReviewUpdateRequest } from '../types/review';

interface QuestionEditorProps {
  question: QuestionReview;
  open: boolean;
  onClose: () => void;
  onSave: (questionId: number, updates: QuestionReviewUpdateRequest) => Promise<void>;
  loading?: boolean;
}

const QuestionEditor: React.FC<QuestionEditorProps> = ({
  question,
  open,
  onClose,
  onSave,
  loading = false,
}) => {
  const { t } = useTranslation();
  const [formData, setFormData] = useState<QuestionReviewUpdateRequest>({});
  const [options, setOptions] = useState<string[]>([]);
  const [newOption, setNewOption] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [hasChanges, setHasChanges] = useState(false);

  // Initialize form data when question changes
  useEffect(() => {
    if (question) {
      setFormData({
        question_text: question.question_text,
        options: question.options,
        correct_answer: question.correct_answer,
        explanation: question.explanation,
        difficulty: question.difficulty,
        bloom_level: question.bloom_level,
        estimated_time_minutes: question.estimated_time_minutes,
      });
      setOptions(question.options || []);
      setHasChanges(false);
      setErrors({});
    }
  }, [question, open]);

  const handleFieldChange = (field: keyof QuestionReviewUpdateRequest, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setHasChanges(true);
    // Clear error for this field
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const handleAddOption = () => {
    if (newOption.trim()) {
      const updatedOptions = [...options, newOption.trim()];
      setOptions(updatedOptions);
      handleFieldChange('options', updatedOptions);
      setNewOption('');
    }
  };

  const handleRemoveOption = (index: number) => {
    const updatedOptions = options.filter((_, i) => i !== index);
    setOptions(updatedOptions);
    handleFieldChange('options', updatedOptions);
  };

  const handleCorrectAnswerChange = (value: string) => {
    handleFieldChange('correct_answer', value);
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.question_text || formData.question_text.trim().length < 10) {
      newErrors.question_text = t('components.questionEditor.validationQuestionLength');
    }

    if (question.question_type === 'multiple_choice') {
      if (!options || options.length < 2) {
        newErrors.options = t('components.questionEditor.validationMinOptions');
      }
      if (!formData.correct_answer) {
        newErrors.correct_answer = t('components.questionEditor.validationSelectAnswer');
      }
      if (formData.correct_answer && !options.includes(formData.correct_answer)) {
        newErrors.correct_answer = t('components.questionEditor.validationAnswerInOptions');
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!validateForm()) {
      return;
    }

    try {
      // Only send changed fields
      const updates: QuestionReviewUpdateRequest = {};

      if (formData.question_text !== question.question_text) {
        updates.question_text = formData.question_text;
      }
      if (JSON.stringify(formData.options) !== JSON.stringify(question.options)) {
        updates.options = formData.options;
      }
      if (formData.correct_answer !== question.correct_answer) {
        updates.correct_answer = formData.correct_answer;
      }
      if (formData.explanation !== question.explanation) {
        updates.explanation = formData.explanation;
      }
      if (formData.difficulty !== question.difficulty) {
        updates.difficulty = formData.difficulty;
      }
      if (formData.bloom_level !== question.bloom_level) {
        updates.bloom_level = formData.bloom_level;
      }
      if (formData.estimated_time_minutes !== question.estimated_time_minutes) {
        updates.estimated_time_minutes = formData.estimated_time_minutes;
      }

      await onSave(question.id, updates);
      onClose();
    } catch (error) {
      console.error('Failed to save question:', error);
    }
  };

  const handleCancel = () => {
    if (hasChanges) {
      if (window.confirm(t('components.questionEditor.unsavedConfirm'))) {
        onClose();
      }
    } else {
      onClose();
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleCancel}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">{t('components.questionEditor.title', { id: question.id })}</Typography>
          <IconButton onClick={handleCancel} size="small">
            <Close />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        <Stack spacing={3}>
          {/* Question Text */}
          <TextField
            label={t('components.questionEditor.questionText')}
            multiline
            rows={3}
            fullWidth
            value={formData.question_text || ''}
            onChange={(e) => handleFieldChange('question_text', e.target.value)}
            error={!!errors.question_text}
            helperText={errors.question_text}
            disabled={loading}
            required
          />

          {/* Options (for multiple choice) */}
          {question.question_type === 'multiple_choice' && (
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                {t('components.questionEditor.answerOptions')}
              </Typography>
              <List dense>
                {options.map((option, index) => (
                  <ListItem
                    key={index}
                    sx={{
                      bgcolor: option === formData.correct_answer ? 'success.light' : 'background.paper',
                      borderRadius: 1,
                      mb: 1,
                    }}
                  >
                    <ListItemText primary={option} />
                    <ListItemSecondaryAction>
                      <IconButton
                        edge="end"
                        onClick={() => handleRemoveOption(index)}
                        disabled={loading}
                        size="small"
                      >
                        <Delete />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                ))}
              </List>

              <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                <TextField
                  size="small"
                  fullWidth
                  placeholder={t('components.questionEditor.addOptionPlaceholder')}
                  value={newOption}
                  onChange={(e) => setNewOption(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddOption();
                    }
                  }}
                  disabled={loading}
                />
                <Button
                  variant="outlined"
                  startIcon={<Add />}
                  onClick={handleAddOption}
                  disabled={loading || !newOption.trim()}
                >
                  {t('components.questionEditor.addOption')}
                </Button>
              </Box>
              {errors.options && (
                <Alert severity="error" sx={{ mt: 1 }}>{errors.options}</Alert>
              )}
            </Box>
          )}

          {/* Correct Answer */}
          {question.question_type === 'multiple_choice' ? (
            <FormControl fullWidth error={!!errors.correct_answer}>
              <InputLabel>{t('components.questionEditor.correctAnswer')}</InputLabel>
              <Select
                value={formData.correct_answer || ''}
                onChange={(e) => handleCorrectAnswerChange(e.target.value)}
                disabled={loading}
                label={t('components.questionEditor.correctAnswer')}
              >
                {options.map((option, index) => (
                  <MenuItem key={index} value={option}>
                    {option}
                  </MenuItem>
                ))}
              </Select>
              {errors.correct_answer && (
                <Typography variant="caption" color="error" sx={{ mt: 0.5 }}>
                  {errors.correct_answer}
                </Typography>
              )}
            </FormControl>
          ) : (
            <TextField
              label={t('components.questionEditor.correctAnswer')}
              multiline
              rows={2}
              fullWidth
              value={formData.correct_answer || ''}
              onChange={(e) => handleFieldChange('correct_answer', e.target.value)}
              disabled={loading}
            />
          )}

          {/* Explanation */}
          <TextField
            label={t('components.questionEditor.explanationLabel')}
            multiline
            rows={3}
            fullWidth
            value={formData.explanation || ''}
            onChange={(e) => handleFieldChange('explanation', e.target.value)}
            disabled={loading}
            helperText={t('components.questionEditor.explanationHint')}
          />

          {/* Difficulty */}
          <FormControl fullWidth>
            <InputLabel>{t('components.questionEditor.difficulty')}</InputLabel>
            <Select
              value={formData.difficulty || 'medium'}
              onChange={(e) => handleFieldChange('difficulty', e.target.value)}
              disabled={loading}
              label={t('components.questionEditor.difficulty')}
            >
              <MenuItem value="easy">Easy</MenuItem>
              <MenuItem value="medium">Medium</MenuItem>
              <MenuItem value="hard">Hard</MenuItem>
            </Select>
          </FormControl>

          {/* Bloom Level */}
          <FormControl fullWidth>
            <InputLabel>{t('components.questionEditor.bloomLevel')}</InputLabel>
            <Select
              value={formData.bloom_level || ''}
              onChange={(e) => handleFieldChange('bloom_level', e.target.value ? Number(e.target.value) : undefined)}
              disabled={loading}
              label={t('components.questionEditor.bloomLevel')}
            >
              <MenuItem value="">{t('components.questionEditor.bloomNotSpecified')}</MenuItem>
              <MenuItem value={1}>1 - Remember</MenuItem>
              <MenuItem value={2}>2 - Understand</MenuItem>
              <MenuItem value={3}>3 - Apply</MenuItem>
              <MenuItem value={4}>4 - Analyze</MenuItem>
              <MenuItem value={5}>5 - Evaluate</MenuItem>
              <MenuItem value={6}>6 - Create</MenuItem>
            </Select>
          </FormControl>

          {/* Estimated Time */}
          <TextField
            label={t('components.questionEditor.estimatedTime')}
            type="number"
            fullWidth
            value={formData.estimated_time_minutes || ''}
            onChange={(e) => handleFieldChange('estimated_time_minutes', e.target.value ? Number(e.target.value) : undefined)}
            disabled={loading}
            inputProps={{ min: 1, max: 180 }}
          />

          {/* Change Indicator */}
          {hasChanges && (
            <Alert severity="info">
              {t('components.questionEditor.unsavedChanges')}
            </Alert>
          )}
        </Stack>
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button
          onClick={handleCancel}
          startIcon={<CancelIcon />}
          disabled={loading}
        >
          {t('components.questionEditor.cancel')}
        </Button>
        <Button
          onClick={handleSave}
          variant="contained"
          startIcon={<Save />}
          disabled={loading || !hasChanges}
        >
          {t('components.questionEditor.saveChanges')}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default QuestionEditor;
