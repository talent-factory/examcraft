import React, {
  createContext,
  useContext,
  useState,
  useRef,
  useEffect,
  useCallback,
} from 'react';
import { useAuth } from './AuthContext';
import i18n from '../i18n';
import { AppError } from '../errors';
import {
  readSessionSnapshot,
  writeSessionSnapshot,
} from '../utils/sessionSnapshot';
import type {
  GenerationTaskState,
  GenerationTasksContextType,
  RAGExamRequest,
} from '../types';

const GenerationTasksContext = createContext<GenerationTasksContextType | undefined>(undefined);

const FLUSH_INTERVAL_MS = 500;
const WS_RECONNECT_MAX_RETRIES = 3;
const WS_RECONNECT_BASE_DELAY_MS = 1000;
const TERMINAL_STATUSES = new Set(['SUCCESS', 'FAILURE', 'REVOKED']);

// TF-608: dismissed tasks survive the reload. Without this, the recently
// completed jobs that `/active-tasks` has included since TF-608 would
// reappear on every page load — exactly the notice the user just closed.
const DISMISSED_TASKS_KEY = 'dismissedGenerationTasks';
const DISMISSED_TASKS_VERSION = 1;
// Caps the snapshot; completed jobs are only recoverable for 30 minutes
// anyway (COMPLETED_TASK_MAX_AGE in the backend).
const DISMISSED_TASKS_MAX = 50;

const readDismissedTaskIds = (): string[] => {
  const stored = readSessionSnapshot<string[]>(DISMISSED_TASKS_KEY, DISMISSED_TASKS_VERSION);
  // `readSessionSnapshot` only version-gates the envelope, not the payload
  // shape — an entry from an incompatible previous build could pass
  // `Array.isArray` while containing non-string elements. Filter defensively
  // so a corrupted entry just fails to un-dismiss a task, instead of silently
  // producing a `string[]` that isn't one.
  return Array.isArray(stored) ? stored.filter((id): id is string => typeof id === 'string') : [];
};

const rememberDismissedTaskId = (taskId: string): void => {
  const next = [taskId, ...readDismissedTaskIds().filter((id) => id !== taskId)].slice(
    0,
    DISMISSED_TASKS_MAX
  );
  writeSessionSnapshot(DISMISSED_TASKS_KEY, DISMISSED_TASKS_VERSION, next);
};

export const GenerationTasksProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, accessToken } = useAuth();
  const [tasks, setTasks] = useState<Record<string, GenerationTaskState>>({});
  // TF-608: lets the recovery effect below read the *current* task state
  // (in particular an already-fetched `result`) without depending on `tasks`
  // itself — depending on it would re-run the recovery effect on every
  // state update it causes, i.e. an infinite loop. Kept in sync by the
  // effect right after this declaration, which always runs before the
  // recovery effect (source order = commit order for same-phase effects).
  const tasksRef = useRef<Record<string, GenerationTaskState>>({});
  const progressRef = useRef<Record<string, Partial<GenerationTaskState>>>({});
  // Synchronous record of which task_ids have reached a terminal state. Updated
  // INSIDE `setTasks` updaters (sync) before the React commit phase, so the
  // sticky-terminal guards in `ws.onmessage`/`ws.onclose` cannot lose a race
  // against the post-render `useEffect` that would mirror full task state.
  // The race scenario: server sends FAILURE, then closes the socket in the
  // same JS turn — `ws.onclose` fires before React re-renders, so a `tasks`-
  // mirror ref would still show pre-FAILURE state. The Set is the minimal
  // sync witness needed to make the guards reliable.
  const terminalTaskIdsRef = useRef<Set<string>>(new Set());
  const wsRef = useRef<Record<string, WebSocket>>({});
  const flushIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Keep `tasksRef` mirroring `tasks` after every commit. Unlike
  // `terminalTaskIdsRef` above, this doesn't need same-turn sync (no
  // WebSocket-callback race to beat) — an ordinary post-commit effect is
  // enough, and it must run before the recovery effect further below, which
  // source order guarantees for same-phase effects.
  useEffect(() => {
    tasksRef.current = tasks;
  }, [tasks]);

  // Flush progress from ref to state periodically
  useEffect(() => {
    flushIntervalRef.current = setInterval(() => {
      const pending = progressRef.current;
      if (Object.keys(pending).length === 0) return;

      setTasks((prev) => {
        const next = { ...prev };
        for (const [taskId, updates] of Object.entries(pending)) {
          if (next[taskId]) {
            next[taskId] = { ...next[taskId], ...updates };
          }
        }
        return next;
      });
      progressRef.current = {};
    }, FLUSH_INTERVAL_MS);

    return () => {
      if (flushIntervalRef.current) clearInterval(flushIntervalRef.current);
    };
  }, []);

  // Connect WebSocket for a task
  const connectWebSocket = useCallback((taskId: string, token: string, retryCount = 0) => {
    if (wsRef.current[taskId]) {
      wsRef.current[taskId].close();
    }

    const apiBaseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    const wsBase = apiBaseUrl.replace(/^http/, 'ws');
    const ws = new WebSocket(`${wsBase}/ws/tasks/${taskId}`);
    wsRef.current[taskId] = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ token }));
    };

    ws.onmessage = (event) => {
      let data: any;
      try {
        data = JSON.parse(event.data);
      } catch (parseErr) {
        console.warn('[GenerationTasks] Failed to parse WebSocket message:', parseErr);
        return;
      }

      // Sticky-terminal guard: once a task has reached SUCCESS/FAILURE/REVOKED,
      // ignore any further messages (eg stale Redis state on reconnect, late
      // PROGRESS from a worker that doesn't know it failed). The Set check is
      // synchronous — no React-render race like a `tasks`-mirror ref would have.
      if (terminalTaskIdsRef.current.has(taskId)) {
        return;
      }

      if (data.status === 'SUCCESS') {
        terminalTaskIdsRef.current.add(taskId);
        setTasks((prev) => ({
          ...prev,
          [taskId]: {
            ...prev[taskId],
            status: 'SUCCESS',
            progress: 100,
            message: data.message || i18n.t('contexts.generationTasks.done'),
            result: data.result,
          },
        }));
        delete progressRef.current[taskId];
      } else if (data.status === 'FAILURE' || data.status === 'REVOKED') {
        terminalTaskIdsRef.current.add(taskId);
        setTasks((prev) => ({
          ...prev,
          [taskId]: {
            ...prev[taskId],
            status: data.status,
            progress: prev[taskId]?.progress ?? 0,
            message: data.error || i18n.t('contexts.generationTasks.errorOccurred'),
            result: null,
          },
        }));
        delete progressRef.current[taskId];
      } else {
        // PROGRESS / PENDING / STARTED / RETRY - buffer in ref
        progressRef.current[taskId] = {
          status: data.status,
          progress: data.progress ?? 0,
          message: data.message,
        };
      }
    };

    ws.onclose = (event) => {
      delete wsRef.current[taskId];

      // Sticky-terminal guard: if the task already reached a terminal state
      // (set sync inside the `ws.onmessage` handler before the `setTasks`
      // call), NEVER reconnect. Reconnecting would re-fetch possibly-stale
      // Redis state and could overwrite the committed terminal status with
      // PROGRESS/PENDING from a stale worker.
      if (terminalTaskIdsRef.current.has(taskId)) {
        return;
      }

      if (event.code !== 1000 && event.code !== 1001 && retryCount < WS_RECONNECT_MAX_RETRIES) {
        const delay = WS_RECONNECT_BASE_DELAY_MS * Math.pow(2, retryCount);
        setTimeout(() => connectWebSocket(taskId, token, retryCount + 1), delay);
      } else if (retryCount >= WS_RECONNECT_MAX_RETRIES) {
        setTasks((prev) => ({
          ...prev,
          [taskId]: prev[taskId] ? { ...prev[taskId], status: 'UNKNOWN' } : prev[taskId],
        }));
      }
    };

    ws.onerror = (event) => {
      console.warn(`[GenerationTasks] WebSocket error for task ${taskId}:`, event);
      // onclose will fire after onerror and handle reconnection
    };
  }, []);

  // Recovery: fetch recoverable tasks on mount when authenticated
  useEffect(() => {
    if (!isAuthenticated || !accessToken) return;

    const recover = async () => {
      try {
        const { loadRAGService } = await import('../utils/componentLoader');
        const RAGService = await loadRAGService();
        if (!RAGService) return;

        const response = await RAGService.getActiveTasks();
        const dismissed = new Set(readDismissedTaskIds());

        const recovered: Record<string, GenerationTaskState> = {};
        // TF-608: tasks that finished during a page navigation are now
        // included as terminal entries since TF-608. There's no WebSocket
        // left for them (the task is done) — their result is fetched via
        // HTTP so the result view stays reachable.
        const terminalTaskIds: string[] = [];
        for (const task of response.tasks) {
          if (dismissed.has(task.task_id)) continue;

          // TF-608 fix: this effect runs not only on mount but again on
          // every `accessToken` change (silent token refresh, see the
          // dependency array below) — mid-session, not only after a reload.
          // Without `tasksRef`, a `result` already loaded via WebSocket or a
          // previous recovery pass would get overwritten here with `null`
          // and would stay unreachable until the (possibly failing) refetch
          // further below.
          const existingResult = tasksRef.current[task.task_id]?.result ?? null;
          recovered[task.task_id] = {
            taskId: task.task_id,
            status: task.status as GenerationTaskState['status'],
            progress: task.progress,
            message: task.message,
            topic: task.topic,
            questionCount: task.question_count,
            createdAt: task.created_at,
            result: existingResult,
          };

          if (TERMINAL_STATUSES.has(task.status)) {
            // Set the sticky-terminal guard up front: a straggling PROGRESS
            // message arriving later from an old connection must not demote
            // an already-finished task.
            terminalTaskIdsRef.current.add(task.task_id);
            // Only refetch if we don't already have the result — saves an
            // unnecessary roundtrip and prevents a failing refetch (Celery
            // result meanwhile expired) from making an already-visible
            // result unreachable.
            if (!existingResult) {
              terminalTaskIds.push(task.task_id);
            }
          } else {
            connectWebSocket(task.task_id, accessToken);
          }
        }

        if (Object.keys(recovered).length > 0) {
          setTasks((prev) => ({ ...prev, ...recovered }));
        }

        // Refetch results one by one. Swallow errors per task: an expired
        // Celery result entry must not drag down the others — the task then
        // simply stays visible without a detail view.
        await Promise.all(
          terminalTaskIds.map(async (taskId) => {
            try {
              const detail = await RAGService.getTaskResult(taskId);
              setTasks((prev) =>
                prev[taskId]
                  ? {
                      ...prev,
                      [taskId]: {
                        ...prev[taskId],
                        result: detail.result ?? null,
                        message: detail.error ?? prev[taskId].message,
                      },
                    }
                  : prev
              );
            } catch (err) {
              console.warn(
                `[GenerationTasks] Failed to recover result for task ${taskId}:`,
                err
              );
            }
          })
        );
      } catch (err) {
        console.error('[GenerationTasks] Failed to recover active tasks:', err);
      }
    };

    recover();

    return () => {
      Object.values(wsRef.current).forEach((ws) => ws.close());
      wsRef.current = {};
    };
  }, [isAuthenticated, accessToken, connectWebSocket]);

  const startGeneration = useCallback(async (request: RAGExamRequest): Promise<string> => {
    const { loadRAGService } = await import('../utils/componentLoader');
    const RAGService = await loadRAGService();
    if (!RAGService) throw new AppError('rag.notAvailableInCore', 'RAGService not available in Core mode');

    const { task_id } = await RAGService.triggerGeneration(request);

    setTasks((prev) => ({
      ...prev,
      [task_id]: {
        taskId: task_id,
        status: 'PENDING',
        progress: 0,
        message: i18n.t('contexts.generationTasks.started'),
        topic: request.topic,
        questionCount: request.question_count,
        createdAt: new Date().toISOString(),
        result: null,
      },
    }));

    if (accessToken) {
      connectWebSocket(task_id, accessToken);
    }

    return task_id;
  }, [accessToken, connectWebSocket]);

  const retryTask = useCallback(async (taskId: string): Promise<string> => {
    const { loadRAGService } = await import('../utils/componentLoader');
    const RAGService = await loadRAGService();
    if (!RAGService) throw new AppError('rag.notAvailableInCore', 'RAGService not available in Core mode');

    const { task_id: newTaskId } = await RAGService.retryGeneration(taskId);

    // Close old WebSocket to prevent resource leak
    if (wsRef.current[taskId]) {
      wsRef.current[taskId].close();
      delete wsRef.current[taskId];
    }

    setTasks((prev) => {
      const oldTask = prev[taskId];
      const next = { ...prev };
      delete next[taskId];
      next[newTaskId] = {
        taskId: newTaskId,
        status: 'PENDING',
        progress: 0,
        message: i18n.t('contexts.generationTasks.retrying'),
        topic: oldTask?.topic ?? null,
        questionCount: oldTask?.questionCount ?? null,
        createdAt: new Date().toISOString(),
        result: null,
      };
      return next;
    });

    if (accessToken) {
      connectWebSocket(newTaskId, accessToken);
    }

    return newTaskId;
  }, [accessToken, connectWebSocket]);

  const dismissTask = useCallback((taskId: string) => {
    rememberDismissedTaskId(taskId);
    setTasks((prev) => {
      const next = { ...prev };
      delete next[taskId];
      return next;
    });
    if (wsRef.current[taskId]) {
      wsRef.current[taskId].close();
      delete wsRef.current[taskId];
    }
  }, []);

  const getTask = useCallback((taskId: string) => tasks[taskId], [tasks]);

  const activeTasks = Object.values(tasks).filter((t) => !TERMINAL_STATUSES.has(t.status));
  const completedTasks = Object.values(tasks).filter((t) => TERMINAL_STATUSES.has(t.status));

  return (
    <GenerationTasksContext.Provider
      value={{ tasks, activeTasks, completedTasks, startGeneration, retryTask, dismissTask, getTask }}
    >
      {children}
    </GenerationTasksContext.Provider>
  );
};

export const useGenerationTasks = (): GenerationTasksContextType => {
  const context = useContext(GenerationTasksContext);
  if (!context) {
    throw new Error('useGenerationTasks must be used within GenerationTasksProvider');
  }
  return context;
};
