/**
 * Tests for ImportStatusBanner (TF-428): the Auswertungen status surface that
 * polls an exam's import jobs and shows live "n/total" progress without
 * pinning the import modal open.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';

import ImportStatusBanner from '../ImportStatusBanner';
import { SubmissionsService } from '../../../services/submissionsService';
import { ImportJob } from '../../../types/submission';

jest.mock('../../../api/apiClient');
jest.mock('../../../services/submissionsService');
const mockSubmissionsService = SubmissionsService as jest.Mocked<
  typeof SubmissionsService
>;

const theme = createTheme();
const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>{children}</ThemeProvider>
);

const makeJob = (over: Partial<ImportJob>): ImportJob => ({
  id: 1,
  exam_id: 42,
  driver_name: 'moodle_json',
  status: 'running',
  rows_processed: 0,
  rows_failed: 0,
  graded_total: 4,
  graded_done: 2,
  error_log: null,
  source_metadata: null,
  started_at: null,
  finished_at: null,
  ...over,
});

beforeEach(() => {
  jest.clearAllMocks();
});

test('shows a determinate progress bar for a running import (TF-428)', async () => {
  mockSubmissionsService.listImportJobs.mockResolvedValue({
    items: [makeJob({ status: 'running', graded_total: 4, graded_done: 2 })],
    total: 1,
  });

  render(<ImportStatusBanner examId={42} onCompleted={jest.fn()} />, {
    wrapper: Wrapper,
  });

  // An info banner appears with a determinate bar at 2/4 = 50%.
  expect(await screen.findByRole('alert')).toBeInTheDocument();
  const determinate = await waitFor(() => {
    const bar = screen
      .getAllByRole('progressbar')
      .find((el) => el.getAttribute('aria-valuenow') === '50');
    if (!bar) throw new Error('determinate bar not yet rendered');
    return bar;
  });
  expect(determinate).toHaveAttribute('aria-valuenow', '50');
});

test('renders nothing when no import is active', async () => {
  mockSubmissionsService.listImportJobs.mockResolvedValue({
    items: [makeJob({ status: 'succeeded' })],
    total: 1,
  });

  render(<ImportStatusBanner examId={42} onCompleted={jest.fn()} />, {
    wrapper: Wrapper,
  });

  await waitFor(() =>
    expect(mockSubmissionsService.listImportJobs).toHaveBeenCalled(),
  );
  expect(screen.queryByRole('alert')).toBeNull();
});

test('fires onCompleted when a previously-active job becomes terminal', async () => {
  const onCompleted = jest.fn();
  mockSubmissionsService.listImportJobs
    .mockResolvedValueOnce({
      items: [makeJob({ id: 9, status: 'running' })],
      total: 1,
    })
    .mockResolvedValue({
      items: [makeJob({ id: 9, status: 'succeeded' })],
      total: 1,
    });

  render(
    <ImportStatusBanner examId={42} onCompleted={onCompleted} pollIntervalMs={5} />,
    { wrapper: Wrapper },
  );

  await waitFor(() => expect(onCompleted).toHaveBeenCalled());
});
