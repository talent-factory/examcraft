# TF-208: Question Generation Async Progress — WebSocket Design

**Datum:** 2026-03-18
**Issue:** [TF-208](https://linear.app/talent-factory/issue/TF-208)
**Branch:** `feature/tf-208-backend-async-task-status-tracking-celery-task-progress-with`
**Status:** Design approved

---

## Zusammenfassung

Echtzeit-Fortschrittsanzeige für die asynchrone Fragengenerierung via WebSocket. Die Fragengenerierung wird von einem synchronen FastAPI-Endpoint in einen Celery Task ausgelagert. Der Client erhält sofort eine `task_id` und verbindet sich mit dem bestehenden WebSocket-Endpoint, um den Fortschritt Frage-für-Frage zu verfolgen.

**Vorbedingung:** Der WebSocket-Endpoint (`/ws/tasks/{task_id}`) und die `ProgressTask`-Basisklasse wurden bereits in TF-208 Phase 1 implementiert. Diese Spec beschreibt Phase 2: Fragengenerierung.

---

## Architektur

```
Frontend                    Backend (FastAPI)              Celery Worker         Redis (DB 3)
   |                              |                              |                  |
   |-- POST /generate-exam -----> |                              |                  |
   |                              |-- QuestionGenerationJob      |                  |
   |                              |   in DB speichern            |                  |
   |                              |-- generate_questions_task    |                  |
   |                              |   .apply_async() ----------->|                  |
   |<-- { task_id: "abc-123" } ---|                              |                  |
   |                              |                              |                  |
   |-- WS /ws/tasks/abc-123 ----> |                              |                  |
   |   {"token": "..."}           |-- JWT + Ownership-Check      |                  |
   |                              |   (QuestionGenerationJob)    |                  |
   |                              |-- poll AsyncResult every 1s: |                  |
   |<-- PROGRESS 14% ------------|<-- Frage 1/5 ---------------- |<-- state --------|
   |<-- PROGRESS 28% ------------|<-- Frage 2/5 ---------------- |                  |
   |   ...                        |                              |                  |
   |<-- SUCCESS + questions ------|                              |                  |
   |                              |-- Connection schliessen      |                  |
```

**Wichtig:** `QuestionGenerationJob` wird in DB gespeichert, **bevor** `apply_async()` aufgerufen wird. Damit ist beim WebSocket-Verbindungsaufbau immer ein Ownership-Record vorhanden.

---

## Neue Dateien

### `packages/core/backend/models/question_generation_job.py`

```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from database import Base


class QuestionGenerationJob(Base):
    __tablename__ = "question_generation_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
```

### `packages/core/backend/tasks/question_tasks.py`

```python
from celery_app import celery_app
from tasks.document_tasks import ProgressTask, run_async
import logging

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    base=ProgressTask,
    name="tasks.question_tasks.generate_questions",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 30},
)
def generate_questions_task(self, request_data: dict, user_id: str) -> dict:
    """
    Asynchrone Fragengenerierung mit per-Frage Progress-Updates.

    Args:
        request_data: Serialisierter RAGExamRequest als dict
        user_id: ID des Users (für Logging)

    Returns:
        Dict mit exam_id, topic, questions, generation_time, quality_metrics
    """
    from premium.services.rag_service import RAGService, RAGExamRequest

    rag_request = RAGExamRequest(**request_data)
    question_count = rag_request.question_count
    # total_steps = 1 (Step 0 vom Task) + 1 (Context) + N (Fragen)
    total_steps = question_count + 2

    # Step 0: Task-Start — vom Celery Task emittiert (nicht vom Callback)
    self.update_progress(0, total_steps, "Starte Fraggenerierung...")

    # Progress-Callback für generate_rag_exam — delegiert an vorhandene update_progress
    def progress_callback(current: int, total: int, message: str) -> None:
        self.update_progress(current, total_steps, message)

    # Premium RAGService instanziieren (lazy import — funktioniert im Worker, da /app/premium vorhanden)
    rag_service = RAGService()
    result = run_async(
        rag_service.generate_rag_exam(rag_request, progress_callback=progress_callback)
    )

    return {
        "exam_id": result.exam_id,
        "topic": result.topic,
        "questions": [q.model_dump() for q in result.questions],
        "generation_time": result.generation_time,
        "quality_metrics": result.quality_metrics,
    }
```

**`run_async()` Definition** (bereits in `tasks/document_tasks.py` vorhanden):

```python
def run_async(coro):
    """Helper um async Code in synchronem Celery-Worker-Kontext auszuführen."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)
```

### `packages/core/backend/alembic/versions/<hash>_add_question_generation_jobs.py`

Alembic-Migration für die neue `question_generation_jobs`-Tabelle (wird via `alembic revision --autogenerate` erzeugt).

---

## Geänderte Dateien

### `packages/premium/backend/services/rag_service.py`

**Optionaler `progress_callback`-Parameter in `generate_rag_exam`:**

```python
async def generate_rag_exam(
    self,
    request: RAGExamRequest,
    progress_callback=None,  # Optional[Callable[[int, int, str], None]]
) -> RAGExamResponse:
    # total_steps wird vom Caller (Celery Task) berechnet und via progress_callback implizit verwendet
    # Callback-Steps: 1 (Context) + N (Fragen) — Step 0 wird vom Task selbst emittiert

    context = await self.retrieve_context(...)
    if progress_callback:
        progress_callback(1, request.question_count + 2, "Context geladen...")

    questions = []
    for i in range(request.question_count):
        question = await self.generate_question(...)
        questions.append(question)
        if progress_callback:
            progress_callback(
                i + 2,
                request.question_count + 2,
                f"Frage {i + 1} von {request.question_count} generiert...",
            )

    # ... Rest der Methode unverändert
```

### `packages/core/backend/api/rag_exams.py`

**Breaking Change:** `POST /generate-exam` gibt neu `GenerateExamTaskResponse` zurück statt `RAGExamResponseModel`.

```python
from tasks.question_tasks import generate_questions_task
from models.question_generation_job import QuestionGenerationJob
from schemas.task import GenerateExamTaskResponse

@router.post("/generate-exam", response_model=GenerateExamTaskResponse)
async def generate_rag_exam(
    request: RAGExamRequest,
    current_user: User = Depends(require_permission("create_questions")),
    db: Session = Depends(get_db),
):
    request_data = request.model_dump(mode="json")

    # Ownership-Record VOR apply_async erstellen (damit WebSocket-Check immer findet)
    import uuid
    task_id = str(uuid.uuid4())
    job = QuestionGenerationJob(task_id=task_id, user_id=current_user.id)
    db.add(job)
    db.commit()

    generate_questions_task.apply_async(
        args=[request_data, str(current_user.id)],
        task_id=task_id,
        queue="question_generation",
    )

    return GenerateExamTaskResponse(
        task_id=task_id,
        message="Fraggenerierung gestartet",
    )
```

**Bestehende Tests:** `test_api_claude.py` und andere Tests, die `POST /generate-exam` aufrufen und `questions` im Response erwarten, müssen aktualisiert werden.

### `packages/core/backend/schemas/task.py`

**Neues Schema:**

```python
class GenerateExamTaskResponse(BaseModel):
    task_id: str
    message: str
```

### `packages/core/backend/api/v1/websocket.py`

**Erweiterter `_check_task_ownership()`:**

Da `QuestionGenerationJob` immer vor `apply_async()` in DB geschrieben wird, gibt es keinen legitimen Fall wo eine gültige `task_id` unbekannt ist. Unbekannte `task_id` werden abgelehnt.

```python
async def _check_task_ownership(websocket, task_id, user):
    db = SessionLocal()
    try:
        # Check 1: Dokument-Task
        document = db.query(Document).filter(Document.task_id == task_id).first()
        if document:
            if document.user_id != user.id:
                logger.warning(f"Ownership-Verletzung: User {user.id}, Task {task_id}")
                await websocket.close(code=1008)
                return False
            return True

        # Check 2: Question-Generation-Task
        from models.question_generation_job import QuestionGenerationJob
        job = db.query(QuestionGenerationJob).filter(
            QuestionGenerationJob.task_id == task_id
        ).first()
        if job:
            if job.user_id != user.id:
                logger.warning(f"Ownership-Verletzung: User {user.id}, Task {task_id}")
                await websocket.close(code=1008)
                return False
            return True

        # Unbekannte task_id — ablehnen (kein legitimer Fall)
        logger.warning(f"Unbekannte task_id {task_id} von User {user.id}")
        await websocket.close(code=1008)
        return False

    except Exception as e:
        logger.error(f"Ownership-Check Fehler: {e}")
        await websocket.close(code=1008)
        return False
    finally:
        db.close()
```

### `packages/core/backend/celery_app.py`

```python
include=[
    "tasks.document_tasks",
    "tasks.question_tasks",   # NEU
    "tasks.session_cleanup",
],
```

Task-Route (exakter Task-Name muss mit `name=` auf dem Decorator übereinstimmen):

```python
"tasks.question_tasks.generate_questions": {
    "queue": "question_generation",
    "routing_key": "question.generate",
},
```

---

## Progress-Steps (Beispiel: 5 Fragen)

`total_steps = question_count + 2 = 7`

| Emittiert von | Step | Progress | Message |
|---|------|----------|---------|
| Celery Task | 0/7 | 0% | Starte Fraggenerierung... |
| Callback | 1/7 | 14% | Context geladen... |
| Callback | 2/7 | 28% | Frage 1 von 5 generiert... |
| Callback | 3/7 | 43% | Frage 2 von 5 generiert... |
| Callback | 4/7 | 57% | Frage 3 von 5 generiert... |
| Callback | 5/7 | 71% | Frage 4 von 5 generiert... |
| Callback | 6/7 | 86% | Frage 5 von 5 generiert... |
| Celery SUCCESS | — | 100% | (SUCCESS-State, kein PROGRESS-Update) |

---

## WebSocket Message Format

```json
// Progress-Update
{
  "task_id": "abc-123",
  "status": "PROGRESS",
  "progress": 28,
  "message": "Frage 1 von 5 generiert..."
}

// Erfolgreich abgeschlossen
{
  "task_id": "abc-123",
  "status": "SUCCESS",
  "progress": 100,
  "result": {
    "exam_id": "...",
    "topic": "Heapsort",
    "questions": [...],
    "generation_time": 12.3,
    "quality_metrics": {...}
  }
}

// Fehler
{
  "task_id": "abc-123",
  "status": "FAILURE",
  "progress": 0,
  "error": "No relevant context found for topic: ..."
}
```

---

## Fehlerbehandlung

| Szenario | Verhalten |
|----------|-----------|
| Premium-Service nicht verfügbar (Core-Modus) | `ImportError` → FAILURE mit klarer Message |
| Kein Context für Thema gefunden | FAILURE mit Fehlermeldung aus rag_service |
| Claude API Rate Limit | Retry (max 2×, countdown 30s) |
| `WebSocketDisconnect` | Sauberes Cleanup, Task läuft im Worker weiter |
| Ownership-Verletzung | Close mit Code `1008` |
| Unbekannte `task_id` | Close mit Code `1008` |

---

## Breaking Change

`POST /generate-exam` gibt neu `{ task_id, message }` zurück statt `{ questions, ... }`.

- Der alte `RAGExamResponseModel` wird entfernt (keine Versionierung, kein Flag)
- **Betroffene Tests:** `test_api_claude.py` und andere Tests die direkt Fragen im Response erwarten → müssen auf den neuen `task_id`-Response aktualisiert werden
- **Frontend-Migration:** Separates Ticket erforderlich

---

## Tests

### `packages/core/backend/tests/test_question_tasks.py`
- `test_generate_questions_task_dispatches_with_task_id()` — Task wird mit vorgegebener `task_id` dispatcht
- `test_generate_questions_task_creates_ownership_job()` — `QuestionGenerationJob` in DB vor `apply_async`
- `test_generate_questions_task_progress_steps()` — 7 Progress-Updates bei 5 Fragen (step 0 vom Task, steps 1–6 vom Callback)
- `test_generate_questions_task_response_model()` — Response enthält `task_id` und `message`

### `packages/core/backend/tests/test_websocket_question_ownership.py`
- `test_question_task_ownership_allowed()` — Owner kann Task tracken
- `test_question_task_ownership_denied()` — Anderer User wird abgelehnt (Code 1008)
- `test_unknown_task_id_denied()` — Unbekannte `task_id` wird abgelehnt (Code 1008)

---

## Nicht im Scope

- **Frontend-Integration** — separates Ticket
- **Load Testing** — separates Backlog-Item
- **`rag_tasks.py` Instrumentierung** — separates Backlog-Item
- **Core-Modus Fallback** — im Core-Modus schlägt der Import fehl → FAILURE; kein Polling-Fallback
