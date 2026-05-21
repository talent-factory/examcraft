/**
 * OverrideGradeDialog — gemeinsamer Dialog für Manual-Override (TF-334).
 *
 * Wird sowohl aus der Review-Queue (vorgeschlagener LLM-Grade) als auch
 * aus der Submissions-Detailansicht (MC/W-F „Manuell überstimmen") aufgerufen.
 * Validiert clientseitig (NaN, Range), zeigt Fehler aus dem Backend
 * unverändert an und ruft ``onSuccess`` nach erfolgreichem Speichern.
 */

import React, { useEffect, useState } from 'react';
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

import { GradesService } from '../../services/gradesService';
import { ApiError } from '../../services/submissionsService';

interface Props {
  open: boolean;
  gradeId: number | null;
  initialPoints: number;
  pointsMax: number;
  onClose: () => void;
  /** Wird nach erfolgreichem Override aufgerufen — Caller kann
   *  reload-Logik anstossen. */
  onSuccess: () => void | Promise<void>;
}

const OverrideGradeDialog: React.FC<Props> = ({
  open,
  gradeId,
  initialPoints,
  pointsMax,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation();
  const [points, setPoints] = useState(initialPoints.toString());
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Beim Öffnen Felder zurücksetzen — sonst trägt der Dialog Werte
  // vom letzten Aufruf in den nächsten.
  useEffect(() => {
    if (open) {
      setPoints(initialPoints.toString());
      setNote('');
      setSubmitting(false);
      setError(null);
    }
  }, [open, initialPoints]);

  const handleSubmit = async () => {
    if (gradeId == null) return;
    const value = Number(points);
    if (Number.isNaN(value)) {
      setError(t('common.invalidNumber'));
      return;
    }
    if (value < 0 || value > pointsMax) {
      setError(
        t('auswertungen.exam.review.overrideDialog.outOfBounds', {
          max: pointsMax,
        }),
      );
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await GradesService.override(gradeId, {
        points_awarded: value,
        reviewer_note: note || undefined,
      });
      await onSuccess();
      onClose();
    } catch (err) {
      setSubmitting(false);
      setError(
        err instanceof ApiError
          ? err.message
          : t('auswertungen.exam.review.actionFailure'),
      );
    }
  };

  return (
    <Dialog
      open={open}
      onClose={() => (submitting ? undefined : onClose())}
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle>
        {t('auswertungen.exam.review.overrideDialog.title')}
      </DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <TextField
            label={t('auswertungen.exam.review.overrideDialog.pointsLabel')}
            type="number"
            value={points}
            onChange={(e) => setPoints(e.target.value)}
            helperText={t(
              'auswertungen.exam.review.overrideDialog.pointsHelp',
              { max: pointsMax },
            )}
            inputProps={{
              min: 0,
              max: pointsMax,
              step: 0.5,
              'data-testid': 'override-points',
            }}
          />
          <TextField
            label={t('auswertungen.exam.review.overrideDialog.noteLabel')}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            multiline
            rows={3}
            inputProps={{ 'data-testid': 'override-note' }}
          />
          {error && <Alert severity="error">{error}</Alert>}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={submitting}>
          {t('auswertungen.exam.review.overrideDialog.cancel')}
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={submitting}
          data-testid="override-submit"
        >
          {t('auswertungen.exam.review.overrideDialog.submit')}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default OverrideGradeDialog;
