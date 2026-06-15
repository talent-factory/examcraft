jest.mock('../../../api/apiClient');
/**
 * Tests for ImportDialog.
 */

import React from 'react';
import {
  render,
  screen,
  fireEvent,
  waitFor,
} from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';

import ImportDialog from '../ImportDialog';
import { SubmissionsService } from '../../../services/submissionsService';
import { ImportJob, ImportPreview } from '../../../types/submission';

jest.mock('../../../services/submissionsService');
const mockSubmissionsService = SubmissionsService as jest.Mocked<
  typeof SubmissionsService
>;

const theme = createTheme();
const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>{children}</ThemeProvider>
);

const samplePreview: ImportPreview = {
  exam_id: 42,
  driver_name: 'moodle_json',
  student_count: 2,
  attempt_count: 2,
  students: [
    { external_id: 'anna@example.org', display_name: 'Anna Beispiel' },
    { external_id: 'bruno@example.org', display_name: null },
  ],
  attempts: [
    {
      student_external_id: 'anna@example.org',
      attempt_number: 1,
      started_at: null,
      submitted_at: null,
      answer_count: 2,
    },
    {
      student_external_id: 'bruno@example.org',
      attempt_number: 1,
      started_at: null,
      submitted_at: null,
      answer_count: 2,
    },
  ],
  warnings: ['Spalte X hat keine zugehörige Frage'],
  errors: [],
  source_metadata: { delimiter: ';' },
};

const sampleJob: ImportJob = {
  id: 7,
  exam_id: 42,
  driver_name: 'moodle_json',
  status: 'succeeded',
  rows_processed: 2,
  rows_failed: 0,
  graded_total: 2,
  graded_done: 2,
  error_log: null,
  source_metadata: null,
  started_at: null,
  finished_at: null,
};

const renderDialog = (
  overrides: Partial<React.ComponentProps<typeof ImportDialog>> = {},
) => {
  const onClose = jest.fn();
  const onImported = jest.fn();
  render(
    <Wrapper>
      <ImportDialog
        open
        examId={42}
        examTitle="Allgemeinbildung"
        onClose={onClose}
        onImported={onImported}
        {...overrides}
      />
    </Wrapper>,
  );
  return { onClose, onImported };
};

const jsonFile = new File(['[[]]'], 'klasse.json', {
  type: 'application/json',
});

describe('ImportDialog', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders title and source step', () => {
    renderDialog();
    expect(
      screen.getByTestId('auswertungen-import-dialog'),
    ).toBeInTheDocument();
    expect(screen.getByTestId('import-driver-radio')).toBeInTheDocument();
  });

  test('moves through all steps and calls preview + commit', async () => {
    mockSubmissionsService.preview.mockResolvedValueOnce(samplePreview);
    mockSubmissionsService.commit.mockResolvedValueOnce(sampleJob);
    const { onImported } = renderDialog();

    // 1. Source → Next
    fireEvent.click(screen.getByTestId('import-next-source'));

    // 2. Upload: choose file
    const input = screen
      .getByTestId('import-file-upload')
      .querySelector('input[type=file]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [jsonFile] } });
    expect(screen.getByTestId('import-file-name')).toHaveTextContent(
      'klasse.json',
    );

    fireEvent.click(screen.getByTestId('import-run-preview'));

    await waitFor(() => {
      expect(mockSubmissionsService.preview).toHaveBeenCalledWith(
        expect.objectContaining({
          examId: 42,
          file: jsonFile,
          driverName: 'moodle_json',
        }),
      );
    });

    // 3. Preview rendered (warten auf React re-render nach state update)
    expect(
      await screen.findByTestId('preview-student-count'),
    ).toHaveTextContent('2');
    expect(screen.getByTestId('preview-warnings')).toBeInTheDocument();
    expect(screen.getByText('anna@example.org')).toBeInTheDocument();

    // 4. Confirm → commit
    fireEvent.click(screen.getByTestId('import-confirm'));
    await waitFor(() => {
      expect(mockSubmissionsService.commit).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(onImported).toHaveBeenCalledWith(sampleJob);
    });
    expect(screen.getByTestId('import-result')).toBeInTheDocument();
  });

  test('polls the queued job until it succeeds, then fires onImported (TF-412)', async () => {
    // Backend now returns a *queued* job and grades asynchronously; the
    // dialog must poll the job until a terminal status before reporting.
    mockSubmissionsService.preview.mockResolvedValueOnce(samplePreview);
    mockSubmissionsService.commit.mockResolvedValueOnce({
      ...sampleJob,
      status: 'queued',
      rows_processed: 0,
    });
    mockSubmissionsService.getImportJob
      .mockResolvedValueOnce({ ...sampleJob, status: 'running', rows_processed: 0 })
      .mockResolvedValueOnce(sampleJob); // succeeded
    const { onImported } = renderDialog({ pollIntervalMs: 5 });

    fireEvent.click(screen.getByTestId('import-next-source'));
    const input = screen
      .getByTestId('import-file-upload')
      .querySelector('input[type=file]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [jsonFile] } });
    fireEvent.click(screen.getByTestId('import-run-preview'));
    await screen.findByTestId('preview-student-count');

    fireEvent.click(screen.getByTestId('import-confirm'));

    await waitFor(() => {
      expect(mockSubmissionsService.getImportJob).toHaveBeenCalledWith(7);
    });
    await waitFor(() => {
      expect(onImported).toHaveBeenCalledWith(sampleJob);
    });
    expect(screen.getByTestId('import-result')).toBeInTheDocument();
  });

  test('polls until failed without firing onImported (TF-412)', async () => {
    mockSubmissionsService.preview.mockResolvedValueOnce(samplePreview);
    mockSubmissionsService.commit.mockResolvedValueOnce({
      ...sampleJob,
      status: 'queued',
      rows_processed: 0,
    });
    mockSubmissionsService.getImportJob.mockResolvedValueOnce({
      ...sampleJob,
      status: 'failed',
      rows_processed: 0,
      rows_failed: 0,
      error_log: [
        { row_index: -1, reason: 'Grading abgebrochen', step: 'grade', details: null },
      ],
    });
    const { onImported } = renderDialog({ pollIntervalMs: 5 });

    fireEvent.click(screen.getByTestId('import-next-source'));
    const input = screen
      .getByTestId('import-file-upload')
      .querySelector('input[type=file]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [jsonFile] } });
    fireEvent.click(screen.getByTestId('import-run-preview'));
    await screen.findByTestId('preview-student-count');

    fireEvent.click(screen.getByTestId('import-confirm'));

    await waitFor(() => {
      expect(mockSubmissionsService.getImportJob).toHaveBeenCalledWith(7);
    });
    // import-result only renders once a *terminal* status is reached (queued/
    // running show the spinner), so finding it confirms polling completed.
    await screen.findByTestId('import-result');
    expect(onImported).not.toHaveBeenCalled();
  });

  test('shows error message when preview fails', async () => {
    mockSubmissionsService.preview.mockRejectedValueOnce(
      new Error('CSV ist leer'),
    );
    renderDialog();

    fireEvent.click(screen.getByTestId('import-next-source'));
    const input = screen
      .getByTestId('import-file-upload')
      .querySelector('input[type=file]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [jsonFile] } });
    fireEvent.click(screen.getByTestId('import-run-preview'));

    await waitFor(() => {
      expect(screen.getByTestId('import-error')).toHaveTextContent(
        'CSV ist leer',
      );
    });
    expect(mockSubmissionsService.commit).not.toHaveBeenCalled();
  });

  test('shows row errors in preview alert', async () => {
    const previewWithErrors: ImportPreview = {
      ...samplePreview,
      errors: [
        { row_index: 3, reason: 'Leere external_id' },
        { row_index: 5, reason: 'Datum ungültig' },
      ],
    };
    mockSubmissionsService.preview.mockResolvedValueOnce(previewWithErrors);
    renderDialog();

    fireEvent.click(screen.getByTestId('import-next-source'));
    const input = screen
      .getByTestId('import-file-upload')
      .querySelector('input[type=file]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [jsonFile] } });
    fireEvent.click(screen.getByTestId('import-run-preview'));

    await waitFor(() => {
      expect(screen.getByTestId('preview-errors')).toBeInTheDocument();
    });
    expect(screen.getByText(/Leere external_id/)).toBeInTheDocument();
  });

  test('cancel button calls onClose without committing', () => {
    const { onClose } = renderDialog();
    fireEvent.click(screen.getByText(/Abbrechen|Cancel/));
    expect(onClose).toHaveBeenCalled();
    expect(mockSubmissionsService.preview).not.toHaveBeenCalled();
    expect(mockSubmissionsService.commit).not.toHaveBeenCalled();
  });

  test('lets a long-running import finish in the background instead of timing out (TF-428)', async () => {
    // A free-text-heavy import legitimately runs for minutes. The dialog must
    // NOT surface a client-side timeout (the backend guarantees a terminal
    // status via the task time_limit + the reaper); instead it shows live
    // n/total progress, and the user can close the dialog to let grading
    // finish in the background — onImported never fires on close, and no
    // error is shown.
    mockSubmissionsService.preview.mockResolvedValueOnce(samplePreview);
    mockSubmissionsService.commit.mockResolvedValueOnce({
      ...sampleJob,
      status: 'queued',
      rows_processed: 0,
      graded_total: 4,
      graded_done: 0,
    });
    // Stays non-terminal with climbing progress — never reaches a deadline.
    mockSubmissionsService.getImportJob.mockResolvedValue({
      ...sampleJob,
      status: 'running',
      rows_processed: 0,
      graded_total: 4,
      graded_done: 2,
    });
    const { onImported, onClose } = renderDialog({ pollIntervalMs: 5 });

    fireEvent.click(screen.getByTestId('import-next-source'));
    const input = screen
      .getByTestId('import-file-upload')
      .querySelector('input[type=file]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [jsonFile] } });
    fireEvent.click(screen.getByTestId('import-run-preview'));
    await screen.findByTestId('preview-student-count');

    fireEvent.click(screen.getByTestId('import-confirm'));

    // Live progress is shown — never a timeout/error alert.
    await screen.findByTestId('import-grading-progress');
    expect(screen.queryByTestId('import-error')).toBeNull();

    // The close button stays enabled while the import runs; closing lets the
    // job finish in the background without an error or a (false) success.
    const closeBtn = screen.getByTestId('import-close');
    expect(closeBtn).not.toBeDisabled();
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalled();
    expect(onImported).not.toHaveBeenCalled();
  });

  test('aborts the poll loop on unmount without firing onImported (TF-412)', async () => {
    // Closing the dialog mid-poll must stop the loop; a late terminal status
    // must never call onImported on an unmounted component.
    mockSubmissionsService.preview.mockResolvedValueOnce(samplePreview);
    mockSubmissionsService.commit.mockResolvedValueOnce({
      ...sampleJob,
      status: 'queued',
      rows_processed: 0,
    });
    // Never terminal → the loop only stops when aborted on unmount.
    mockSubmissionsService.getImportJob.mockResolvedValue({
      ...sampleJob,
      status: 'running',
      rows_processed: 0,
    });
    const onImported = jest.fn();
    const { unmount } = render(
      <Wrapper>
        <ImportDialog
          open
          examId={42}
          examTitle="Allgemeinbildung"
          onClose={jest.fn()}
          onImported={onImported}
          pollIntervalMs={5}
        />
      </Wrapper>,
    );

    fireEvent.click(screen.getByTestId('import-next-source'));
    const input = screen
      .getByTestId('import-file-upload')
      .querySelector('input[type=file]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [jsonFile] } });
    fireEvent.click(screen.getByTestId('import-run-preview'));
    await screen.findByTestId('preview-student-count');

    fireEvent.click(screen.getByTestId('import-confirm'));
    await waitFor(() => {
      expect(mockSubmissionsService.getImportJob).toHaveBeenCalled();
    });

    unmount(); // triggers the abort in the cleanup effect

    // Give any in-flight poll promise a chance to (incorrectly) resolve.
    await new Promise((resolve) => setTimeout(resolve, 30));
    expect(onImported).not.toHaveBeenCalled();
  });

  test('does not fire onImported for partial commit so the user can read the alert', async () => {
    mockSubmissionsService.preview.mockResolvedValueOnce(samplePreview);
    mockSubmissionsService.commit.mockResolvedValueOnce({
      ...sampleJob,
      status: 'partial',
      rows_failed: 1,
      error_log: [{ row_index: 3, reason: 'Leere external_id', step: null, details: null }],
    });
    const { onImported } = renderDialog();

    fireEvent.click(screen.getByTestId('import-next-source'));
    const input = screen
      .getByTestId('import-file-upload')
      .querySelector('input[type=file]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [jsonFile] } });
    fireEvent.click(screen.getByTestId('import-run-preview'));

    await screen.findByTestId('preview-student-count');
    fireEvent.click(screen.getByTestId('import-confirm'));

    // Result alert renders, but onImported must NOT fire — otherwise the
    // parent page navigates away before the user reads the warning.
    await waitFor(() => {
      expect(screen.getByTestId('import-result')).toBeInTheDocument();
    });
    expect(onImported).not.toHaveBeenCalled();
  });
});
