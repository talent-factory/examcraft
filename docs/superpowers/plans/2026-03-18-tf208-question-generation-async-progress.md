# TF-208 Phase 2: Question Generation Async Progress

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `POST /api/v1/rag/generate-exam` from synchronous to async Celery task with per-question WebSocket progress updates.

**Architecture:** A new `generate_questions_task` Celery task dispatches question generation, writing a `QuestionGenerationJob` ownership record to DB before dispatching. The existing WebSocket endpoint at `/ws/tasks/{task_id}` streams progress as each question is generated. The premium `RAGService.generate_rag_exam()` gets an optional `progress_callback` for per-question granularity.

**Tech Stack:** Python, FastAPI, Celery, SQLAlchemy, Alembic, Pydantic v2, pytest, Premium package pattern (`from premium.services.rag_service import RAGService`)

---

## Context for implementers

### What already exists (do NOT re-implement)

- **`tasks/document_tasks.py`**: `ProgressTask` base class with `update_progress(current, total, message)` and `run_async(coro)` helper. The question task reuses both.

  **`update_progress` contract:** `progress = int(current / total * 100)`. `total` is the denominator, NOT the count of steps minus 1. For `total_steps = 7` (5 questions): step 0/7 = 0%, step 1/7 = 14%, ..., step 6/7 = 85%. The final 100% is delivered by the WebSocket's SUCCESS handler, not by a progress update.
- **`api/v1/websocket.py`**: WebSocket endpoint at `/ws/tasks/{task_id}`. The ownership check function `_check_task_ownership()` needs to be extended — not replaced.
- **`schemas/task.py`**: `TaskStatus` enum and `TaskStatusMessage` Pydantic model.
- **`celery_app.py`**: Already has a `question_generation` queue (`routing_key="question.generate"`). Just needs the task added to `include` and routes.
- **`packages/premium/backend/services/rag_service.py`**: Premium RAGService at line 693 has `generate_rag_exam(self, request)`. Add `progress_callback=None` parameter. Called via `from premium.services.rag_service import RAGService` — works in both FastAPI and Celery worker because `/app/premium` is a subdirectory of the worker's working directory `/app`.

### File structure

```
packages/core/backend/
├── models/
│   └── question_generation_job.py        ← NEW: DB model for ownership
├── tasks/
│   └── question_tasks.py                 ← NEW: Celery task
├── schemas/
│   └── task.py                           ← MODIFY: add GenerateExamTaskResponse
├── api/
│   └── rag_exams.py                      ← MODIFY: return task_id (breaking change)
├── api/v1/
│   └── websocket.py                      ← MODIFY: extend ownership check
├── celery_app.py                         ← MODIFY: add include + route
├── alembic/versions/
│   └── <hash>_add_question_generation_jobs.py  ← GENERATED via autogenerate
└── tests/
    ├── test_question_tasks.py            ← NEW: task tests
    ├── test_websocket_question_ownership.py  ← NEW: ownership tests
    └── test_rag_api.py                   ← MODIFY: update for breaking change

packages/premium/backend/services/
└── rag_service.py                        ← MODIFY: add progress_callback param
```

---

## Chunk 1: Foundation — Model, Migration, Schema

### Task 1: QuestionGenerationJob Model

**Files:**
- Create: `packages/core/backend/models/question_generation_job.py`

- [ ] **Step 1: Write the failing test**

Create `packages/core/backend/tests/test_question_generation_job.py`:

```python
"""Tests für QuestionGenerationJob DB-Modell"""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base


def test_question_generation_job_model_importable():
    """Modell kann importiert werden"""
    from models.question_generation_job import QuestionGenerationJob
    assert QuestionGenerationJob.__tablename__ == "question_generation_jobs"


def test_question_generation_job_columns():
    """Modell hat die erwarteten Spalten"""
    from models.question_generation_job import QuestionGenerationJob
    columns = {c.name for c in QuestionGenerationJob.__table__.columns}
    assert "id" in columns
    assert "task_id" in columns
    assert "user_id" in columns
    assert "created_at" in columns


def test_task_id_is_unique():
    """task_id Spalte hat unique constraint"""
    from models.question_generation_job import QuestionGenerationJob
    task_id_col = QuestionGenerationJob.__table__.columns["task_id"]
    assert task_id_col.unique is True


def test_task_id_is_indexed():
    """task_id Spalte ist indexiert"""
    from models.question_generation_job import QuestionGenerationJob
    task_id_col = QuestionGenerationJob.__table__.columns["task_id"]
    assert task_id_col.index is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd packages/core/backend
python3 -m pytest tests/test_question_generation_job.py -v
```

Expected: `FAILED` — `ModuleNotFoundError: No module named 'models.question_generation_job'`

- [ ] **Step 3: Implement the model**

Create `packages/core/backend/models/question_generation_job.py`:

```python
"""
QuestionGenerationJob — Ownership-Tracking für asynchrone Fragengenerierungs-Tasks.
Wird vor dem Celery-Task-Dispatch erstellt, damit der WebSocket-Ownership-Check
immer einen Eintrag findet.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from database import Base


class QuestionGenerationJob(Base):
    __tablename__ = "question_generation_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # datetime.utcnow (ohne Klammern) — Python-seitiger Default, konsistent mit restlichen Models
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python3 -m pytest tests/test_question_generation_job.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add models/question_generation_job.py tests/test_question_generation_job.py
git commit -m "feat(models): Füge QuestionGenerationJob für Task-Ownership hinzu"
```

---

### Task 2: Alembic Migration

**Files:**
- Generate: `packages/core/backend/alembic/versions/<hash>_add_question_generation_jobs.py`

- [ ] **Step 1: Import model in alembic env.py so autogenerate detects it**

Check `packages/core/backend/alembic/env.py` — it must import the new model. Open the file and add the import near the other model imports:

```python
from models.question_generation_job import QuestionGenerationJob  # noqa: F401
```

- [ ] **Step 2: Generate migration**

```bash
cd packages/core/backend
docker compose --env-file ../../../.env -f ../../../docker-compose.full.yml exec backend \
  alembic revision --autogenerate -m "add_question_generation_jobs"
```

Expected output: `Generating .../alembic/versions/<hash>_add_question_generation_jobs.py`

- [ ] **Step 3: Verify migration content**

Open the generated file. It should contain:
```python
op.create_table('question_generation_jobs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('task_id', sa.String(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
)
op.create_index(op.f('ix_question_generation_jobs_task_id'), 'question_generation_jobs', ['task_id'], unique=True)
```

If the content looks correct, proceed.

- [ ] **Step 4: Apply migration**

```bash
docker compose --env-file ../../../.env -f ../../../docker-compose.full.yml exec backend \
  alembic upgrade head
```

Expected: `Running upgrade ... -> <hash>, add_question_generation_jobs`

- [ ] **Step 5: Commit**

```bash
git add alembic/versions/
git commit -m "feat(db): Migration für question_generation_jobs Tabelle"
```

---

### Task 3: GenerateExamTaskResponse Schema

**Files:**
- Modify: `packages/core/backend/schemas/task.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/core/backend/tests/test_task_schemas.py` (file already exists — append these tests):

```python
def test_generate_exam_task_response_valid():
    """GenerateExamTaskResponse hat task_id und message"""
    from schemas.task import GenerateExamTaskResponse
    resp = GenerateExamTaskResponse(
        task_id="abc-123",
        message="Fraggenerierung gestartet",
    )
    assert resp.task_id == "abc-123"
    assert resp.message == "Fraggenerierung gestartet"


def test_generate_exam_task_response_requires_task_id():
    """task_id ist Pflichtfeld"""
    import pytest
    from pydantic import ValidationError
    from schemas.task import GenerateExamTaskResponse
    with pytest.raises(ValidationError):
        GenerateExamTaskResponse(message="test")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_task_schemas.py::test_generate_exam_task_response_valid -v
```

Expected: `FAILED` — `ImportError: cannot import name 'GenerateExamTaskResponse'`

- [ ] **Step 3: Add schema**

Append to `packages/core/backend/schemas/task.py`:

```python

class GenerateExamTaskResponse(BaseModel):
    """Response für den asynchronen Fraggenerierungs-Endpoint"""

    task_id: str
    message: str
```

Also update the `__init__.py` export if it exists:

```bash
grep -n "GenerateExamTaskResponse\|from schemas" packages/core/backend/schemas/__init__.py
```

If `schemas/__init__.py` exports task classes, add `GenerateExamTaskResponse` to it.

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_task_schemas.py -v
```

Expected: all tests pass (7 total including the 5 existing + 2 new)

- [ ] **Step 5: Commit**

```bash
git add schemas/task.py tests/test_task_schemas.py
git commit -m "feat(schemas): Füge GenerateExamTaskResponse hinzu"
```

---

## Chunk 2: Core Logic — Premium Service + Celery Task

### Task 4: progress_callback in Premium RAGService

**Files:**
- Modify: `packages/premium/backend/services/rag_service.py` (line 693)

- [ ] **Step 1: Write the failing test**

Create `packages/core/backend/tests/test_question_generation_progress_callback.py`:

```python
"""
Tests für den progress_callback-Parameter in generate_rag_exam.
Testet die Callback-Integration ohne echten Claude API-Aufruf.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_generate_rag_exam_accepts_progress_callback():
    """generate_rag_exam akzeptiert progress_callback ohne Fehler"""
    # Importiere nur wenn Premium verfügbar
    pytest.importorskip("premium.services.rag_service")
    from premium.services.rag_service import RAGService
    import inspect
    sig = inspect.signature(RAGService.generate_rag_exam)
    assert "progress_callback" in sig.parameters


@pytest.mark.asyncio
async def test_generate_rag_exam_calls_callback_after_context():
    """Callback wird nach dem Context-Laden aufgerufen (Step 1)"""
    pytest.importorskip("premium.services.rag_service")
    from premium.services.rag_service import RAGService
    from services.rag_service import RAGExamRequest

    request = RAGExamRequest(topic="Test", question_count=2)
    callback_calls = []

    def mock_callback(current, total, message):
        callback_calls.append((current, total, message))

    service = RAGService.__new__(RAGService)

    mock_context = MagicMock()
    mock_context.retrieved_chunks = [MagicMock()]
    mock_context.query = "Test"
    mock_context.total_similarity_score = 0.9
    mock_context.source_documents = []
    mock_context.context_length = 100

    mock_question = MagicMock()
    mock_question.model_dump = MagicMock(return_value={})

    service.retrieve_context = AsyncMock(return_value=mock_context)
    service.generate_question = AsyncMock(return_value=mock_question)
    service._calculate_quality_metrics = MagicMock(return_value={})

    await service.generate_rag_exam(request, progress_callback=mock_callback)

    # Step 1 = Context geladen (current=1)
    assert any(call[0] == 1 for call in callback_calls), \
        f"Expected callback with current=1, got: {callback_calls}"


@pytest.mark.asyncio
async def test_generate_rag_exam_calls_callback_per_question():
    """Callback wird nach jeder generierten Frage aufgerufen"""
    pytest.importorskip("premium.services.rag_service")
    from premium.services.rag_service import RAGService
    from services.rag_service import RAGExamRequest

    question_count = 3
    request = RAGExamRequest(topic="Test", question_count=question_count)
    callback_calls = []

    def mock_callback(current, total, message):
        callback_calls.append((current, total, message))

    service = RAGService.__new__(RAGService)

    mock_context = MagicMock()
    mock_context.retrieved_chunks = [MagicMock(), MagicMock(), MagicMock()]
    mock_context.query = "Test"
    mock_context.total_similarity_score = 0.9
    mock_context.source_documents = []
    mock_context.context_length = 300

    mock_question = MagicMock()
    mock_question.model_dump = MagicMock(return_value={})

    service.retrieve_context = AsyncMock(return_value=mock_context)
    service.generate_question = AsyncMock(return_value=mock_question)
    service._calculate_quality_metrics = MagicMock(return_value={})

    await service.generate_rag_exam(request, progress_callback=mock_callback)

    # 1 context call + question_count question calls
    assert len(callback_calls) == question_count + 1, \
        f"Expected {question_count + 1} callbacks, got {len(callback_calls)}"
    # Last question call has current = question_count + 1
    question_calls = [c for c in callback_calls if c[0] >= 2]
    assert len(question_calls) == question_count


@pytest.mark.asyncio
async def test_generate_rag_exam_callback_messages_are_german():
    """Callback-Messages sind auf Deutsch"""
    pytest.importorskip("premium.services.rag_service")
    from premium.services.rag_service import RAGService
    from services.rag_service import RAGExamRequest

    request = RAGExamRequest(topic="Test", question_count=2)
    messages = []

    def mock_callback(current, total, message):
        messages.append(message)

    service = RAGService.__new__(RAGService)

    mock_context = MagicMock()
    mock_context.retrieved_chunks = [MagicMock(), MagicMock()]
    mock_context.query = "Test"
    mock_context.total_similarity_score = 0.9
    mock_context.source_documents = []
    mock_context.context_length = 200

    mock_question = MagicMock()
    service.retrieve_context = AsyncMock(return_value=mock_context)
    service.generate_question = AsyncMock(return_value=mock_question)
    service._calculate_quality_metrics = MagicMock(return_value={})

    await service.generate_rag_exam(request, progress_callback=mock_callback)

    assert any("Context" in m or "geladen" in m.lower() for m in messages), \
        f"Expected German context message, got: {messages}"
    assert any("Frage" in m for m in messages), \
        f"Expected German question message, got: {messages}"


@pytest.mark.asyncio
async def test_generate_rag_exam_works_without_callback():
    """generate_rag_exam funktioniert ohne Callback (None)"""
    pytest.importorskip("premium.services.rag_service")
    from premium.services.rag_service import RAGService
    from services.rag_service import RAGExamRequest

    request = RAGExamRequest(topic="Test", question_count=1)
    service = RAGService.__new__(RAGService)

    mock_context = MagicMock()
    mock_context.retrieved_chunks = [MagicMock()]
    mock_context.query = "Test"
    mock_context.total_similarity_score = 0.9
    mock_context.source_documents = []
    mock_context.context_length = 100

    mock_question = MagicMock()
    service.retrieve_context = AsyncMock(return_value=mock_context)
    service.generate_question = AsyncMock(return_value=mock_question)
    service._calculate_quality_metrics = MagicMock(return_value={})

    # Sollte kein Fehler werfen
    result = await service.generate_rag_exam(request, progress_callback=None)
    assert result is not None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_question_generation_progress_callback.py -v
```

Expected: `test_generate_rag_exam_accepts_progress_callback` fails because `progress_callback` is not in the signature.

- [ ] **Step 3: Add progress_callback to generate_rag_exam**

Open `packages/premium/backend/services/rag_service.py` at line 693.

Change the signature from:
```python
async def generate_rag_exam(self, request: RAGExamRequest) -> RAGExamResponse:
```

To:
```python
async def generate_rag_exam(
    self,
    request: RAGExamRequest,
    progress_callback=None,  # Optional[Callable[[int, int, str], None]]
) -> RAGExamResponse:
```

Add callback call after context retrieval (after line ~716, after the `if not context.retrieved_chunks` check):

```python
if progress_callback:
    progress_callback(1, request.question_count + 2, "Context geladen...")
```

Add callback call inside the question loop (after `questions.append(question)` at ~line 770):

```python
if progress_callback:
    progress_callback(
        i + 2,
        request.question_count + 2,
        f"Frage {i + 1} von {request.question_count} generiert...",
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_question_generation_progress_callback.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add packages/premium/backend/services/rag_service.py \
        packages/core/backend/tests/test_question_generation_progress_callback.py
git commit -m "feat(rag): Füge progress_callback Parameter zu generate_rag_exam hinzu"
```

---

### Task 5: generate_questions_task + celery_app Registration

**Files:**
- Create: `packages/core/backend/tasks/question_tasks.py`
- Modify: `packages/core/backend/celery_app.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/core/backend/tests/test_question_tasks.py`:

```python
"""
Tests für den generate_questions_task Celery Task.
Testet Task-Dispatch, Progress-Steps und Rückgabe-Format.
"""
import pytest
from unittest.mock import MagicMock, patch, call


def test_generate_questions_task_importable():
    """Task kann importiert werden"""
    from tasks.question_tasks import generate_questions_task
    assert generate_questions_task is not None


def test_generate_questions_task_name():
    """Task hat den korrekten Celery-Namen"""
    from tasks.question_tasks import generate_questions_task
    assert generate_questions_task.name == "tasks.question_tasks.generate_questions"


def test_generate_questions_task_uses_progress_task_base():
    """Task verwendet ProgressTask als Basis"""
    from tasks.question_tasks import generate_questions_task
    from tasks.document_tasks import ProgressTask
    assert isinstance(generate_questions_task, ProgressTask)


def test_generate_questions_task_registered_in_celery():
    """Task ist in der Celery-App registriert"""
    from celery_app import celery_app
    assert "tasks.question_tasks.generate_questions" in celery_app.tasks


def test_generate_questions_task_has_correct_queue_route():
    """Task ist der question_generation Queue zugeordnet"""
    from celery_app import celery_app
    routes = celery_app.conf.task_routes
    route = routes.get("tasks.question_tasks.generate_questions", {})
    assert route.get("queue") == "question_generation"
    assert route.get("routing_key") == "question.generate"


def test_generate_questions_task_emits_progress_steps():
    """Task emittiert mindestens 3 Progress-Updates (0%, Context, mind. 1 Frage)"""
    from tasks.question_tasks import generate_questions_task

    progress_updates = []

    mock_result = MagicMock()
    mock_result.exam_id = "exam_001"
    mock_result.topic = "Heapsort"
    mock_result.questions = [MagicMock(model_dump=MagicMock(return_value={"q": 1}))]
    mock_result.generation_time = 5.0
    mock_result.quality_metrics = {}

    mock_rag_service = MagicMock()
    mock_rag_service.generate_rag_exam = MagicMock(return_value=mock_result)

    def fake_run_async(coro):
        # Simuliere den progress_callback-Aufruf durch generate_rag_exam
        # Wir extrahieren den callback aus dem coroutine-Aufruf
        return mock_result

    with patch("tasks.question_tasks.run_async", side_effect=fake_run_async), \
         patch("tasks.question_tasks.RAGService", return_value=mock_rag_service):

        task = generate_questions_task
        task.update_state = MagicMock(side_effect=lambda state, meta: progress_updates.append(meta))

        request_data = {
            "topic": "Heapsort",
            "question_count": 1,
            "question_types": ["multiple_choice"],
            "difficulty": "medium",
            "language": "de",
            "document_ids": None,
            "context_chunks_per_question": 3,
            "prompt_config": None,
        }

        result = generate_questions_task.run(request_data, "42")

    # Step 0 muss emittiert werden
    assert len(progress_updates) >= 1
    first = progress_updates[0]
    assert first["current"] == 0
    assert first["progress"] == 0
    assert "Fraggenerierung" in first["message"] or "Starte" in first["message"]


def test_generate_questions_task_returns_correct_format():
    """Task gibt dict mit exam_id, topic, questions, generation_time, quality_metrics zurück.

    mock_result simuliert RAGExamResponse aus premium/services/rag_service.py.
    Die echte RAGExamResponse hat: exam_id(str), topic(str), questions(List[RAGQuestion]),
    generation_time(float), quality_metrics(dict).
    RAGQuestion hat model_dump() via Pydantic v2.
    """
    from tasks.question_tasks import generate_questions_task

    # Mock für RAGExamResponse (premium Pydantic-Modell)
    mock_result = MagicMock()
    mock_result.exam_id = "exam_001"
    mock_result.topic = "Heapsort"
    # Mock für RAGQuestion mit Pydantic v2 model_dump()
    mock_q = MagicMock()
    mock_q.model_dump = MagicMock(return_value={"question_text": "Was ist ein Heap?"})
    mock_result.questions = [mock_q]
    mock_result.generation_time = 5.0
    mock_result.quality_metrics = {"total_questions": 1}  # dict, wie von _calculate_quality_metrics

    mock_rag_service = MagicMock()

    with patch("tasks.question_tasks.run_async", return_value=mock_result), \
         patch("tasks.question_tasks.RAGService", return_value=mock_rag_service):

        generate_questions_task.update_state = MagicMock()

        request_data = {
            "topic": "Heapsort",
            "question_count": 1,
            "question_types": ["multiple_choice"],
            "difficulty": "medium",
            "language": "de",
            "document_ids": None,
            "context_chunks_per_question": 3,
            "prompt_config": None,
        }

        result = generate_questions_task.run(request_data, "42")

    assert result["exam_id"] == "exam_001"
    assert result["topic"] == "Heapsort"
    assert isinstance(result["questions"], list)
    assert result["questions"][0]["question_text"] == "Was ist ein Heap?"
    assert result["generation_time"] == 5.0
    assert "total_questions" in result["quality_metrics"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_question_tasks.py -v
```

Expected: `FAILED` — `ModuleNotFoundError: No module named 'tasks.question_tasks'`

- [ ] **Step 3: Create question_tasks.py**

Create `packages/core/backend/tasks/question_tasks.py`:

```python
"""
Celery Task für asynchrone Fragengenerierung mit Progress-Tracking.
Sendet per-Frage Progress-Updates via ProgressTask.update_progress().
"""

import logging
from typing import Any, Dict

from celery.exceptions import Ignore, Reject

from celery_app import celery_app
from tasks.document_tasks import ProgressTask, run_async

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    base=ProgressTask,
    name="tasks.question_tasks.generate_questions",
    autoretry_for=(Exception,),
    dont_autoretry_for=(Ignore, Reject),  # Celery-interne Exceptions nicht nochmals retry
    retry_kwargs={"max_retries": 2, "countdown": 30},
)
def generate_questions_task(self, request_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Asynchrone Fragengenerierung mit per-Frage Progress-Updates.

    Args:
        request_data: Serialisierter RAGExamRequest als dict (via model_dump(mode='json'))
        user_id: ID des Users (für Logging)

    Returns:
        Dict mit exam_id, topic, questions, generation_time, quality_metrics
    """
    # Lazy Import — Premium-Package ist im Worker unter /app/premium verfügbar
    from premium.services.rag_service import RAGService
    from services.rag_service import RAGExamRequest

    rag_request = RAGExamRequest(**request_data)
    question_count = rag_request.question_count
    # total_steps = N + 2:
    #   Step 0:     Task-Start (emittiert vom Task)
    #   Step 1:     Context geladen (emittiert via Callback)
    #   Steps 2..N+1: Fragen 1..N (emittiert via Callback)
    # Der Sprung von Step N+1 (letztes PROGRESS) auf 100% erfolgt durch den SUCCESS-State im WebSocket.
    total_steps = question_count + 2

    # Step 0: Emittiert vom Task selbst (nicht vom Callback)
    self.update_progress(0, total_steps, "Starte Fragengenerierung...")

    # Progress-Callback delegiert an bestehende update_progress-Abstraktion.
    # Der `total`-Parameter vom Service (question_count + 2) ist identisch mit
    # `total_steps` und wird daher durch den Closure-Wert ersetzt — so bleibt
    # total_steps als Single Source of Truth im Task.
    def progress_callback(current: int, total: int, message: str) -> None:  # noqa: ARG001
        self.update_progress(current, total_steps, message)

    logger.info(f"Starte Fragengenerierung für User {user_id}: {question_count} Fragen zum Thema '{rag_request.topic}'")

    rag_service = RAGService()
    result = run_async(
        rag_service.generate_rag_exam(rag_request, progress_callback=progress_callback)
    )

    logger.info(f"Fragengenerierung abgeschlossen: {result.exam_id} ({question_count} Fragen in {result.generation_time:.1f}s)")

    return {
        "exam_id": result.exam_id,
        "topic": result.topic,
        "questions": [q.model_dump() for q in result.questions],
        "generation_time": result.generation_time,
        "quality_metrics": result.quality_metrics,
    }
```

- [ ] **Step 4: Register in celery_app.py**

Open `packages/core/backend/celery_app.py`.

Change `include` list from:
```python
include=[
    "tasks.document_tasks",
    # "tasks.rag_tasks",  # Requires Premium RAGService
    "tasks.session_cleanup",
],
```

To:
```python
include=[
    "tasks.document_tasks",
    "tasks.question_tasks",
    # "tasks.rag_tasks",  # Requires Premium RAGService
    "tasks.session_cleanup",
],
```

Add task route to `celery_app.conf.task_routes`:
```python
"tasks.question_tasks.generate_questions": {
    "queue": "question_generation",
    "routing_key": "question.generate",
},
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_question_tasks.py -v
```

Expected: `7 passed`

- [ ] **Step 6: Commit**

```bash
git add tasks/question_tasks.py celery_app.py tests/test_question_tasks.py
git commit -m "feat(tasks): Implementiere generate_questions_task mit Progress-Callback"
```

---

## Chunk 3: API + WebSocket Integration

### Task 6: Update rag_exams.py — Breaking Change

**Files:**
- Modify: `packages/core/backend/api/rag_exams.py`
- Modify: `packages/core/backend/tests/test_rag_api.py`

- [ ] **Step 1: Update existing tests for the breaking change**

Open `packages/core/backend/tests/test_rag_api.py`.

Tests that call `POST /api/v1/rag/generate-exam` and assert on `questions` in the response must be updated to assert on `task_id` instead. The mock for `rag_service.generate_rag_exam` is no longer needed in these tests since the endpoint now dispatches a Celery task.

For each test calling `/api/v1/rag/generate-exam`, update the assertion pattern from:
```python
assert response.status_code == 200
data = response.json()
assert "questions" in data
```

To:
```python
assert response.status_code == 200
data = response.json()
assert "task_id" in data
assert "message" in data
assert len(data["task_id"]) > 0
```

Also patch `generate_questions_task.apply_async` instead of `rag_service.generate_rag_exam`:
```python
from unittest.mock import patch, MagicMock

with patch("api.rag_exams.generate_questions_task") as mock_task, \
     patch("api.rag_exams.get_db"):
    mock_task.apply_async.return_value = MagicMock(id="test-task-id-123")
    # ... rest of test
```

- [ ] **Step 2: Run updated tests to verify they fail (still testing old endpoint)**

```bash
python3 -m pytest tests/test_rag_api.py -v -k "generate_exam" 2>&1 | head -30
```

Expected: Some tests fail because endpoint still returns `questions`.

- [ ] **Step 3: Update the endpoint**

Open `packages/core/backend/api/rag_exams.py`.

Add imports at the top:
```python
import uuid
from models.question_generation_job import QuestionGenerationJob
from tasks.question_tasks import generate_questions_task
from schemas.task import GenerateExamTaskResponse
```

Replace the entire `generate_rag_exam` function body. Change response model and implementation:

```python
@router.post("/generate-exam", response_model=GenerateExamTaskResponse)
async def generate_rag_exam(
    request: RAGExamRequestModel,
    http_request: Request,
    current_user: User = Depends(require_permission("create_questions")),
    db: Session = Depends(get_db),
):
    """
    Startet asynchrone Fragengenerierung via Celery Task.
    Gibt sofort task_id zurück — Fortschritt via WebSocket /ws/tasks/{task_id}.
    """
    try:
        # Request validieren (Fragetypen prüfen)
        valid_types = ["multiple_choice", "open_ended", "true_false"]
        if request.question_types:
            for qtype in request.question_types:
                if qtype not in valid_types:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid question type: {qtype}. Valid types: {valid_types}",
                    )

        # Request serialisieren
        from services.rag_service import RAGExamRequest, PromptConfig as RAGPromptConfig

        prompt_config_dict = None
        if request.prompt_config:
            prompt_config_dict = {}
            for question_type, config in request.prompt_config.items():
                prompt_config_dict[question_type] = {
                    "prompt_id": config.prompt_id,
                    "variables": config.variables,
                }

        rag_request = RAGExamRequest(
            topic=request.topic,
            document_ids=request.document_ids,
            question_count=request.question_count,
            question_types=request.question_types,
            difficulty=request.difficulty,
            language=request.language,
            context_chunks_per_question=request.context_chunks_per_question,
            prompt_config=prompt_config_dict,
        )
        request_data = rag_request.model_dump(mode="json")

        # UUID vorab generieren — wird sowohl als DB-Record-Key als auch als
        # Celery task_id verwendet. apply_async(..., task_id=task_id) akzeptiert
        # eine externe UUID, daher ist die Reihenfolge DB-zuerst möglich.
        task_id = str(uuid.uuid4())
        job = QuestionGenerationJob(task_id=task_id, user_id=current_user.id)
        db.add(job)
        db.commit()

        # Celery Task dispatchen — bei Fehler (z.B. Broker nicht erreichbar) Job bereinigen
        try:
            generate_questions_task.apply_async(
                args=[request_data, str(current_user.id)],
                task_id=task_id,      # Celery verwendet dieselbe UUID
                queue="question_generation",
            )
        except Exception as broker_error:
            # Orphaned Job-Record entfernen
            db.delete(job)
            db.commit()
            logger.error(f"Celery Broker nicht erreichbar: {broker_error}")
            raise HTTPException(
                status_code=503,
                detail="Task-Queue nicht verfügbar. Bitte später erneut versuchen.",
            )

        logger.info(
            f"Fragengenerierung gestartet: task_id={task_id}, "
            f"user={current_user.id}, topic='{request.topic}'"
        )

        return GenerateExamTaskResponse(
            task_id=task_id,
            message="Fragengenerierung gestartet",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Starten der Fragengenerierung: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fragengenerierung konnte nicht gestartet werden: {str(e)}")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_rag_api.py -v
```

Expected: all previously-updated tests pass.

- [ ] **Step 5: Commit**

```bash
git add api/rag_exams.py tests/test_rag_api.py
git commit -m "feat(api): Konvertiere /generate-exam zu async Celery Task (Breaking Change)"
```

---

### Task 7: WebSocket Ownership — extend _check_task_ownership

**Files:**
- Modify: `packages/core/backend/api/v1/websocket.py`

- [ ] **Step 1: Verify existing Document-ownership tests still pass**

The refactored `_check_task_ownership()` must continue to deny Document-task access for wrong users.
Run the existing websocket tests to confirm the Document deny path is covered:

```bash
python3 -m pytest tests/test_websocket.py::TestWebSocketConnection::test_websocket_wrong_ownership -v
```

Expected: PASS (Document ownership deny still works after refactoring)

- [ ] **Step 2: Write the failing tests for QuestionGenerationJob paths**

Create `packages/core/backend/tests/test_websocket_question_ownership.py`:

```python
"""
Tests für WebSocket Ownership-Check mit QuestionGenerationJob.
Deckt die 3 neuen Pfade ab: Job+richtiger User, Job+falscher User, unbekannte task_id.
Die bestehenden tests/test_websocket.py decken Document-Ownership (Pfade 1+2) ab.
"""
import importlib
import importlib.util
import os
import sys
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from starlette.testclient import TestClient
from fastapi import FastAPI
from starlette.websockets import WebSocketDisconnect


@pytest.fixture
def ws_module():
    """Lädt das websocket Modul frisch für jeden Test"""
    ws_path = os.path.join(
        os.path.dirname(__file__), "..", "api", "v1", "websocket.py"
    )
    spec = importlib.util.spec_from_file_location("api.v1.websocket_test", ws_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["api.v1.websocket_test"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def ws_app(ws_module):
    app = FastAPI()
    app.include_router(ws_module.router)
    return app


class TestQuestionJobOwnership:
    def test_question_task_owner_can_connect(self, ws_app):
        """Owner eines QuestionGenerationJob kann WebSocket öffnen"""
        mock_user = MagicMock()
        mock_user.id = 42

        mock_job = MagicMock()
        mock_job.user_id = 42  # Same as current_user.id

        mock_task_data = {"state": "PENDING", "info": None, "result": None}

        with patch("api.v1.websocket_test._authenticate_websocket", new=AsyncMock(return_value=mock_user)), \
             patch("api.v1.websocket_test.SessionLocal") as mock_session_cls, \
             patch("api.v1.websocket_test._get_task_result", return_value=mock_task_data):

            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                None,       # Document lookup: not found
                mock_job,   # QuestionGenerationJob lookup: found
            ]
            mock_session_cls.return_value = mock_db

            client = TestClient(ws_app, raise_server_exceptions=False)
            with client.websocket_connect("/ws/tasks/test-task-999") as ws:
                ws.send_json({"token": "valid-token"})
                # Connection should stay open (PENDING, no timeout yet)

    def test_wrong_user_denied_for_question_task(self, ws_app):
        """Anderer User wird abgelehnt (Close 1008) für QuestionGenerationJob"""
        mock_user = MagicMock()
        mock_user.id = 99  # Different from job owner

        mock_job = MagicMock()
        mock_job.user_id = 42  # Job belongs to user 42

        with patch("api.v1.websocket_test._authenticate_websocket", new=AsyncMock(return_value=mock_user)), \
             patch("api.v1.websocket_test.SessionLocal") as mock_session_cls:

            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                None,       # Document lookup: not found
                mock_job,   # QuestionGenerationJob lookup: found, wrong user
            ]
            mock_session_cls.return_value = mock_db

            client = TestClient(ws_app, raise_server_exceptions=False)
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect("/ws/tasks/test-task-999") as ws:
                    ws.send_json({"token": "valid-token"})
                    ws.receive_json()

    def test_unknown_task_id_denied(self, ws_app):
        """Unbekannte task_id wird abgelehnt (Close 1008)"""
        mock_user = MagicMock()
        mock_user.id = 42

        with patch("api.v1.websocket_test._authenticate_websocket", new=AsyncMock(return_value=mock_user)), \
             patch("api.v1.websocket_test.SessionLocal") as mock_session_cls:

            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = None  # Nothing found
            mock_session_cls.return_value = mock_db

            client = TestClient(ws_app, raise_server_exceptions=False)
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect("/ws/tasks/unknown-task-xyz") as ws:
                    ws.send_json({"token": "valid-token"})
                    ws.receive_json()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_websocket_question_ownership.py -v
```

Expected: `test_wrong_user_denied_for_question_task` and `test_unknown_task_id_denied` fail because current code allows unknown task_ids.

- [ ] **Step 3: Update _check_task_ownership in websocket.py**

Open `packages/core/backend/api/v1/websocket.py`.

Replace the entire `_check_task_ownership` function.

**Session handling:** Create a fresh `SessionLocal()` at the start (same pattern as the existing function), close it in `finally`. Do NOT reuse a session from the caller.

**Column for lookup:** Both Document and QuestionGenerationJob are looked up by their `task_id` column (the Celery UUID string), NOT by their integer primary key `id`.

```python
async def _check_task_ownership(websocket: WebSocket, task_id: str, user: User) -> bool:
    """
    Prüft ob der authentifizierte User der Owner des Tasks ist.
    Prüft Document.task_id (Dokument-Tasks) und QuestionGenerationJob.task_id
    (Fragen-Tasks). Unbekannte task_ids werden abgelehnt.
    """
    from models.question_generation_job import QuestionGenerationJob

    db = SessionLocal()
    try:
        # Check 1: Dokument-Task
        document = db.query(Document).filter(Document.task_id == task_id).first()
        if document:
            if document.user_id != user.id:
                logger.warning(
                    f"Ownership-Verletzung (Dokument): User {user.id} versucht Task "
                    f"{task_id} (Owner: {document.user_id}) zu überwachen"
                )
                await websocket.close(code=1008)
                return False
            return True

        # Check 2: Fragen-Task
        job = (
            db.query(QuestionGenerationJob)
            .filter(QuestionGenerationJob.task_id == task_id)
            .first()
        )
        if job:
            if job.user_id != user.id:
                logger.warning(
                    f"Ownership-Verletzung (Fragen): User {user.id} versucht Task "
                    f"{task_id} (Owner: {job.user_id}) zu überwachen"
                )
                await websocket.close(code=1008)
                return False
            return True

        # Unbekannte task_id — ablehnen (kein legitimer Fall, da Job vor apply_async erstellt wird)
        logger.warning(f"Unbekannte task_id {task_id!r} von User {user.id} abgelehnt")
        await websocket.close(code=1008)
        return False

    except Exception as e:
        logger.error(f"Ownership-Check Fehler: {e}")
        await websocket.close(code=1008)
        return False
    finally:
        db.close()
```

- [ ] **Step 4: Run all WebSocket tests**

```bash
python3 -m pytest tests/test_websocket.py tests/test_websocket_question_ownership.py tests/test_websocket_route.py -v
```

Expected: all pass. Note: existing `test_websocket.py` tests mock the ownership check, so they are not affected by this change.

- [ ] **Step 5: Commit**

```bash
git add api/v1/websocket.py tests/test_websocket_question_ownership.py
git commit -m "feat(websocket): Erweitere Ownership-Check für QuestionGenerationJob"
```

---

### Task 8: Full Test Suite + Docker Rebuild

- [ ] **Step 1: Run all TF-208 tests**

```bash
cd packages/core/backend
python3 -m pytest \
  tests/test_question_generation_job.py \
  tests/test_task_schemas.py \
  tests/test_question_generation_progress_callback.py \
  tests/test_question_tasks.py \
  tests/test_websocket.py \
  tests/test_websocket_question_ownership.py \
  tests/test_websocket_route.py \
  tests/test_celery_config.py \
  tests/test_document_task_progress.py \
  tests/test_celery_tasks.py \
  -v
```

Expected: all pass.

- [ ] **Step 2: Rebuild Docker image and restart**

```bash
cd /path/to/examcraft  # repo root
docker compose --env-file .env -f docker-compose.full.yml up -d --build backend celery-worker
```

- [ ] **Step 3: Apply migration in running container**

```bash
docker compose --env-file .env -f docker-compose.full.yml exec backend alembic upgrade head
```

- [ ] **Step 4: Manual end-to-end test**

```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"your-password-here"}' \  # pragma: allowlist secret
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2. Start question generation
TASK_ID=$(curl -s -X POST http://localhost:8000/api/v1/rag/generate-exam \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"topic":"Heapsort","question_count":3,"document_ids":null}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['task_id'])")
echo "Task ID: $TASK_ID"

# 3. Connect WebSocket (requires websocat: brew install websocat)
websocat ws://localhost:8000/ws/tasks/$TASK_ID
# Then type: {"token": "<TOKEN>"}
```

Expected WebSocket output:
```json
{"task_id":"...","status":"PROGRESS","progress":0,"message":"Starte Fraggenerierung..."}
{"task_id":"...","status":"PROGRESS","progress":14,"message":"Context geladen..."}
{"task_id":"...","status":"PROGRESS","progress":38,"message":"Frage 1 von 3 generiert..."}
{"task_id":"...","status":"PROGRESS","progress":62,"message":"Frage 2 von 3 generiert..."}
{"task_id":"...","status":"PROGRESS","progress":86,"message":"Frage 3 von 3 generiert..."}
{"task_id":"...","status":"SUCCESS","progress":100,"result":{"exam_id":"...","questions":[...]}}
```

- [ ] **Step 5: Final commit**

```bash
git add .
git commit -m "chore: TF-208 Phase 2 vollständig implementiert und getestet"
```
