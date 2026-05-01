/**
 * Tests for the evaluations overview page.
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { MemoryRouter } from 'react-router-dom';

import Auswertungen from '../Auswertungen';
import { ComposerService } from '../../services/ComposerService';
import { Exam, ExamStatus } from '../../types/composer';

// Explizite Factory verhindert das Laden des echten Moduls (axios-ESM-
// Import bricht in Jest's CJS-Transform).
jest.mock('../../services/ComposerService', () => ({
  ComposerService: {
    listExams: jest.fn(),
    getExam: jest.fn(),
  },
  getErrorMessage: (e: unknown, fb: string) => (e instanceof Error ? e.message : fb),
}));
jest.mock('../../components/auswertungen/ImportDialog', () => ({
  __esModule: true,
  default: ({
    examId,
    onClose,
  }: {
    examId: number;
    onClose: () => void;
  }) => (
    <div data-testid={`import-dialog-stub-${examId}`}>
      <button onClick={onClose}>close-stub</button>
    </div>
  ),
}));

const mockComposerService = ComposerService as jest.Mocked<typeof ComposerService>;

const theme = createTheme();

const sampleExams: Exam[] = [
  {
    id: 1,
    title: 'Allgemeinbildung FS26',
    course: 'ABU',
    exam_date: '2026-05-15',
    time_limit_minutes: 90,
    allowed_aids: null,
    instructions: null,
    passing_percentage: 50,
    total_points: 10,
    status: ExamStatus.FINALIZED,
    language: 'de',
    institution_id: 1,
    created_by: 1,
    created_at: '2026-04-30T00:00:00',
    updated_at: '2026-04-30T00:00:00',
    default_document_ids: null,
  } as Exam,
  {
    id: 2,
    title: 'Mathe-Test',
    course: null,
    exam_date: null,
    time_limit_minutes: null,
    allowed_aids: null,
    instructions: null,
    passing_percentage: 50,
    total_points: 5,
    status: ExamStatus.DRAFT,
    language: 'de',
    institution_id: 1,
    created_by: 1,
    created_at: '2026-04-30T00:00:00',
    updated_at: '2026-04-30T00:00:00',
    default_document_ids: null,
  } as Exam,
];

const renderPage = () =>
  render(
    <MemoryRouter>
      <ThemeProvider theme={theme}>
        <Auswertungen />
      </ThemeProvider>
    </MemoryRouter>,
  );

describe('Auswertungen overview', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders exam table and opens import dialog on click', async () => {
    mockComposerService.listExams.mockResolvedValue({
      total: 2,
      exams: sampleExams,
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId('auswertungen-exam-table')).toBeInTheDocument();
    });
    expect(screen.getByText('Allgemeinbildung FS26')).toBeInTheDocument();
    expect(screen.getByText('Mathe-Test')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('exam-1-import'));
    expect(screen.getByTestId('import-dialog-stub-1')).toBeInTheDocument();
  });

  test('shows error alert when listExams fails', async () => {
    mockComposerService.listExams.mockRejectedValue(
      new Error('Backend down'),
    );
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Backend down')).toBeInTheDocument();
    });
  });

  test('listExams limit stays within backend cap (≤100)', async () => {
    // Regression-Guard: Backend `/api/v1/exams/` enforces le=100 on
    // ``limit`` and 422s on anything higher. The Auswertungen overview
    // previously sent limit=200 which broke the page entirely.
    mockComposerService.listExams.mockResolvedValue({ total: 0, exams: [] });
    renderPage();
    await waitFor(() => {
      expect(mockComposerService.listExams).toHaveBeenCalled();
    });
    const arg = mockComposerService.listExams.mock.calls[0][0];
    expect(arg?.limit).toBeLessThanOrEqual(100);
    expect(arg?.limit).toBeGreaterThan(0);
  });
});
