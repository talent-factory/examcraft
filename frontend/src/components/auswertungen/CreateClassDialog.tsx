/**
 * CreateClassDialog — minimal "Klasse anlegen" modal (TF-336 G2).
 *
 * Re-used in two flows: standalone "Klasse anlegen" button on the
 * Klassen list page, and the rename flow when ``initialName`` is set
 * (the parent passes ``mode='rename'``).
 */

import React, { useEffect, useState } from 'react';
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
} from '@mui/material';
import { useTranslation } from 'react-i18next';

import { ApiError } from '../../services/submissionsService';
import { StudentClassesService } from '../../services/studentClassesService';
import type { StudentClassSummary } from '../../types/studentClass';

interface Props {
  open: boolean;
  mode?: 'create' | 'rename';
  classId?: number;
  initialName?: string;
  onClose: () => void;
  onSaved: (cls: StudentClassSummary) => void;
}

const CreateClassDialog: React.FC<Props> = ({
  open,
  mode = 'create',
  classId,
  initialName,
  onClose,
  onSaved,
}) => {
  const { t } = useTranslation();
  const [name, setName] = useState(initialName ?? '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setName(initialName ?? '');
      setError(null);
    }
  }, [open, initialName]);

  const handleSubmit = async () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    setLoading(true);
    setError(null);
    try {
      const result =
        mode === 'rename' && classId
          ? await StudentClassesService.rename(classId, trimmed)
          : await StudentClassesService.create(trimmed);
      onSaved(result);
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError(t('auswertungen.klassen.createDialog.duplicate'));
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError(t('auswertungen.klassen.createDialog.error'));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>
        {mode === 'rename'
          ? t('auswertungen.klassen.renameDialog.title')
          : t('auswertungen.klassen.createDialog.title')}
      </DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} data-testid="create-class-error">
            {error}
          </Alert>
        )}
        <TextField
          autoFocus
          fullWidth
          label={t('auswertungen.klassen.createDialog.nameLabel')}
          helperText={t('auswertungen.klassen.createDialog.nameHelper')}
          value={name}
          onChange={(e) => setName(e.target.value)}
          inputProps={{ 'data-testid': 'create-class-name', maxLength: 200 }}
          sx={{ mt: 1 }}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>
          {t('auswertungen.klassen.createDialog.cancel')}
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={loading || !name.trim()}
          data-testid="create-class-submit"
        >
          {mode === 'rename'
            ? t('auswertungen.klassen.renameDialog.submit')
            : t('auswertungen.klassen.createDialog.submit')}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default CreateClassDialog;
