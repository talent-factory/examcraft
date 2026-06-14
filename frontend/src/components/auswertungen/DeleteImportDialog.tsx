/**
 * Delete-import confirmation dialog (TF-421).
 *
 * Lets a Dozent / Admin wipe **all** imported results of an exam (attempts +
 * answers + grades, across every source) so a corrupt import can be corrected
 * by re-importing cleanly — without DB access. On open it loads a summary
 * (`GET /import/summary`) and shows how many students / attempts would be
 * removed, requiring an explicit confirmation before the irreversible
 * `DELETE /import`. A 403 (missing `submissions:delete`) surfaces as an error.
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Alert,
  AlertTitle,
  CircularProgress,
  Chip,
} from '@mui/material';
import { DeleteForever as DeleteForeverIcon } from '@mui/icons-material';

import { ApiError, SubmissionsService } from '../../services/submissionsService';
import { ImportDeletionSummary } from '../../types/submission';

interface DeleteImportDialogProps {
  open: boolean;
  onClose: () => void;
  examId: number;
  examTitle: string;
  /** Called after a successful delete so the parent can refresh its list. */
  onDeleted?: (result: ImportDeletionSummary) => void;
}

const DeleteImportDialog: React.FC<DeleteImportDialogProps> = ({
  open,
  onClose,
  examId,
  examTitle,
  onDeleted,
}) => {
  const { t } = useTranslation();

  const [summary, setSummary] = useState<ImportDeletionSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleApiError = useCallback(
    (err: unknown, fallbackKey: string) => {
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : t(fallbackKey),
      );
    },
    [t],
  );

  // Load the deletion summary whenever the dialog opens, so the confirmation
  // shows accurate affected counts. Deps are intentionally limited to
  // open/examId — the summary does not depend on the active language, and
  // including the (possibly unstable) `t`/handleApiError identity would
  // re-fire the fetch on every render.
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setSummary(null);
    setError(null);
    setLoading(true);
    SubmissionsService.getImportSummary(examId)
      .then((res) => {
        if (!cancelled) setSummary(res);
      })
      .catch((err) => {
        if (!cancelled)
          handleApiError(err, 'auswertungen.deleteImportDialog.errorLoad');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, examId]);

  const handleConfirm = async () => {
    setDeleting(true);
    setError(null);
    try {
      const result = await SubmissionsService.deleteImport(examId);
      onDeleted?.(result);
      onClose();
    } catch (err) {
      handleApiError(err, 'auswertungen.deleteImportDialog.errorDelete');
    } finally {
      setDeleting(false);
    }
  };

  const nothingToDelete = summary !== null && summary.submission_count === 0;
  const canConfirm = summary !== null && !nothingToDelete && !deleting;

  return (
    <Dialog
      open={open}
      onClose={deleting ? undefined : onClose}
      maxWidth="sm"
      fullWidth
      data-testid="auswertungen-delete-import-dialog"
    >
      <DialogTitle>
        {t('auswertungen.deleteImportDialog.title', { examTitle })}
      </DialogTitle>

      <DialogContent dividers>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} data-testid="delete-import-error">
            {error}
          </Alert>
        )}

        {loading && (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {!loading && nothingToDelete && (
          <Alert severity="info" data-testid="delete-import-empty">
            {t('auswertungen.deleteImportDialog.nothingToDelete')}
          </Alert>
        )}

        {!loading && summary && !nothingToDelete && (
          <Box>
            <Alert severity="warning" sx={{ mb: 2 }}>
              <AlertTitle>
                {t('auswertungen.deleteImportDialog.warningTitle')}
              </AlertTitle>
              {t('auswertungen.deleteImportDialog.warningBody')}
            </Alert>

            <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
              <Chip
                color="primary"
                label={t('auswertungen.deleteImportDialog.studentCount', {
                  count: summary.student_count,
                })}
                data-testid="delete-import-student-count"
              />
              <Chip
                color="secondary"
                label={t('auswertungen.deleteImportDialog.attemptCount', {
                  count: summary.attempt_count,
                })}
                data-testid="delete-import-attempt-count"
              />
              <Chip
                color="default"
                label={t('auswertungen.deleteImportDialog.submissionCount', {
                  count: summary.submission_count,
                })}
                data-testid="delete-import-submission-count"
              />
            </Box>

            {summary.by_source.length > 0 && (
              <Typography
                variant="body2"
                color="text.secondary"
                data-testid="delete-import-by-source"
              >
                {t('auswertungen.deleteImportDialog.bySourceLabel')}{' '}
                {summary.by_source
                  .map(
                    (s) =>
                      `${s.source} (${t(
                        'auswertungen.deleteImportDialog.attemptCount',
                        { count: s.attempt_count },
                      )})`,
                  )
                  .join(', ')}
              </Typography>
            )}
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={deleting}>
          {t('common.cancel')}
        </Button>
        <Button
          variant="contained"
          color="error"
          startIcon={
            deleting ? <CircularProgress size={20} /> : <DeleteForeverIcon />
          }
          onClick={handleConfirm}
          disabled={!canConfirm}
          data-testid="delete-import-confirm"
        >
          {t('auswertungen.deleteImportDialog.confirm')}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default DeleteImportDialog;
