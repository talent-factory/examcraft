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

  // TF-358: Wenn die Fragenanzahl ans verfügbare Dokumenten-Material gekoppelt
  // wurde, trägt das Result eine context_limited_notice, die im Erfolgs-Eintrag
  // angezeigt werden muss (zusätzlich zum Klick-Hinweis).
  test('shows context-limited notice on SUCCESS when result carries one', () => {
    const notice =
      'Es konnten nur 3 von 5 angeforderten Fragen erstellt werden, weil die ausgewählten Dokumente zu wenig durchsuchbaren Inhalt enthalten.';
    const cappedTask = makeTask({
      taskId: 'task-capped',
      status: 'SUCCESS',
      progress: 100,
      topic: 'Knappes Material',
      result: { quality_metrics: { context_limited_notice: notice } } as any,
    });

    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [],
      completedTasks: [cappedTask],
      dismissTask: mockDismissTask,
      retryTask: mockRetryTask,
    });

    render(<GenerationTasksBar />, { wrapper: Wrapper });

    expect(screen.getByText('Klicken zum Anzeigen')).toBeInTheDocument();
    expect(screen.getByText(/nur 3 von 5 angeforderten Fragen/)).toBeInTheDocument();
  });

  test('does NOT show a notice on a normal SUCCESS without context_limited_notice', () => {
    const okTask = makeTask({
      taskId: 'task-ok-nonotice',
      status: 'SUCCESS',
      progress: 100,
      topic: 'Genug Material',
      result: { quality_metrics: { total_questions: 5 } } as any,
    });

    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [],
      completedTasks: [okTask],
      dismissTask: mockDismissTask,
      retryTask: mockRetryTask,
    });

    render(<GenerationTasksBar />, { wrapper: Wrapper });

    expect(screen.getByText('Klicken zum Anzeigen')).toBeInTheDocument();
    expect(screen.queryByText(/angeforderten Fragen/)).not.toBeInTheDocument();
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
});
