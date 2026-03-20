import React, {
  createContext,
  useContext,
  useState,
  useRef,
  useEffect,
  useCallback,
} from 'react';
import { useAuth } from './AuthContext';
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

export const GenerationTasksProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, accessToken } = useAuth();
  const [tasks, setTasks] = useState<Record<string, GenerationTaskState>>({});
  const progressRef = useRef<Record<string, Partial<GenerationTaskState>>>({});
  const wsRef = useRef<Record<string, WebSocket>>({});
  const flushIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

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

      if (data.status === 'SUCCESS') {
        setTasks((prev) => ({
          ...prev,
          [taskId]: {
            ...prev[taskId],
            status: 'SUCCESS',
            progress: 100,
            message: data.message || 'Fertig',
            result: data.result,
          },
        }));
        delete progressRef.current[taskId];
      } else if (data.status === 'FAILURE' || data.status === 'REVOKED') {
        setTasks((prev) => ({
          ...prev,
          [taskId]: {
            ...prev[taskId],
            status: data.status,
            progress: prev[taskId]?.progress ?? 0,
            message: data.error || 'Fehler aufgetreten',
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

  // Recovery: fetch active tasks on mount when authenticated
  useEffect(() => {
    if (!isAuthenticated || !accessToken) return;

    const recover = async () => {
      try {
        const { loadRAGService } = await import('../utils/componentLoader');
        const RAGService = await loadRAGService();
        if (!RAGService) return;

        const response = await RAGService.getActiveTasks();

        const recovered: Record<string, GenerationTaskState> = {};
        for (const task of response.tasks) {
          recovered[task.task_id] = {
            taskId: task.task_id,
            status: task.status as GenerationTaskState['status'],
            progress: task.progress,
            message: task.message,
            topic: task.topic,
            questionCount: task.question_count,
            createdAt: task.created_at,
            result: null,
          };
          connectWebSocket(task.task_id, accessToken);
        }

        if (Object.keys(recovered).length > 0) {
          setTasks((prev) => ({ ...prev, ...recovered }));
        }
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
    if (!RAGService) throw new Error('RAGService not available in Core mode');

    const { task_id } = await RAGService.triggerGeneration(request);

    setTasks((prev) => ({
      ...prev,
      [task_id]: {
        taskId: task_id,
        status: 'PENDING',
        progress: 0,
        message: 'Gestartet...',
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

  const dismissTask = useCallback((taskId: string) => {
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
      value={{ tasks, activeTasks, completedTasks, startGeneration, dismissTask, getTask }}
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
