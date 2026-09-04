import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import GenerationTasksBar from '../GenerationTasksBar';
import type { GenerationTaskState } from '../../types';

/**
 * Wiring test for GenerationTasksBar's handleRetry -> translateError() call —
 * one of the three files (alongside useFeatures.ts and ChatInterface.tsx)
 * the RAGExamCreator.errorChain.test.tsx header comment names as a real bug
 * site during TF-671 development. The existing GenerationTasksBar.test.tsx
 * covers rendering/progress/dismiss but never exercises a failed retry.
 */

const mockDismissTask = jest.fn();
const mockRetryTask = jest.fn();
const mockUseGenerationTasks = jest.fn();

jest.mock('../../contexts/GenerationTasksContext', () => ({
  useGenerationTasks: () => mockUseGenerationTasks(),
}));

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn(),
}));

const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <MemoryRouter>
    <ThemeProvider theme={createTheme()}>{children}</ThemeProvider>
  </MemoryRouter>
);

const makeTask = (overrides: Partial<GenerationTaskState>): GenerationTaskState => ({
  taskId: 'task-1',
  status: 'FAILURE',
  progress: 0,
  message: 'HTTP 503: RAG service unavailable',
  topic: 'Test Topic',
  questionCount: 5,
  createdAt: new Date().toISOString(),
  result: null,
  ...overrides,
});

describe('GenerationTasksBar — Retry-Fehler erreichen die UI übersetzt, nie roh', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('zeigt die übersetzte Standardmeldung, wenn der Retry an einem AppError scheitert', async () => {
    const task = makeTask();
    mockRetryTask.mockRejectedValueOnce(new Error('ECONNREFUSED 10.0.0.5:8000'));
    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [],
      completedTasks: [task],
      dismissTask: mockDismissTask,
      retryTask: mockRetryTask,
    });

    render(<GenerationTasksBar />, { wrapper: Wrapper });

    fireEvent.click(screen.getByLabelText('Erneut versuchen'));

    expect(await screen.findByText('Der erneute Versuch ist fehlgeschlagen.')).toBeInTheDocument();
    expect(screen.queryByText(/ECONNREFUSED/)).not.toBeInTheDocument();
  });

  it('räumt den Retry-Fehler nicht weg, während der nächste Retry noch läuft', async () => {
    // Regression guard: retryError is keyed on taskId and only rendered
    // while retryingTaskId is null for that task — a stale error from a
    // previous attempt must not still show once a new retry starts.
    const task = makeTask();
    let resolveSecondRetry: () => void = () => {};
    mockRetryTask
      .mockRejectedValueOnce(new Error('boom'))
      .mockImplementationOnce(
        () => new Promise<void>((resolve) => { resolveSecondRetry = resolve; }),
      );
    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [],
      completedTasks: [task],
      dismissTask: mockDismissTask,
      retryTask: mockRetryTask,
    });

    render(<GenerationTasksBar />, { wrapper: Wrapper });

    fireEvent.click(screen.getByLabelText('Erneut versuchen'));
    expect(await screen.findByText('Der erneute Versuch ist fehlgeschlagen.')).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('Erneut versuchen'));
    await waitFor(() =>
      expect(screen.queryByText('Der erneute Versuch ist fehlgeschlagen.')).not.toBeInTheDocument(),
    );

    resolveSecondRetry();
  });
});
