import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { ExamComposer } from '../ExamComposer';
import { ComposerService } from '../../services/ComposerService';
import type { ExamListResponse, ExamDetail } from '../../types/composer';
import { ExamStatus } from '../../types/composer';
import { useActivityHeartbeat } from '../../hooks/useActivityHeartbeat';

// TF-838 (PR #286 review): mocked so pre-existing tests don't fire real,
// unmocked heartbeat POSTs as a side effect — and so the "which bucket did
// we pass" wiring below can assert on it directly.
jest.mock('../../hooks/useActivityHeartbeat', () => ({
  useActivityHeartbeat: jest.fn(),
}));
const mockUseActivityHeartbeat = useActivityHeartbeat as jest.Mock;

// Mock axios to prevent ESM parse errors (ComposerService imports axios)
jest.mock('axios', () => ({
  __esModule: true,
  default: { create: jest.fn(() => ({ get: jest.fn(), post: jest.fn(), put: jest.fn(), delete: jest.fn(), interceptors: { request: { use: jest.fn() }, response: { use: jest.fn() } } })) },
}));

// Mock ComposerService so tests don't make real HTTP calls
jest.mock('../../services/ComposerService');
const mockComposerService = ComposerService as jest.Mocked<typeof ComposerService>;

// TF-398: the composer renders ExamListView, which reads the delete_exams
// permission via useAuth. Stub it so the page test needs no AuthProvider.
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ hasPermission: () => true }),
}));

// Mock child components so tests stay fast and focused on ExamComposer routing logic
jest.mock('../../components/composer/ExamBuilderView', () => ({
  __esModule: true,
  default: ({ examId, onBack }: { examId: number; onBack: () => void }) => (
    <div data-testid="exam-builder-view">
      <span data-testid="exam-builder-exam-id">{examId}</span>
      <button onClick={onBack}>Zurück</button>
    </div>
  ),
}));

const theme = createTheme();

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>{children}</ThemeProvider>
    </QueryClientProvider>
  );
  return Wrapper;
};

const emptyListResponse: ExamListResponse = { total: 0, exams: [] };

describe('ExamComposer', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // -------------------------------------------------------------------------
  // Default view
  // -------------------------------------------------------------------------

  describe('default view', () => {
    it('renders ExamListView by default (shows Prüfungskomponist heading)', async () => {
      mockComposerService.listExams.mockResolvedValue(emptyListResponse);

      render(<ExamComposer />, { wrapper: createWrapper() });

      // ExamListView renders this heading
      expect(screen.getByText('Prüfungskomponist')).toBeInTheDocument();
    });

    it('does NOT render ExamBuilderView initially', async () => {
      mockComposerService.listExams.mockResolvedValue(emptyListResponse);

      render(<ExamComposer />, { wrapper: createWrapper() });

      expect(screen.queryByTestId('exam-builder-view')).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Navigation: list → builder → list
  // -------------------------------------------------------------------------

  describe('navigation', () => {
    it('switches to ExamBuilderView when an exam is selected', async () => {
      const exam = {
        id: 42,
        title: 'Test Exam',
        course: null,
        exam_date: null,
        time_limit_minutes: null,
        allowed_aids: null,
        instructions: null,
        passing_percentage: 50,
        total_points: 0,
        status: ExamStatus.DRAFT,
        language: 'de',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
        question_count: 0,
      };
      mockComposerService.listExams.mockResolvedValue({ total: 1, exams: [exam] });

      render(<ExamComposer />, { wrapper: createWrapper() });

      // Wait for the exam card to appear
      await waitFor(() => {
        expect(screen.getByText('Test Exam')).toBeInTheDocument();
      });

      // Click the card to select the exam
      fireEvent.click(screen.getByText('Test Exam').closest('div')!);

      // ExamBuilderView mock should now be visible
      await waitFor(() => {
        expect(screen.getByTestId('exam-builder-view')).toBeInTheDocument();
        expect(screen.getByTestId('exam-builder-exam-id')).toHaveTextContent('42');
      });
    });

    it('switches back to ExamListView when onBack is called from builder', async () => {
      const exam = {
        id: 42,
        title: 'Test Exam',
        course: null,
        exam_date: null,
        time_limit_minutes: null,
        allowed_aids: null,
        instructions: null,
        passing_percentage: 50,
        total_points: 0,
        status: ExamStatus.DRAFT,
        language: 'de',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
        question_count: 0,
      };
      mockComposerService.listExams.mockResolvedValue({ total: 1, exams: [exam] });

      render(<ExamComposer />, { wrapper: createWrapper() });

      // Navigate to builder
      await waitFor(() => {
        expect(screen.getByText('Test Exam')).toBeInTheDocument();
      });
      fireEvent.click(screen.getByText('Test Exam').closest('div')!);

      await waitFor(() => {
        expect(screen.getByTestId('exam-builder-view')).toBeInTheDocument();
      });

      // Navigate back
      fireEvent.click(screen.getByRole('button', { name: 'Zurück' }));

      await waitFor(() => {
        expect(screen.queryByTestId('exam-builder-view')).not.toBeInTheDocument();
        expect(screen.getByText('Prüfungskomponist')).toBeInTheDocument();
      });
    });

    it('navigates to builder via createExam (from dialog)', async () => {
      const newExam = {
        id: 99,
        title: 'Neue Prüfung',
        course: null,
        exam_date: null,
        time_limit_minutes: null,
        allowed_aids: null,
        instructions: null,
        passing_percentage: 50,
        total_points: 0,
        status: ExamStatus.DRAFT,
        language: 'de',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
        question_count: 0,
      };
      mockComposerService.listExams.mockResolvedValue(emptyListResponse);
      mockComposerService.createExam.mockResolvedValue(newExam);

      render(<ExamComposer />, { wrapper: createWrapper() });

      // Open create dialog
      fireEvent.click(screen.getByText('+ Neue Prüfung'));

      await waitFor(() => {
        expect(screen.getByLabelText(/Titel/)).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText(/Titel/), {
        target: { value: 'Neue Prüfung' },
      });
      fireEvent.click(screen.getByRole('button', { name: 'Erstellen' }));

      await waitFor(() => {
        expect(screen.getByTestId('exam-builder-view')).toBeInTheDocument();
        expect(screen.getByTestId('exam-builder-exam-id')).toHaveTextContent('99');
      });
    });
  });

  // -------------------------------------------------------------------------
  // Live-Activity heartbeat wiring (TF-838, PR #286 review): the hook's own
  // tests cover its internal behavior — this only verifies ExamComposer
  // passes the *correct* bucket-or-null value at each state transition,
  // since an inverted condition here wouldn't be caught anywhere else.
  // -------------------------------------------------------------------------

  describe('Live-Activity heartbeat wiring', () => {
    it('passes null (not "exam_compose") while browsing the exam list', async () => {
      mockComposerService.listExams.mockResolvedValue(emptyListResponse);

      render(<ExamComposer />, { wrapper: createWrapper() });

      expect(mockUseActivityHeartbeat).toHaveBeenLastCalledWith(null);
    });

    it('passes "exam_compose" only once an exam is actually selected for editing', async () => {
      const exam = {
        id: 42,
        title: 'Test Exam',
        course: null,
        exam_date: null,
        time_limit_minutes: null,
        allowed_aids: null,
        instructions: null,
        passing_percentage: 50,
        total_points: 0,
        status: ExamStatus.DRAFT,
        language: 'de',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
        question_count: 0,
      };
      mockComposerService.listExams.mockResolvedValue({ total: 1, exams: [exam] });

      render(<ExamComposer />, { wrapper: createWrapper() });

      await screen.findByText('Test Exam');
      expect(mockUseActivityHeartbeat).toHaveBeenLastCalledWith(null);

      fireEvent.click(screen.getByText('Test Exam').closest('div')!);

      await screen.findByTestId('exam-builder-view');
      expect(mockUseActivityHeartbeat).toHaveBeenLastCalledWith('exam_compose');

      fireEvent.click(screen.getByRole('button', { name: 'Zurück' }));

      await waitFor(() => expect(screen.queryByTestId('exam-builder-view')).not.toBeInTheDocument());
      expect(mockUseActivityHeartbeat).toHaveBeenLastCalledWith(null);
    });
  });
});
