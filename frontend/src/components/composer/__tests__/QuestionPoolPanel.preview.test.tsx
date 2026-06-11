import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import QuestionPoolPanel from '../QuestionPoolPanel';
import { ComposerService } from '../../../services/ComposerService';
import type { ApprovedQuestion } from '../../../types/composer';

jest.mock('axios', () => ({
  __esModule: true,
  default: {
    create: jest.fn(() => ({
      get: jest.fn(),
      post: jest.fn(),
      put: jest.fn(),
      delete: jest.fn(),
      interceptors: { request: { use: jest.fn() }, response: { use: jest.fn() } },
    })),
  },
}));

jest.mock('../../../services/ComposerService');
const mockComposerService = ComposerService as jest.Mocked<typeof ComposerService>;

jest.mock('../../../api/tagsApi', () => ({
  __esModule: true,
  default: { listTags: jest.fn().mockResolvedValue([]) },
  tagsApi: { listTags: jest.fn().mockResolvedValue([]) },
}));

const theme = createTheme();

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>{children}</ThemeProvider>
    </QueryClientProvider>
  );
  return Wrapper;
};

const listQuestion: ApprovedQuestion = {
  id: 42,
  question_text: 'Welcher Sortieralgorithmus ist O(n log n)?',
  question_type: 'multiple_choice',
  difficulty: 'medium',
  topic: 'Sortieren',
  bloom_level: 2,
  options: ['Bubblesort', 'Heapsort', 'Selectionsort', 'Insertionsort'],
  usage_count: 0,
  tags: [],
};

const defaultProps = {
  addedQuestionIds: new Set<number>(),
  onAddQuestions: jest.fn(),
  examId: 1,
  disabled: false,
  onInvalidate: jest.fn(),
  onPreview: jest.fn(),
};

const renderPanel = () =>
  render(<QuestionPoolPanel {...defaultProps} />, { wrapper: createWrapper() });

describe('QuestionPoolPanel — TF-405 preview triggers', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockComposerService.listApprovedQuestions.mockResolvedValue({ total: 1, questions: [listQuestion] });
    mockComposerService.listDocumentsWithQuestions.mockResolvedValue([]);
  });

  it('calls onPreview with the question id when the preview icon is clicked', async () => {
    renderPanel();
    await screen.findByText(listQuestion.question_text);

    fireEvent.click(screen.getByLabelText('Frage-Vorschau öffnen'));
    expect(defaultProps.onPreview).toHaveBeenCalledWith(42);
  });

  it('calls onPreview on double-click of the card', async () => {
    renderPanel();
    const card = await screen.findByText(listQuestion.question_text);

    fireEvent.doubleClick(card);
    expect(defaultProps.onPreview).toHaveBeenCalledWith(42);
  });
});
