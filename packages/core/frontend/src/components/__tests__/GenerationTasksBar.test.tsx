import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import GenerationTasksBar from '../GenerationTasksBar';
import type { GenerationTaskState } from '../../types';

// Mock useGenerationTasks
const mockDismissTask = jest.fn();
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
    });

    render(<GenerationTasksBar />, { wrapper: Wrapper });

    fireEvent.click(screen.getByLabelText('Schliessen'));
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
    });

    render(<GenerationTasksBar />, { wrapper: Wrapper });

    expect(screen.getByText('Timeout erreicht')).toBeInTheDocument();
  });

  test('collapses and expands on toggle click', () => {
    const activeTask = makeTask({ status: 'STARTED', progress: 20, topic: 'Toggle Test' });

    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [activeTask],
      completedTasks: [],
      dismissTask: mockDismissTask,
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
