# Parallel Question Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable multiple concurrent question generations with progress bars that persist across page navigation and browser refresh.

**Architecture:** React Context for global frontend state + backend recovery endpoint querying `QuestionGenerationJob`. WebSocket connections managed per-task in the context. Celery task writes terminal status to DB.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Celery, Redis, React 18, TypeScript, Material UI, Tailwind CSS

**Spec:** `docs/superpowers/specs/2026-03-19-parallel-question-generation-design.md`

---

### Task 1: Extend QuestionGenerationJob Model

**Files:**
- Modify: `packages/core/backend/models/question_generation_job.py`
- Create: `packages/core/backend/alembic/versions/xxxx_add_job_metadata_fields.py` (via autogenerate)
- Test: `packages/core/backend/tests/test_question_generation_job.py`

- [ ] **Step 1: Write failing test for new columns**

Add to `packages/core/backend/tests/test_question_generation_job.py`:

```python
def test_question_generation_job_has_metadata_columns():
    """New columns for parallel generation display and recovery."""
    columns = {c.name for c in QuestionGenerationJob.__table__.columns}
    assert "topic" in columns
    assert "question_count" in columns
    assert "status" in columns


def test_question_generation_job_status_default():
    """Status defaults to PENDING."""
    job = QuestionGenerationJob(task_id="test-123", user_id=1)
    assert job.status == "PENDING"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/core/backend && python -m pytest tests/test_question_generation_job.py -v -k "metadata_columns or status_default"`
Expected: FAIL

- [ ] **Step 3: Add new columns to model**

In `packages/core/backend/models/question_generation_job.py`, add after line 22:

```python
topic = Column(String, nullable=True)
question_count = Column(Integer, nullable=True)
status = Column(String, default="PENDING", server_default="PENDING", nullable=False)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/core/backend && python -m pytest tests/test_question_generation_job.py -v`
Expected: PASS

- [ ] **Step 5: Generate Alembic migration**

Run: `cd packages/core/backend && alembic revision --autogenerate -m "add topic, question_count, status to question_generation_jobs"`

Verify the generated migration adds the three columns with correct types and defaults.

- [ ] **Step 6: Apply migration**

Run: `cd packages/core/backend && alembic upgrade head`

- [ ] **Step 7: Commit**

```bash
git add packages/core/backend/models/question_generation_job.py packages/core/backend/alembic/versions/ packages/core/backend/tests/test_question_generation_job.py
git commit -m "feat: add topic, question_count, status columns to QuestionGenerationJob"
```

---

### Task 2: Update generate-exam Endpoint to Populate New Fields

**Files:**
- Modify: `packages/core/backend/api/rag_exams.py:207-210`
- Test: `packages/core/backend/tests/test_rag_api.py`

- [ ] **Step 1: Write failing test**

Add to `packages/core/backend/tests/test_rag_api.py`:

```python
def test_generate_exam_populates_job_metadata(mock_db, mock_user, mock_celery):
    """Job record should include topic and question_count for recovery."""
    # After calling the endpoint, inspect the QuestionGenerationJob that was added to db
    added_job = mock_db.add.call_args[0][0]
    assert added_job.topic == "Heapsort"
    assert added_job.question_count == 5
    assert added_job.status == "PENDING"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/core/backend && python -m pytest tests/test_rag_api.py -v -k "populates_job_metadata"`
Expected: FAIL (job has no topic/question_count attributes set)

- [ ] **Step 3: Update job creation in rag_exams.py**

At `packages/core/backend/api/rag_exams.py:208`, change:

```python
# Before:
job = QuestionGenerationJob(task_id=task_id, user_id=current_user.id)

# After:
job = QuestionGenerationJob(
    task_id=task_id,
    user_id=current_user.id,
    topic=request.topic,
    question_count=request.question_count,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/core/backend && python -m pytest tests/test_rag_api.py -v -k "populates_job_metadata"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/core/backend/api/rag_exams.py packages/core/backend/tests/test_rag_api.py
git commit -m "feat: populate topic and question_count on QuestionGenerationJob at dispatch"
```

---

### Task 3: Update Celery Task to Write Terminal Status

**Files:**
- Modify: `packages/core/backend/tasks/question_tasks.py:206-215`
- Test: `packages/core/backend/tests/test_question_tasks.py`

- [ ] **Step 1: Write failing test**

Add to `packages/core/backend/tests/test_question_tasks.py`:

```python
from unittest.mock import patch, MagicMock
from tasks.question_tasks import _update_job_status


def test_update_job_status_sets_success():
    """_update_job_status should set job.status to SUCCESS and commit."""
    with patch("tasks.question_tasks.SessionLocal") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_job = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_job

        _update_job_status("test-task-id", "SUCCESS")

        assert mock_job.status == "SUCCESS"
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()


def test_update_job_status_sets_failure():
    """_update_job_status should set job.status to FAILURE and commit."""
    with patch("tasks.question_tasks.SessionLocal") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_job = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_job

        _update_job_status("test-task-id", "FAILURE")

        assert mock_job.status == "FAILURE"
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()


def test_update_job_status_handles_missing_job():
    """_update_job_status should not crash if job not found."""
    with patch("tasks.question_tasks.SessionLocal") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        _update_job_status("nonexistent-task", "SUCCESS")

        mock_session.commit.assert_not_called()
        mock_session.close.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/core/backend && python -m pytest tests/test_question_tasks.py -v -k "job_status"`
Expected: FAIL

- [ ] **Step 3: Add status update to task**

In `packages/core/backend/tasks/question_tasks.py`, add a helper function and wrap the return/except:

```python
def _update_job_status(task_id: str, status: str) -> None:
    """Update QuestionGenerationJob.status to terminal state."""
    from database import SessionLocal
    session = SessionLocal()
    try:
        job = session.query(QuestionGenerationJob).filter_by(task_id=task_id).first()
        if job:
            job.status = status
            session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to update job status for {task_id}: {e}")
    finally:
        session.close()
```

Then at the end of `generate_questions_task`, before the return statement (line ~206):

```python
_update_job_status(self.request.id, "SUCCESS")
```

And in the task's exception handler, add:

```python
_update_job_status(self.request.id, "FAILURE")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/core/backend && python -m pytest tests/test_question_tasks.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/core/backend/tasks/question_tasks.py packages/core/backend/tests/test_question_tasks.py
git commit -m "feat: update QuestionGenerationJob status on task completion/failure"
```

---

### Task 4: New GET /api/v1/rag/active-tasks Endpoint

**Files:**
- Modify: `packages/core/backend/api/rag_exams.py`
- Create: `packages/core/backend/schemas/active_tasks.py`
- Test: `packages/core/backend/tests/test_active_tasks.py`

- [ ] **Step 1: Create response schema**

Create `packages/core/backend/schemas/active_tasks.py`:

```python
"""Schemas for active generation task recovery."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ActiveTaskInfo(BaseModel):
    task_id: str
    status: str
    progress: int = Field(ge=0, le=100, default=0)
    message: Optional[str] = None
    created_at: datetime
    topic: Optional[str] = None
    question_count: Optional[int] = None


class ActiveTasksResponse(BaseModel):
    tasks: List[ActiveTaskInfo]
```

- [ ] **Step 2: Write failing test for endpoint**

Create `packages/core/backend/tests/test_active_tasks.py`:

```python
"""Tests for GET /api/v1/rag/active-tasks endpoint."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


def test_active_tasks_returns_pending_jobs(mock_db, mock_user):
    """Should return jobs with non-terminal status within 2h."""
    # Setup: create mock jobs with PENDING and SUCCESS status
    pending_job = MagicMock(
        task_id="task-1", status="PENDING", topic="Heapsort",
        question_count=5, created_at=datetime.now(UTC)
    )
    success_job = MagicMock(
        task_id="task-2", status="SUCCESS", topic="Sorting",
        question_count=3, created_at=datetime.now(UTC)
    )
    mock_db.query.return_value.filter.return_value.all.return_value = [pending_job]

    # Call endpoint
    # Assert only pending_job is returned
    # Assert SUCCESS job is filtered out


def test_active_tasks_excludes_old_jobs(mock_db, mock_user):
    """Jobs older than 2 hours should be excluded."""
    old_job = MagicMock(
        task_id="task-old", status="PENDING",
        created_at=datetime.now(UTC) - timedelta(hours=3)
    )
    # Assert old_job is not returned


def test_active_tasks_fetches_celery_progress(mock_db, mock_user):
    """Progress and message should come from Celery AsyncResult."""
    with patch("celery.result.AsyncResult") as mock_result:
        mock_result.return_value.state = "PROGRESS"
        mock_result.return_value.info = {"current": 3, "total": 7, "message": "Frage 3/5"}
        # Assert response includes progress and message from Celery


def test_active_tasks_celery_unavailable_returns_defaults(mock_db, mock_user):
    """If Celery state unavailable, return progress=0, message=null."""
    with patch("celery.result.AsyncResult", side_effect=Exception("Redis down")):
        # Assert response has progress=0, message=None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd packages/core/backend && python -m pytest tests/test_active_tasks.py -v`
Expected: FAIL (endpoint doesn't exist)

- [ ] **Step 4: Implement the endpoint**

Add to `packages/core/backend/api/rag_exams.py`:

```python
from datetime import UTC, datetime, timedelta
from celery.result import AsyncResult
from schemas.active_tasks import ActiveTaskInfo, ActiveTasksResponse

TERMINAL_STATUSES = {"SUCCESS", "FAILURE", "REVOKED"}
ACTIVE_TASK_MAX_AGE = timedelta(hours=2)


@router.get("/active-tasks", response_model=ActiveTasksResponse)
async def get_active_tasks(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all active (non-terminal) generation tasks for the current user."""
    # QuestionGenerationJob.created_at is naive DateTime — use naive cutoff to match
    cutoff = datetime.utcnow() - ACTIVE_TASK_MAX_AGE
    jobs = (
        db.query(QuestionGenerationJob)
        .filter(
            QuestionGenerationJob.user_id == current_user.id,
            QuestionGenerationJob.status.notin_(TERMINAL_STATUSES),
            QuestionGenerationJob.created_at > cutoff,
        )
        .all()
    )

    tasks = []
    for job in jobs:
        progress = 0
        message = None
        try:
            result = AsyncResult(job.task_id)
            if result.state == "PROGRESS" and isinstance(result.info, dict):
                current = result.info.get("current", 0)
                total = result.info.get("total", 1)
                progress = int((current / max(total, 1)) * 100)
                message = result.info.get("message")
            elif result.state == "STARTED":
                progress = 0
                message = "Gestartet..."
        except Exception:
            pass  # Return defaults: progress=0, message=None

        tasks.append(ActiveTaskInfo(
            task_id=job.task_id,
            status=job.status,
            progress=progress,
            message=message,
            created_at=job.created_at,
            topic=job.topic,
            question_count=job.question_count,
        ))

    return ActiveTasksResponse(tasks=tasks)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd packages/core/backend && python -m pytest tests/test_active_tasks.py -v`
Expected: PASS

- [ ] **Step 6: Run all backend tests**

Run: `cd packages/core/backend && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add packages/core/backend/schemas/active_tasks.py packages/core/backend/api/rag_exams.py packages/core/backend/tests/test_active_tasks.py
git commit -m "feat: add GET /api/v1/rag/active-tasks endpoint for task recovery"
```

---

### Task 5: Frontend TypeScript Types for Generation Tasks

**Files:**
- Modify: `packages/core/frontend/src/types/document.ts`
- No test file needed (type-only changes, checked by TypeScript compiler)

- [ ] **Step 1: Add types**

Add to `packages/core/frontend/src/types/document.ts`:

```typescript
/** State of a single generation task tracked by GenerationTasksContext */
export interface GenerationTaskState {
  taskId: string;
  status: 'PENDING' | 'STARTED' | 'PROGRESS' | 'SUCCESS' | 'FAILURE' | 'REVOKED' | 'RETRY' | 'UNKNOWN';
  progress: number;
  message: string | null;
  topic: string | null;
  questionCount: number | null;
  createdAt: string;
  result: RAGExamResponse | null;
}

/** Response from GET /api/v1/rag/active-tasks */
export interface ActiveTaskInfo {
  task_id: string;
  status: string;
  progress: number;
  message: string | null;
  created_at: string;
  topic: string | null;
  question_count: number | null;
}

export interface ActiveTasksResponse {
  tasks: ActiveTaskInfo[];
}

/** Context value exposed by GenerationTasksContext */
export interface GenerationTasksContextType {
  tasks: Record<string, GenerationTaskState>;
  activeTasks: GenerationTaskState[];
  completedTasks: GenerationTaskState[];
  startGeneration: (request: RAGExamRequest) => Promise<string>;
  dismissTask: (taskId: string) => void;
  getTask: (taskId: string) => GenerationTaskState | undefined;
}
```

- [ ] **Step 2: Verify types are auto-exported**

`packages/core/frontend/src/types/index.ts` already uses `export * from './document'`, so the new types are automatically re-exported. No changes needed to `index.ts`.

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd packages/core/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add packages/core/frontend/src/types/document.ts
git commit -m "feat: add TypeScript types for parallel generation task tracking"
```

---

### Task 6: RAGService Refactoring - triggerGeneration

**Files:**
- Modify: `packages/premium/frontend/src/services/RAGService.ts:32-99`
- Test: `packages/premium/frontend/src/services/__tests__/RAGService.test.ts`

- [ ] **Step 1: Write test for triggerGeneration**

Create `packages/premium/frontend/src/services/__tests__/RAGService.test.ts`:

```typescript
import RAGService from '../RAGService';

// Mock fetch
global.fetch = jest.fn();

describe('RAGService.triggerGeneration', () => {
  it('should POST to generate-exam and return task_id', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ task_id: 'test-uuid', message: 'Started' }),
    });

    const result = await RAGService.triggerGeneration({
      topic: 'Heapsort',
      question_count: 5,
      question_types: ['multiple_choice'],
      difficulty: 'medium',
      language: 'de',
      context_chunks_per_question: 3,
    });

    expect(result.task_id).toBe('test-uuid');
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/rag/generate-exam'),
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('should throw on API error', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({ detail: 'Queue unavailable' }),
    });

    await expect(RAGService.triggerGeneration({} as any)).rejects.toThrow();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/premium/frontend && npx jest --testPathPattern=RAGService.test`
Expected: FAIL (triggerGeneration doesn't exist)

- [ ] **Step 3a: Add loadRAGService to componentLoader**

In `packages/core/frontend/src/utils/componentLoader.tsx`, add a service loader that follows the existing component loader pattern:

```typescript
/**
 * Loads the premium RAGService class for use by GenerationTasksContext.
 * Unlike component loaders (which return React.lazy components), this returns the service class directly.
 */
export const loadRAGService = async () => {
  try {
    const module = await import(
      /* webpackChunkName: "rag-service" */
      '@premium/services/RAGService'
    );
    return module.default;
  } catch {
    // Fallback: core stub has no RAGService
    return null;
  }
};
```

Check the existing import aliases in `tsconfig.json` / `craco.config.js` to verify the `@premium` alias is available. If not, use the relative path: `../../../../premium/frontend/src/services/RAGService`.

- [ ] **Step 3b: Add triggerGeneration method to RAGService**

In `packages/premium/frontend/src/services/RAGService.ts`, add a new method (keep `generateRAGExam` for now, mark deprecated):

```typescript
/**
 * Triggers question generation without WebSocket tracking.
 * Returns immediately with task_id. WebSocket management handled by GenerationTasksContext.
 */
static async triggerGeneration(request: RAGExamRequest): Promise<{ task_id: string; message: string }> {
  const token = localStorage.getItem('examcraft_access_token');
  const response = await fetch(`${API_BASE}/api/v1/rag/generate-exam`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Generation failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}
```

Also add a static method for fetching active tasks:

```typescript
static async getActiveTasks(): Promise<ActiveTasksResponse> {
  const token = localStorage.getItem('examcraft_access_token');
  const response = await fetch(`${API_BASE}/api/v1/rag/active-tasks`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch active tasks: HTTP ${response.status}`);
  }

  return response.json();
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/premium/frontend && npx jest --testPathPattern=RAGService.test`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/premium/frontend/src/services/RAGService.ts packages/premium/frontend/src/services/__tests__/RAGService.test.ts packages/core/frontend/src/utils/componentLoader.tsx
git commit -m "feat: add triggerGeneration, getActiveTasks to RAGService and loadRAGService to componentLoader"
```

---

### Task 7: GenerationTasksContext

**Files:**
- Create: `packages/core/frontend/src/contexts/GenerationTasksContext.tsx`
- Test: `packages/core/frontend/src/contexts/__tests__/GenerationTasksContext.test.tsx`

- [ ] **Step 1: Write tests for context**

Create `packages/core/frontend/src/contexts/__tests__/GenerationTasksContext.test.tsx`:

```typescript
import React from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import { GenerationTasksProvider, useGenerationTasks } from '../GenerationTasksContext';
import { AuthProvider } from '../AuthContext';
import { MemoryRouter } from 'react-router-dom';

// Mock RAGService
jest.mock('../../utils/componentLoader', () => ({
  // Mock the dynamic import of premium RAGService
}));

const TestConsumer: React.FC = () => {
  const { activeTasks, tasks } = useGenerationTasks();
  return (
    <div>
      <span data-testid="active-count">{activeTasks.length}</span>
      <span data-testid="total-count">{Object.keys(tasks).length}</span>
    </div>
  );
};

describe('GenerationTasksContext', () => {
  it('provides empty state initially', async () => {
    render(
      <MemoryRouter>
        <GenerationTasksProvider>
          <TestConsumer />
        </GenerationTasksProvider>
      </MemoryRouter>
    );

    expect(screen.getByTestId('active-count')).toHaveTextContent('0');
    expect(screen.getByTestId('total-count')).toHaveTextContent('0');
  });

  it('recovers active tasks on mount when authenticated', async () => {
    // Mock getActiveTasks to return one active task
    // Verify it appears in activeTasks
  });

  it('opens WebSocket for recovered tasks', async () => {
    // Mock WebSocket, verify connection opened for each recovered task
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/core/frontend && npx react-scripts test --testPathPattern=GenerationTasksContext --watchAll=false`
Expected: FAIL (file doesn't exist)

- [ ] **Step 3: Implement GenerationTasksContext**

Create `packages/core/frontend/src/contexts/GenerationTasksContext.tsx`:

```typescript
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
  ActiveTaskInfo,
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
  const flushIntervalRef = useRef<NodeJS.Timer | null>(null);

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
    // Close existing connection if any
    if (wsRef.current[taskId]) {
      wsRef.current[taskId].close();
    }

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsBase = `${wsProtocol}//${window.location.host}`;
    const ws = new WebSocket(`${wsBase}/ws/tasks/${taskId}`);
    wsRef.current[taskId] = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ token }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.status === 'SUCCESS') {
        // Immediately flush terminal state (don't wait for interval)
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
        // PROGRESS / PENDING / STARTED - buffer in ref
        progressRef.current[taskId] = {
          status: data.status,
          progress: data.progress ?? 0,
          message: data.message,
        };
      }
    };

    ws.onclose = (event) => {
      delete wsRef.current[taskId];
      // Auto-reconnect if not a clean close and task isn't terminal
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

    ws.onerror = () => {
      // onclose will fire after onerror, handling reconnect
    };
  }, []);

  // Recovery: fetch active tasks on mount when authenticated
  useEffect(() => {
    if (!isAuthenticated || !accessToken) return;

    const recover = async () => {
      try {
        // Dynamic import to handle premium/core split
        const { loadRAGService } = await import('../utils/componentLoader');
        const RAGService = await loadRAGService();
        if (!RAGService) return; // Core mode - no premium RAGService available

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
      } catch {
        // Silent degradation - will retry on next mount/navigation
      }
    };

    recover();

    // Cleanup WebSockets on unmount
    return () => {
      Object.values(wsRef.current).forEach((ws) => ws.close());
      wsRef.current = {};
    };
  }, [isAuthenticated, accessToken, connectWebSocket]);

  // Start a new generation
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

  const activeTasks = Object.values(tasks).filter((t) => !TERMINAL_STATUSES.has(t.status) && t.status !== 'UNKNOWN');
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
```

**Note to implementer:** The `loadRAGService` function must be added to `packages/core/frontend/src/utils/componentLoader.tsx` as part of Task 6. It follows the existing `loadRAGExamCreator` pattern but returns a service class instead of a React component. See Task 6 Step 3a for the implementation.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/core/frontend && npx react-scripts test --testPathPattern=GenerationTasksContext --watchAll=false`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/core/frontend/src/contexts/GenerationTasksContext.tsx packages/core/frontend/src/contexts/__tests__/GenerationTasksContext.test.tsx
git commit -m "feat: add GenerationTasksContext for parallel generation state management"
```

---

### Task 8: Wire GenerationTasksContext into App

**Files:**
- Modify: `packages/core/frontend/src/AppWithAuth.tsx:55-56`

- [ ] **Step 1: Add provider to AppWithAuth**

In `packages/core/frontend/src/AppWithAuth.tsx`, add import and wrap `BrowserRouter`:

```typescript
import { GenerationTasksProvider } from './contexts/GenerationTasksContext';
```

At line 55 (`<AuthProvider>`) and line 56 (`<BrowserRouter>`), wrap the BrowserRouter with GenerationTasksProvider:

```typescript
// Before:
<AuthProvider>
  <BrowserRouter>

// After:
<AuthProvider>
  <GenerationTasksProvider>
    <BrowserRouter>
```

And add the closing tag before `</AuthProvider>`:

```typescript
// Before:
  </BrowserRouter>
</AuthProvider>

// After:
    </BrowserRouter>
  </GenerationTasksProvider>
</AuthProvider>
```

- [ ] **Step 2: Verify app compiles**

Run: `cd packages/core/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add packages/core/frontend/src/AppWithAuth.tsx
git commit -m "feat: wire GenerationTasksContext into app provider tree"
```

---

### Task 9: GenerationTasksBar Global Component

**Files:**
- Create: `packages/core/frontend/src/components/GenerationTasksBar.tsx`
- Test: `packages/core/frontend/src/components/__tests__/GenerationTasksBar.test.tsx`

- [ ] **Step 1: Write tests**

Create `packages/core/frontend/src/components/__tests__/GenerationTasksBar.test.tsx`:

```typescript
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import GenerationTasksBar from '../GenerationTasksBar';

const theme = createTheme();

// Mock useGenerationTasks
const mockDismiss = jest.fn();
const mockNavigate = jest.fn();
jest.mock('../../contexts/GenerationTasksContext', () => ({
  useGenerationTasks: jest.fn(),
}));
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

import { useGenerationTasks } from '../../contexts/GenerationTasksContext';
const mockUseGenerationTasks = useGenerationTasks as jest.Mock;

const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <MemoryRouter>
    <ThemeProvider theme={theme}>{children}</ThemeProvider>
  </MemoryRouter>
);

describe('GenerationTasksBar', () => {
  it('renders nothing when no tasks', () => {
    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [],
      completedTasks: [],
      dismissTask: mockDismiss,
    });
    const { container } = render(<GenerationTasksBar />, { wrapper: Wrapper });
    expect(container.firstChild).toBeNull();
  });

  it('shows progress for active tasks', () => {
    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [{
        taskId: 't1', status: 'PROGRESS', progress: 45,
        message: 'Frage 3/5', topic: 'Heapsort', questionCount: 5,
      }],
      completedTasks: [],
      dismissTask: mockDismiss,
    });
    render(<GenerationTasksBar />, { wrapper: Wrapper });
    expect(screen.getByText('Heapsort')).toBeInTheDocument();
    expect(screen.getByText('45%')).toBeInTheDocument();
  });

  it('shows checkmark for completed tasks', () => {
    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [],
      completedTasks: [{
        taskId: 't1', status: 'SUCCESS', progress: 100,
        topic: 'Heapsort', result: {},
      }],
      dismissTask: mockDismiss,
    });
    render(<GenerationTasksBar />, { wrapper: Wrapper });
    expect(screen.getByText('Heapsort')).toBeInTheDocument();
  });

  it('navigates to generation page on completed task click', () => {
    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [],
      completedTasks: [{
        taskId: 't1', status: 'SUCCESS', progress: 100,
        topic: 'Heapsort', result: {},
      }],
      dismissTask: mockDismiss,
    });
    render(<GenerationTasksBar />, { wrapper: Wrapper });
    fireEvent.click(screen.getByText('Heapsort'));
    expect(mockNavigate).toHaveBeenCalledWith('/questions/generate', expect.anything());
  });

  it('is collapsible', () => {
    mockUseGenerationTasks.mockReturnValue({
      activeTasks: [{
        taskId: 't1', status: 'PROGRESS', progress: 45,
        topic: 'Test', questionCount: 5,
      }],
      completedTasks: [],
      dismissTask: mockDismiss,
    });
    render(<GenerationTasksBar />, { wrapper: Wrapper });
    // Find collapse button and click it
    const collapseBtn = screen.getByLabelText('Minimize');
    fireEvent.click(collapseBtn);
    // Topic should be hidden when collapsed
    expect(screen.queryByText('Test')).not.toBeVisible();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/core/frontend && npx react-scripts test --testPathPattern=GenerationTasksBar --watchAll=false`
Expected: FAIL

- [ ] **Step 3: Implement GenerationTasksBar**

Create `packages/core/frontend/src/components/GenerationTasksBar.tsx`:

```typescript
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Paper, Typography, LinearProgress, IconButton, Collapse, Chip,
} from '@mui/material';
import {
  ExpandLess, ExpandMore, CheckCircle, Error as ErrorIcon, Close,
} from '@mui/icons-material';
import { useGenerationTasks } from '../contexts/GenerationTasksContext';
import type { GenerationTaskState } from '../types';

const AUTO_HIDE_DELAY_MS = 30_000;

const GenerationTasksBar: React.FC = () => {
  const { activeTasks, completedTasks, dismissTask } = useGenerationTasks();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const [visible, setVisible] = useState(true);
  const hideTimerRef = useRef<NodeJS.Timeout | null>(null);

  const allTasks = [...activeTasks, ...completedTasks];

  // Auto-hide after all tasks complete
  useEffect(() => {
    if (hideTimerRef.current) clearTimeout(hideTimerRef.current);

    if (activeTasks.length === 0 && completedTasks.length > 0) {
      hideTimerRef.current = setTimeout(() => setVisible(false), AUTO_HIDE_DELAY_MS);
    } else if (activeTasks.length > 0) {
      setVisible(true);
    }

    return () => {
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
    };
  }, [activeTasks.length, completedTasks.length]);

  if (allTasks.length === 0 || !visible) return null;

  const handleTaskClick = (task: GenerationTaskState) => {
    if (task.status === 'SUCCESS') {
      navigate('/questions/generate', { state: { viewTaskId: task.taskId } });
    }
  };

  return (
    <Paper
      elevation={6}
      sx={{
        position: 'fixed', bottom: 16, right: 16, zIndex: 1300,
        width: 320, maxHeight: 400, overflow: 'hidden',
        borderRadius: 2,
      }}
    >
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', px: 2, py: 1, bgcolor: 'primary.main', color: 'white' }}>
        <Typography variant="subtitle2" sx={{ flex: 1 }}>
          Generierungen ({activeTasks.length} aktiv)
        </Typography>
        <IconButton size="small" onClick={() => setCollapsed(!collapsed)} sx={{ color: 'white' }} aria-label="Minimize">
          {collapsed ? <ExpandLess /> : <ExpandMore />}
        </IconButton>
      </Box>

      {/* Task List */}
      <Collapse in={!collapsed}>
        <Box sx={{ maxHeight: 340, overflow: 'auto', p: 1 }}>
          {allTasks.map((task) => (
            <Box
              key={task.taskId}
              onClick={() => handleTaskClick(task)}
              sx={{
                p: 1, mb: 0.5, borderRadius: 1,
                cursor: task.status === 'SUCCESS' ? 'pointer' : 'default',
                '&:hover': task.status === 'SUCCESS' ? { bgcolor: 'action.hover' } : {},
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {task.status === 'SUCCESS' && <CheckCircle color="success" fontSize="small" />}
                {task.status === 'FAILURE' && <ErrorIcon color="error" fontSize="small" />}
                <Typography variant="body2" noWrap sx={{ flex: 1 }}>
                  {task.topic || 'Generierung'}
                </Typography>
                {task.status !== 'PROGRESS' && task.status !== 'PENDING' && task.status !== 'STARTED' && (
                  <IconButton size="small" onClick={(e) => { e.stopPropagation(); dismissTask(task.taskId); }}>
                    <Close fontSize="small" />
                  </IconButton>
                )}
              </Box>
              {!['SUCCESS', 'FAILURE', 'REVOKED'].includes(task.status) && (
                <>
                  <LinearProgress
                    variant="determinate"
                    value={task.progress}
                    sx={{ mt: 0.5, borderRadius: 1 }}
                  />
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.25 }}>
                    <Typography variant="caption" color="text.secondary" noWrap>
                      {task.message || 'Warte...'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {task.progress}%
                    </Typography>
                  </Box>
                </>
              )}
              {task.status === 'SUCCESS' && (
                <Typography variant="caption" color="success.main">
                  Klicken zum Anzeigen
                </Typography>
              )}
              {task.status === 'FAILURE' && (
                <Typography variant="caption" color="error">
                  {task.message || 'Fehler aufgetreten'}
                </Typography>
              )}
            </Box>
          ))}
        </Box>
      </Collapse>
    </Paper>
  );
};

export default GenerationTasksBar;
```

- [ ] **Step 4: Add GenerationTasksBar to AppWithAuth layout**

In `packages/core/frontend/src/AppWithAuth.tsx`, import and render:

```typescript
import GenerationTasksBar from './components/GenerationTasksBar';
```

Place `<GenerationTasksBar />` inside `<GenerationTasksProvider>`, after `<BrowserRouter>`:

```typescript
<GenerationTasksProvider>
  <BrowserRouter>
    <GenerationTasksBar />
    {/* ... routes ... */}
  </BrowserRouter>
</GenerationTasksProvider>
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/core/frontend && npx react-scripts test --testPathPattern=GenerationTasksBar --watchAll=false`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packages/core/frontend/src/components/GenerationTasksBar.tsx packages/core/frontend/src/components/__tests__/GenerationTasksBar.test.tsx packages/core/frontend/src/AppWithAuth.tsx
git commit -m "feat: add GenerationTasksBar for global progress display"
```

---

### Task 10: Update RAGExamCreator for Parallel Generation

**Files:**
- Modify: `packages/premium/frontend/src/components/RAGExamCreator.tsx`
- Test: `packages/premium/frontend/src/components/RAGExamCreator.test.tsx`

- [ ] **Step 1: Write tests for new behavior**

Add to `packages/premium/frontend/src/components/RAGExamCreator.test.tsx`:

```typescript
describe('Parallel Generation', () => {
  it('shows active tasks section when tasks are running', () => {
    // Mock useGenerationTasks with one active task
    // Render RAGExamCreator
    // Assert "Laufende Generierungen" section is visible
  });

  it('resets wizard after starting generation', () => {
    // Start generation via context
    // Assert wizard resets to step 0 (ready for next)
  });

  it('shows result when completed task card is clicked', () => {
    // Mock useGenerationTasks with one completed task with result
    // Click on the completed task card
    // Assert step 4 (results) is shown with the task's result
  });

  it('shows "Neue Generierung" button when a generation is running', () => {
    // Mock useGenerationTasks with active task
    // Assert button is visible
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/premium/frontend && npx jest --testPathPattern=RAGExamCreator --watchAll=false`
Expected: FAIL

- [ ] **Step 3: Update RAGExamCreator**

Key changes in `packages/premium/frontend/src/components/RAGExamCreator.tsx`:

1. **Import and use context** (replace direct RAGService calls):

```typescript
import { useGenerationTasks } from '@core/contexts/GenerationTasksContext';

// Inside the component:
const { activeTasks, completedTasks, startGeneration } = useGenerationTasks();
```

2. **Remove local generation state** (lines 111-113):
   - Remove: `isGenerating`, `generationProgress`, `generationMessage`
   - These are now managed by the context

3. **Add "Laufende Generierungen" section** above the stepper:

```typescript
{(activeTasks.length > 0 || completedTasks.length > 0) && (
  <Box sx={{ mb: 3 }}>
    <Typography variant="h6" gutterBottom>
      Laufende Generierungen
    </Typography>
    {[...activeTasks, ...completedTasks].map((task) => (
      <Card key={task.taskId} sx={{ mb: 1, cursor: task.status === 'SUCCESS' ? 'pointer' : 'default' }}
        onClick={() => {
          if (task.status === 'SUCCESS' && task.result) {
            setGeneratedExam(task.result);
            setActiveStep(3);
          }
        }}
      >
        <CardContent sx={{ py: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="subtitle2">{task.topic}</Typography>
            <Chip size="small" label={`${task.questionCount} Fragen`} />
            {task.status === 'SUCCESS' && <CheckCircle color="success" fontSize="small" />}
          </Box>
          {!['SUCCESS', 'FAILURE', 'REVOKED'].includes(task.status) && (
            <>
              <LinearProgress variant="determinate" value={task.progress} sx={{ mt: 1 }} />
              <Typography variant="caption">{task.message} ({task.progress}%)</Typography>
            </>
          )}
        </CardContent>
      </Card>
    ))}
  </Box>
)}
```

4. **Update handleGenerateExam** (lines 202-284):

```typescript
const handleGenerateExam = async () => {
  try {
    setError('');
    // Build request with prompt_config (existing logic lines 215-257)
    const fullRequest = { ...ragRequest, prompt_config: promptConfig };

    await startGeneration(fullRequest);

    // Reset wizard for next generation
    setActiveStep(0);
    setSelectedDocs([]);
    setRagRequest({ /* default values */ });
  } catch (err: any) {
    setError(err.message || 'Fehler bei der Generierung');
  }
};
```

5. **Add "Neue Generierung" buttons** visible when tasks are running:

```typescript
{/* Full wizard restart */}
{activeTasks.length > 0 && (
  <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
    <Button onClick={() => { setActiveStep(0); setSelectedDocs([]); }} variant="outlined">
      Neue Generierung (von Anfang)
    </Button>
    {/* Quick-repeat: pre-fill document_ids and jump to step 2 */}
    <Button
      onClick={() => {
        // Keep selectedDocs and ragRequest from previous run, reset to step 1 (params)
        setActiveStep(1);
      }}
      variant="contained"
    >
      Schnelle Wiederholung
    </Button>
  </Box>
)}
```

The quick-repeat button pre-fills `document_ids` from the previous run by keeping `selectedDocs` and `ragRequest` state intact. The user can tweak parameters at step 2 before generating. Backend validates document IDs on submit, so stale IDs fail with a clear API error.

6. **Handle viewTaskId from navigation state** (for GlobalBar "click to view"):

```typescript
import { useLocation } from 'react-router-dom';

const location = useLocation();

useEffect(() => {
  const viewTaskId = (location.state as any)?.viewTaskId;
  if (viewTaskId) {
    const task = completedTasks.find((t) => t.taskId === viewTaskId);
    if (task?.result) {
      setGeneratedExam(task.result);
      setActiveStep(3);
    }
    // Clear navigation state
    window.history.replaceState({}, document.title);
  }
}, [location.state, completedTasks]);
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/premium/frontend && npx jest --testPathPattern=RAGExamCreator --watchAll=false`
Expected: PASS

- [ ] **Step 5: Remove deprecated generateRAGExam from RAGService**

In `packages/premium/frontend/src/services/RAGService.ts`, remove the old `generateRAGExam` method (lines 32-99) that included inline WebSocket management.

- [ ] **Step 6: Verify TypeScript compiles**

Run: `cd packages/core/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 7: Commit**

```bash
git add packages/premium/frontend/src/components/RAGExamCreator.tsx packages/premium/frontend/src/services/RAGService.ts packages/premium/frontend/src/components/RAGExamCreator.test.tsx
git commit -m "feat: update RAGExamCreator for parallel generation with context"
```

---

### Task 11: Integration Test - End-to-End Parallel Generation

**Files:**
- Create: `packages/core/frontend/src/__tests__/parallel-generation.integration.test.tsx`

- [ ] **Step 1: Write integration test**

```typescript
import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { QueryClientProvider, QueryClient } from '@tanstack/react-query';
import { AuthProvider } from '../contexts/AuthContext';
import { GenerationTasksProvider } from '../contexts/GenerationTasksContext';
import GenerationTasksBar from '../components/GenerationTasksBar';

const theme = createTheme();
const queryClient = new QueryClient();

// Mock WebSocket
class MockWebSocket {
  onopen: (() => void) | null = null;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onclose: (() => void) | null = null;
  send = jest.fn();
  close = jest.fn();
  constructor(public url: string) {
    setTimeout(() => this.onopen?.(), 0);
  }
}
(global as any).WebSocket = MockWebSocket;

// Mock RAGService
jest.mock('../utils/componentLoader');

describe('Parallel Generation Integration', () => {
  it('shows multiple progress bars in GenerationTasksBar', async () => {
    // Setup: mock two active tasks from getActiveTasks
    // Render GenerationTasksProvider + GenerationTasksBar
    // Assert two task entries are visible
    // Simulate WebSocket progress messages
    // Assert progress updates are reflected
  });

  it('survives page navigation (context persists)', async () => {
    // Setup: start generation
    // Navigate away (change route)
    // Navigate back
    // Assert task is still visible
  });
});
```

- [ ] **Step 2: Run integration test**

Run: `cd packages/core/frontend && npx react-scripts test --testPathPattern=parallel-generation.integration --watchAll=false`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `cd packages/core/frontend && npx react-scripts test --watchAll=false`
Run: `cd packages/core/backend && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add packages/core/frontend/src/__tests__/parallel-generation.integration.test.tsx
git commit -m "test: add integration tests for parallel question generation"
```

---

### Task 12: Manual Smoke Test

- [ ] **Step 1: Start dev environment**

Run: `./start-dev.sh --full`

- [ ] **Step 2: Test parallel generation**

1. Navigate to Question Generation
2. Start a generation (full wizard flow)
3. Verify progress bar appears in GenerationTasksBar (bottom-right)
4. While first generation runs, start a second generation
5. Verify both progress bars are visible
6. Navigate to Documents page
7. Verify GenerationTasksBar still shows progress
8. Navigate back to Question Generation
9. Verify "Laufende Generierungen" section shows both tasks

- [ ] **Step 3: Test browser refresh recovery**

1. While a generation is running, refresh the browser (F5)
2. After reload, verify the GenerationTasksBar reappears with the active task
3. Verify WebSocket reconnects and progress updates resume

- [ ] **Step 4: Test completion flow**

1. Wait for a generation to complete
2. Verify green checkmark appears in GenerationTasksBar
3. Click on the completed task in GenerationTasksBar
4. Verify navigation to Question Generation page with results displayed
5. Verify bar auto-hides after 30s

- [ ] **Step 5: Final commit with any fixes**

```bash
git add -A
git commit -m "fix: address smoke test findings for parallel generation"
```
