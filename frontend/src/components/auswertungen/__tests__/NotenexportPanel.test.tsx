/**
 * Tests for NotenexportPanel — TF-335 Phase 3.
 *
 * Covers the user-visible behaviour the silent-failure-hunter and the
 * pr-test-analyzer flagged: each format triggers the right service
 * call, the panel is disabled while reviews are pending, and the 409
 * "review pending" message is surfaced (not collapsed to "Export
 * failed (409)").
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import NotenexportPanel from '../NotenexportPanel';
import { GradeExportService } from '../../../services/gradeExportService';
import { ApiError } from '../../../services/submissionsService';

// react-i18next is globally mocked in setupTests.ts to resolve keys
// against the real DE translation.json — no per-test i18n bootstrap.

jest.mock('../../../services/gradeExportService', () => ({
  GradeExportService: { download: jest.fn() },
}));

jest.mock('../../../services/submissionsService', () => ({
  ApiError: class ApiError extends Error {
    kind: string;
    status: number;
    constructor(opts: { kind: string; status: number; message: string }) {
      super(opts.message);
      this.kind = opts.kind;
      this.status = opts.status;
    }
  },
}));

const mockedDownload = GradeExportService.download as jest.MockedFunction<
  typeof GradeExportService.download
>;

const renderPanel = (props: {
  totalSubmissions?: number;
  pendingCount?: number;
}) =>
  render(
    <NotenexportPanel
      examId={42}
      totalSubmissions={props.totalSubmissions ?? 5}
      pendingCount={props.pendingCount ?? 0}
      onOpenReview={() => {}}
    />,
  );

describe('NotenexportPanel', () => {
  // jsdom doesn't ship URL.createObjectURL — the panel uses it to
  // trigger downloads, so stub once for the suite.
  beforeAll(() => {
    Object.defineProperty(URL, 'createObjectURL', {
      writable: true,
      value: jest.fn().mockReturnValue('blob:mock'),
    });
    Object.defineProperty(URL, 'revokeObjectURL', {
      writable: true,
      value: jest.fn(),
    });
  });

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('disables download while reviews are pending', () => {
    renderPanel({ pendingCount: 3 });
    const button = screen.getByRole('button', { name: /Herunterladen/ });
    expect(button).toBeDisabled();
  });

  it('disables download when there are zero submissions', () => {
    renderPanel({ totalSubmissions: 0, pendingCount: 0 });
    const button = screen.getByRole('button', { name: /Herunterladen/ });
    expect(button).toBeDisabled();
  });

  it('triggers a CSV download by default', async () => {
    mockedDownload.mockResolvedValueOnce({
      blob: new Blob(['ok'], { type: 'text/csv' }),
      filename: 'noten-X.csv',
    });
    renderPanel({ pendingCount: 0 });
    fireEvent.click(screen.getByRole('button', { name: /Herunterladen/ }));
    await waitFor(() =>
      expect(mockedDownload).toHaveBeenCalledWith(42, 'csv'),
    );
  });

  it('switches format and downloads PDF when chosen', async () => {
    mockedDownload.mockResolvedValueOnce({
      blob: new Blob([new Uint8Array([0x25, 0x50, 0x44, 0x46])], {
        type: 'application/pdf',
      }),
      filename: 'noten-X.pdf',
    });
    renderPanel({ pendingCount: 0 });
    fireEvent.click(screen.getByLabelText(/PDF/));
    fireEvent.click(screen.getByRole('button', { name: /Herunterladen/ }));
    await waitFor(() =>
      expect(mockedDownload).toHaveBeenCalledWith(42, 'pdf'),
    );
  });

  it('surfaces backend 409 detail (not the generic kind message)', async () => {
    mockedDownload.mockRejectedValueOnce(
      new ApiError({
        kind: 'conflict',
        status: 409,
        message: 'Notenexport gesperrt: Review zuerst abarbeiten.',
      }),
    );
    renderPanel({ pendingCount: 0 });
    fireEvent.click(screen.getByRole('button', { name: /Herunterladen/ }));
    expect(
      await screen.findByText(/Review zuerst abarbeiten/),
    ).toBeInTheDocument();
  });
});
