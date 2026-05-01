/**
 * Tests for the per-exam submissions page (overview + drawer + import).
 */

import React from 'react';
import {
  render,
  screen,
  waitFor,
  within,
  fireEvent,
} from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import AuswertungenExam from '../AuswertungenExam';
import { ComposerService } from '../../services/ComposerService';
import { SubmissionsService } from '../../services/submissionsService';
import { ExamStatus } from '../../types/composer';
import {
  SubmissionDetail,
  SubmissionList,
} from '../../types/submission';

jest.mock('../../services/ComposerService', () => ({
  ComposerService: {
    getExam: jest.fn(),
  },
  getErrorMessage: (e: unknown, fb: string) =>
    e instanceof Error ? e.message : fb,
}));
jest.mock('../../services/submissionsService', () => ({
  SubmissionsService: {
    listForExam: jest.fn(),
    getDetail: jest.fn(),
  },
  ApiError: class ApiError extends Error {},
}));
jest.mock('../../components/auswertungen/ImportDialog', () => ({
  __esModule: true,
  default: ({
    examId,
    onClose,
    onImported,
  }: {
    examId: number;
    onClose: () => void;
    onImported?: (job: unknown) => void;
  }) => (
    <div data-testid={`import-dialog-stub-${examId}`}>
      <button onClick={onClose}>close-stub</button>
      <button
        onClick={() =>
          onImported?.({
            id: 99,
            exam_id: examId,
            driver_name: 'moodle_csv',
            status: 'succeeded',
            rows_processed: 1,
            rows_failed: 0,
            error_log: null,
            source_metadata: null,
            started_at: null,
            finished_at: null,
          })
        }
      >
        trigger-imported
      </button>
    </div>
  ),
}));

const mockComposer = ComposerService as jest.Mocked<typeof ComposerService>;
const mockSubs = SubmissionsService as jest.Mocked<typeof SubmissionsService>;

const theme = createTheme();

const sampleExam = {
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
  questions: [],
} as never;

const oneSubmission = {
  items: [
    {
      id: 42,
      exam_id: 1,
      student_id: 7,
      student_external_id: 'anna@example.com',
      student_display_name: 'Anna Beispiel',
      attempt_count: 1,
      total_points_awarded: 5.0,
      total_points_max: 10.0,
      percentage: 50,
      grade_status: 'fully_reviewed',
    },
  ],
  total: 1,
} satisfies SubmissionList;

const sampleDetail: SubmissionDetail = {
  id: 42,
  exam_id: 1,
  student_id: 7,
  student_external_id: 'anna@example.com',
  student_display_name: 'Anna Beispiel',
  scoring_strategy: 'latest',
  graded_attempt_id: 100,
  total_points_awarded: 5.0,
  total_points_max: 10.0,
  percentage: 50,
  grade_status: 'fully_reviewed',
  attempts: [
    {
      id: 100,
      attempt_number: 1,
      started_at: '2026-04-30T08:00:00',
      submitted_at: '2026-04-30T08:30:00',
      source: 'moodle_csv',
      source_attempt_id: 'anna@example.com|2026-04-30T08:00:00|1',
      answers: [
        {
          id: 200,
          exam_question_id: 11,
          given_answer: 'Bern',
          moodle_points_awarded: null,
          grade: {
            id: 300,
            points_awarded: 4,
            points_max: 4,
            status: 'proposed',
            is_correct: true,
            llm_confidence: null,
            llm_rationale: null,
          },
        },
        {
          id: 201,
          exam_question_id: 12,
          given_answer: 'Föderalismus erklärt …',
          moodle_points_awarded: null,
          grade: {
            id: 301,
            points_awarded: 0,
            points_max: 5,
            status: 'proposed',
            is_correct: null,
            llm_confidence: null,
            llm_rationale: null,
          },
        },
      ],
    },
  ],
};

const renderPage = (examId: string = '1') =>
  render(
    <MemoryRouter initialEntries={[`/auswertungen/${examId}/submissions`]}>
      <ThemeProvider theme={theme}>
        <Routes>
          <Route
            path="/auswertungen/:examId/submissions"
            element={<AuswertungenExam />}
          />
        </Routes>
      </ThemeProvider>
    </MemoryRouter>,
  );

describe('AuswertungenExam', () => {
  beforeEach(() => {
    jest.resetAllMocks();
    mockComposer.getExam.mockResolvedValue(sampleExam);
  });

  test('renders submissions table with row, points and grade-status chip', async () => {
    mockSubs.listForExam.mockResolvedValue(oneSubmission);

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId('submissions-table')).toBeInTheDocument();
    });
    const row = screen.getByTestId('submission-row-42');
    expect(within(row).getByText('anna@example.com')).toBeInTheDocument();
    expect(within(row).getByText('Anna Beispiel')).toBeInTheDocument();
    expect(within(row).getByText('5.0 / 10.0')).toBeInTheDocument();
    expect(within(row).getByText('50%')).toBeInTheDocument();
    // 'fully_reviewed' label maps via i18n; assert chip presence by role
    expect(within(row).getByText(/Reviewt/i)).toBeInTheDocument();
  });

  test('opens drawer with attempts, graded-attempt chip, and is_correct icons on row click', async () => {
    mockSubs.listForExam.mockResolvedValue(oneSubmission);
    mockSubs.getDetail.mockResolvedValue(sampleDetail);

    renderPage();
    await screen.findByTestId('submission-row-42');

    fireEvent.click(screen.getByTestId('submission-row-42'));

    await waitFor(() => {
      expect(mockSubs.getDetail).toHaveBeenCalledWith(42);
    });

    // Wait for the drawer to load (independent of the table cell that
    // also contains "Anna Beispiel" — assert on a drawer-only string).
    expect(await screen.findByText(/Versuch 1/)).toBeInTheDocument();
    // graded_attempt_id matches → "Wertend" chip rendered
    expect(screen.getByText(/Wertend/)).toBeInTheDocument();
    // is_correct=true → ✓ shown; open-ended stub → no tick/cross.
    expect(screen.getByText(/4\.0 \/ 4\.0\s*✓/)).toBeInTheDocument();
    expect(screen.getByText(/0\.0 \/ 5\.0$/)).toBeInTheDocument();
  });

  test('shows empty-state hint and import button when there are no submissions', async () => {
    mockSubs.listForExam.mockResolvedValue({ items: [], total: 0 });

    renderPage();
    expect(
      await screen.findByText(/Noch keine Resultate importiert/i),
    ).toBeInTheDocument();
    // Two import entrypoints in DOM: header + empty-state. Either works.
    expect(screen.getAllByText(/Resultate importieren/i).length).toBeGreaterThan(0);
  });

  test('reloads list after a successful import', async () => {
    mockSubs.listForExam.mockResolvedValueOnce({ items: [], total: 0 });
    renderPage();
    await screen.findByText(/Noch keine Resultate importiert/i);

    // Open import dialog via header button.
    fireEvent.click(screen.getByTestId('auswertungen-exam-import'));
    expect(screen.getByTestId('import-dialog-stub-1')).toBeInTheDocument();

    // After import, the page reloads → second listForExam returns rows.
    mockSubs.listForExam.mockResolvedValueOnce(oneSubmission);
    fireEvent.click(screen.getByText('trigger-imported'));

    await waitFor(() => {
      expect(mockSubs.listForExam).toHaveBeenCalledTimes(2);
    });
    expect(await screen.findByTestId('submission-row-42')).toBeInTheDocument();
  });

  test('shows error alert when list load fails', async () => {
    mockSubs.listForExam.mockRejectedValue(new Error('listForExam down'));

    renderPage();
    await waitFor(() => {
      expect(screen.getByText('listForExam down')).toBeInTheDocument();
    });
  });

  test('shows drawer-local error alert when row-detail load fails', async () => {
    mockSubs.listForExam.mockResolvedValue(oneSubmission);
    mockSubs.getDetail.mockRejectedValue(new Error('detail down'));

    renderPage();
    await screen.findByTestId('submission-row-42');
    fireEvent.click(screen.getByTestId('submission-row-42'));

    // Error must surface inside the drawer (next to the click), not in
    // the page-level alert at the top.
    await waitFor(() => {
      expect(screen.getByTestId('drawer-error')).toHaveTextContent(
        'detail down',
      );
    });
  });
});
