import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import QuestionPreviewModal from '../QuestionPreviewModal';
import { ComposerService } from '../../../services/ComposerService';
import type { ApprovedQuestionDetail } from '../../../types/composer';

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

const detail: ApprovedQuestionDetail = {
  id: 42,
  question_text: 'Welcher Sortieralgorithmus ist O(n log n)?',
  question_type: 'multiple_choice',
  difficulty: 'medium',
  topic: 'Sortieren',
  language: 'de',
  bloom_level: 2,
  ln_level: 3,
  estimated_time_minutes: 4,
  options: [
    { text: 'Bubblesort', is_correct: false },
    { text: 'Heapsort', is_correct: true },
    { text: 'Selectionsort', is_correct: false },
    { text: 'Insertionsort', is_correct: false },
  ],
  correct_answer: 'Heapsort',
  explanation: 'Heapsort garantiert O(n log n) im Worst Case.',
  usage_count: 0,
  competency: null,
  source_documents: [],
};

const baseProps = {
  questionId: 42 as number | null,
  isAdded: false,
  canEdit: true,
  onAdd: jest.fn(),
  onRemove: jest.fn(),
  onClose: jest.fn(),
};

const renderModal = (props: Partial<typeof baseProps> = {}) =>
  render(<QuestionPreviewModal {...baseProps} {...props} />, { wrapper: createWrapper() });

describe('QuestionPreviewModal — TF-405', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockComposerService.getApprovedQuestion.mockResolvedValue(detail);
  });

  it('lazily fetches the detail and marks the correct option + explanation', async () => {
    renderModal();
    await waitFor(() => expect(mockComposerService.getApprovedQuestion).toHaveBeenCalledWith(42));
    await screen.findByText('Heapsort');

    const dialog = screen.getByRole('dialog');
    const correctRow = within(dialog)
      .getAllByRole('listitem')
      .find((row) => within(row).queryByText('Heapsort'));
    expect(correctRow).toBeDefined();
    expect(within(correctRow as HTMLElement).getByText('✓')).toBeInTheDocument();
    expect(screen.getByText('Heapsort garantiert O(n log n) im Worst Case.')).toBeInTheDocument();
  });

  it('does not fetch while closed (questionId null)', () => {
    renderModal({ questionId: null });
    expect(mockComposerService.getApprovedQuestion).not.toHaveBeenCalled();
  });

  it('shows "+ Hinzufügen" and adds when the question is not yet in the exam', async () => {
    renderModal({ isAdded: false });
    await screen.findByText('Heapsort');

    const dialog = screen.getByRole('dialog');
    const addBtn = within(dialog).getByRole('button', { name: /Hinzufügen/ });
    fireEvent.click(addBtn);
    expect(baseProps.onAdd).toHaveBeenCalledTimes(1);
    expect(baseProps.onRemove).not.toHaveBeenCalled();
    expect(baseProps.onClose).toHaveBeenCalled();
  });

  it('shows "− Entfernen" and removes when the question is already in the exam', async () => {
    renderModal({ isAdded: true });
    await screen.findByText('Heapsort');

    const dialog = screen.getByRole('dialog');
    expect(within(dialog).queryByRole('button', { name: /Hinzufügen/ })).not.toBeInTheDocument();
    const removeBtn = within(dialog).getByRole('button', { name: /Entfernen/ });
    fireEvent.click(removeBtn);
    expect(baseProps.onRemove).toHaveBeenCalledTimes(1);
    expect(baseProps.onAdd).not.toHaveBeenCalled();
    expect(baseProps.onClose).toHaveBeenCalled();
  });

  it('disables the action button for non-editable (finalised) exams', async () => {
    renderModal({ isAdded: false, canEdit: false });
    await screen.findByText('Heapsort');

    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByRole('button', { name: /Hinzufügen/ })).toBeDisabled();
  });

  it('closes on the close button and on Escape', async () => {
    const { rerender } = renderModal();
    await screen.findByText('Heapsort');

    fireEvent.click(screen.getByText('Schliessen'));
    expect(baseProps.onClose).toHaveBeenCalled();

    rerender(<QuestionPreviewModal {...baseProps} />);
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape', code: 'Escape' });
    expect(baseProps.onClose).toHaveBeenCalledTimes(2);
  });
});
