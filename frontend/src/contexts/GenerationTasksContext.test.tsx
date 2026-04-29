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

// Mock the dynamic loader so startGeneration / retryTask never reach the network
jest.mock('../utils/componentLoader', () => ({
  loadRAGService: () => Promise.resolve({
    getActiveTasks: () => Promise.resolve({ tasks: [] }),
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
      question_types: ['multiple_choice'],
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
