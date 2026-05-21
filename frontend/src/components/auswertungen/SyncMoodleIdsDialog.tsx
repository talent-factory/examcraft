/**
 * SyncMoodleIdsDialog (TF-336 Subarea D).
 *
 * Lehrperson trägt die Moodle-Quiz-ID ein (optional inkl. der
 * Question-IDs in Slot-Reihenfolge). Wir POSTen an
 * `/api/v1/exams/{id}/sync-moodle-question-ids`; Backend verifiziert
 * via Web-Service-Call und schreibt `external_refs` zurück.
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
} from '@mui/material';

import { ApiError } from '../../services/submissionsService';
import { MoodleConnectionsService } from '../../services/moodleConnectionsService';

interface Props {
  open: boolean;
  examId: number;
  onClose: () => void;
  onSynced?: (count: number, quizId: number) => void;
}

const SyncMoodleIdsDialog: React.FC<Props> = ({
  open,
  examId,
  onClose,
  onSynced,
}) => {
  const { t } = useTranslation();
  const [quizIdRaw, setQuizIdRaw] = useState('');
  const [questionIdsRaw, setQuestionIdsRaw] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSubmit = async () => {
    setError(null);
    setSuccess(null);
    const quizId = Number(quizIdRaw);
    if (!Number.isFinite(quizId) || quizId <= 0) {
      setError(t('auswertungen.moodleSync.error'));
      return;
    }
    let questionIds: number[] | undefined;
    const trimmed = questionIdsRaw.trim();
    if (trimmed) {
      const parts = trimmed
        .split(/[,\s]+/)
        .map((s) => Number(s.trim()))
        .filter((n) => !Number.isNaN(n));
      if (parts.length === 0) {
        setError(t('auswertungen.moodleSync.error'));
        return;
      }
      questionIds = parts;
    }
    setSubmitting(true);
    try {
      const result = await MoodleConnectionsService.syncQuestionIds(examId, {
        moodle_quiz_id: quizId,
        moodle_question_ids: questionIds,
      });
      setSuccess(
        t('auswertungen.moodleSync.success', {
          count: result.questions.length,
          quiz: result.moodle_quiz_id,
        }),
      );
      onSynced?.(result.questions.length, result.moodle_quiz_id);
      // Auto-close after a short delay so the user sees the success.
      setTimeout(() => {
        setSuccess(null);
        onClose();
      }, 1500);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setError(
          t('auswertungen.moodleSync.notVisible', { id: quizId }),
        );
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError(t('auswertungen.moodleSync.error'));
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>{t('auswertungen.moodleSync.dialogTitle')}</DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} data-testid="sync-error">
            {error}
          </Alert>
        )}
        {success && (
          <Alert severity="success" sx={{ mb: 2 }} data-testid="sync-success">
            {success}
          </Alert>
        )}
        <Stack spacing={2} sx={{ mt: 1 }}>
          <TextField
            autoFocus
            fullWidth
            label={t('auswertungen.moodleSync.quizIdLabel')}
            helperText={t('auswertungen.moodleSync.quizIdHelper')}
            value={quizIdRaw}
            onChange={(e) => setQuizIdRaw(e.target.value)}
            inputProps={{ 'data-testid': 'sync-quiz-id', inputMode: 'numeric' }}
          />
          <TextField
            fullWidth
            multiline
            minRows={2}
            label={t('auswertungen.moodleSync.questionIdsLabel')}
            helperText={t('auswertungen.moodleSync.questionIdsHelper')}
            value={questionIdsRaw}
            onChange={(e) => setQuestionIdsRaw(e.target.value)}
            inputProps={{ 'data-testid': 'sync-question-ids' }}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>
          {t('auswertungen.moodleSync.cancel')}
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={submitting || !quizIdRaw}
          data-testid="sync-submit"
        >
          {t('auswertungen.moodleSync.submit')}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default SyncMoodleIdsDialog;
