/**
 * Import dialog for exam results.
 *
 * Two source paths:
 *   - ``moodle_json``: file upload (default).
 *   - ``moodle_api``: nur sichtbar, wenn die Institution eine
 *     ``moodle_connections``-Eintragung hat. Statt Datei-Upload wird
 *     die Moodle-Quiz-ID erfasst; Preview/Commit gehen an
 *     `/import/api-preview` resp. `/import/api-commit`. Tier-Quota
 *     402 propagiert via `ApiError.message`.
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
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  TextField,
} from '@mui/material';
import { CloudUpload as CloudUploadIcon } from '@mui/icons-material';

import { ApiError, SubmissionsService } from '../../services/submissionsService';
import { MoodleConnectionsService } from '../../services/moodleConnectionsService';
import {
  DriverName,
  ImportJob,
  ImportJobStatus,
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
  /**
   * Cadence for polling the async import job (TF-412). Defaults to 1.5 s;
   * exposed so tests can poll fast without fake timers.
   */
  pollIntervalMs?: number;
  /**
   * @deprecated TF-428: no longer used. The dialog now polls until the job
   * reaches a terminal status — the backend guarantees one via the import
   * task's hard ``time_limit`` plus the stuck-job reaper — so there is no
   * client-side cutoff that could time out before a long free-text grading
   * run finishes. The user can close the dialog to let the import continue in
   * the background. Kept optional so existing callers/tests still type-check.
   */
  pollTimeoutMs?: number;
}

type WizardStep = 'source' | 'upload' | 'preview' | 'submitting';

// 25 MB matches the backend MAX_UPLOAD_BYTES guard. Keeping the
// client-side limit equal means a too-large file fails fast in the
// browser without uploading.
const MAX_FILE_BYTES = 25 * 1024 * 1024;
const MAX_VISIBLE_ERRORS = 5;
const DEFAULT_POLL_INTERVAL_MS = 1500;

// The import commit is async (TF-412): the endpoint returns a ``queued``
// job and a Celery worker grades it. ``queued``/``running`` are transient;
// the dialog polls until the job reaches a terminal status (the set below).
const TERMINAL_STATUSES: readonly ImportJobStatus[] = [
  'succeeded',
  'partial',
  'failed',
];
const isTerminalStatus = (status: ImportJobStatus): boolean =>
  TERMINAL_STATUSES.includes(status);

// Promise that resolves after ``ms`` but rejects immediately on abort, so
// closing the dialog stops the poll loop without waiting out the interval.
const abortableDelay = (ms: number, signal: AbortSignal): Promise<void> =>
  new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException('Aborted', 'AbortError'));
      return;
    }
    const id = setTimeout(resolve, ms);
    signal.addEventListener(
      'abort',
      () => {
        clearTimeout(id);
        reject(new DOMException('Aborted', 'AbortError'));
      },
      { once: true },
    );
  });

const ImportDialog: React.FC<ImportDialogProps> = ({
  open,
  onClose,
  examId,
  examTitle,
  onImported,
  pollIntervalMs = DEFAULT_POLL_INTERVAL_MS,
}) => {
  const { t } = useTranslation();

  const [step, setStep] = useState<WizardStep>('source');
  const [driverName, setDriverName] = useState<DriverName>('moodle_json');
  const [file, setFile] = useState<File | null>(null);
  const [quizIdRaw, setQuizIdRaw] = useState('');
  const [hasMoodleConnection, setHasMoodleConnection] = useState<boolean | null>(
    null,
  );
  // ``null`` means "probe finished cleanly — either no permission or
  // no connection, both rendered as the existing 'unavailableTag'
  // chip". A non-null string means the probe itself errored
  // (network, 500, parse) and we surface it so the operator sees the
  // real cause instead of a silent disabled radio.
  const [moodleProbeError, setMoodleProbeError] = useState<string | null>(
    null,
  );
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

  // TF-336: Beim Öffnen prüfen, ob die Institution eine Moodle-API-
  // Connection hat — nur dann ist das ``moodle_api``-Radio aktiv.
  // 403/permission-Fehler ist normal (Lehrperson hat
  // ``moodle:configure`` nicht) und wird als "keine Connection"
  // gerendert. Andere Fehler (Netzwerk, 500, Parse) müssen sichtbar
  // werden, sonst sieht die Lehrperson nur ein deaktiviertes Radio
  // ohne zu wissen, warum.
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setMoodleProbeError(null);
    MoodleConnectionsService.list()
      .then((res) => {
        if (cancelled) return;
        setHasMoodleConnection(res.items.length > 0);
      })
      .catch((err) => {
        if (cancelled) return;
        setHasMoodleConnection(false);
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          // Expected: caller has no ``moodle:configure``. Stay silent
          // and let the radio's existing "unavailable" chip explain.
          return;
        }
        setMoodleProbeError(
          err instanceof ApiError
            ? err.message
            : t('auswertungen.importDialog.moodleProbeError'),
        );
      });
    return () => {
      cancelled = true;
    };
  }, [open, t]);

  const resetState = () => {
    setStep('source');
    setDriverName('moodle_json');
    setFile(null);
    setQuizIdRaw('');
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
    setBusy(true);
    setError(null);
    setErrorIssues([]);
    abortRef.current = new AbortController();
    try {
      let result: ImportPreview;
      if (driverName === 'moodle_api') {
        const quizId = Number(quizIdRaw);
        if (!Number.isFinite(quizId) || quizId <= 0) {
          throw new Error(t('auswertungen.importDialog.errorPreview'));
        }
        result = await SubmissionsService.apiPreview({
          examId,
          quizId,
          signal: abortRef.current.signal,
        });
      } else {
        if (!file) return;
        result = await SubmissionsService.preview({
          examId,
          file,
          driverName,
          signal: abortRef.current.signal,
        });
      }
      setPreview(result);
      setStep('preview');
    } catch (err) {
      handleApiError(err, 'auswertungen.importDialog.errorPreview');
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  };

  // Poll the async import job until it reaches a terminal status, updating
  // the visible job state on each tick so the user sees live n/total progress.
  //
  // TF-428: no client-side deadline. A free-text-heavy import legitimately
  // runs for minutes, and the backend guarantees a terminal state (the task's
  // hard time_limit + the reap_stuck_import_jobs watchdog), so a wall-clock
  // cutoff here only ever produced a false "timeout" while the job actually
  // succeeded. The user can close the dialog at any point and the import keeps
  // running in the background; polling then stops via the abort signal.
  const pollUntilTerminal = async (
    jobId: number,
    signal: AbortSignal,
  ): Promise<ImportJob> => {
    for (;;) {
      await abortableDelay(pollIntervalMs, signal);
      const polled = await SubmissionsService.getImportJob(jobId);
      if (signal.aborted) {
        throw new DOMException('Aborted', 'AbortError');
      }
      setJob(polled);
      if (isTerminalStatus(polled.status)) {
        return polled;
      }
    }
  };

  const runCommit = async () => {
    setBusy(true);
    setStep('submitting');
    setError(null);
    setErrorIssues([]);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      let result: ImportJob;
      if (driverName === 'moodle_api') {
        const quizId = Number(quizIdRaw);
        result = await SubmissionsService.apiCommit({
          examId,
          quizId,
          signal: controller.signal,
        });
      } else {
        if (!file) return;
        result = await SubmissionsService.commit({
          examId,
          file,
          driverName,
          signal: controller.signal,
        });
      }
      setJob(result);

      // Commit only *enqueues* now (TF-412): the response is a queued job and
      // a Celery worker grades it. Poll until grading finishes (or fails). A
      // response that is already terminal — e.g. a fast worker, or a test mock
      // — skips the loop entirely.
      let finalJob = result;
      if (!isTerminalStatus(result.status)) {
        finalJob = await pollUntilTerminal(result.id, controller.signal);
      }

      // Only signal completion when nothing failed AND something was actually
      // persisted. partial / failed imports keep the dialog open so the user
      // reads the alert before the parent page navigates / reloads; TF-500: an
      // all-duplicates import (status succeeded, rows_processed === 0) does too,
      // so the "no new results" info is read instead of being skipped past on a
      // hollow success.
      if (finalJob.status === 'succeeded' && finalJob.rows_processed > 0) {
        onImported?.(finalJob);
      }
    } catch (err) {
      // Dialog closed mid-import: handleClose already aborted and ran
      // resetState, so any in-flight rejection must not re-pollute state for
      // the next open. The expected case is the AbortError; a real error that
      // merely lost the race to the abort is logged (not surfaced — the dialog
      // is gone) so it isn't completely invisible.
      if (controller.signal.aborted) {
        if (!(err instanceof DOMException && err.name === 'AbortError')) {
          console.warn('[ImportDialog] import error after dialog close:', err);
        }
        return;
      }
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
    const skippedDuplicates = Number(
      (j.source_metadata?.attempts_skipped_idempotent as number | undefined) ??
        0,
    );
    // TF-500: a "successful" import that persisted nothing because every row
    // was an already-imported duplicate is shown as an informational outcome,
    // not a plain green success. "0 verarbeitet" under a success banner reads
    // as "nothing happened / silently broken" — exactly the confusion that hid
    // the cross-exam idempotency bug. This also covers the legitimate case of
    // re-importing the same file into the same exam.
    const allDuplicates =
      j.status === 'succeeded' &&
      j.rows_processed === 0 &&
      skippedDuplicates > 0;
    const severity = allDuplicates
      ? 'info'
      : j.status === 'succeeded'
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
          {allDuplicates
            ? t('auswertungen.importDialog.result.allDuplicates')
            : t(`auswertungen.importDialog.result.${j.status}`)}
        </AlertTitle>
        <Typography variant="body2">
          {allDuplicates
            ? t('auswertungen.importDialog.allDuplicatesSummary', {
                skipped: skippedDuplicates,
              })
            : t('auswertungen.importDialog.resultSummary', {
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
                value="moodle_json"
                control={<Radio />}
                label={t('auswertungen.importDialog.sourceMoodleJson')}
              />
              <FormControlLabel
                value="moodle_api"
                control={<Radio disabled={!hasMoodleConnection} />}
                label={
                  <span>
                    {t('auswertungen.importDialog.sourceMoodleApi')}
                    {!hasMoodleConnection && (
                      <Chip
                        label={t('auswertungen.importDialog.unavailableTag')}
                        size="small"
                        color="default"
                        sx={{ ml: 1 }}
                      />
                    )}
                  </span>
                }
              />
            </RadioGroup>
            {moodleProbeError && (
              <Alert severity="warning" sx={{ mt: 1 }}>
                {moodleProbeError}
              </Alert>
            )}
          </FormControl>
        )}

        {step === 'upload' && driverName === 'moodle_json' && (
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
                accept=".json,application/json"
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

        {step === 'upload' && driverName === 'moodle_api' && (
          <Box sx={{ py: 2 }}>
            <TextField
              autoFocus
              fullWidth
              label={t('auswertungen.moodleSync.quizIdLabel')}
              helperText={t('auswertungen.moodleSync.quizIdHelper')}
              value={quizIdRaw}
              onChange={(e) => setQuizIdRaw(e.target.value)}
              inputProps={{
                'data-testid': 'import-quiz-id',
                inputMode: 'numeric',
              }}
            />
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
            {!job || !isTerminalStatus(job.status) ? (
              // queued / running: grading happens in the worker (TF-412) —
              // show live n/total progress (TF-428) and make clear the import
              // continues in the background so the user can close the dialog.
              <>
                {job && job.graded_total != null && job.graded_total > 0 ? (
                  <Box sx={{ px: { xs: 0, sm: 4 } }} data-testid="import-grading-progress">
                    <LinearProgress
                      variant="determinate"
                      value={Math.min(
                        100,
                        Math.round(
                          (job.graded_done / job.graded_total) * 100,
                        ),
                      )}
                    />
                    <Typography sx={{ mt: 2 }}>
                      {t('auswertungen.importDialog.gradingProgress', {
                        done: job.graded_done,
                        total: job.graded_total,
                      })}
                    </Typography>
                  </Box>
                ) : (
                  <>
                    <CircularProgress />
                    <Typography sx={{ mt: 2 }}>
                      {t('auswertungen.importDialog.submitting')}
                    </Typography>
                  </>
                )}
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mt: 2 }}
                >
                  {t('auswertungen.importDialog.backgroundHint')}
                </Typography>
              </>
            ) : (
              renderJobResult(job)
            )}
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        {(() => {
          // TF-428: while the import runs (queued/running), the close button
          // stays enabled so the user can leave it to finish in the
          // background instead of being pinned to the spinner. handleClose
          // aborts only the client poll — the worker keeps grading, and the
          // Auswertungen status surface then tracks the job.
          const runningImport =
            step === 'submitting' && (!job || !isTerminalStatus(job.status));
          return (
            <Button
              onClick={handleClose}
              disabled={busy && !runningImport}
              data-testid="import-close"
            >
              {runningImport
                ? t('auswertungen.importDialog.runInBackground')
                : job
                  ? t('common.close')
                  : t('common.cancel')}
            </Button>
          );
        })()}

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
            disabled={
              busy ||
              (driverName === 'moodle_json'
                ? !file
                : !quizIdRaw || Number(quizIdRaw) <= 0)
            }
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
