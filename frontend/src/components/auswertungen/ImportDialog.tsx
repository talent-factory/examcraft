/**
 * Import dialog for exam results.
 *
 * The moodle_api radio is disabled in the UI rather than hidden so
 * users see what will eventually be available without the page having
 * to know about a feature flag.
 */

import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Stepper,
  Step,
  StepLabel,
  Radio,
  RadioGroup,
  FormControlLabel,
  FormControl,
  FormLabel,
  Box,
  Typography,
  Alert,
  AlertTitle,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
} from '@mui/material';
import { CloudUpload as CloudUploadIcon } from '@mui/icons-material';

import { ApiError, SubmissionsService } from '../../services/submissionsService';
import {
  DriverName,
  ImportJob,
  ImportPreview,
  ImportRowError,
} from '../../types/submission';

interface ImportDialogProps {
  open: boolean;
  onClose: () => void;
  examId: number;
  examTitle: string;
  /**
   * Called only after a fully successful commit (status === 'succeeded')
   * so the caller can navigate or refresh. Partial / failed imports keep
   * the dialog open with an error so the user can read it before leaving.
   */
  onImported?: (job: ImportJob) => void;
}

type WizardStep = 'source' | 'upload' | 'preview' | 'submitting';

// 25 MB matches the backend MAX_UPLOAD_BYTES guard. Keeping the
// client-side limit equal means a too-large file fails fast in the
// browser without uploading.
const MAX_FILE_BYTES = 25 * 1024 * 1024;
const MAX_VISIBLE_ERRORS = 5;

const ImportDialog: React.FC<ImportDialogProps> = ({
  open,
  onClose,
  examId,
  examTitle,
  onImported,
}) => {
  const { t } = useTranslation();

  const [step, setStep] = useState<WizardStep>('source');
  const [driverName, setDriverName] = useState<DriverName>('moodle_csv');
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorIssues, setErrorIssues] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [job, setJob] = useState<ImportJob | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Abort any in-flight request when the dialog closes/unmounts so a
  // 25 MB upload doesn't keep streaming after the user leaves.
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const resetState = () => {
    setStep('source');
    setDriverName('moodle_csv');
    setFile(null);
    setPreview(null);
    setError(null);
    setErrorIssues([]);
    setJob(null);
  };

  const handleClose = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    resetState();
    setBusy(false);
    onClose();
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const next = event.target.files?.[0] ?? null;
    if (next && next.size > MAX_FILE_BYTES) {
      setFile(null);
      setError(
        t('auswertungen.importDialog.fileTooLarge', {
          maxMb: Math.floor(MAX_FILE_BYTES / (1024 * 1024)),
          actualMb: (next.size / (1024 * 1024)).toFixed(1),
        }),
      );
      setErrorIssues([]);
      return;
    }
    setFile(next);
    setError(null);
    setErrorIssues([]);
  };

  const handleApiError = (err: unknown, fallbackKey: string) => {
    if (err instanceof ApiError) {
      setError(err.message);
      setErrorIssues(err.issues);
      return;
    }
    setError(err instanceof Error ? err.message : t(fallbackKey));
    setErrorIssues([]);
  };

  const runPreview = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    setErrorIssues([]);
    abortRef.current = new AbortController();
    try {
      const result = await SubmissionsService.preview({
        examId,
        file,
        driverName,
        signal: abortRef.current.signal,
      });
      setPreview(result);
      setStep('preview');
    } catch (err) {
      handleApiError(err, 'auswertungen.importDialog.errorPreview');
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  };

  const runCommit = async () => {
    if (!file) return;
    setBusy(true);
    setStep('submitting');
    setError(null);
    setErrorIssues([]);
    abortRef.current = new AbortController();
    try {
      const result = await SubmissionsService.commit({
        examId,
        file,
        driverName,
        signal: abortRef.current.signal,
      });
      setJob(result);
      // Only signal completion when nothing failed — partial / failed
      // imports must keep the dialog open so the user reads the alert
      // before the parent page navigates / reloads.
      if (result.status === 'succeeded') {
        onImported?.(result);
      }
    } catch (err) {
      handleApiError(err, 'auswertungen.importDialog.errorCommit');
      setStep('preview'); // allow retry without re-uploading
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  };

  const stepIndex = (
    {
      source: 0,
      upload: 1,
      preview: 2,
      submitting: 3,
    } as const
  )[step];

  const renderJobResult = (j: ImportJob) => {
    const severity =
      j.status === 'succeeded'
        ? 'success'
        : j.status === 'partial'
          ? 'warning'
          : 'error';
    const errorRows: ImportRowError[] = (j.error_log ?? []).filter(
      (e): e is ImportRowError => Boolean(e),
    );
    return (
      <Alert severity={severity} data-testid="import-result">
        <AlertTitle>
          {t(`auswertungen.importDialog.result.${j.status}`)}
        </AlertTitle>
        <Typography variant="body2">
          {t('auswertungen.importDialog.resultSummary', {
            processed: j.rows_processed,
            failed: j.rows_failed,
          })}
        </Typography>
        {errorRows.length > 0 && (
          <Box sx={{ mt: 1.5 }} data-testid="import-result-errors">
            <Typography variant="subtitle2">
              {t('auswertungen.importDialog.errorListTitle')}
            </Typography>
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              {errorRows.slice(0, MAX_VISIBLE_ERRORS).map((e, idx) => (
                <li key={`${e.row_index}-${idx}`}>
                  {t('auswertungen.importDialog.rowError', {
                    row: e.row_index,
                    reason: e.reason,
                  })}
                </li>
              ))}
            </ul>
            {errorRows.length > MAX_VISIBLE_ERRORS && (
              <Typography
                variant="caption"
                sx={{ display: 'block', mt: 0.5 }}
                data-testid="import-result-errors-truncated"
              >
                {t('auswertungen.importDialog.errorListTruncated', {
                  count: errorRows.length - MAX_VISIBLE_ERRORS,
                })}
              </Typography>
            )}
          </Box>
        )}
      </Alert>
    );
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      data-testid="auswertungen-import-dialog"
    >
      <DialogTitle>
        {t('auswertungen.importDialog.title', { examTitle })}
      </DialogTitle>

      <DialogContent dividers>
        <Stepper activeStep={stepIndex} sx={{ mb: 3 }}>
          <Step>
            <StepLabel>{t('auswertungen.importDialog.steps.source')}</StepLabel>
          </Step>
          <Step>
            <StepLabel>{t('auswertungen.importDialog.steps.upload')}</StepLabel>
          </Step>
          <Step>
            <StepLabel>{t('auswertungen.importDialog.steps.preview')}</StepLabel>
          </Step>
          <Step>
            <StepLabel>{t('auswertungen.importDialog.steps.confirm')}</StepLabel>
          </Step>
        </Stepper>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} data-testid="import-error">
            <AlertTitle>{error}</AlertTitle>
            {errorIssues.length > 0 && (
              <ul
                style={{ margin: 0, paddingLeft: 20 }}
                data-testid="import-error-issues"
              >
                {errorIssues.slice(0, MAX_VISIBLE_ERRORS).map((iss) => (
                  <li key={iss}>{iss}</li>
                ))}
                {errorIssues.length > MAX_VISIBLE_ERRORS && (
                  <li>
                    {t('auswertungen.importDialog.errorListTruncated', {
                      count: errorIssues.length - MAX_VISIBLE_ERRORS,
                    })}
                  </li>
                )}
              </ul>
            )}
          </Alert>
        )}

        {step === 'source' && (
          <FormControl>
            <FormLabel>{t('auswertungen.importDialog.sourceLabel')}</FormLabel>
            <RadioGroup
              value={driverName}
              onChange={(e) => setDriverName(e.target.value as DriverName)}
              data-testid="import-driver-radio"
            >
              <FormControlLabel
                value="moodle_csv"
                control={<Radio />}
                label={t('auswertungen.importDialog.sourceMoodleCsv')}
              />
              <FormControlLabel
                value="moodle_api"
                control={<Radio disabled />}
                label={
                  <span>
                    {t('auswertungen.importDialog.sourceMoodleApi')}{' '}
                    <Chip
                      label={t('auswertungen.importDialog.unavailableTag')}
                      size="small"
                      color="default"
                      sx={{ ml: 1 }}
                    />
                  </span>
                }
              />
            </RadioGroup>
          </FormControl>
        )}

        {step === 'upload' && (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Button
              component="label"
              variant="outlined"
              startIcon={<CloudUploadIcon />}
              data-testid="import-file-upload"
            >
              {t('auswertungen.importDialog.chooseFile')}
              <input
                type="file"
                hidden
                accept=".csv,text/csv"
                onChange={handleFileChange}
              />
            </Button>
            {file && (
              <Typography sx={{ mt: 2 }} data-testid="import-file-name">
                {file.name} ({Math.round(file.size / 1024)} KB)
              </Typography>
            )}
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ mt: 3 }}
            >
              {t('auswertungen.importDialog.uploadHint')}
            </Typography>
          </Box>
        )}

        {step === 'preview' && preview && (
          <Box>
            <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
              <Chip
                color="primary"
                label={t('auswertungen.importDialog.studentCount', {
                  count: preview.student_count,
                })}
                data-testid="preview-student-count"
              />
              <Chip
                color="secondary"
                label={t('auswertungen.importDialog.attemptCount', {
                  count: preview.attempt_count,
                })}
                data-testid="preview-attempt-count"
              />
              {preview.errors.length > 0 && (
                <Chip
                  color="warning"
                  label={t('auswertungen.importDialog.errorCount', {
                    count: preview.errors.length,
                  })}
                />
              )}
              {preview.truncated && (
                <Chip
                  color="default"
                  label={t('auswertungen.importDialog.truncatedTag')}
                  data-testid="preview-truncated"
                />
              )}
            </Box>

            {preview.warnings.length > 0 && (
              <Alert
                severity="warning"
                sx={{ mb: 2 }}
                data-testid="preview-warnings"
              >
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  {preview.warnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              </Alert>
            )}

            {preview.errors.length > 0 && (
              <Alert severity="warning" sx={{ mb: 2 }} data-testid="preview-errors">
                <Typography variant="subtitle2">
                  {t('auswertungen.importDialog.errorListTitle')}
                </Typography>
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  {preview.errors.slice(0, MAX_VISIBLE_ERRORS).map((e) => (
                    <li key={`${e.row_index}-${e.reason}`}>
                      {t('auswertungen.importDialog.rowError', {
                        row: e.row_index,
                        reason: e.reason,
                      })}
                    </li>
                  ))}
                </ul>
                {preview.errors.length > MAX_VISIBLE_ERRORS && (
                  <Typography
                    variant="caption"
                    sx={{ display: 'block', mt: 0.5 }}
                  >
                    {t('auswertungen.importDialog.errorListTruncated', {
                      count: preview.errors.length - MAX_VISIBLE_ERRORS,
                    })}
                  </Typography>
                )}
              </Alert>
            )}

            <TableContainer component={Paper} variant="outlined">
              <Table size="small" data-testid="preview-students-table">
                <TableHead>
                  <TableRow>
                    <TableCell>
                      {t('auswertungen.importDialog.colExternalId')}
                    </TableCell>
                    <TableCell>
                      {t('auswertungen.importDialog.colDisplayName')}
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {preview.students.map((s) => (
                    <TableRow key={s.external_id}>
                      <TableCell>{s.external_id}</TableCell>
                      <TableCell>{s.display_name ?? '—'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}

        {step === 'submitting' && (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            {!job ? (
              <>
                <CircularProgress />
                <Typography sx={{ mt: 2 }}>
                  {t('auswertungen.importDialog.submitting')}
                </Typography>
              </>
            ) : (
              renderJobResult(job)
            )}
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose} disabled={busy}>
          {job ? t('common.close') : t('common.cancel')}
        </Button>

        {step === 'source' && (
          <Button
            variant="contained"
            onClick={() => setStep('upload')}
            data-testid="import-next-source"
          >
            {t('common.next')}
          </Button>
        )}

        {step === 'upload' && (
          <Button
            variant="contained"
            disabled={!file || busy}
            onClick={runPreview}
            data-testid="import-run-preview"
          >
            {busy ? <CircularProgress size={20} /> : t('common.next')}
          </Button>
        )}

        {step === 'preview' && (
          <>
            <Button
              onClick={() => {
                setStep('upload');
                setPreview(null);
              }}
              disabled={busy}
            >
              {t('common.back')}
            </Button>
            <Button
              variant="contained"
              onClick={runCommit}
              disabled={busy}
              data-testid="import-confirm"
            >
              {t('auswertungen.importDialog.confirm')}
            </Button>
          </>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default ImportDialog;
