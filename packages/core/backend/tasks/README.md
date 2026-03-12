# 🚀 Celery Tasks - Asynchrone Verarbeitung

Dieses Verzeichnis enthält alle Celery Tasks für asynchrone Verarbeitung in ExamCraft AI.

## 📋 Übersicht

| Task | Datei | Beschreibung | Queue | Timeout |
|------|-------|-------------|-------|---------|
| `process_document` | `document_tasks.py` | Verarbeite Dokument mit Docling | `document_processing` | 1h |
| `create_embeddings` | `rag_tasks.py` | Erstelle RAG Embeddings | `rag_embedding` | 30m |
| `cleanup_sessions` | `session_cleanup.py` | Cleanup alte Sessions | `default` | 5m |

## 📄 document_tasks.py

### process_document

Haupttask für die asynchrone Dokumentenverarbeitung.

**Signatur:**
```python
@celery_app.task(bind=True, base=DocumentProcessingTask)
def process_document(self, document_id: str, user_id: str) -> Dict[str, Any]
```

**Parameter:**
- `document_id` (str): UUID des Dokuments
- `user_id` (str): UUID des Benutzers

**Rückgabe:**
```python
{
    "success": True,
    "document_id": "abc-123",
    "title": "Example Document",
    "chunks": 45,
    "embedding_task_id": "xyz-789"
}
```

**Workflow:**
1. Lade Dokument aus Database
2. Setze Status auf `PROCESSING`
3. Verarbeite mit Docling Service
4. Speichere Metadaten (title, content, page_count)
5. Erstelle Chunks mit RAG Service
6. Dispatch `create_embeddings` Task
7. Setze Status auf `COMPLETED`
8. Bei Fehler: Status auf `FAILED`, Retry nach 60s

**Retry-Logik:**
- Max 3 Retries
- Exponential Backoff: 60s, 120s, 240s
- Automatisch bei Exception

**Beispiel-Verwendung:**

```python
from tasks.document_tasks import process_document

# Dispatch Task
task = process_document.apply_async(
    args=[str(document.id), str(user.id)],
    countdown=0,  # Sofort starten
    priority=5    # Höhere Priorität
)

# Task ID speichern
document.task_id = task.id
db.commit()

# Status später abrufen
from celery.result import AsyncResult
result = AsyncResult(task.id, app=celery_app)
print(result.state)  # PENDING, STARTED, SUCCESS, FAILURE
```

## 🧠 rag_tasks.py

### create_embeddings

Task für die Erstellung von RAG Vector Embeddings.

**Signatur:**
```python
@celery_app.task(name="tasks.rag_tasks.create_embeddings")
def create_embeddings(document_id: str, chunks: List[str]) -> Dict[str, Any]
```

**Parameter:**
- `document_id` (str): UUID des Dokuments
- `chunks` (List[str]): Liste von Text-Chunks

**Rückgabe:**
```python
{
    "success": True,
    "document_id": "abc-123",
    "chunks_embedded": 45
}
```

**Workflow:**
1. Lade RAG Service
2. Erstelle Embeddings für alle Chunks
3. Speichere in Qdrant Vector Database
4. Update Document Status
5. Bei Fehler: Log Error und Retry

**Beispiel-Verwendung:**

```python
from tasks.rag_tasks import create_embeddings

# Dispatch Task (normalerweise von process_document)
task = create_embeddings.apply_async(
    args=[str(document.id), chunks],
    countdown=5  # 5 Sekunden Verzögerung
)
```

## ⏰ session_cleanup.py

### cleanup_sessions

Scheduled Task für die Bereinigung alter Sessions.

**Signatur:**
```python
@celery_app.task(name="tasks.session_cleanup.cleanup_sessions")
def cleanup_sessions() -> Dict[str, Any]
```

**Workflow:**
1. Finde Sessions älter als 24 Stunden
2. Lösche aus Redis
3. Lösche aus Database
4. Log Statistiken

**Scheduling:**
```python
# celery_app.py
celery_app.conf.beat_schedule = {
    'cleanup-sessions': {
        'task': 'tasks.session_cleanup.cleanup_sessions',
        'schedule': crontab(hour=2, minute=0),  # Täglich um 2:00 Uhr
    },
}
```

## 🔧 Task Configuration

### Queue Definition

```python
# celery_app.py
celery_app.conf.task_queues = (
    Queue(
        "document_processing",
        default_exchange,
        routing_key="document.process",
        durable=True,
        queue_arguments={"x-max-priority": 10}
    ),
    Queue(
        "rag_embedding",
        default_exchange,
        routing_key="rag.embed",
        durable=True
    ),
)
```

### Task Routes

```python
celery_app.conf.task_routes = {
    "tasks.document_tasks.process_document": {
        "queue": "document_processing",
        "routing_key": "document.process",
    },
    "tasks.rag_tasks.create_embeddings": {
        "queue": "rag_embedding",
        "routing_key": "rag.embed",
    },
}
```

## 📊 Monitoring

### Task Status Abrufen

```python
from celery.result import AsyncResult

task = AsyncResult(task_id, app=celery_app)

# Status
print(task.state)  # PENDING, STARTED, SUCCESS, FAILURE, RETRY

# Ergebnis
if task.successful():
    print(task.result)

# Fehler
if task.failed():
    print(task.info)  # Exception
```

### RabbitMQ Queue Status

```bash
# Über Management UI
http://localhost:15672 → Queues Tab

# Oder CLI
docker exec examcraft-rabbitmq rabbitmqctl list_queues name messages consumers
```

### Celery Worker Status

```bash
# Aktive Tasks
celery -A celery_app inspect active

# Registered Tasks
celery -A celery_app inspect registered

# Worker Stats
celery -A celery_app inspect stats
```

## 🧪 Testing

### Unit Tests

```bash
pytest tests/test_celery_tasks.py -v
```

### Test-Beispiel

```python
def test_process_document_task_success():
    """Test successful document processing"""
    with patch('tasks.document_tasks.SessionLocal') as mock_session:
        # Setup mocks
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        # Execute task
        result = process_document(
            document_id="test-id",
            user_id="user-id"
        )

        # Verify
        assert result["success"] is True
        assert result["document_id"] == "test-id"
```

## 🐛 Troubleshooting

### Task wird nicht ausgeführt

```bash
# 1. Worker läuft?
docker ps | grep celery_worker

# 2. Queue hat Tasks?
docker exec examcraft-rabbitmq rabbitmqctl list_queues

# 3. Worker Logs
docker logs examcraft-celery-worker | grep ERROR
```

### Task Timeout

```bash
# Erhöhe Timeout in celery_app.py
celery_app.conf.task_time_limit = 3600  # 1 Stunde
celery_app.conf.task_soft_time_limit = 3300  # 55 Minuten
```

### Task Retry Loop

```bash
# Logs anschauen
docker logs examcraft-celery-worker | grep "Retry"

# Max Retries reduzieren
class DocumentProcessingTask(Task):
    retry_kwargs = {"max_retries": 1}  # Statt 3
```

## 📚 Best Practices

1. **Idempotent Tasks**: Tasks sollten sicher mehrfach ausgeführt werden
2. **Error Handling**: Immer try/except mit aussagekräftigen Fehlern
3. **Logging**: Ausreichend Logging für Debugging
4. **Timeouts**: Realistische Timeouts setzen
5. **Monitoring**: Task Status regelmäßig überprüfen
6. **Testing**: Unit Tests für alle Tasks schreiben

## 🔗 Weitere Ressourcen

- [Celery Dokumentation](https://docs.celeryproject.org/)
- [RabbitMQ Dokumentation](https://www.rabbitmq.com/documentation.html)
- [ExamCraft Async Processing Guide](../../docs/ASYNC_DOCUMENT_PROCESSING.md)
- [Backend README](../README.md)
