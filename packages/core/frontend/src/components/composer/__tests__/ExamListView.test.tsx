import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import ExamListView from '../ExamListView';
import { ComposerService } from '../../../services/ComposerService';
import type { Exam, ExamListResponse } from '../../../types/composer';
import { ExamStatus } from '../../../types/composer';

// Mock axios to prevent ESM parse errors (ComposerService imports axios)
jest.mock('axios', () => ({
  __esModule: true,
  default: { create: jest.fn(() => ({ get: jest.fn(), post: jest.fn(), put: jest.fn(), delete: jest.fn(), interceptors: { request: { use: jest.fn() }, response: { use: jest.fn() } } })) },
}));

// Mock ComposerService so tests don't make real HTTP calls
jest.mock('../../../services/ComposerService');
const mockComposerService = ComposerService as jest.Mocked<typeof ComposerService>;

// Mock window.confirm
const mockConfirm = jest.fn();
window.confirm = mockConfirm;

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

const makeExam = (overrides: Partial<Exam> = {}): Exam => ({
  id: 1,
  title: 'Grundlagen der Informatik',
  course: 'Informatik 101',
  exam_date: '2025-06-15',
  time_limit_minutes: 90,
  allowed_aids: null,
  instructions: null,
  passing_percentage: 50,
  total_points: 100,
  status: ExamStatus.DRAFT,
  language: 'de',
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
  question_count: 5,
  ...overrides,
});

describe('ExamListView', () => {
  const mockOnSelectExam = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockConfirm.mockReturnValue(false);
  });

  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  describe('loading state', () => {
    it('shows loading message while query is pending', () => {
      // Never resolves during this test
      mockComposerService.listExams.mockImplementation(() => new Promise(() => {}));

      render(<ExamListView onSelectExam={mockOnSelectExam} />, {
        wrapper: createWrapper(),
      });

      expect(screen.getByText('Lade Prüfungen...')).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Empty state
  // -------------------------------------------------------------------------

  describe('empty state', () => {
    it('shows empty state message when no exams exist', async () => {
      const emptyResponse: ExamListResponse = { total: 0, exams: [] };
      mockComposerService.listExams.mockResolvedValue(emptyResponse);

      render(<ExamListView onSelectExam={mockOnSelectExam} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(
          screen.getByText(/Noch keine Prüfungen erstellt/)
        ).toBeInTheDocument();
      });
    });
  });

  // -------------------------------------------------------------------------
  // Exam cards
  // -------------------------------------------------------------------------

  describe('exam cards', () => {
    it('renders exam title, course, question count and points', async () => {
      const exam = makeExam();
      mockComposerService.listExams.mockResolvedValue({ total: 1, exams: [exam] });

      render(<ExamListView onSelectExam={mockOnSelectExam} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByText('Grundlagen der Informatik')).toBeInTheDocument();
      });

      expect(screen.getByText('Informatik 101')).toBeInTheDocument();
      expect(screen.getByText('5 Fragen')).toBeInTheDocument();
      expect(screen.getByText('100 Punkte')).toBeInTheDocument();
    });

    it('shows status label for draft exam', async () => {
      mockComposerService.listExams.mockResolvedValue({
        total: 1,
        exams: [makeExam({ status: ExamStatus.DRAFT })],
      });

      render(<ExamListView onSelectExam={mockOnSelectExam} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByText('Entwurf')).toBeInTheDocument();
      });
    });

    it('shows status label for finalized exam', async () => {
      mockComposerService.listExams.mockResolvedValue({
        total: 1,
        exams: [makeExam({ status: ExamStatus.FINALIZED })],
      });

      render(<ExamListView onSelectExam={mockOnSelectExam} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByText('Finalisiert')).toBeInTheDocument();
      });
    });

    it('calls onSelectExam when exam card is clicked', async () => {
      const exam = makeExam({ id: 42 });
      mockComposerService.listExams.mockResolvedValue({ total: 1, exams: [exam] });

      render(<ExamListView onSelectExam={mockOnSelectExam} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByText('Grundlagen der Informatik')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Grundlagen der Informatik').closest('div')!);
      expect(mockOnSelectExam).toHaveBeenCalledWith(42);
    });

    it('renders multiple exam cards', async () => {
      const exams = [
        makeExam({ id: 1, title: 'Prüfung Eins' }),
        makeExam({ id: 2, title: 'Prüfung Zwei' }),
        makeExam({ id: 3, title: 'Prüfung Drei' }),
      ];
      mockComposerService.listExams.mockResolvedValue({ total: 3, exams });

      render(<ExamListView onSelectExam={mockOnSelectExam} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByText('Prüfung Eins')).toBeInTheDocument();
        expect(screen.getByText('Prüfung Zwei')).toBeInTheDocument();
        expect(screen.getByText('Prüfung Drei')).toBeInTheDocument();
      });
    });
  });

  // -------------------------------------------------------------------------
  // Delete button
  // -------------------------------------------------------------------------

  describe('delete button', () => {
    it('shows Löschen button for draft exams', async () => {
      mockComposerService.listExams.mockResolvedValue({
        total: 1,
        exams: [makeExam({ status: ExamStatus.DRAFT })],
      });

      render(<ExamListView onSelectExam={mockOnSelectExam} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByText('Löschen')).toBeInTheDocument();
      });
    });

    it('does NOT show Löschen button for finalized exams', async () => {
      mockComposerService.listExams.mockResolvedValue({
        total: 1,
        exams: [makeExam({ status: ExamStatus.FINALIZED })],
      });

      render(<ExamListView onSelectExam={mockOnSelectExam} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.queryByText('Löschen')).not.toBeInTheDocument();
      });
    });

    it('calls deleteExam when delete is clicked and confirmed', async () => {
      mockConfirm.mockReturnValue(true);
      mockComposerService.listExams.mockResolvedValue({
        total: 1,
        exams: [makeExam({ id: 7 })],
      });
      mockComposerService.deleteExam.mockResolvedValue(undefined);

      render(<ExamListView onSelectExam={mockOnSelectExam} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByText('Löschen')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Löschen'));

      await waitFor(() => {
        expect(mockComposerService.deleteExam).toHaveBeenCalled();
        expect(mockComposerService.deleteExam.mock.calls[0][0]).toBe(7);
      });
    });

    it('does NOT call deleteExam when delete is cancelled', async () => {
      mockConfirm.mockReturnValue(false);
      mockComposerService.listExams.mockResolvedValue({
        total: 1,
        exams: [makeExam({ id: 7 })],
      });

      render(<ExamListView onSelectExam={mockOnSelectExam} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByText('Löschen')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Löschen'));
      expect(mockComposerService.deleteExam).not.toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // Create dialog
  // -------------------------------------------------------------------------

  describe('create dialog', () => {
    it('opens dialog when "+ Neue Prüfung" button is clicked', async () => {
      mockComposerService.listExams.mockResolvedValue({ total: 0, exams: [] });

      render(<ExamListView onSelectExam={mockOnSelectExam} />, {
        wrapper: createWrapper(),
      });

      fireEvent.click(screen.getByText('+ Neue Prüfung'));

      await waitFor(() => {
        expect(screen.getByText('Neue Prüfung erstellen')).toBeInTheDocument();
      });
    });

    it('renders form fields in the dialog', async () => {
      mockComposerService.listExams.mockResolvedValue({ total: 0, exams: [] });

      render(<ExamListView onSelectExam={mockOnSelectExam} />, {
        wrapper: createWrapper(),
      });

      fireEvent.click(screen.getByText('+ Neue Prüfung'));

      await waitFor(() => {
        expect(screen.getByLabelText(/Titel/)).toBeInTheDocument();
        expect(screen.getByLabelText(/Kurs/)).toBeInTheDocument();
      });
    });

    it('Erstellen button is disabled when title is empty', async () => {
      mockComposerService.listExams.mockResolvedValue({ total: 0, exams: [] });

      render(<ExamListView onSelectExam={mockOnSelectExam} />, {
        wrapper: createWrapper(),
      });

      fireEvent.click(screen.getByText('+ Neue Prüfung'));

      await waitFor(() => {
        const createBtn = screen.getByRole('button', { name: 'Erstellen' });
        expect(createBtn).toBeDisabled();
      });
    });

    it('Erstellen button is enabled when title has text', async () => {
      mockComposerService.listExams.mockResolvedValue({ total: 0, exams: [] });

      render(<ExamListView onSelectExam={mockOnSelectExam} />, {
        wrapper: createWrapper(),
      });

      fireEvent.click(screen.getByText('+ Neue Prüfung'));

      await waitFor(() => {
        expect(screen.getByLabelText(/Titel/)).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText(/Titel/), {
        target: { value: 'Meine neue Prüfung' },
      });

      const createBtn = screen.getByRole('button', { name: 'Erstellen' });
      expect(createBtn).not.toBeDisabled();
    });

    it('calls createExam and closes dialog on successful submit', async () => {
      const newExam = makeExam({ id: 99, title: 'Meine neue Prüfung' });
      mockComposerService.listExams.mockResolvedValue({ total: 0, exams: [] });
      mockComposerService.createExam.mockResolvedValue(newExam);

      render(<ExamListView onSelectExam={mockOnSelectExam} />, {
        wrapper: createWrapper(),
      });

      fireEvent.click(screen.getByText('+ Neue Prüfung'));

      await waitFor(() => {
        expect(screen.getByLabelText(/Titel/)).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText(/Titel/), {
        target: { value: 'Meine neue Prüfung' },
      });

      fireEvent.click(screen.getByRole('button', { name: 'Erstellen' }));

      await waitFor(() => {
        expect(mockComposerService.createExam).toHaveBeenCalled();
        expect(mockComposerService.createExam.mock.calls[0][0]).toMatchObject({ title: 'Meine neue Prüfung' });
      });

      await waitFor(() => {
        expect(mockOnSelectExam).toHaveBeenCalledWith(99);
      });
    });

    it('closes dialog when Abbrechen is clicked', async () => {
      mockComposerService.listExams.mockResolvedValue({ total: 0, exams: [] });

      render(<ExamListView onSelectExam={mockOnSelectExam} />, {
        wrapper: createWrapper(),
      });

      fireEvent.click(screen.getByText('+ Neue Prüfung'));

      await waitFor(() => {
        expect(screen.getByText('Neue Prüfung erstellen')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('button', { name: 'Abbrechen' }));

      await waitFor(() => {
        expect(screen.queryByText('Neue Prüfung erstellen')).not.toBeInTheDocument();
      });
    });
  });

  // -------------------------------------------------------------------------
  // Header always present
  // -------------------------------------------------------------------------

  describe('header', () => {
    it('renders the Exam Composer heading', async () => {
      mockComposerService.listExams.mockResolvedValue({ total: 0, exams: [] });

      render(<ExamListView onSelectExam={mockOnSelectExam} />, {
        wrapper: createWrapper(),
      });

      expect(screen.getByText('Exam Composer')).toBeInTheDocument();
    });

    it('renders the search input', async () => {
      mockComposerService.listExams.mockResolvedValue({ total: 0, exams: [] });

      render(<ExamListView onSelectExam={mockOnSelectExam} />, {
        wrapper: createWrapper(),
      });

      expect(screen.getByPlaceholderText('Prüfungen durchsuchen...')).toBeInTheDocument();
    });
  });
});
