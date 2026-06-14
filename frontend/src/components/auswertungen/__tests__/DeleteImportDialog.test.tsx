/**
 * Tests for DeleteImportDialog (TF-421).
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';

import DeleteImportDialog from '../DeleteImportDialog';
import {
  ApiError,
  SubmissionsService,
} from '../../../services/submissionsService';
import { ImportDeletionSummary } from '../../../types/submission';

// Spy on the real class (keeps ApiError real for the error-path test).
const getImportSummary = jest.spyOn(SubmissionsService, 'getImportSummary');
const deleteImport = jest.spyOn(SubmissionsService, 'deleteImport');

const theme = createTheme();
const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>{children}</ThemeProvider>
);

const summary: ImportDeletionSummary = {
  exam_id: 42,
  submission_count: 2,
  attempt_count: 3,
  student_count: 2,
  by_source: [{ source: 'moodle_csv', attempt_count: 3 }],
};

const renderDialog = (
  overrides: Partial<React.ComponentProps<typeof DeleteImportDialog>> = {},
) => {
  const onClose = jest.fn();
  const onDeleted = jest.fn();
  render(
    <Wrapper>
      <DeleteImportDialog
        open
        examId={42}
        examTitle="Allgemeinbildung"
        onClose={onClose}
        onDeleted={onDeleted}
        {...overrides}
      />
    </Wrapper>,
  );
  return { onClose, onDeleted };
};

describe('DeleteImportDialog', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('loads summary on open and shows affected counts', async () => {
    getImportSummary.mockResolvedValue(summary);
    renderDialog();

    await waitFor(() =>
      expect(getImportSummary).toHaveBeenCalledWith(42),
    );
    expect(
      await screen.findByTestId('delete-import-attempt-count'),
    ).toBeInTheDocument();
    expect(screen.getByTestId('delete-import-student-count')).toBeInTheDocument();
    expect(screen.getByTestId('delete-import-by-source')).toBeInTheDocument();
  });

  test('confirm calls deleteImport and onDeleted, then closes', async () => {
    getImportSummary.mockResolvedValue(summary);
    deleteImport.mockResolvedValue(summary);
    const { onClose, onDeleted } = renderDialog();

    // Wait for the summary to load so the confirm button is enabled.
    await screen.findByTestId('delete-import-attempt-count');
    fireEvent.click(screen.getByTestId('delete-import-confirm'));

    await waitFor(() => expect(onDeleted).toHaveBeenCalledWith(summary));
    expect(deleteImport).toHaveBeenCalledWith(42);
    expect(onClose).toHaveBeenCalled();
  });

  test('shows empty state and disables confirm when nothing to delete', async () => {
    getImportSummary.mockResolvedValue({
      ...summary,
      submission_count: 0,
      attempt_count: 0,
      student_count: 0,
      by_source: [],
    });
    renderDialog();

    expect(await screen.findByTestId('delete-import-empty')).toBeInTheDocument();
    expect(screen.getByTestId('delete-import-confirm')).toBeDisabled();
    expect(deleteImport).not.toHaveBeenCalled();
  });

  test('surfaces a delete error and keeps the dialog open', async () => {
    getImportSummary.mockResolvedValue(summary);
    deleteImport.mockRejectedValueOnce(
      new ApiError({
        kind: 'permission',
        status: 403,
        message: 'Keine Berechtigung',
        detail: null,
        issues: [],
      }),
    );
    const { onClose } = renderDialog();

    await screen.findByTestId('delete-import-attempt-count');
    fireEvent.click(screen.getByTestId('delete-import-confirm'));

    expect(await screen.findByTestId('delete-import-error')).toHaveTextContent(
      'Keine Berechtigung',
    );
    expect(onClose).not.toHaveBeenCalled();
  });

  test('surfaces a summary-load error and disables confirm', async () => {
    getImportSummary.mockRejectedValueOnce(
      new ApiError({
        kind: 'permission',
        status: 403,
        message: 'Kein Zugriff',
        detail: null,
        issues: [],
      }),
    );
    renderDialog();

    expect(await screen.findByTestId('delete-import-error')).toHaveTextContent(
      'Kein Zugriff',
    );
    // No summary loaded → confirm stays disabled, delete never attempted.
    expect(screen.getByTestId('delete-import-confirm')).toBeDisabled();
    expect(deleteImport).not.toHaveBeenCalled();
  });
});
