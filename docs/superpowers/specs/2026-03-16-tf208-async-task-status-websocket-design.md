# TF-208: Async Task Status Tracking — WebSocket Design

**Datum:** 2026-03-16
**Issue:** [TF-208](https://linear.app/talent-factory/issue/TF-208)
**Branch:** `feature/tf-208-backend-async-task-status-tracking-celery-task-progress-with`
**Status:** Design approved

---

## Zusammenfassung

Echtzeit-Fortschrittsanzeige für asynchrone Celery-Tasks (aktuell: Dokumentverarbeitung) via WebSocket. Der Client verbindet sich nach dem Starten eines Tasks mit einem WebSocket-Endpoint und erhält granulare Progress-Updates bis zur Fertigstellung oder einem Fehler.

**Pattern:** WebSocket + serverseitiges Polling — der Server pollt Redis (`AsyncResult`) alle 1s via `run_in_executor` und pusht den Status an den Client. Dies ist kein event-driven Push-Modell (kein Redis Pub/Sub), sondern ein poll-basierter Ansatz, der für Single-Instance-Deployments (Fly.io, Docker Compose) optimal geeignet ist.

---

## Architektur

```
Frontend                    Backend (FastAPI)              Celery Worker         Redis (DB 3)
   |                              |                              |                  |
   |-- WS /ws/tasks/{task_id} --> |                              |                  |
   |   erste Message: {"token": "..."}                           |                  |
   |                              |-- decode_token()             |                  |
   |                              |-- is_token_revoked() ------> |                  |
   |                              |-- load user from DB          |                  |
   |                              |-- Document.task_id lookup    |                  |
   |                              |-- Ownership check            |                  |
   |                              |-- run_in_executor every 1s:  |                  |
   |                              |   AsyncResult(task_id) ----->|                  |
   |                              |                              |-- task state ---->|
   |                              |<-----------------------------|<-- state ---------|
   |<-- TaskStatusMessage JSON ---|                              |                  |
   |                              |                              |                  |
   |   (loop bis terminal state)  |                              |                  |
   |                              |-- finale Message senden      |                  |
   |                              |-- Connection schliessen      |                  |
```

---

## Neue Dateien

### `packages/core/backend/api/v1/websocket.py`

**`ConnectionManager`** — Modul-Level-Singleton (einmal instanziiert, für alle Connections):

```python
manager = ConnectionManager()  # Modul-Level-Singleton
```

**Authentifizierungs-Flow (inline, kein FastAPI `Depends`):**

Da WebSocket-Handler keine FastAPI `Depends`-Abhängigkeiten für mid-connection Messages verwenden können, wird die Authentifizierungslogik inline repliziert:

1. Client verbindet sich mit `/ws/tasks/{task_id}` (kein Token in der URL — verhindert JWT in Server-Logs)
2. Client sendet als **erste WebSocket-Message**: `{"token": "<jwt>"}`
3. Server ruft direkt auf:
   - `AuthService.decode_token(token)` → extrahiert `jti`, `user_id`
   - `AuthService.is_token_revoked(jti, db)` → Redis-Blacklist-Check
   - `db.query(User).filter(User.id == user_id).first()` → User laden
4. Bei ungültigem/abgelaufenem/revokiertem Token → `await websocket.close(code=1008)`
5. Ownership-Check: `db.query(Document).filter(Document.task_id == task_id).first()` → `document.user_id == current_user.id`
6. Bei fehlender Ownership → `await websocket.close(code=1008)`

**DB-Session-Lifecycle:**

- Eine `SessionLocal()`-Session wird für Auth + Ownership-Check erstellt und **danach sofort geschlossen**
- Der Polling-Loop hält **keine** DB-Session offen

**Polling-Loop:**

```python
while True:
    # Blockierender Redis-Call in Thread-Pool ausgelagert
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: AsyncResult(task_id, app=celery_app)
    )
    state = result.state
    info = result.info or {}

    if state == "PROGRESS":
        await websocket.send_json({...})
    elif state in ("SUCCESS", "FAILURE", "REVOKED"):
        await websocket.send_json({...})
        await websocket.close()
        break

    await asyncio.sleep(1)
```

- Poll-Intervall: 1 Sekunde
- **Timeout: 120 Sekunden** bei PENDING (> 60s Retry-Countdown von `DocumentProcessingTask`)
- Bei terminalem State (SUCCESS, FAILURE, REVOKED): finale Message senden, dann Connection serverseitig schliessen
- Bei `WebSocketDisconnect`: sauberes Cleanup aus `ConnectionManager`, kein Error-Log

> **Begründung Timeout 120s:** `DocumentProcessingTask` hat `retry_kwargs = {"max_retries": 3, "countdown": 60}`. Bei einem Retry bleibt der State 60s auf PENDING. Ein Timeout von 30s würde die Connection vorzeitig schliessen. 120s gibt Raum für den ersten Retry-Zyklus.

**Progress-Delivery-Mechanismus:**

Der Celery Worker schreibt via `self.update_state(state="PROGRESS", meta={...})` in Redis (DB 3, Result Backend). Der WebSocket-Polling-Loop liest diesen State via `AsyncResult.state` und `AsyncResult.info`. Es gibt keine direkte Verbindung zwischen Celery Worker und WebSocket — Redis ist der Kommunikationskanal.

### `packages/core/backend/schemas/task.py`

```python
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    PROGRESS = "PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    REVOKED = "REVOKED"
    RETRY = "RETRY"


class TaskStatusMessage(BaseModel):
    """WebSocket-Message Format für Task-Fortschritt"""
    task_id: str
    status: TaskStatus
    progress: int = Field(ge=0, le=100)
    message: Optional[str] = None
    result: Optional[Any] = None   # Nur bei SUCCESS
    error: Optional[str] = None    # Nur bei FAILURE
```

---

## Geänderte Dateien

### `packages/core/backend/celery_app.py`

**Redis DB-Index-Konflikt beheben:**

Aktuelle Belegung:
- DB 0: Sessions (`redis_service.py`)
- DB 1: Token-Blacklist (`redis_service.py` — `REDIS_DB_BLACKLIST = 1`)
- DB 2: Rate-Limiting (`redis_service.py`)
- DB 1: Celery Result Backend ← **Konflikt!**

Änderung: Celery Result Backend auf **DB 3** verschieben:

```python
backend=os.getenv(
    "CELERY_RESULT_BACKEND",
    os.getenv("REDIS_URL", "redis://redis:6379/3")  # DB 3: frei von anderen Services
),
```

### `packages/core/backend/tasks/document_tasks.py`

`ProgressTask` Base Class:

```python
class ProgressTask(Task):
    def update_progress(self, current: int, total: int, message: str = ""):
        self.update_state(
            state="PROGRESS",
            meta={
                "current": current,
                "total": total,
                "progress": int((current / total) * 100),
                "message": message,
            }
        )
```

**Progress-Steps** (deutsche Messages):

| Step | Progress | Message |
|------|----------|---------|
| 0 | 0% | Starte Verarbeitung... |
| 1 | 10% | Dokument wird geladen... |
| 2 | 20% | Text wird extrahiert... |
| 3 | 30% | Docling-Verarbeitung läuft... |
| 4–8 | 40–80% | Vektoren werden erstellt... |
| 9 | 90% | In Datenbank speichern... |
| 10 | 100% | Abgeschlossen! |

**Progress-Updates** werden direkt im Task (nicht via Callback in den Service) als Klammern um `run_async()` gesetzt:

```python
@celery_app.task(bind=True, base=ProgressTask, ...)
def process_document(self, document_id: str, user_id: str):
    self.update_progress(0, 10, "Starte Verarbeitung...")

    # DB-Load
    self.update_progress(1, 10, "Dokument wird geladen...")
    document = db.query(Document)...

    self.update_progress(2, 10, "Text wird extrahiert...")
    self.update_progress(3, 10, "Docling-Verarbeitung läuft...")

    # Hauptverarbeitung (Docling + Vektoren) — Steps 4-8 als Bracket
    self.update_progress(4, 10, "Vektoren werden erstellt...")
    result = run_async(document_service.process_document_with_vectors(...))
    self.update_progress(8, 10, "Vektoren werden erstellt...")

    self.update_progress(9, 10, "In Datenbank speichern...")
    db.commit()

    self.update_progress(10, 10, "Abgeschlossen!")
    return {...}
```

> **Begründung Bracket-Ansatz statt Callback:** Da `process_document_with_vectors` asynchron ist und auf dem Celery-Worker-Event-Loop läuft (nicht auf dem FastAPI-Event-Loop), ist ein direkter Callback technisch aufwändiger. Da die Zwischenschritte (Docling, Vektoren) als Black-Box laufen, bilden grobe Brackets ausreichende Granularität.

### `packages/core/backend/main.py`

WebSocket-Router registrieren (analog zu bestehenden Routers).

---

## WebSocket Message Format

```json
// Progress-Update
{
  "task_id": "abc-123",
  "status": "PROGRESS",
  "progress": 40,
  "message": "Docling-Verarbeitung läuft..."
}

// Erfolgreich abgeschlossen
{
  "task_id": "abc-123",
  "status": "SUCCESS",
  "progress": 100,
  "result": {"document_id": 42, "title": "Mein Dokument"}
}

// Fehler
{
  "task_id": "abc-123",
  "status": "FAILURE",
  "progress": 0,
  "error": "Fehlermeldung"
}
```

---

## Fehlerbehandlung

| Szenario | Verhalten |
|----------|-----------|
| `WebSocketDisconnect` | Sauberes Cleanup aus ConnectionManager, kein Error-Log |
| JWT ungültig/abgelaufen | Close mit Code `1008` |
| JWT revoziert (Redis-Blacklist) | Close mit Code `1008` |
| Task-Ownership verletzt | Close mit Code `1008` |
| Task-ID unbekannt (120s PENDING) | Timeout-Message, dann Connection schliessen |
| Celery Worker down (Retry läuft) | PENDING/RETRY bleibt → Timeout nach 120s |
| Terminaler State (SUCCESS/FAILURE/REVOKED) | Finale Message senden, Connection serverseitig schliessen |

---

## Nicht im Scope

- **Polling-Endpoint** (Option C) — WebSocket reicht für den aktuellen Use-Case
- **Redis Pub/Sub** (Option B) — nicht nötig für Single-Instance-Deployment
- **`rag_tasks.py` Instrumentierung** (`create_embeddings`, `update_embeddings`) — separates Backlog-Item
- **Load Testing** (100+ gleichzeitige Connections) — separates Backlog-Item
- **Frontend-Integration** — separates Ticket

---

## Tests (`packages/core/backend/tests/test_websocket.py`)

- `test_websocket_connection_valid_token()` — Verbindungsaufbau + Token-Handshake erfolgreich
- `test_websocket_invalid_token()` — Ablehnung bei ungültigem JWT, Close `1008`
- `test_websocket_revoked_token()` — Ablehnung bei revoziertem JWT (Redis-Blacklist), Close `1008`
- `test_websocket_wrong_ownership()` — Ablehnung wenn User nicht Document-Owner, Close `1008`
- `test_task_progress_updates()` — PROGRESS-Messages korrekt übertragen
- `test_websocket_disconnect_handling()` — Sauberes Cleanup bei Client-Disconnect
- `test_connection_closed_on_success()` — Connection wird nach SUCCESS serverseitig geschlossen
- `test_connection_closed_on_failure()` — Connection wird nach FAILURE serverseitig geschlossen
- `test_celery_task_progress_steps()` — `ProgressTask.update_progress()` sendet korrekte States mit deutschen Messages
- `test_pending_timeout()` — Connection wird nach 120s PENDING geschlossen
