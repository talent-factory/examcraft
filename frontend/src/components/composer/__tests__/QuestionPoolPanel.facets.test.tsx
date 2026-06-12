import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
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

// TF-406: Kompetenz-Facette speist sich aus den Frameworks der Institution.
jest.mock('../../../api/competencyFrameworksApi', () => ({
  competencyFrameworksApi: {
    listFrameworks: jest.fn().mockResolvedValue([
      {
        id: 1,
        name: 'Modul B',
        competencies: [
          { id: 7, code: 'B3', title: 'Handlungskompetenz B3', descriptors: null, position: 0 },
        ],
      },
    ]),
  },
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

describe('QuestionPoolPanel — TF-406 facets, sort & auto-compose entry', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockComposerService.listApprovedQuestions.mockResolvedValue({
      total: 1,
      questions: [listQuestion],
    });
    mockComposerService.listDocumentsWithQuestions.mockResolvedValue([]);
  });

  it('renders the new facet dropdowns, sort and both auto-compose entry buttons', async () => {
    renderPanel();
    await screen.findByText(listQuestion.question_text);

    expect(screen.getByLabelText('Nach Anforderungsniveau filtern')).toBeInTheDocument();
    expect(screen.getByLabelText('Nach Qualitätsstufe filtern')).toBeInTheDocument();
    expect(screen.getByLabelText('Nach Bloom-Stufe filtern')).toBeInTheDocument();
    expect(screen.getByLabelText('Sortierung')).toBeInTheDocument();
    expect(screen.getByText('Nur nie verwendete')).toBeInTheDocument();
    // Auto-Compose is a visible, top-level entry (≤2 clicks → 1 click here).
    expect(screen.getByText('Auto-Komposition')).toBeInTheDocument();
    expect(screen.getByText('Auto-Fill')).toBeInTheDocument();
  });

  it('labels every Bloom level correctly (1=Erinnern … 6=Erschaffen)', async () => {
    renderPanel();
    await screen.findByText(listQuestion.question_text);

    // Regression guard for the BLOOM_LABELS off-by-one: the dropdown is keyed
    // 1–6, so level 1 must read "Erinnern" and level 6 "Erschaffen" — never
    // blank (level 1 → BLOOM_LABELS[0]) nor shifted down a rank.
    const bloomSelect = screen.getByLabelText('Nach Bloom-Stufe filtern');
    const optionTexts = within(bloomSelect)
      .getAllByRole('option')
      .map((o) => o.textContent);
    expect(optionTexts).toEqual([
      'Bloom: alle',
      'Erinnern',
      'Verstehen',
      'Anwenden',
      'Analysieren',
      'Bewerten',
      'Erschaffen',
    ]);
  });

  it('refetches with ln_level when the requirement-level facet changes', async () => {
    renderPanel();
    await screen.findByText(listQuestion.question_text);

    fireEvent.change(screen.getByLabelText('Nach Anforderungsniveau filtern'), {
      target: { value: '3' },
    });

    await waitFor(() =>
      expect(mockComposerService.listApprovedQuestions).toHaveBeenLastCalledWith(
        expect.objectContaining({ ln_level: 3 }),
      ),
    );
    // An active-filter chip appeared. Assert on its remove button (chip-only)
    // rather than counting "LN 3" occurrences, which would couple to the
    // incidental option/chip text duplication.
    expect(
      screen.getByRole('button', { name: 'Filter entfernen' }),
    ).toBeInTheDocument();
  });

  it('refetches with the chosen competency once frameworks load', async () => {
    renderPanel();
    await screen.findByText(listQuestion.question_text);
    // Competency option only appears after the frameworks query resolves.
    await screen.findByRole('option', { name: /B3/ });

    fireEvent.change(screen.getByLabelText('Nach Handlungskompetenz filtern'), {
      target: { value: '7' },
    });

    await waitFor(() =>
      expect(mockComposerService.listApprovedQuestions).toHaveBeenLastCalledWith(
        expect.objectContaining({ competency_id: 7 }),
      ),
    );
  });

  it('refetches with sort=most_used when the sort dropdown changes', async () => {
    renderPanel();
    await screen.findByText(listQuestion.question_text);

    fireEvent.change(screen.getByLabelText('Sortierung'), {
      target: { value: 'most_used' },
    });

    await waitFor(() =>
      expect(mockComposerService.listApprovedQuestions).toHaveBeenLastCalledWith(
        expect.objectContaining({ sort: 'most_used' }),
      ),
    );
  });

  it('refetches with unused=true when the "never used" toggle is checked', async () => {
    renderPanel();
    await screen.findByText(listQuestion.question_text);

    fireEvent.click(screen.getByLabelText('Nur nie verwendete'));

    await waitFor(() =>
      expect(mockComposerService.listApprovedQuestions).toHaveBeenLastCalledWith(
        expect.objectContaining({ unused: true }),
      ),
    );
  });

  it('clears every facet via "Filter zurücksetzen"', async () => {
    renderPanel();
    await screen.findByText(listQuestion.question_text);

    fireEvent.change(screen.getByLabelText('Nach Anforderungsniveau filtern'), {
      target: { value: '2' },
    });
    // Chip present → assert on its remove button, not a text count.
    expect(
      await screen.findByRole('button', { name: 'Filter entfernen' }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByText('Filter zurücksetzen'));

    // Chip cleared → no remove-filter affordance remains.
    await waitFor(() =>
      expect(
        screen.queryByRole('button', { name: 'Filter entfernen' }),
      ).not.toBeInTheDocument(),
    );
    await waitFor(() =>
      expect(mockComposerService.listApprovedQuestions).toHaveBeenLastCalledWith(
        expect.objectContaining({ ln_level: undefined, sort: 'newest' }),
      ),
    );
  });

  it('opens the constraint-based auto-compose dialog directly in composition mode', async () => {
    renderPanel();
    await screen.findByText(listQuestion.question_text);

    fireEvent.click(screen.getByText('Auto-Komposition'));

    // Composition-only control ("Zielpunkte" number field) proves the dialog
    // opened in composition mode rather than the simple auto-fill mode.
    expect(
      await screen.findByRole('spinbutton', { name: 'Zielpunkte' }),
    ).toBeInTheDocument();
  });
});
