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

Query: `QuestionGenerationJob` records with non-terminal status and `created_at` < 2h.

#### Extended `QuestionGenerationJob` Model

New fields:
- `topic: String` - Generation topic (for display)
- `question_count: Integer` - Number of questions (for display)
- `status: String` - Cached task status, default `"PENDING"`. Updated by WebSocket handler on terminal state.

#### Unchanged Infrastructure

- WebSocket handler: no changes (already supports multiple parallel connections per user)
- Celery task: no changes
- `POST /api/v1/rag/generate-exam`: no changes (already creates `QuestionGenerationJob`)

### Frontend Changes

#### `GenerationTasksContext`

New React Context at App level (alongside `AuthContext`).

**Responsibilities:**
- State: Map of `task_id -> TaskState` (status, progress, message, topic, question_count, result)
- WebSocket management: opens/closes WS connections per task
- Recovery: on mount, `GET /api/v1/rag/active-tasks`, reconnect WS for each active task
- API: `startGeneration(request) -> task_id`, `getTask(task_id)`, `tasks`, `activeTasks`

**Performance:** Progress updates stored in `useRef`, flushed to state every 500ms to prevent excessive rerenders.

#### `GenerationTasksBar` (Global Component)

Fixed-position component (bottom-right), visible on all pages while tasks are active.

- Per task: one row with topic, compact progress bar, percentage
- On completion: green checkmark + "Click to view" -> navigates to Question Generation page, opens result inline
- On failure: red X + error message
- Collapsible (chevron) to minimize distraction
- Auto-hides 30s after last task completes

#### `RAGExamCreator` Changes

- Wizard flow unchanged for normal use
- New section above wizard: "Laufende Generierungen" showing active tasks as detailed cards
- New "Neue Generierung starten" button: resets wizard to step 1 (full) or step 2 (quick-repeat with pre-filled parameters)
- Click on completed card: loads result and shows step 4 (result view) inline
- `handleGenerateExam()` delegates to `context.startGeneration()` instead of calling `RAGService` directly

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

- `QuestionGenerationJob.status` updated to terminal state by WebSocket handler
- Active-tasks endpoint returns only non-terminal jobs with `created_at` < 2h
- Frontend removes completed tasks from display after 30s or manual dismiss
