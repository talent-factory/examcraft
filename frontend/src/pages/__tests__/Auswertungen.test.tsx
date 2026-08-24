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

// Explicit factory prevents loading the real module (axios ESM
// import breaks in Jest's CJS transform).
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

  test('listExams limit stays within backend cap (≤500)', async () => {
    // Regression-Guard: Backend `/api/v1/exams/` enforces le=500 on
    // ``limit`` (TF-335 raised from le=100) and 422s on anything
    // higher. The Auswertungen overview previously sent limit=200
    // which broke the page entirely on the old le=100 cap.
    mockComposerService.listExams.mockResolvedValue({ total: 0, exams: [] });
    renderPage();
    await waitFor(() => {
      expect(mockComposerService.listExams).toHaveBeenCalled();
    });
    const arg = mockComposerService.listExams.mock.calls[0][0];
    expect(arg?.limit).toBeLessThanOrEqual(500);
    expect(arg?.limit).toBeGreaterThan(0);
  });

  test('paginates with ≥101 exams via TablePagination', async () => {
    // TF-335 DoD MUSS: institutions with >100 exams must be able to
    // navigate page-by-page. We mock 25 exams on page 0 (total 101) and
    // verify the second page-load fires with offset=25.
    const page0 = Array.from({ length: 25 }, (_, i) => ({
      ...sampleExams[0],
      id: i + 1,
      title: `Exam ${i + 1}`,
    })) as Exam[];
    const page1 = Array.from({ length: 25 }, (_, i) => ({
      ...sampleExams[0],
      id: i + 26,
      title: `Exam ${i + 26}`,
    })) as Exam[];
    // Mock implementation responds based on offset so any number of
    // re-renders (e.g. duplicate effect runs in StrictMode/test harness)
    // doesn't exhaust a fixed queue and surface as
    // "Cannot read properties of undefined (reading 'then')".
    mockComposerService.listExams.mockImplementation(
      async (params: { limit: number; offset: number }) => ({
        total: 101,
        exams: (params.offset ?? 0) >= 25 ? page1 : page0,
      }),
    );

    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Exam 1')).toBeInTheDocument();
    });

    // First call: offset=0, limit=25 (default rowsPerPage)
    expect(mockComposerService.listExams.mock.calls[0][0]).toEqual({
      limit: 25,
      offset: 0,
    });

    // Click "next page" — TablePagination renders a button with
    // aria-label "Go to next page".
    const nextBtn = screen.getByRole('button', { name: /next/i });
    fireEvent.click(nextBtn);

    // After the click we expect at least one additional call with
    // offset=25. Don't pin the exact total — re-renders from MUI's
    // pagination + the mock implementation can produce extras that
    // are harmless. The behaviour we care about: a refetch happened
    // for the new page, and the new rows render.
    await waitFor(() => {
      const offsets = mockComposerService.listExams.mock.calls.map(
        (c) => c[0]?.offset,
      );
      expect(offsets).toContain(25);
    });
    await waitFor(() => {
      expect(screen.getByText('Exam 26')).toBeInTheDocument();
    });
  });
});
