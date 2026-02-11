# ExamCraft Backend 🚀

FastAPI Backend für ExamCraft AI mit asynchroner Dokumentenverarbeitung, RAG-Integration und RBAC.

## 📋 Inhaltsverzeichnis

- [Quick Start](#quick-start)
- [Architektur](#architektur)
- [Asynchrone Verarbeitung](#asynchrone-verarbeitung)
- [API Endpoints](#api-endpoints)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## 🚀 Quick Start

### 1. Abhängigkeiten installieren

```bash
cd packages/core/backend
pip install -r requirements.txt
```

### 2. Environment konfigurieren

```bash
# .env Datei erstellen
cp .env.example .env

# Wichtige Variablen:
DATABASE_URL=postgresql://examcraft:examcraft_dev@localhost:5432/examcraft  # pragma: allowlist secret
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=amqp://examcraft:secure_password_here@localhost:5672/  # pragma: allowlist secret
CELERY_RESULT_BACKEND=redis://localhost:6379/1
CLAUDE_API_KEY=sk-...  # pragma: allowlist secret
```

### 3. Docker Services starten

```bash
# Vom Projekt-Root
./start-dev.sh --full

# Oder manuell
docker compose --env-file .env -f docker-compose.full.yml up -d
```

### 4. Database Migrations

```bash
cd packages/core/backend
alembic upgrade head
```

### 5. Backend starten

```bash
# Development mit Auto-Reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Oder via Docker (bereits laufend)
docker logs -f examcraft-backend
```

### 6. API testen

```bash
# Swagger UI
http://localhost:8000/docs

# ReDoc
http://localhost:8000/redoc
```

## 🏗️ Architektur

### Verzeichnisstruktur

```
backend/
├── main.py                 # FastAPI App Entry Point
├── database.py             # SQLAlchemy Setup
├── celery_app.py          # Celery Configuration
├── requirements.txt        # Python Dependencies
├── api/                   # API Endpoints
│   ├── auth.py           # Authentication
│   ├── documents.py       # Document Management
│   └── v1/               # Versioned API
├── models/               # SQLAlchemy Models
│   ├── auth.py          # User, Role, Institution
│   ├── document.py       # Document Model
│   └── question_review.py # Review Models
├── services/            # Business Logic
│   ├── auth_service.py
│   ├── document_service.py
│   ├── rag_service.py
│   ├── claude_service.py
│   └── ...
├── tasks/              # Celery Tasks
│   ├── document_tasks.py  # Async Document Processing
│   ├── rag_tasks.py       # RAG Embedding Tasks
│   └── session_cleanup.py # Scheduled Tasks
├── middleware/         # Middleware
│   ├── rbac_middleware.py
│   ├── rate_limit.py
│   └── ...
├── utils/             # Utilities
│   ├── auth_utils.py
│   ├── tenant_utils.py
│   └── ...
├── tests/            # Unit & Integration Tests
│   ├── test_celery_tasks.py
│   ├── test_api_documents.py
│   └── ...
└── alembic/          # Database Migrations
    └── versions/
```

## ⚙️ Asynchrone Verarbeitung

### Celery Tasks

Alle langwierigen Operationen werden als Celery Tasks ausgeführt:

#### 1. Document Processing

```python
# tasks/document_tasks.py
@celery_app.task(bind=True, base=DocumentProcessingTask)
def process_document(self, document_id: str, user_id: str):
    """Verarbeite Dokument mit Docling und erstelle RAG Embeddings"""
    # 1. Lade Dokument aus DB
    # 2. Verarbeite mit Docling
    # 3. Erstelle RAG Chunks
    # 4. Dispatch Embedding Task
    # 5. Update Status
```

**Verwendung:**

```python
# In API Endpoint
task = process_document.apply_async(
    args=[str(document.id), str(user.id)],
    countdown=0  # Sofort starten
)
document.task_id = task.id
```

#### 2. RAG Embeddings

```python
# tasks/rag_tasks.py
@celery_app.task(name="tasks.rag_tasks.create_embeddings")
def create_embeddings(document_id: str, chunks: List[str]):
    """Erstelle Vector Embeddings für Dokument-Chunks"""
    # 1. Lade RAG Service
    # 2. Erstelle Embeddings
    # 3. Speichere in Qdrant
```

### Task Status Abrufen

```python
# In API Endpoint
from celery.result import AsyncResult

task = AsyncResult(document.task_id, app=celery_app)
status = {
    "state": task.state,  # PENDING, STARTED, SUCCESS, FAILURE
    "result": task.result,
    "error": task.info if task.failed() else None
}
```

### Retry-Logik

```python
class DocumentProcessingTask(Task):
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 60}
    retry_backoff = True
    retry_jitter = True
```

## 📡 API Endpoints

### Document Upload

```bash
POST /api/v1/documents/upload
Content-Type: multipart/form-data

# Response
{
  "document_id": "abc-123",
  "filename": "example.pdf",
  "status": "queued",
  "message": "Document queued for processing..."
}
```

### Document Status

```bash
GET /api/v1/documents/{document_id}/status

# Response
{
  "document_id": "abc-123",
  "status": "processing",
  "task_status": {
    "task_id": "xyz-789",
    "state": "STARTED"
  },
  "processing_info": {
    "chunks_created": 45
  }
}
```

### Document List

```bash
GET /api/v1/documents

# Response
{
  "documents": [
    {
      "id": "abc-123",
      "filename": "example.pdf",
      "status": "completed",
      "page_count": 50,
      "created_at": "2025-11-03T14:00:00Z"
    }
  ]
}
```

## 🧪 Testing

### Unit Tests

```bash
# Alle Tests
pytest tests/ -v

# Spezifische Test-Datei
pytest tests/test_celery_tasks.py -v

# Mit Coverage
pytest tests/ --cov=. --cov-report=html
```

### Integration Tests

```bash
# Mit Docker Services
./start-dev.sh --full

# Tests ausführen
pytest tests/test_api_documents.py -v
```

### Test-Struktur

```
tests/
├── test_celery_tasks.py      # Celery Task Tests
├── test_api_documents.py     # Document API Tests
├── test_auth_api.py          # Authentication Tests
├── test_rbac.py              # RBAC Tests
└── conftest.py               # Pytest Fixtures
```

## 🐛 Troubleshooting

### Problem: "ModuleNotFoundError"

```bash
# Lösung: Abhängigkeiten neu installieren
pip install -r requirements.txt --force-reinstall

# Oder im Docker Container
docker exec examcraft-backend pip install -r requirements.txt
```

### Problem: "Database connection refused"

```bash
# Lösung 1: PostgreSQL läuft?
docker ps | grep postgres

# Lösung 2: DATABASE_URL korrekt?
echo $DATABASE_URL

# Lösung 3: Migrations ausführen
alembic upgrade head
```

### Problem: "Celery Worker nicht erreichbar"

```bash
# Logs anschauen
docker logs examcraft-celery-worker

# Worker neu starten
docker restart examcraft-celery-worker

# Status prüfen
docker exec examcraft-celery-worker celery -A celery_app inspect active
```

### Problem: "RabbitMQ Connection Error"

```bash
# RabbitMQ läuft?
docker ps | grep rabbitmq

# RabbitMQ Logs
docker logs examcraft-rabbitmq

# Credentials prüfen
echo $CELERY_BROKER_URL
```

## 📚 Weitere Ressourcen

- [FastAPI Dokumentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Dokumentation](https://docs.sqlalchemy.org/)
- [Celery Dokumentation](https://docs.celeryproject.org/)
- [Alembic Dokumentation](https://alembic.sqlalchemy.org/)
- [ExamCraft Async Processing Guide](../../docs/ASYNC_DOCUMENT_PROCESSING.md)

## 🤝 Contributing

1. Erstelle einen Feature Branch: `git checkout -b feature/TF-XXX-description`
2. Schreibe Tests für neue Features
3. Führe Tests aus: `pytest tests/`
4. Commit mit Conventional Commits: `git commit -m "feat: description"`
5. Push und erstelle Pull Request

## 📝 Code Standards

- **Python**: PEP 8, Type Hints, Docstrings
- **Testing**: pytest mit >80% Coverage
- **Linting**: ruff check
- **Formatting**: ruff format
