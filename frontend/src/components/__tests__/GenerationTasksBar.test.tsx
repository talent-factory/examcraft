import React from 'react';
import { act } from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import GenerationTasksBar from '../GenerationTasksBar';
import type { GenerationTaskState } from '../../types';

// Mock useGenerationTasks
const mockDismissTask = jest.fn();
const mockRetryTask = jest.fn();
const mockUseGenerationTasks = jest.fn();

jest.mock('../../contexts/GenerationTasksContext', () => ({
  useGenerationTasks: () => mockUseGenerationTasks(),
}));

// Mock useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <MemoryRouter>
    <ThemeProvider theme={createTheme()}>{children}</ThemeProvider>
  </MemoryRouter>
);

const makeTask = (overrides: Partial<GenerationTaskState>): GenerationTaskState => ({
  taskId: 'task-1',
  status: 'PENDING',
  progress: 0,
  message: '',
  topic: 'Test Topic',
  questionCount: 5,
  createdAt: new Date().toISOString(),
  result: null,
  ...overrides,
});

describe('GenerationTasksBar', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders nothing when no tasks', () => {
    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [],
      completedTasks: [],
      dismissTask: mockDismissTask,
      retryTask: mockRetryTask,
    });

    const { container } = render(<GenerationTasksBar />, { wrapper: Wrapper });
    expect(container.firstChild).toBeNull();
  });

  test('shows progress bar and percentage for active tasks', () => {
    const activeTask = makeTask({
      taskId: 'task-active',
      status: 'PROGRESS',
      progress: 42,
      topic: 'Heapsort Algorithmen',
    });

    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [activeTask],
      completedTasks: [],
      dismissTask: mockDismissTask,
      retryTask: mockRetryTask,
    });

    render(<GenerationTasksBar />, { wrapper: Wrapper });

    expect(screen.getByText('Heapsort Algorithmen')).toBeInTheDocument();
    expect(screen.getByText(/42%/)).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  test('shows header with active task count', () => {
    const activeTask = makeTask({ status: 'STARTED', progress: 10 });

    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [activeTask],
      completedTasks: [],
      dismissTask: mockDismissTask,
      retryTask: mockRetryTask,
    });

    render(<GenerationTasksBar />, { wrapper: Wrapper });

    expect(screen.getByText('Generierungen (1 aktiv)')).toBeInTheDocument();
  });

  test('shows completed tasks with checkmark and click hint', () => {
    const completedTask = makeTask({
      taskId: 'task-done',
      status: 'SUCCESS',
      progress: 100,
      topic: 'Datenstrukturen',
    });

    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [],
      completedTasks: [completedTask],
      dismissTask: mockDismissTask,
      retryTask: mockRetryTask,
    });

    render(<GenerationTasksBar />, { wrapper: Wrapper });

    expect(screen.getByText('Datenstrukturen')).toBeInTheDocument();
    expect(screen.getByText('Klicken zum Anzeigen')).toBeInTheDocument();
  });

  test('navigates to /questions/generate on completed task click', () => {
    const completedTask = makeTask({
      taskId: 'task-nav',
      status: 'SUCCESS',
      progress: 100,
      topic: 'Sortieralgorithmen',
    });

    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [],
      completedTasks: [completedTask],
      dismissTask: mockDismissTask,
      retryTask: mockRetryTask,
    });

    render(<GenerationTasksBar />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText('Sortieralgorithmen'));

    expect(mockNavigate).toHaveBeenCalledWith('/questions/generate', {
      state: { viewTaskId: 'task-nav' },
    });
  });

  test('calls dismissTask when close button clicked on completed task', () => {
    const completedTask = makeTask({
      taskId: 'task-dismiss',
      status: 'SUCCESS',
      progress: 100,
      topic: 'Graphen',
    });

    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [],
      completedTasks: [completedTask],
      dismissTask: mockDismissTask,
      retryTask: mockRetryTask,
    });

    render(<GenerationTasksBar />, { wrapper: Wrapper });

    fireEvent.click(screen.getByLabelText('Schließen'));
    expect(mockDismissTask).toHaveBeenCalledWith('task-dismiss');
  });

  test('shows error message for failed tasks', () => {
    const failedTask = makeTask({
      taskId: 'task-fail',
      status: 'FAILURE',
      progress: 30,
      topic: 'Suche',
      message: 'Timeout erreicht',
    });

    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [],
      completedTasks: [failedTask],
      dismissTask: mockDismissTask,
      retryTask: mockRetryTask,
    });

    render(<GenerationTasksBar />, { wrapper: Wrapper });

    expect(screen.getByText('Timeout erreicht')).toBeInTheDocument();
  });

  test('auto-hides after 30s when all tasks are SUCCESS', () => {
    jest.useFakeTimers();
    const successTask = makeTask({ taskId: 'task-ok', status: 'SUCCESS', progress: 100 });

    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [],
      completedTasks: [successTask],
      dismissTask: mockDismissTask,
      retryTask: mockRetryTask,
    });

    render(<GenerationTasksBar />, { wrapper: Wrapper });
    expect(screen.getByText('Test Topic')).toBeInTheDocument();

    act(() => { jest.advanceTimersByTime(30_000); });

    expect(screen.queryByText('Test Topic')).not.toBeInTheDocument();
    jest.useRealTimers();
  });

  test('does NOT auto-hide when a FAILURE task is present', () => {
    jest.useFakeTimers();
    const failedTask = makeTask({
      taskId: 'task-fail',
      status: 'FAILURE',
      topic: 'Fehlgeschlagene Generierung',
      message: 'Verarbeitung fehlgeschlagen',
    });

    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [],
      completedTasks: [failedTask],
      dismissTask: mockDismissTask,
      retryTask: mockRetryTask,
    });

    render(<GenerationTasksBar />, { wrapper: Wrapper });
    expect(screen.getByText('Fehlgeschlagene Generierung')).toBeInTheDocument();

    act(() => { jest.advanceTimersByTime(30_000); });

    // Bar must remain visible — user must dismiss manually
    expect(screen.getByText('Fehlgeschlagene Generierung')).toBeInTheDocument();
    jest.useRealTimers();
  });

  test('does NOT auto-hide when a REVOKED task is present', () => {
    jest.useFakeTimers();
    const revokedTask = makeTask({
      taskId: 'task-rev',
      status: 'REVOKED',
      topic: 'Abgebrochen',
      message: 'Vom Nutzer abgebrochen',
    });

    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [],
      completedTasks: [revokedTask],
      dismissTask: mockDismissTask,
      retryTask: mockRetryTask,
    });

    render(<GenerationTasksBar />, { wrapper: Wrapper });

    act(() => { jest.advanceTimersByTime(30_000); });

    expect(screen.getByText('Abgebrochen')).toBeInTheDocument();
    jest.useRealTimers();
  });

  test('does NOT auto-hide when SUCCESS and FAILURE are mixed', () => {
    jest.useFakeTimers();
    const successTask = makeTask({
      taskId: 'task-ok',
      status: 'SUCCESS',
      progress: 100,
      topic: 'Erfolgreich',
    });
    const failedTask = makeTask({
      taskId: 'task-fail',
      status: 'FAILURE',
      topic: 'Fehlgeschlagen',
      message: 'Boom',
    });

    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [],
      completedTasks: [successTask, failedTask],
      dismissTask: mockDismissTask,
      retryTask: mockRetryTask,
    });

    render(<GenerationTasksBar />, { wrapper: Wrapper });

    act(() => { jest.advanceTimersByTime(30_000); });

    // A single FAILURE in the mix must keep the whole bar visible so the user
    // sees and dismisses the error explicitly.
    expect(screen.getByText('Erfolgreich')).toBeInTheDocument();
    expect(screen.getByText('Fehlgeschlagen')).toBeInTheDocument();
    jest.useRealTimers();
  });

  test('logs a warning when a FAILURE task arrives without a message', () => {
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    const failedTask = makeTask({
      taskId: 'task-silent-fail',
      status: 'FAILURE',
      topic: 'Stiller Fehler',
      message: '',
    });

    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [],
      completedTasks: [failedTask],
      dismissTask: mockDismissTask,
      retryTask: mockRetryTask,
    });

    render(<GenerationTasksBar />, { wrapper: Wrapper });

    expect(warnSpy).toHaveBeenCalledWith(
      '[GenerationTasks] Terminal task has no error message',
      expect.objectContaining({ taskId: 'task-silent-fail', status: 'FAILURE' }),
    );
    warnSpy.mockRestore();
  });

  // TF-506: right was 16, which overlapped the HelpWidget FAB
  // (help/HelpWidget.tsx: right 24 + 56px width = occupies 24-80px from the
  // viewport edge). right: 88 leaves an 8px gap past that FAB.
  test('positions the fixed panel clear of the HelpWidget FAB', () => {
    const activeTask = makeTask({ status: 'STARTED', progress: 10 });

    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [activeTask],
      completedTasks: [],
      dismissTask: mockDismissTask,
      retryTask: mockRetryTask,
    });

    const { container } = render(<GenerationTasksBar />, { wrapper: Wrapper });

    expect(container.firstChild).toHaveStyle({ position: 'fixed', bottom: '16px', right: '88px' });
  });

  test('collapses and expands on toggle click', () => {
    const activeTask = makeTask({ status: 'STARTED', progress: 20, topic: 'Toggle Test' });

    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [activeTask],
      completedTasks: [],
      dismissTask: mockDismissTask,
      retryTask: mockRetryTask,
    });

    render(<GenerationTasksBar />, { wrapper: Wrapper });

    // Topic is visible initially (expanded)
    expect(screen.getByText('Toggle Test')).toBeInTheDocument();

    // Click collapse button
    fireEvent.click(screen.getByLabelText('Einklappen'));

    // After collapse, toggle button should now be "Ausklappen"
    expect(screen.getByLabelText('Ausklappen')).toBeInTheDocument();
  });

  // TF-736: an under-filled generation (fewer questions than requested because
  // the document material ran out) is a SUCCESS that needs the same attention
  // as a failure, and the notice is built from the counts in the user's
  // language instead of showing the backend's German-only text.
  describe('context-limited SUCCESS (TF-736)', () => {
    const limitedMetrics = {
      requested_question_count: 15,
      generated_question_count: 6,
      context_limited: true,
      context_limited_notice: 'BACKEND-TEXT-DARF-NICHT-ERSCHEINEN',
    };

    const makeLimitedTask = (overrides: Partial<GenerationTaskState> = {}) =>
      makeTask({
        taskId: 'task-limited',
        status: 'SUCCESS',
        progress: 100,
        topic: 'Knappes Material',
        questionCount: 15,
        result: { quality_metrics: limitedMetrics } as any,
        ...overrides,
      });

    const mockTasks = (completedTasks: GenerationTaskState[], activeTasks: GenerationTaskState[] = []) =>
      mockUseGenerationTasks.mockReturnValue({
        activeTasks,
        completedTasks,
        dismissTask: mockDismissTask,
        retryTask: mockRetryTask,
      });

    afterEach(() => {
      jest.useRealTimers();
    });

    // Test case 1
    test('stays visible after 31 s when context_limited is true', () => {
      jest.useFakeTimers();
      mockTasks([makeLimitedTask()]);

      render(<GenerationTasksBar />, { wrapper: Wrapper });
      act(() => { jest.advanceTimersByTime(31_000); });

      expect(screen.getByText('Knappes Material')).toBeInTheDocument();
    });

    // Test case 2
    test('still auto-hides after 31 s on a SUCCESS without limitation', () => {
      jest.useFakeTimers();
      mockTasks([
        makeTask({
          taskId: 'task-full',
          status: 'SUCCESS',
          progress: 100,
          topic: 'Genug Material',
          result: {
            quality_metrics: { requested_question_count: 5, generated_question_count: 5 },
          } as any,
        }),
      ]);

      render(<GenerationTasksBar />, { wrapper: Wrapper });
      act(() => { jest.advanceTimersByTime(31_000); });

      expect(screen.queryByText('Genug Material')).not.toBeInTheDocument();
    });

    // Test case 3 (FAILURE unchanged) is covered by
    // 'does NOT auto-hide when a FAILURE task is present' above.

    // Test case 4
    test('stays visible when a limited and a normal SUCCESS are mixed', () => {
      jest.useFakeTimers();
      mockTasks([
        makeTask({ taskId: 'task-ok', status: 'SUCCESS', progress: 100, topic: 'Normal' }),
        makeLimitedTask(),
      ]);

      render(<GenerationTasksBar />, { wrapper: Wrapper });
      act(() => { jest.advanceTimersByTime(31_000); });

      expect(screen.getByText('Normal')).toBeInTheDocument();
      expect(screen.getByText('Knappes Material')).toBeInTheDocument();
    });

    // Test case 5
    test('disappears when the limited task is dismissed', () => {
      mockTasks([makeLimitedTask()]);
      const { rerender } = render(<GenerationTasksBar />, { wrapper: Wrapper });

      fireEvent.click(screen.getByLabelText('Schließen'));
      expect(mockDismissTask).toHaveBeenCalledWith('task-limited');

      // The context drops the dismissed task; the bar then renders nothing.
      mockTasks([]);
      rerender(<GenerationTasksBar />);
      expect(screen.queryByText('Knappes Material')).not.toBeInTheDocument();
      expect(screen.queryByTestId('generation-task-context-limited')).not.toBeInTheDocument();
    });

    // Test case 6
    test('renders the notice from the new keys and the counts, not the backend text', () => {
      mockTasks([makeLimitedTask()]);

      render(<GenerationTasksBar />, { wrapper: Wrapper });

      const notice = screen.getByTestId('generation-task-context-limited');
      expect(notice).toHaveTextContent('Weniger Fragen als angefordert');
      expect(notice).toHaveTextContent(
        'Es konnten nur 6 von 15 angeforderten Fragen erstellt werden'
      );
      expect(notice).toHaveTextContent(
        'Wähle für mehr Fragen zusätzliche oder umfangreichere Dokumente aus.'
      );
      expect(screen.queryByText(/BACKEND-TEXT-DARF-NICHT-ERSCHEINEN/)).not.toBeInTheDocument();
      // The click hint of a normal SUCCESS stays.
      expect(screen.getByText('Klicken zum Anzeigen')).toBeInTheDocument();
    });

    test('decides by the boolean, not by the notice text', () => {
      jest.useFakeTimers();
      mockTasks([
        makeTask({
          taskId: 'task-text-only',
          status: 'SUCCESS',
          progress: 100,
          topic: 'Nur Text',
          result: { quality_metrics: { context_limited_notice: 'irgendwas' } } as any,
        }),
      ]);

      render(<GenerationTasksBar />, { wrapper: Wrapper });
      expect(screen.queryByTestId('generation-task-context-limited')).not.toBeInTheDocument();

      act(() => { jest.advanceTimersByTime(31_000); });
      expect(screen.queryByText('Nur Text')).not.toBeInTheDocument();
    });

    test('uses the job-row counts when the Celery result has expired', () => {
      jest.useFakeTimers();
      mockTasks([
        makeLimitedTask({ result: null, contextLimited: true, generatedQuestionCount: 6 }),
      ]);

      render(<GenerationTasksBar />, { wrapper: Wrapper });

      expect(screen.getByTestId('generation-task-context-limited')).toHaveTextContent(
        'Es konnten nur 6 von 15 angeforderten Fragen erstellt werden'
      );
      act(() => { jest.advanceTimersByTime(31_000); });
      expect(screen.getByText('Knappes Material')).toBeInTheDocument();
    });

    // Recovery after a reload: `/active-tasks` delivers the bare terminal
    // task first, the result follows from a second request. Neither list
    // length changes when it arrives, so the already-running timer must be
    // cancelled by the flag itself.
    test('cancels a running auto-hide timer when the limitation arrives later', () => {
      jest.useFakeTimers();
      mockTasks([makeLimitedTask({ result: null })]);
      const { rerender } = render(<GenerationTasksBar />, { wrapper: Wrapper });

      act(() => { jest.advanceTimersByTime(10_000); });
      mockTasks([makeLimitedTask()]);
      rerender(<GenerationTasksBar />);
      act(() => { jest.advanceTimersByTime(31_000); });

      expect(screen.getByText('Knappes Material')).toBeInTheDocument();
    });

    // Regression: the second recovery roundtrip can land AFTER the 31s
    // auto-hide already fired (slow network, or combined with a token
    // refresh that briefly loses the flag) — the panel must come back, not
    // stay hidden for the rest of the session.
    test('brings the panel back if the limitation arrives after auto-hide already fired', () => {
      jest.useFakeTimers();
      const bareTask = makeTask({
        taskId: 'task-late',
        status: 'SUCCESS',
        progress: 100,
        topic: 'Spät entdeckt',
        questionCount: 15,
        result: null,
      });
      mockTasks([bareTask]);
      const { rerender } = render(<GenerationTasksBar />, { wrapper: Wrapper });

      act(() => { jest.advanceTimersByTime(31_000); });
      expect(screen.queryByText('Spät entdeckt')).not.toBeInTheDocument();

      mockTasks([{ ...bareTask, contextLimited: true, generatedQuestionCount: 6 }]);
      rerender(<GenerationTasksBar />);

      expect(screen.getByText('Spät entdeckt')).toBeInTheDocument();
      expect(screen.getByTestId('generation-task-context-limited')).toHaveTextContent(
        'Es konnten nur 6 von 15 angeforderten Fragen erstellt werden'
      );
    });

    test('renders the title and action without a body when only the boolean is known', () => {
      // e.g. context_limited=true from a live metrics object without a
      // paired count — the degraded-but-safe rendering path.
      mockTasks([
        makeTask({
          taskId: 'task-bool-only',
          status: 'SUCCESS',
          progress: 100,
          topic: 'Nur Flag',
          questionCount: 15,
          result: { quality_metrics: { context_limited: true } } as any,
        }),
      ]);

      render(<GenerationTasksBar />, { wrapper: Wrapper });

      const notice = screen.getByTestId('generation-task-context-limited');
      expect(notice).toHaveTextContent('Weniger Fragen als angefordert');
      expect(notice).not.toHaveTextContent('Es konnten nur');
      expect(notice).toHaveTextContent(
        'Wähle für mehr Fragen zusätzliche oder umfangreichere Dokumente aus.'
      );
    });

    test('renders zero generated questions, not a suppressed body', () => {
      mockTasks([
        makeLimitedTask({
          result: {
            quality_metrics: {
              requested_question_count: 15,
              generated_question_count: 0,
              context_limited: true,
            },
          } as any,
        }),
      ]);

      render(<GenerationTasksBar />, { wrapper: Wrapper });

      expect(screen.getByTestId('generation-task-context-limited')).toHaveTextContent(
        'Es konnten nur 0 von 15 angeforderten Fragen erstellt werden'
      );
    });
  });
});
