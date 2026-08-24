import { render, act, waitFor } from '@testing-library/react';
import React from 'react';
import { GenerationTasksProvider, useGenerationTasks } from './GenerationTasksContext';

// Mock the AuthContext to provide a stable token
jest.mock('./AuthContext', () => ({
  useAuth: () => ({ isAuthenticated: true, accessToken: 'test-token' }),
}));

// Mock i18n to bypass translations
jest.mock('../i18n', () => ({
  __esModule: true,
  default: { t: (key: string) => key },
}));

// Mock the dynamic loader so startGeneration / retryTask never reach the network.
// The recovery-facing methods are jest.fn()s so individual tests can re-programme
// them (see the TF-608 block below).
const mockGetActiveTasks = jest.fn(() => Promise.resolve({ tasks: [] as any[] }));
const mockGetTaskResult = jest.fn((_taskId: string) =>
  Promise.resolve({ task_id: _taskId, status: 'SUCCESS', result: null, error: null }),
);

jest.mock('../utils/componentLoader', () => ({
  loadRAGService: () => Promise.resolve({
    getActiveTasks: () => mockGetActiveTasks(),
    getTaskResult: (taskId: string) => mockGetTaskResult(taskId),
    triggerGeneration: () => Promise.resolve({ task_id: 'task-1' }),
    retryGeneration: () => Promise.resolve({ task_id: 'task-2' }),
  }),
}));

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  url: string;
  readyState = 0;
  onopen: ((ev: Event) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  sentMessages: string[] = [];

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send(data: string) {
    this.sentMessages.push(data);
  }

  close() {
    this.readyState = 3;
  }

  // Test helpers
  emitOpen() {
    this.readyState = 1;
    this.onopen?.(new Event('open'));
  }
  emitMessage(payload: object) {
    this.onmessage?.({ data: JSON.stringify(payload) } as MessageEvent);
  }
  emitClose(code: number) {
    this.readyState = 3;
    this.onclose?.({ code } as CloseEvent);
  }
}

beforeEach(() => {
  MockWebSocket.instances = [];
  (global as any).WebSocket = MockWebSocket;
  window.sessionStorage.clear();
  mockGetActiveTasks.mockReset();
  mockGetActiveTasks.mockResolvedValue({ tasks: [] });
  mockGetTaskResult.mockReset();
  mockGetTaskResult.mockImplementation((taskId: string) =>
    Promise.resolve({ task_id: taskId, status: 'SUCCESS', result: null, error: null }),
  );
});

// Helper component exposes context to tests
let captured: ReturnType<typeof useGenerationTasks> | null = null;
const Capture: React.FC = () => {
  captured = useGenerationTasks();
  return null;
};

const renderProvider = () =>
  render(
    <GenerationTasksProvider>
      <Capture />
    </GenerationTasksProvider>,
  );

const startTaskAndGetWs = async (): Promise<MockWebSocket> => {
  await act(async () => {
    await captured!.startGeneration({
      topic: 'T',
      question_count: 1,
      question_types: ['single_choice'],
      difficulty: 'medium',
      language: 'de',
      document_ids: null,
      context_chunks_per_question: 3,
      prompt_config: null,
    } as any);
  });
  await waitFor(() => expect(MockWebSocket.instances.length).toBeGreaterThan(0));
  return MockWebSocket.instances[MockWebSocket.instances.length - 1];
};

describe('GenerationTasksProvider — sticky terminal state (TF-328)', () => {
  it('does NOT reconnect WebSocket when task is already FAILURE', async () => {
    renderProvider();
    const ws = await startTaskAndGetWs();
    ws.emitOpen();

    // Server sends FAILURE
    act(() => {
      ws.emitMessage({ status: 'FAILURE', progress: 0, error: 'boom' });
    });
    await waitFor(() => expect(captured!.getTask('task-1')?.status).toBe('FAILURE'));

    // Connection drops abnormally (NOT code 1000/1001) — without the fix
    // this would schedule a reconnect after 1 s.
    act(() => {
      ws.emitClose(1006);
    });

    // Wait long enough for the legacy 1 s reconnect delay to fire if buggy
    await new Promise((r) => setTimeout(r, 1500));

    // Only the original WS instance should exist — no reconnect attempted.
    expect(MockWebSocket.instances.length).toBe(1);
    expect(captured!.getTask('task-1')?.status).toBe('FAILURE');
  });

  it('does NOT reconnect WebSocket when task is already REVOKED', async () => {
    renderProvider();
    const ws = await startTaskAndGetWs();
    ws.emitOpen();

    act(() => {
      ws.emitMessage({ status: 'REVOKED', progress: 0, error: 'cancelled' });
    });
    await waitFor(() => expect(captured!.getTask('task-1')?.status).toBe('REVOKED'));

    act(() => {
      ws.emitClose(1006);
    });
    await new Promise((r) => setTimeout(r, 1500));

    expect(MockWebSocket.instances.length).toBe(1);
    expect(captured!.getTask('task-1')?.status).toBe('REVOKED');
  });

  it('ignores PROGRESS messages once task has reached FAILURE', async () => {
    renderProvider();
    const ws = await startTaskAndGetWs();
    ws.emitOpen();

    act(() => {
      ws.emitMessage({ status: 'FAILURE', progress: 0, error: 'boom' });
    });
    await waitFor(() => expect(captured!.getTask('task-1')?.status).toBe('FAILURE'));

    // Server (somehow — eg stale connection) sends a late PROGRESS update.
    act(() => {
      ws.emitMessage({ status: 'PROGRESS', progress: 42, message: 'still going' });
    });

    // Wait past the 500 ms flush interval
    await new Promise((r) => setTimeout(r, 600));

    // Status must remain FAILURE, progress must NOT advance to 42.
    expect(captured!.getTask('task-1')?.status).toBe('FAILURE');
    expect(captured!.getTask('task-1')?.progress).toBe(0);
  });

  it('still reconnects on abnormal close when task is non-terminal', async () => {
    renderProvider();
    const ws = await startTaskAndGetWs();
    ws.emitOpen();

    // Task is still PENDING — abnormal close should trigger reconnect.
    act(() => {
      ws.emitClose(1006);
    });

    await waitFor(
      () => expect(MockWebSocket.instances.length).toBe(2),
      { timeout: 3000 },
    );
  });
});

describe('GenerationTasksProvider — recovery of completed tasks (TF-608)', () => {
  const EXAM_RESULT = { exam_id: 'exam-9', questions: [{ question_text: 'Q?' }] };

  const completedTask = (taskId: string, status = 'SUCCESS') => ({
    task_id: taskId,
    status,
    progress: status === 'SUCCESS' ? 100 : 0,
    message: null,
    created_at: new Date().toISOString(),
    topic: 'Heapsort',
    question_count: 5,
  });

  it('pulls the result for a task that finished while the page was away', async () => {
    mockGetActiveTasks.mockResolvedValue({ tasks: [completedTask('task-done')] });
    mockGetTaskResult.mockResolvedValue({
      task_id: 'task-done',
      status: 'SUCCESS',
      result: EXAM_RESULT,
      error: null,
    });

    renderProvider();

    await waitFor(() => expect(captured!.getTask('task-done')?.result).toEqual(EXAM_RESULT));
    expect(captured!.completedTasks).toHaveLength(1);
    expect(mockGetTaskResult).toHaveBeenCalledWith('task-done');
  });

  it('opens no WebSocket for an already-terminal task', async () => {
    mockGetActiveTasks.mockResolvedValue({ tasks: [completedTask('task-done')] });

    renderProvider();

    await waitFor(() => expect(captured!.getTask('task-done')).toBeDefined());
    // The task is done — a connection for it would just be dead weight, and
    // an expired Redis entry could even demote it back to PENDING.
    expect(MockWebSocket.instances).toHaveLength(0);
  });

  it('still connects a WebSocket for a task that is still running', async () => {
    mockGetActiveTasks.mockResolvedValue({
      tasks: [{ ...completedTask('task-running'), status: 'PROGRESS', progress: 40 }],
    });

    renderProvider();

    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));
    expect(mockGetTaskResult).not.toHaveBeenCalled();
  });

  it('keeps a task visible when its result can no longer be fetched', async () => {
    mockGetActiveTasks.mockResolvedValue({ tasks: [completedTask('task-expired')] });
    mockGetTaskResult.mockRejectedValue(new Error('HTTP 404'));
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});

    renderProvider();

    await waitFor(() => expect(captured!.getTask('task-expired')?.status).toBe('SUCCESS'));
    expect(captured!.getTask('task-expired')?.result).toBeNull();
    expect(warn).toHaveBeenCalled();
    warn.mockRestore();
  });

  it('surfaces the error message of a recovered FAILURE task', async () => {
    mockGetActiveTasks.mockResolvedValue({ tasks: [completedTask('task-failed', 'FAILURE')] });
    mockGetTaskResult.mockResolvedValue({
      task_id: 'task-failed',
      status: 'FAILURE',
      result: null,
      error: 'Claude timeout',
    });

    renderProvider();

    await waitFor(() =>
      expect(captured!.getTask('task-failed')?.message).toBe('Claude timeout'),
    );
  });

  it('does not resurrect a task the user dismissed before the reload', async () => {
    mockGetActiveTasks.mockResolvedValue({ tasks: [completedTask('task-done')] });
    mockGetTaskResult.mockResolvedValue({
      task_id: 'task-done',
      status: 'SUCCESS',
      result: EXAM_RESULT,
      error: null,
    });

    const first = renderProvider();
    await waitFor(() => expect(captured!.getTask('task-done')?.result).toEqual(EXAM_RESULT));

    act(() => {
      captured!.dismissTask('task-done');
    });
    expect(captured!.getTask('task-done')).toBeUndefined();

    // Simulate a reload: new provider, same sessionStorage.
    first.unmount();
    mockGetTaskResult.mockClear();
    renderProvider();

    await waitFor(() => expect(mockGetActiveTasks).toHaveBeenCalledTimes(2));
    expect(captured!.getTask('task-done')).toBeUndefined();
    expect(mockGetTaskResult).not.toHaveBeenCalled();
  });
});
