import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import ExamDisplay from '../ExamDisplay';
import { ExamResponse } from '../../types/exam';

// Mock MarkdownRenderer to render plain text (avoids react-markdown ESM in Jest)
jest.mock('../MarkdownRenderer', () => ({
  __esModule: true,
  default: ({ content }: { content: string }) => <span>{content}</span>,
}));

const theme = createTheme();

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>{children}</ThemeProvider>
);

const baseExam = (questions: ExamResponse['questions']): ExamResponse => ({
  exam_id: 'exam-1',
  topic: 'Sortieralgorithmen',
  questions,
  created_at: '2026-06-11T10:00:00Z',
  metadata: {
    difficulty: 'medium',
    question_count: questions.length,
    language: 'de',
    generated_by: 'test',
  },
});

describe('ExamDisplay — multiple_choice rendering (TF-403)', () => {
  it('renders a multiple_choice question with checkboxes', () => {
    const exam = baseExam([
      {
        id: 'q-multi',
        type: 'multiple_choice',
        question: 'Welche Aussagen treffen zu?',
        options: ['Aussage A', 'Aussage B', 'Aussage C', 'Aussage D'],
        correct_answer: '["Aussage A","Aussage C"]',
        difficulty: 'medium',
        topic: 'Sortieralgorithmen',
      },
    ]);

    render(
      <TestWrapper>
        <ExamDisplay exam={exam} onNewExam={() => {}} />
      </TestWrapper>,
    );

    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes).toHaveLength(4);
    expect(screen.queryAllByRole('radio')).toHaveLength(0);
  });

  it('renders a single_choice question with radio buttons', () => {
    const exam = baseExam([
      {
        id: 'q-single',
        type: 'single_choice',
        question: 'Welche Aussage trifft zu?',
        options: ['Aussage A', 'Aussage B', 'Aussage C', 'Aussage D'],
        correct_answer: 'Aussage A',
        difficulty: 'medium',
        topic: 'Sortieralgorithmen',
      },
    ]);

    render(
      <TestWrapper>
        <ExamDisplay exam={exam} onNewExam={() => {}} />
      </TestWrapper>,
    );

    const radios = screen.getAllByRole('radio');
    expect(radios).toHaveLength(4);
    expect(screen.queryAllByRole('checkbox')).toHaveLength(0);
  });
});
