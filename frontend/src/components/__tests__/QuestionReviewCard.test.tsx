import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import QuestionReviewCard from '../QuestionReviewCard';
import { QuestionReview, ReviewStatus } from '../../types/review';

// Mock theme
const theme = createTheme();

// Test wrapper with theme
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>
    {children}
  </ThemeProvider>
);

// Sample test data
const mockQuestion: QuestionReview = {
  id: 1,
  question_text: 'What is a heap data structure?',
  question_type: 'multiple_choice',
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
    it('renders all action buttons', () => {
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

      expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /reject/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /edit/i })).toBeInTheDocument();
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

      const approveButton = screen.getByRole('button', { name: /approve/i });
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

      const rejectButton = screen.getByRole('button', { name: /reject/i });
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

      const editButton = screen.getByRole('button', { name: /edit/i });
      fireEvent.click(editButton);

      expect(mockOnEdit).toHaveBeenCalledWith(1);
    });

    it('calls onComment when comment button is clicked', () => {
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

    it('disables buttons when loading', () => {
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

      expect(screen.getByRole('button', { name: /approve/i })).toBeDisabled();
      expect(screen.getByRole('button', { name: /reject/i })).toBeDisabled();
      expect(screen.getByRole('button', { name: /edit/i })).toBeDisabled();
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

    it('expands/collapses source citations', () => {
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
});

