import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import QuestionEditor from '../QuestionEditor';
import { QuestionReview, ReviewStatus } from '../../types/review';

// Mock tagsApi to avoid ESM axios issues in Jest
jest.mock('../../api/tagsApi', () => ({
  tagsApi: {
    listTags: jest.fn().mockResolvedValue([]),
    createTag: jest.fn(),
    setQuestionTags: jest.fn().mockResolvedValue({ tags: [] }),
    removeQuestionTag: jest.fn(),
  },
}));

// Mock TagAutocomplete to avoid dependency on tagsApi in Jest
jest.mock('../shared/TagAutocomplete', () => ({
  __esModule: true,
  default: () => null,
}));

// Mock theme
const theme = createTheme();

// Test wrapper with theme
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>
    {children}
  </ThemeProvider>
);

/**
 * QuestionEditor tests. The suite below sat on `describe.skip` with English
 * labels until TF-775; it now asserts the German copy the global i18n mock in
 * setupTests.ts renders from de/translation.json.
 */

// Sample test data
const mockQuestion: QuestionReview = {
  id: 1,
  question_text: 'What is a heap data structure?',
  question_type: 'single_choice',
  options: ['A tree-based structure', 'A linear structure', 'A graph structure'],
  correct_answer: 'A tree-based structure',
  explanation: 'A heap is a specialized tree-based data structure.',
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
};

describe('QuestionEditor', () => {
  const mockOnClose = jest.fn();
  const mockOnSave = jest.fn().mockResolvedValue(undefined);

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders dialog when open', () => {
      render(
        <TestWrapper>
          <QuestionEditor
            question={mockQuestion}
            open={true}
            onClose={mockOnClose}
            onSave={mockOnSave}
          />
        </TestWrapper>
      );

      expect(screen.getByText(/Frage #1 bearbeiten/i)).toBeInTheDocument();
    });

    it('does not render when closed', () => {
      render(
        <TestWrapper>
          <QuestionEditor
            question={mockQuestion}
            open={false}
            onClose={mockOnClose}
            onSave={mockOnSave}
          />
        </TestWrapper>
      );

      expect(screen.queryByText(/Frage #1 bearbeiten/i)).not.toBeInTheDocument();
    });

    it('renders all form fields', () => {
      render(
        <TestWrapper>
          <QuestionEditor
            question={mockQuestion}
            open={true}
            onClose={mockOnClose}
            onSave={mockOnSave}
          />
        </TestWrapper>
      );

      expect(screen.getByLabelText(/Fragetext/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Korrekte Antwort/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Erklärung/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Schwierigkeit/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Bloom-Taxonomiestufe/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Geschätzte Zeit/i)).toBeInTheDocument();
    });

    it('pre-fills form with question data', () => {
      render(
        <TestWrapper>
          <QuestionEditor
            question={mockQuestion}
            open={true}
            onClose={mockOnClose}
            onSave={mockOnSave}
          />
        </TestWrapper>
      );

      const questionTextInput = screen.getByLabelText(/Fragetext/i) as HTMLInputElement;
      expect(questionTextInput.value).toBe('What is a heap data structure?');

      const explanationInput = screen.getByLabelText(/Erklärung/i) as HTMLTextAreaElement;
      expect(explanationInput.value).toBe('A heap is a specialized tree-based data structure.');
    });
  });

  describe('Form Editing', () => {
    it('allows editing question text', () => {
      render(
        <TestWrapper>
          <QuestionEditor
            question={mockQuestion}
            open={true}
            onClose={mockOnClose}
            onSave={mockOnSave}
          />
        </TestWrapper>
      );

      const questionTextInput = screen.getByLabelText(/Fragetext/i);
      fireEvent.change(questionTextInput, { target: { value: 'Updated question text' } });

      expect((questionTextInput as HTMLInputElement).value).toBe('Updated question text');
    });

    it('allows changing difficulty', () => {
      render(
        <TestWrapper>
          <QuestionEditor
            question={mockQuestion}
            open={true}
            onClose={mockOnClose}
            onSave={mockOnSave}
          />
        </TestWrapper>
      );

      const difficultySelect = screen.getByLabelText(/Schwierigkeit/i);
      fireEvent.mouseDown(difficultySelect);

      const hardOption = screen.getByRole('option', { name: /Schwer/i });
      fireEvent.click(hardOption);

      expect(difficultySelect).toHaveTextContent('Schwer');
    });

    it('allows changing Bloom level', () => {
      render(
        <TestWrapper>
          <QuestionEditor
            question={mockQuestion}
            open={true}
            onClose={mockOnClose}
            onSave={mockOnSave}
          />
        </TestWrapper>
      );

      const bloomSelect = screen.getByLabelText(/Bloom-Taxonomiestufe/i);
      fireEvent.mouseDown(bloomSelect);

      const level5Option = screen.getByRole('option', { name: /5 - Bewerten/i });
      fireEvent.click(level5Option);

      expect(bloomSelect).toHaveTextContent('5 - Bewerten');
    });
  });

  describe('Multiple Choice Options', () => {
    it('displays existing options', () => {
      render(
        <TestWrapper>
          <QuestionEditor
            question={mockQuestion}
            open={true}
            onClose={mockOnClose}
            onSave={mockOnSave}
          />
        </TestWrapper>
      );

      // The correct answer shows twice: in the option list and as the value
      // of the correct-answer select.
      expect(screen.getAllByText('A tree-based structure')).toHaveLength(2);
      expect(screen.getByText('A linear structure')).toBeInTheDocument();
      expect(screen.getByText('A graph structure')).toBeInTheDocument();
    });

    it('allows adding new option', async () => {
      render(
        <TestWrapper>
          <QuestionEditor
            question={mockQuestion}
            open={true}
            onClose={mockOnClose}
            onSave={mockOnSave}
          />
        </TestWrapper>
      );

      const newOptionInput = screen.getByPlaceholderText(/Neue Option hinzufügen/i);
      fireEvent.change(newOptionInput, { target: { value: 'New option' } });

      const addButton = screen.getByRole('button', { name: /Hinzufügen/i });
      fireEvent.click(addButton);

      await waitFor(() => {
        expect(screen.getByText('New option')).toBeInTheDocument();
      });
    });

    it('allows removing option', () => {
      render(
        <TestWrapper>
          <QuestionEditor
            question={mockQuestion}
            open={true}
            onClose={mockOnClose}
            onSave={mockOnSave}
          />
        </TestWrapper>
      );

      const deleteButtons = screen.getAllByRole('button', { name: '' }).filter(
        btn => btn.querySelector('svg[data-testid="DeleteIcon"]')
      );

      fireEvent.click(deleteButtons[0]);

      expect(screen.queryByText('A tree-based structure')).not.toBeInTheDocument();
    });
  });

  describe('Form Validation', () => {
    it('shows error for empty question text', async () => {
      render(
        <TestWrapper>
          <QuestionEditor
            question={mockQuestion}
            open={true}
            onClose={mockOnClose}
            onSave={mockOnSave}
          />
        </TestWrapper>
      );

      const questionTextInput = screen.getByLabelText(/Fragetext/i);
      fireEvent.change(questionTextInput, { target: { value: '' } });

      const saveButton = screen.getByRole('button', { name: /Änderungen speichern/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/Der Fragetext muss mindestens 10 Zeichen lang sein/i)).toBeInTheDocument();
      });

      expect(mockOnSave).not.toHaveBeenCalled();
    });

    it('shows error for too few options in multiple choice', async () => {
      const questionWithOneOption: QuestionReview = {
        ...mockQuestion,
        options: ['Only one option']
      };

      render(
        <TestWrapper>
          <QuestionEditor
            question={questionWithOneOption}
            open={true}
            onClose={mockOnClose}
            onSave={mockOnSave}
          />
        </TestWrapper>
      );

      // Save stays disabled until something changed, so change something first.
      fireEvent.change(screen.getByLabelText(/Fragetext/i), {
        target: { value: 'What is a heap data structure, exactly?' },
      });
      const saveButton = screen.getByRole('button', { name: /Änderungen speichern/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/Multiple-Choice-Fragen benötigen mindestens 2 Optionen/i)).toBeInTheDocument();
      });

      expect(mockOnSave).not.toHaveBeenCalled();
    });
  });

  describe('Save and Cancel', () => {
    it('calls onSave with updated data when save button is clicked', async () => {
      render(
        <TestWrapper>
          <QuestionEditor
            question={mockQuestion}
            open={true}
            onClose={mockOnClose}
            onSave={mockOnSave}
          />
        </TestWrapper>
      );

      const questionTextInput = screen.getByLabelText(/Fragetext/i);
      fireEvent.change(questionTextInput, { target: { value: 'Updated question text for testing' } });

      const saveButton = screen.getByRole('button', { name: /Änderungen speichern/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(
          1,
          expect.objectContaining({
            question_text: 'Updated question text for testing'
          })
        );
      });
    });

    it('calls onClose when cancel button is clicked without changes', () => {
      render(
        <TestWrapper>
          <QuestionEditor
            question={mockQuestion}
            open={true}
            onClose={mockOnClose}
            onSave={mockOnSave}
          />
        </TestWrapper>
      );

      const cancelButton = screen.getByRole('button', { name: /Abbrechen/i });
      fireEvent.click(cancelButton);

      expect(mockOnClose).toHaveBeenCalled();
    });

    it('shows confirmation when canceling with unsaved changes', () => {
      // Mock window.confirm
      const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(false);

      render(
        <TestWrapper>
          <QuestionEditor
            question={mockQuestion}
            open={true}
            onClose={mockOnClose}
            onSave={mockOnSave}
          />
        </TestWrapper>
      );

      const questionTextInput = screen.getByLabelText(/Fragetext/i);
      fireEvent.change(questionTextInput, { target: { value: 'Changed text' } });

      const cancelButton = screen.getByRole('button', { name: /Abbrechen/i });
      fireEvent.click(cancelButton);

      expect(confirmSpy).toHaveBeenCalled();
      expect(mockOnClose).not.toHaveBeenCalled();

      confirmSpy.mockRestore();
    });

    it('disables save button when no changes made', () => {
      render(
        <TestWrapper>
          <QuestionEditor
            question={mockQuestion}
            open={true}
            onClose={mockOnClose}
            onSave={mockOnSave}
          />
        </TestWrapper>
      );

      const saveButton = screen.getByRole('button', { name: /Änderungen speichern/i });
      expect(saveButton).toBeDisabled();
    });

    it('enables save button when changes are made', () => {
      render(
        <TestWrapper>
          <QuestionEditor
            question={mockQuestion}
            open={true}
            onClose={mockOnClose}
            onSave={mockOnSave}
          />
        </TestWrapper>
      );

      const questionTextInput = screen.getByLabelText(/Fragetext/i);
      fireEvent.change(questionTextInput, { target: { value: 'Updated question' } });

      const saveButton = screen.getByRole('button', { name: /Änderungen speichern/i });
      expect(saveButton).not.toBeDisabled();
    });
  });

  describe('Loading State', () => {
    it('disables all inputs when loading', () => {
      render(
        <TestWrapper>
          <QuestionEditor
            question={mockQuestion}
            open={true}
            onClose={mockOnClose}
            onSave={mockOnSave}
            loading={true}
          />
        </TestWrapper>
      );

      expect(screen.getByLabelText(/Fragetext/i)).toBeDisabled();
      expect(screen.getByLabelText(/Erklärung/i)).toBeDisabled();
      expect(screen.getByRole('button', { name: /Änderungen speichern/i })).toBeDisabled();
    });
  });
});

/**
 * TF-403: multi-answer `multiple_choice` correct-answer editing + validation.
 *
 * Separate, NON-skipped block (the suite above was `describe.skip`ed until
 * TF-775). i18n is mocked in setupTests to return the real German
 * strings, so assertions use the German labels/messages.
 */
describe('QuestionEditor — TF-403 multiple_choice', () => {
  const onClose = jest.fn();
  const onSave = jest.fn().mockResolvedValue(undefined);

  // German values from core/frontend/src/locales/de/translation.json
  const SAVE = 'Änderungen speichern';
  const ERR_SELECT = 'Bitte wähle eine korrekte Antwort';
  const ERR_IN_OPTIONS = 'Die korrekte Antwort muss eine der Optionen sein';

  const multiQuestion: QuestionReview = {
    ...mockQuestion,
    question_type: 'multiple_choice',
    options: ['Bern', 'Genf', 'Zürich'],
    correct_answer: '', // nothing selected yet
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  const renderEditor = (question: QuestionReview) =>
    render(
      <TestWrapper>
        <QuestionEditor question={question} open={true} onClose={onClose} onSave={onSave} />
      </TestWrapper>
    );

  it('blocks save with an error when no correct answer is selected', async () => {
    renderEditor(multiQuestion);

    // Make a change so the Save button enables, without selecting an answer.
    fireEvent.change(screen.getByLabelText(/Fragetext/i), {
      target: { value: 'Welche zwei Städte liegen in der Schweiz?' },
    });
    fireEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() => {
      expect(screen.getByText(ERR_SELECT)).toBeInTheDocument();
    });
    expect(onSave).not.toHaveBeenCalled();
  });

  it('blocks save when a selected answer is not among the options', async () => {
    renderEditor({ ...multiQuestion, correct_answer: '["Paris"]' });

    // Trigger a change to enable Save; the stale "Paris" selection stays invalid.
    fireEvent.change(screen.getByLabelText(/Fragetext/i), {
      target: { value: 'Welche Stadt liegt in der Schweiz?' },
    });
    fireEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() => {
      expect(screen.getByText(ERR_IN_OPTIONS)).toBeInTheDocument();
    });
    expect(onSave).not.toHaveBeenCalled();
  });

  it('toggling a checkbox serializes the selection to a JSON array and saves', async () => {
    renderEditor(multiQuestion);

    // The "Korrekte Antworten" section renders one checkbox per option.
    fireEvent.click(screen.getByRole('checkbox', { name: 'Bern' }));
    fireEvent.click(screen.getByRole('checkbox', { name: 'Zürich' }));
    fireEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith(
        multiQuestion.id,
        expect.objectContaining({ correct_answer: '["Bern","Zürich"]' })
      );
    });
  });

  it('un-checking a selected option removes it from the JSON array', async () => {
    renderEditor({ ...multiQuestion, correct_answer: '["Bern","Zürich"]' });

    fireEvent.click(screen.getByRole('checkbox', { name: 'Bern' })); // uncheck Bern
    fireEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith(
        multiQuestion.id,
        expect.objectContaining({ correct_answer: '["Zürich"]' })
      );
    });
  });
});
