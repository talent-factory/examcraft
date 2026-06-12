import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import ExamQuestionsPanel from '../ExamQuestionsPanel';
import type { ExamQuestion } from '../../../types/composer';

const theme = createTheme();
const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>{children}</ThemeProvider>
);

// Row id (eqId) and question_id are deliberately different so the test pins down
// that preview is triggered with question_id (the QuestionReview id), NOT the
// ExamQuestion row id — the modal's add/remove logic resolves the row by question_id.
const examQuestion: ExamQuestion = {
  id: 999,
  question_id: 42,
  position: 1,
  points: 4,
  section: null,
  question_text: 'Welcher Sortieralgorithmus ist O(n log n)?',
  question_type: 'single_choice',
  difficulty: 'medium',
  topic: 'Sortieren',
  bloom_level: 2,
  review_status: 'approved',
  options: ['Bubblesort', 'Heapsort'],
  correct_answer: 'Heapsort',
  explanation: null,
};

const defaultProps = {
  questions: [examQuestion],
  disabled: false,
  onRemove: jest.fn(),
  onUpdatePoints: jest.fn(),
  onReorder: jest.fn(),
  onPreview: jest.fn(),
};

const renderPanel = (props: Partial<typeof defaultProps> = {}) =>
  render(<ExamQuestionsPanel {...defaultProps} {...props} />, { wrapper: Wrapper });

describe('ExamQuestionsPanel — TF-405 preview from the right panel', () => {
  beforeEach(() => jest.clearAllMocks());

  it('calls onPreview with question_id (not the row id) when the eye icon is clicked', () => {
    renderPanel();
    fireEvent.click(screen.getByLabelText('Frage-Vorschau öffnen'));
    expect(defaultProps.onPreview).toHaveBeenCalledWith(42);
    expect(defaultProps.onPreview).not.toHaveBeenCalledWith(999);
  });

  it('calls onPreview with question_id on double-click of the question text', () => {
    renderPanel();
    fireEvent.doubleClick(screen.getByText(examQuestion.question_text));
    expect(defaultProps.onPreview).toHaveBeenCalledWith(42);
  });

  it('keeps the preview icon available even when the exam is finalised (disabled)', () => {
    renderPanel({ disabled: true });
    fireEvent.click(screen.getByLabelText('Frage-Vorschau öffnen'));
    expect(defaultProps.onPreview).toHaveBeenCalledWith(42);
  });
});
