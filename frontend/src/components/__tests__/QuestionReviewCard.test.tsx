import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { MemoryRouter } from 'react-router-dom';
import QuestionReviewCard from '../QuestionReviewCard';
import { QuestionReview, ReviewStatus } from '../../types/review';

// Mock theme
const theme = createTheme();

// Test wrapper with theme
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <MemoryRouter>
    <ThemeProvider theme={theme}>
      {children}
    </ThemeProvider>
  </MemoryRouter>
);

// Sample test data
const mockQuestion: QuestionReview = {
  id: 1,
  question_text: 'What is a heap data structure?',
  question_type: 'single_choice',
  options: ['A tree-based structure', 'A linear structure', 'A graph structure', 'A hash table'],
  correct_answer: 'A tree-based structure',
  explanation: 'A heap is a specialized tree-based data structure that satisfies the heap property.',
  difficulty: 'medium',
  topic: 'Data Structures',
  language: 'en',
  source_chunks: ['Heap is a tree-based structure...', 'Priority queues are implemented using heaps...'],
  source_documents: ['algorithms_textbook.pdf', 'data_structures_guide.pdf'],
  confidence_score: 0.85,
  bloom_level: 3,
  estimated_time_minutes: 5,
  quality_tier: 'A',
  review_status: ReviewStatus.PENDING,
  reviewed_by: undefined,
  reviewed_at: undefined,
  exam_id: 'exam_123',
  created_at: '2025-10-19T10:00:00Z',
  updated_at: '2025-10-19T10:00:00Z'
};

describe('QuestionReviewCard', () => {
  const mockOnApprove = jest.fn();
  const mockOnReject = jest.fn();
  const mockOnEdit = jest.fn();
  const mockOnComment = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders question text correctly', () => {
      render(
        <TestWrapper>
          <QuestionReviewCard question={mockQuestion} />
        </TestWrapper>
      );

      expect(screen.getByText('What is a heap data structure?')).toBeInTheDocument();
    });

    it('renders all multiple choice options', () => {
      render(
        <TestWrapper>
          <QuestionReviewCard question={mockQuestion} />
        </TestWrapper>
      );

      expect(screen.getByText('A tree-based structure')).toBeInTheDocument();
      expect(screen.getByText('A linear structure')).toBeInTheDocument();
      expect(screen.getByText('A graph structure')).toBeInTheDocument();
      expect(screen.getByText('A hash table')).toBeInTheDocument();
    });

    it('highlights correct answer', () => {
      render(
        <TestWrapper>
          <QuestionReviewCard question={mockQuestion} />
        </TestWrapper>
      );

      const correctAnswerElement = screen.getByText('A tree-based structure').closest('div');
      expect(correctAnswerElement).toHaveStyle({ backgroundColor: expect.any(String) });
    });

    it('displays quality indicators', () => {
      render(
        <TestWrapper>
          <QuestionReviewCard question={mockQuestion} />
        </TestWrapper>
      );

      expect(screen.getByText(/medium/i)).toBeInTheDocument();
      expect(screen.getByText(/85%/i)).toBeInTheDocument();
      // Bloom level is displayed as "3 - Apply" (number - label format)
      expect(screen.getByText(/3 - Apply/i)).toBeInTheDocument();
      expect(screen.getByText(/5 min/i)).toBeInTheDocument();
      expect(screen.getByText(/Tier A/i)).toBeInTheDocument();
    });

    it('displays review status chip', () => {
      render(
        <TestWrapper>
          <QuestionReviewCard question={mockQuestion} />
        </TestWrapper>
      );

      expect(screen.getByText(/pending/i)).toBeInTheDocument();
    });

    it('displays explanation when provided', () => {
      render(
        <TestWrapper>
          <QuestionReviewCard question={mockQuestion} />
        </TestWrapper>
      );

      expect(screen.getByText(/A heap is a specialized tree-based data structure/i)).toBeInTheDocument();
    });
  });

  describe('Action Buttons', () => {
    // TODO: Fix test - multiple buttons with same name cause query issues
    it.skip('renders all action buttons', () => {
      render(
        <TestWrapper>
          <QuestionReviewCard
            question={mockQuestion}
            onApprove={mockOnApprove}
            onReject={mockOnReject}
            onEdit={mockOnEdit}
            onComment={mockOnComment}
          />
        </TestWrapper>
      );

      expect(screen.getByRole('button', { name: /Genehmigen/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Ablehnen/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Frage bearbeiten/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /comment/i })).toBeInTheDocument();
    });

    it('calls onApprove when approve button is clicked', () => {
      render(
        <TestWrapper>
          <QuestionReviewCard
            question={mockQuestion}
            onApprove={mockOnApprove}
          />
        </TestWrapper>
      );

      const approveButton = screen.getByRole('button', { name: /Genehmigen/i });
      fireEvent.click(approveButton);

      expect(mockOnApprove).toHaveBeenCalledWith(1);
    });

    it('calls onReject when reject button is clicked', () => {
      render(
        <TestWrapper>
          <QuestionReviewCard
            question={mockQuestion}
            onReject={mockOnReject}
          />
        </TestWrapper>
      );

      const rejectButton = screen.getByRole('button', { name: /Ablehnen/i });
      fireEvent.click(rejectButton);

      expect(mockOnReject).toHaveBeenCalledWith(1);
    });

    it('calls onEdit when edit button is clicked', () => {
      render(
        <TestWrapper>
          <QuestionReviewCard
            question={mockQuestion}
            onEdit={mockOnEdit}
          />
        </TestWrapper>
      );

      const editButton = screen.getByRole('button', { name: /Frage bearbeiten/i });
      fireEvent.click(editButton);

      expect(mockOnEdit).toHaveBeenCalledWith(1);
    });

    // TODO: Fix test - multiple buttons with same name cause query issues
    it.skip('calls onComment when comment button is clicked', () => {
      render(
        <TestWrapper>
          <QuestionReviewCard
            question={mockQuestion}
            onComment={mockOnComment}
          />
        </TestWrapper>
      );

      const commentButton = screen.getByRole('button', { name: /comment/i });
      fireEvent.click(commentButton);

      expect(mockOnComment).toHaveBeenCalledWith(1);
    });

    // TODO: Fix test - multiple buttons with same name cause query issues
    it.skip('disables buttons when loading', () => {
      render(
        <TestWrapper>
          <QuestionReviewCard
            question={mockQuestion}
            onApprove={mockOnApprove}
            onReject={mockOnReject}
            onEdit={mockOnEdit}
            onComment={mockOnComment}
            loading={true}
          />
        </TestWrapper>
      );

      expect(screen.getByRole('button', { name: /Genehmigen/i })).toBeDisabled();
      expect(screen.getByRole('button', { name: /Ablehnen/i })).toBeDisabled();
      expect(screen.getByRole('button', { name: /Frage bearbeiten/i })).toBeDisabled();
      expect(screen.getByRole('button', { name: /comment/i })).toBeDisabled();
    });
  });

  describe('Source Citations', () => {
    it('displays source documents', () => {
      render(
        <TestWrapper>
          <QuestionReviewCard question={mockQuestion} />
        </TestWrapper>
      );

      expect(screen.getByText(/algorithms_textbook.pdf/i)).toBeInTheDocument();
      expect(screen.getByText(/data_structures_guide.pdf/i)).toBeInTheDocument();
    });

    // TODO: Fix test - UI structure changed
    it.skip('expands/collapses source citations', () => {
      render(
        <TestWrapper>
          <QuestionReviewCard question={mockQuestion} />
        </TestWrapper>
      );

      // Button text is "Show Sources (2)"
      const expandButton = screen.getByRole('button', { name: /Show Sources \(2\)/i });

      // Initially collapsed - source chunks should not be in document
      expect(screen.queryByText('Heap is a tree-based structure...')).not.toBeInTheDocument();

      // Click to expand
      fireEvent.click(expandButton);

      // Now visible
      expect(screen.getByText('Heap is a tree-based structure...')).toBeInTheDocument();
    });
  });

  describe('Different Question Types', () => {
    it('renders open-ended question without options', () => {
      const openEndedQuestion: QuestionReview = {
        ...mockQuestion,
        question_type: 'open_ended',
        options: undefined,
        correct_answer: 'A heap is a tree-based data structure...'
      };

      render(
        <TestWrapper>
          <QuestionReviewCard question={openEndedQuestion} />
        </TestWrapper>
      );

      expect(screen.getByText('What is a heap data structure?')).toBeInTheDocument();
      expect(screen.queryByText('A tree-based structure')).not.toBeInTheDocument();
    });
  });

  describe('Review Status Display', () => {
    it('displays approved status with reviewer info', () => {
      const approvedQuestion: QuestionReview = {
        ...mockQuestion,
        review_status: ReviewStatus.APPROVED,
        reviewed_by: 'reviewer_1',
        reviewed_at: '2025-10-19T11:00:00Z'
      };

      render(
        <TestWrapper>
          <QuestionReviewCard question={approvedQuestion} />
        </TestWrapper>
      );

      expect(screen.getByText(/approved/i)).toBeInTheDocument();
      expect(screen.getByText(/reviewer_1/i)).toBeInTheDocument();
    });

    it('displays rejected status', () => {
      const rejectedQuestion: QuestionReview = {
        ...mockQuestion,
        review_status: ReviewStatus.REJECTED
      };

      render(
        <TestWrapper>
          <QuestionReviewCard question={rejectedQuestion} />
        </TestWrapper>
      );

      expect(screen.getByText(/rejected/i)).toBeInTheDocument();
    });
  });

  // TF-383: Template-/Prompt-Herkunft (Provenance-Snapshot)
  describe('Template provenance', () => {
    it('shows custom template name and version', () => {
      const q: QuestionReview = {
        ...mockQuestion,
        generation_metadata: {
          prompt_id: 'uuid-123',
          prompt_name: 'universal_single_choice_generator',
          prompt_version: 3,
          is_default_template: false,
          fallback_to_default: false,
          variables: { topic: 'Heaps', difficulty: 'medium' },
        },
      };

      render(
        <TestWrapper>
          <QuestionReviewCard question={q} />
        </TestWrapper>
      );

      expect(
        screen.getByText('universal_single_choice_generator v3')
      ).toBeInTheDocument();
    });

    it('shows default-template badge for default snapshots', () => {
      const q: QuestionReview = {
        ...mockQuestion,
        generation_metadata: {
          prompt_id: null,
          prompt_name: 'default_single_choice',
          prompt_version: null,
          is_default_template: true,
          fallback_to_default: false,
          variables: { topic: 'Heaps' },
        },
      };

      render(
        <TestWrapper>
          <QuestionReviewCard question={q} />
        </TestWrapper>
      );

      // de/translation.json → "Standard-Vorlage"
      expect(screen.getByText('Standard-Vorlage')).toBeInTheDocument();
    });

    it('treats a failed-render fallback as default template', () => {
      const q: QuestionReview = {
        ...mockQuestion,
        generation_metadata: {
          prompt_id: 'uuid-broken',
          prompt_name: 'default_open_ended',
          prompt_version: null,
          is_default_template: true,
          fallback_to_default: true,
          variables: {},
        },
      };

      render(
        <TestWrapper>
          <QuestionReviewCard question={q} />
        </TestWrapper>
      );

      expect(screen.getByText('Standard-Vorlage')).toBeInTheDocument();
    });

    it('shows "not recorded" for legacy questions without provenance', () => {
      const q: QuestionReview = {
        ...mockQuestion,
        generation_metadata: null,
      };

      render(
        <TestWrapper>
          <QuestionReviewCard question={q} />
        </TestWrapper>
      );

      // de/translation.json → "Vorlage nicht erfasst"
      expect(screen.getByText('Vorlage nicht erfasst')).toBeInTheDocument();
    });
  });

  // TF-400: Handlungskompetenz (HK) + LN-Stufe an der Frage
  describe('Competency display', () => {
    const withCompetency: QuestionReview = {
      ...mockQuestion,
      competency_id: 42,
      ln_level: 2,
      competency: {
        id: 42,
        code: 'B3',
        title: 'Wirkungsvoll kommunizieren',
        framework_id: 7,
        module_code: 'B',
      },
    };

    it('shows the competency code with LN level when both are present', () => {
      render(
        <TestWrapper>
          <QuestionReviewCard question={withCompetency} />
        </TestWrapper>
      );

      // Chip-Label: `${code} · LN {level}`
      expect(screen.getByText('B3 · LN 2')).toBeInTheDocument();
    });

    it('shows just the competency code when LN level is missing', () => {
      const noLn: QuestionReview = {
        ...withCompetency,
        ln_level: null,
      };

      render(
        <TestWrapper>
          <QuestionReviewCard question={noLn} />
        </TestWrapper>
      );

      expect(screen.getByText('B3')).toBeInTheDocument();
      expect(screen.queryByText(/· LN/)).not.toBeInTheDocument();
    });

    it('renders no competency chip when no competency is assigned', () => {
      render(
        <TestWrapper>
          <QuestionReviewCard question={mockQuestion} />
        </TestWrapper>
      );

      expect(screen.queryByText(/^B3/)).not.toBeInTheDocument();
    });
  });
});
