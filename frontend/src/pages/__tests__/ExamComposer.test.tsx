import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { ExamComposer } from '../ExamComposer';
import { ComposerService } from '../../services/ComposerService';
import type { ExamListResponse, ExamDetail } from '../../types/composer';
import { ExamStatus } from '../../types/composer';

// Mock axios to prevent ESM parse errors (ComposerService imports axios)
jest.mock('axios', () => ({
  __esModule: true,
  default: { create: jest.fn(() => ({ get: jest.fn(), post: jest.fn(), put: jest.fn(), delete: jest.fn(), interceptors: { request: { use: jest.fn() }, response: { use: jest.fn() } } })) },
}));

// Mock ComposerService so tests don't make real HTTP calls
jest.mock('../../services/ComposerService');
const mockComposerService = ComposerService as jest.Mocked<typeof ComposerService>;

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
    it('renders ExamListView by default (shows Exam Composer heading)', async () => {
      mockComposerService.listExams.mockResolvedValue(emptyListResponse);

      render(<ExamComposer />, { wrapper: createWrapper() });

      // ExamListView renders this heading
      expect(screen.getByText('Exam Composer')).toBeInTheDocument();
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
        expect(screen.getByText('Exam Composer')).toBeInTheDocument();
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
});
