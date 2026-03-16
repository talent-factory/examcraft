# TF-208: Async Task Status Tracking — WebSocket Design

**Datum:** 2026-03-16
**Issue:** [TF-208](https://linear.app/talent-factory/issue/TF-208)
**Branch:** `feature/tf-208-backend-async-task-status-tracking-celery-task-progress-with`
**Status:** Design approved

---

## Zusammenfassung

Echtzeit-Fortschrittsanzeige für asynchrone Celery-Tasks (aktuell: Dokumentverarbeitung) via WebSocket. Der Client verbindet sich nach dem Starten eines Tasks mit einem WebSocket-Endpoint und erhält granulare Progress-Updates bis zur Fertigstellung oder einem Fehler.

---

## Architektur

### Komponenten

```
Frontend                    Backend (FastAPI)              Celery Worker         Redis
   |                              |                              |                  |
   |-- WS /ws/tasks/{id}?token -->|                              |                  |
   |                              |-- JWT validieren             |                  |
   |                              |-- loop every 1s:             |                  |
   |                              |   AsyncResult(task_id) ----->|                  |
   |                              |                              |-- task state ---->|
   |                              |<-----------------------------|<-- state ---------|
   |<-- {"status","progress"} ----|                              |                  |
   |                              |                              |                  |
   |   (loop bis SUCCESS/FAIL)    |                              |                  |
```

### Ansatz: Pull-based WebSocket (Option A)

Der WebSocket-Endpoint pollt Redis alle 1 Sekunde via Celery `AsyncResult` und pusht den Status an den Client. Dieser Ansatz wurde gegenüber Redis Pub/Sub (Option B) gewählt, da er für den aktuellen Use-Case (Tasks dauern 10-30s) ausreichend ist und deutlich einfacher zu implementieren und zu testen ist.

---

## Neue Dateien

### `packages/core/backend/api/v1/websocket.py`

WebSocket-Endpoint mit `ConnectionManager`:

```python
@router.websocket("/ws/tasks/{task_id}")
async def task_progress_websocket(
    websocket: WebSocket,
    task_id: str,
    token: str = Query(...)
):
    """Echtzeit Task-Fortschritt via WebSocket"""
```

- JWT-Validierung via Query-Parameter `?token=<jwt>`
- Ungültiger Token → sofortiges Schliessen mit Code `1008`
- Poll-Intervall: 1 Sekunde
- Timeout: 30 Sekunden bei PENDING ohne Fortschritt
- Bei SUCCESS/FAILURE: finale Message senden, dann Connection schliessen

### `packages/core/backend/schemas/task.py`

Pydantic-Schemas für Task-Status:

```python
class TaskStatus(str, Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    PROGRESS = "PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"

class TaskStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    progress: int = Field(ge=0, le=100)
    message: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
```

---

## Geänderte Dateien

### `packages/core/backend/tasks/document_tasks.py`

`ProgressTask` Base Class mit granularen Updates:

| Step | Progress | Message (Deutsch) |
|------|----------|--------------------|
| 0 | 0% | Starte Verarbeitung... |
| 1 | 10% | Dokument wird geladen... |
| 2 | 20% | Text wird extrahiert... |
| 3 | 30% | Docling-Verarbeitung läuft... |
| 4–8 | 40–80% | Vektoren werden erstellt... |
| 9 | 90% | In Datenbank speichern... |
| 10 | 100% | Abgeschlossen! |

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

### `packages/core/backend/main.py`

WebSocket-Router registrieren (analog zu bestehenden Routers).

### `packages/core/backend/celery_app.py`

Keine Änderungen nötig — `task_track_started=True` ist bereits gesetzt.

---

## WebSocket Message Format

```json
// Progress-Update
{
  "status": "PROGRESS",
  "progress": 40,
  "message": "Docling-Verarbeitung läuft..."
}

// Erfolgreich abgeschlossen
{
  "status": "SUCCESS",
  "progress": 100,
  "result": {"document_id": "123", "title": "Mein Dokument"}
}

// Fehler
{
  "status": "FAILURE",
  "progress": 0,
  "error": "Fehlermeldung"
}
```

---

## Authentifizierung

JWT-Token als Query-Parameter: `/ws/tasks/{task_id}?token=<jwt>`

- HTTP-Headers funktionieren im Browser bei WebSocket-Verbindungen nicht
- Bestehender `get_current_active_user`-Mechanismus wird für WS-Kontext angepasst
- Ungültiger/abgelaufener Token → WebSocket-Close mit Code `1008` (Policy Violation)

---

## Fehlerbehandlung

| Szenario | Verhalten |
|----------|-----------|
| `WebSocketDisconnect` | Sauberes Cleanup, kein Error-Log |
| JWT ungültig/abgelaufen | Close mit Code `1008` |
| Task-ID unbekannt (30s PENDING) | Timeout-Message, dann Connection schliessen |
| Celery Worker down | PENDING bleibt → Timeout greift nach 30s |

---

## Tests (`packages/core/backend/tests/test_websocket.py`)

- `test_websocket_connection()` — Verbindungsaufbau mit gültigem Token
- `test_websocket_invalid_token()` — Ablehnung bei ungültigem JWT
- `test_task_progress_updates()` — Progress-Messages korrekt übertragen
- `test_websocket_disconnect_handling()` — Sauberes Cleanup bei Disconnect
- `test_celery_task_progress()` — `ProgressTask` sendet korrekte States

---

## Nicht im Scope

- Polling-Endpoint (Option C) — nicht implementiert, WebSocket reicht
- Redis Pub/Sub (Option B) — nicht nötig für aktuellen Use-Case
- Load Testing (100+ gleichzeitige Connections) — separates Backlog-Item
- Frontend-Integration — separates Ticket
