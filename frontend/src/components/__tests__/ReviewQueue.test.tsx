import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { MemoryRouter } from 'react-router-dom';
import ReviewQueue from '../ReviewQueue';
import { ReviewService } from '../../services/ReviewService';
import { QuestionReview, ReviewStatus } from '../../types/review';

// TF-838 (PR #286 review): mocked so this suite doesn't fire real, unmocked
// heartbeat POSTs as a side effect on every render.
jest.mock('../../hooks/useActivityHeartbeat', () => ({
  useActivityHeartbeat: jest.fn(),
}));

const mockHasPermission = jest.fn();
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ hasPermission: mockHasPermission }),
}));

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

// The editor dialog pulls in tagsApi (ESM axios) — same stubs as QuestionEditor.test.tsx.
jest.mock('../../api/tagsApi', () => ({
  tagsApi: {
    listTags: jest.fn().mockResolvedValue([]),
    createTag: jest.fn(),
    setQuestionTags: jest.fn().mockResolvedValue({ tags: [] }),
    removeQuestionTag: jest.fn(),
  },
}));
jest.mock('../shared/TagAutocomplete', () => ({
  __esModule: true,
  default: () => null,
}));

jest.mock('../../services/ReviewService');
const mockReviewService = ReviewService as jest.Mocked<typeof ReviewService>;

const theme = createTheme();

const renderQueue = () =>
  render(
    <MemoryRouter>
      <ThemeProvider theme={theme}>
        <ReviewQueue />
      </ThemeProvider>
    </MemoryRouter>
  );

/**
 * ReviewQueue tests. The suite sat on `describe.skip` with English labels
 * until TF-1057; it now asserts the German copy the global i18n mock in
 * setupTests.ts renders from de/translation.json. Which fallback code each
 * service call maps to is pinned in services/__tests__/ReviewService.errors.test.ts
 * and not repeated here — this suite covers the component's wiring.
 */

const mockQuestions: QuestionReview[] = [
  {
    id: 1,
    question_text: 'What is a heap data structure?',
    question_type: 'single_choice',
    options: ['A tree-based structure', 'A linear structure'],
    correct_answer: 'A tree-based structure',
    explanation: 'A heap is a tree-based structure.',
    difficulty: 'medium',
    topic: 'Data Structures',
    language: 'en',
    confidence_score: 0.85,
    bloom_level: 3,
    estimated_time_minutes: 5,
    quality_tier: 'A',
    review_status: ReviewStatus.PENDING,
    exam_id: 'exam_123',
    created_at: '2025-10-19T10:00:00Z',
    updated_at: '2025-10-19T10:00:00Z'
  },
  {
    id: 2,
    question_text: 'Explain the concept of polymorphism.',
    question_type: 'open_ended',
    correct_answer: 'Polymorphism allows objects of different types...',
    difficulty: 'hard',
    topic: 'OOP',
    language: 'en',
    confidence_score: 0.75,
    bloom_level: 4,
    estimated_time_minutes: 10,
    quality_tier: 'B',
    review_status: ReviewStatus.PENDING,
    exam_id: 'exam_124',
    created_at: '2025-10-19T11:00:00Z',
    updated_at: '2025-10-19T11:00:00Z'
  }
];

const mockReviewQueueResponse = {
  total: 7,
  pending: 3,
  approved: 2,
  rejected: 1,
  in_review: 1,
  questions: mockQuestions
};

/** The question cards render once the first queue response has arrived. */
const waitForQuestions = () => screen.findByText('What is a heap data structure?');

/** Card actions exist once per card; the first one belongs to question 1. */
const firstCardButton = (name: string) => screen.getAllByRole('button', { name })[0];

describe('ReviewQueue', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockHasPermission.mockReturnValue(false);
    mockReviewService.getReviewQueue.mockResolvedValue(mockReviewQueueResponse);
  });

  describe('Rendering', () => {
    it('renders title, statistics and the loaded questions', async () => {
      renderQueue();

      expect(screen.getByText('Fragen-Review Queue')).toBeInTheDocument();
      await waitForQuestions();
      expect(screen.getByText('Explain the concept of polymorphism.')).toBeInTheDocument();

      // Each statistic card pairs the count from the response with its label.
      const stats: Array<[string, string]> = [
        ['Gesamt', '7'],
        ['Ausstehend', '3'],
        ['Genehmigt', '2'],
        ['Abgelehnt', '1'],
      ];
      for (const [label, value] of stats) {
        // eslint-disable-next-line testing-library/no-node-access
        const card = screen.getAllByText(label)[0].closest('.MuiCardContent-root') as HTMLElement;
        expect(within(card).getByText(value)).toBeInTheDocument();
      }
    });

    it('shows the empty-state message when no question matches', async () => {
      mockReviewService.getReviewQueue.mockResolvedValue({
        total: 0,
        pending: 0,
        approved: 0,
        rejected: 0,
        in_review: 0,
        questions: []
      });

      renderQueue();

      expect(
        await screen.findByText('Keine Fragen gefunden, die deinen Filtern entsprechen.')
      ).toBeInTheDocument();
    });

    it('shows the translated load error, not the raw message', async () => {
      mockReviewService.getReviewQueue.mockRejectedValue(new Error('Failed to load'));

      renderQueue();

      expect(await screen.findByText('Fragen konnten nicht geladen werden')).toBeInTheDocument();
      expect(screen.queryByText(/Failed to load/)).not.toBeInTheDocument();
    });
  });

  describe('Filters', () => {
    // The three MUI Selects carry no accessible name (InputLabel is not wired
    // via labelId), so they are addressed by position: status, difficulty, type.
    const pickFilter = async (index: number, option: string) => {
      fireEvent.mouseDown(screen.getAllByRole('combobox')[index]);
      fireEvent.click(within(await screen.findByRole('listbox')).getByText(option));
    };

    it.each([
      [0, 'Ausstehend', { status: ReviewStatus.PENDING }],
      [1, 'Mittel', { difficulty: 'medium' }],
      [2, 'Einfachauswahl', { question_type: 'single_choice' }],
    ])('reloads the queue with the chosen filter (select %i: %s)', async (index, option, expected) => {
      renderQueue();
      await waitForQuestions();

      await pickFilter(index, option);

      await waitFor(() => {
        expect(mockReviewService.getReviewQueue).toHaveBeenLastCalledWith(
          expect.objectContaining({ ...expected, offset: 0 })
        );
      });
    });

    it('switches to the archive view', async () => {
      renderQueue();
      await waitForQuestions();

      fireEvent.click(screen.getByRole('button', { name: 'Archiv anzeigen' }));

      await waitFor(() => {
        expect(mockReviewService.getReviewQueue).toHaveBeenLastCalledWith(
          expect.objectContaining({ archived_only: true })
        );
      });
      expect(screen.getByRole('button', { name: 'Aktive anzeigen' })).toBeInTheDocument();
    });

    it('reloads the queue when refresh is clicked', async () => {
      renderQueue();
      await waitForQuestions();
      mockReviewService.getReviewQueue.mockClear();

      fireEvent.click(screen.getByRole('button', { name: 'Aktualisieren' }));

      await waitFor(() => {
        expect(mockReviewService.getReviewQueue).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('Approve/Reject Workflow', () => {
    it('approves a question through the confirmation dialog and reloads', async () => {
      mockReviewService.approveQuestion.mockResolvedValue({
        ...mockQuestions[0],
        review_status: ReviewStatus.APPROVED
      });

      renderQueue();
      await waitForQuestions();
      fireEvent.click(firstCardButton('Genehmigen'));

      const dialog = await screen.findByRole('dialog');
      expect(within(dialog).getByText('Frage genehmigen')).toBeInTheDocument();
      mockReviewService.getReviewQueue.mockClear();
      fireEvent.click(within(dialog).getByRole('button', { name: 'Genehmigen' }));

      await waitFor(() => {
        expect(mockReviewService.approveQuestion).toHaveBeenCalledWith(1, { reason: undefined });
      });
      await waitFor(() => {
        expect(mockReviewService.getReviewQueue).toHaveBeenCalledTimes(1);
      });
      expect(mockReviewService.rejectQuestion).not.toHaveBeenCalled();
    });

    it('rejects a question and passes the entered reason', async () => {
      mockReviewService.rejectQuestion.mockResolvedValue({
        ...mockQuestions[0],
        review_status: ReviewStatus.REJECTED
      });

      renderQueue();
      await waitForQuestions();
      fireEvent.click(firstCardButton('Ablehnen'));

      const dialog = await screen.findByRole('dialog');
      expect(within(dialog).getByText('Frage ablehnen')).toBeInTheDocument();
      fireEvent.change(within(dialog).getByLabelText('Begründung (optional)'), {
        target: { value: 'Question is ambiguous' }
      });
      fireEvent.click(within(dialog).getByRole('button', { name: 'Ablehnen' }));

      await waitFor(() => {
        expect(mockReviewService.rejectQuestion).toHaveBeenCalledWith(1, {
          reason: 'Question is ambiguous'
        });
      });
      expect(mockReviewService.approveQuestion).not.toHaveBeenCalled();
    });

    it('keeps the dialog open and shows the error when the action fails', async () => {
      mockReviewService.approveQuestion.mockRejectedValue(new Error('boom'));

      renderQueue();
      await waitForQuestions();
      fireEvent.click(firstCardButton('Genehmigen'));
      const dialog = await screen.findByRole('dialog');
      fireEvent.click(within(dialog).getByRole('button', { name: 'Genehmigen' }));

      expect(await screen.findByText('Aktion fehlgeschlagen')).toBeInTheDocument();
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });
  });

  describe('Other Card Actions', () => {
    it('starts a review and navigates to the review page', async () => {
      mockReviewService.startReview.mockResolvedValue(mockQuestions[0]);

      renderQueue();
      await waitForQuestions();
      fireEvent.click(firstCardButton('Review starten'));

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/questions/review/1');
      });
      expect(mockReviewService.startReview).toHaveBeenCalledWith(1);
    });

    it('opens the editor for the clicked question', async () => {
      renderQueue();
      await waitForQuestions();

      fireEvent.click(firstCardButton('Frage bearbeiten'));

      const dialog = await screen.findByRole('dialog');
      expect(within(dialog).getByDisplayValue('What is a heap data structure?')).toBeInTheDocument();
    });

    it('adds a comment through the comment dialog', async () => {
      renderQueue();
      await waitForQuestions();
      fireEvent.click(firstCardButton('Kommentar hinzufügen'));

      const dialog = await screen.findByRole('dialog');
      const submit = within(dialog).getByRole('button', { name: 'Kommentar hinzufügen' });
      expect(submit).toBeDisabled();

      fireEvent.change(within(dialog).getByLabelText('Kommentar'), {
        target: { value: 'Distractor B is too obvious' }
      });
      fireEvent.click(submit);

      await waitFor(() => {
        expect(mockReviewService.addComment).toHaveBeenCalledWith(1, {
          comment_text: 'Distractor B is too obvious',
          comment_type: 'general'
        });
      });
    });

    it('archives a question and reloads', async () => {
      renderQueue();
      await waitForQuestions();
      mockReviewService.getReviewQueue.mockClear();
      fireEvent.click(firstCardButton('Archivieren'));

      await waitFor(() => {
        expect(mockReviewService.archiveQuestion).toHaveBeenCalledWith(1);
      });
      await waitFor(() => {
        expect(mockReviewService.getReviewQueue).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('Hard Delete (TF-396/TF-408)', () => {
    const archivedResponse = {
      ...mockReviewQueueResponse,
      questions: [{ ...mockQuestions[0], archived_at: '2025-10-20T10:00:00Z' }],
    };

    it('hides the delete action without the delete_questions permission', async () => {
      mockReviewService.getReviewQueue.mockResolvedValue(archivedResponse);

      renderQueue();
      await waitForQuestions();

      expect(screen.getByRole('button', { name: 'Wiederherstellen' })).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Endgültig löschen' })).not.toBeInTheDocument();
      expect(mockHasPermission).toHaveBeenCalledWith('delete_questions');
    });

    it('shows a failed delete inline in the still-open dialog', async () => {
      mockHasPermission.mockReturnValue(true);
      mockReviewService.getReviewQueue.mockResolvedValue(archivedResponse);
      mockReviewService.deleteQuestion.mockRejectedValue(new Error('in use'));

      renderQueue();
      await waitForQuestions();
      fireEvent.click(screen.getByRole('button', { name: 'Endgültig löschen' }));

      const dialog = await screen.findByRole('dialog');
      fireEvent.click(within(dialog).getByRole('button', { name: 'Löschen' }));

      expect(await within(dialog).findByText('Löschen fehlgeschlagen')).toBeInTheDocument();
      expect(mockReviewService.deleteQuestion).toHaveBeenCalledWith(1);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });
  });
});
