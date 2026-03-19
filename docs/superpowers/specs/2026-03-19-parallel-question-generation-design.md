# Parallel Question Generation with Persistent Progress Tracking

**Date:** 2026-03-19
**Status:** Approved
**Feature:** Allow multiple concurrent question generations with progress bars that persist across page navigation and browser refresh

## Problem

Currently, the question generation UI blocks during generation. Only one generation can run at a time, and progress state is lost when navigating away from the page or refreshing the browser. Users cannot start a second generation while one is in progress.

## Requirements

1. Users can start multiple question generations in parallel
2. Each generation shows its own progress bar
3. Progress bars persist when navigating between pages (global visibility)
4. Progress bars are restored after browser refresh via backend recovery
5. Completed tasks show inline results when clicked on the Question Generation page
6. No hard limit on parallel generations (existing quota system applies)
7. Users can start new generations via full wizard or quick-repeat with same/tweaked parameters

## Architecture: React Context + Backend Recovery

### Backend Changes

#### New Endpoint: `GET /api/v1/rag/active-tasks`

Returns all active generation tasks for the authenticated user.

```json
{
  "tasks": [
    {
      "task_id": "uuid",
      "status": "PROGRESS",
      "progress": 45,
      "message": "Generiere Frage 3/5...",
      "created_at": "2026-03-19T20:00:00Z",
      "topic": "Heapsort",
      "question_count": 5
    }
  ]
}
```

Query filter (pseudo-SQL):
```sql
WHERE status NOT IN ('SUCCESS', 'FAILURE', 'REVOKED')
  AND created_at > NOW() - INTERVAL '2 hours'
```

The `progress` and `message` fields are fetched live from Celery's `AsyncResult` for each matching job. If Celery state is unavailable (expired or Redis error), the endpoint returns `progress: 0` and `message: null` - the frontend will open a WebSocket which will get the real-time state or timeout if the task is truly gone.

#### Extended `QuestionGenerationJob` Model

New fields (requires Alembic migration):
- `topic: String` - Generation topic (for display)
- `question_count: Integer` - Number of questions (for display)
- `status: String` - Cached task status, default `"PENDING"`

**Status write path:** The Celery task (`generate_questions_task`) updates `QuestionGenerationJob.status` to the terminal state (`SUCCESS`/`FAILURE`) at the end of execution, since the task always runs to completion or raises. This is more reliable than updating from the WebSocket handler, which may not be connected when the task finishes. The `POST /api/v1/rag/generate-exam` endpoint already creates the job record and sets `topic` and `question_count` at dispatch time.

#### Unchanged Infrastructure

- WebSocket handler: no changes. Supports multiple parallel connections per user for distinct `task_id` values. Note: same `task_id` from multiple tabs will cause the older connection to close (existing `ConnectionManager` behavior, code 1001). Multi-tab is out of scope.
- Celery task: minor change only - update `QuestionGenerationJob.status` on completion/failure
- `POST /api/v1/rag/generate-exam`: minor change - populate `topic` and `question_count` on the existing `QuestionGenerationJob` record

### Frontend Changes

#### `GenerationTasksContext`

New React Context at App level (alongside `AuthContext`).

**Responsibilities:**
- State: Map of `task_id -> TaskState` (status, progress, message, topic, question_count, result)
- WebSocket management: opens/closes WS connections per task
- Recovery: on mount, `GET /api/v1/rag/active-tasks`, reconnect WS for each active task
- API: `startGeneration(request) -> task_id`, `getTask(task_id)`, `tasks`, `activeTasks`

**Performance:** Progress updates stored in `useRef` (one ref map for all tasks), flushed to React state every 500ms via a single `setInterval` in the context. The interval is cleared on context unmount (app-level, so effectively on app teardown only). Both `GenerationTasksBar` and `RAGExamCreator` cards consume the same flushed state.

#### `GenerationTasksBar` (Global Component)

Fixed-position component (bottom-right), visible on all pages while tasks are active.

- Per task: one row with topic, compact progress bar, percentage
- On completion: green checkmark + "Click to view" -> navigates to Question Generation page, opens result inline
- On failure: red X + error message
- Collapsible (chevron) to minimize distraction
- Auto-hides 30s after last task completes or is manually dismissed

#### `RAGExamCreator` Changes

- Wizard flow unchanged for normal use
- New section above wizard: "Laufende Generierungen" showing active tasks as detailed cards
- New "Neue Generierung starten" button: resets wizard to step 1 (full) or step 2 (quick-repeat with pre-filled parameters). Quick-repeat pre-fills `document_ids` from the previous run; backend validates these IDs exist and are processed at generation time, so stale IDs fail gracefully with an API error
- Click on completed card: loads result and shows step 4 (result view) inline
- `handleGenerateExam()` delegates to `context.startGeneration()` (which internally calls `RAGService.triggerGeneration()`) instead of calling `RAGService.generateRAGExam()` directly. The old `generateRAGExam()` method is removed

#### `RAGService` Refactoring

Split `generateRAGExam()`:
- `triggerGeneration(request) -> { task_id }` - POST only, no WebSocket
- WebSocket management moves entirely into `GenerationTasksContext`

### Data Flow

#### Normal Generation

1. User clicks "Generiere Pruefung"
2. `Context.startGeneration(request)` -> POST endpoint -> receives `task_id`
3. Task added to Context state (PENDING), WebSocket opened
4. Progress updates flow into state via WS
5. Wizard resets to step 1 (ready for next generation)
6. `GenerationTasksBar` shows progress globally

#### Parallel Generation

Same flow repeated. Each task gets its own entry in Context and its own WebSocket connection.

#### Page Navigation

Context lives at App level - WebSocket connections stay open, `GenerationTasksBar` remains visible on all pages. Returning to Question Generation page shows active tasks in the detailed card view.

#### Browser Refresh

1. App starts, `AuthContext` authenticates
2. `GenerationTasksContext` mounts
3. `GET /api/v1/rag/active-tasks` returns active jobs
4. For each active task: open WebSocket, resume progress tracking

### Error Handling

- **WebSocket disconnect:** Auto-reconnect with 3 retries, exponential backoff. After all retries fail: status "UNKNOWN" with retry button.
- **Task failure:** FAILURE status via WebSocket -> card shows error with "Retry" option.
- **Backend unreachable on recovery:** Silent degradation, retry on next navigation.

### Cleanup

- `QuestionGenerationJob.status` updated to terminal state by the Celery task on completion/failure
- Active-tasks endpoint filter: `status NOT IN ('SUCCESS', 'FAILURE', 'REVOKED') AND created_at > NOW() - 2h`
- Frontend `GenerationTasksBar` removes completed tasks from display after 30s or manual dismiss
- `RAGExamCreator` "Laufende Generierungen" section always shows recently completed tasks from context (independent of bar visibility), so users returning to the page can still click to view results
