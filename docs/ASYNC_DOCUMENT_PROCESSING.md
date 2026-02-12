# 🚀 Asynchrone Dokumentenverarbeitung mit RabbitMQ & Celery

## Übersicht

ExamCraft AI verwendet **RabbitMQ** als Message Broker und **Celery** als Task Queue für asynchrone Dokumentenverarbeitung. Dies löst das Problem der langen Upload-Zeiten (10+ Minuten für große PDFs) durch nicht-blockierende, parallele Verarbeitung.

### Problem (Vorher)
- ❌ Synchrone Verarbeitung blockiert FastAPI Server
- ❌ Benutzer muss 10+ Minuten warten
- ❌ Keine Parallelverarbeitung möglich
- ❌ Keine Fehlerbehandlung/Retry-Logik

### Lösung (Nachher)
- ✅ Asynchrone Verarbeitung mit Celery Workers
- ✅ FastAPI antwortet sofort (< 1 Sekunde)
- ✅ Parallele Verarbeitung mehrerer Dokumente
- ✅ Automatische Retry-Logik mit Exponential Backoff
- ✅ Vollständige Task-Status-Verfolgung

## 🏗️ Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                    DOCUMENT UPLOAD FLOW                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Frontend (React)                                           │
│       ↓                                                      │
│  POST /api/v1/documents/upload                             │
│       ↓                                                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FastAPI Backend                                     │  │
│  │  1. Speichere Datei                                  │  │
│  │  2. Erstelle Document DB Entry (status=QUEUED)      │  │
│  │  3. Dispatch Celery Task                            │  │
│  │  4. Antworte sofort mit task_id                     │  │
│  └──────────────────────────────────────────────────────┘  │
│       ↓                                                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         RabbitMQ Message Queue                       │  │
│  │  Queue: document_processing                         │  │
│  │  - Durable: Ja (Persistenz)                         │  │
│  │  - Priority: High/Normal/Low                        │  │
│  │  - TTL: 1 Stunde                                    │  │
│  └──────────────────────────────────────────────────────┘  │
│       ↓                                                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │      Celery Worker Pool (3 Worker)                  │  │
│  │  1. Hole Task aus Queue                             │  │
│  │  2. Verarbeite mit Docling                          │  │
│  │  3. Erstelle RAG Embeddings                         │  │
│  │  4. Update Document Status (COMPLETED/FAILED)      │  │
│  └──────────────────────────────────────────────────────┘  │
│       ↓                                                      │
│  PostgreSQL + Qdrant                                        │
│  WebSocket für Real-time Status Updates                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Setup & Konfiguration

### 1. Docker Compose Services

Die folgenden Services werden automatisch gestartet:

```bash
./start-dev.sh --full
```

**Services:**
- `rabbitmq` - Message Broker (Port 5672 AMQP, 15672 Management UI)
- `celery_worker` - Task Worker (3 concurrent workers)
- `backend` - FastAPI Server
- `postgres` - Database
- `redis` - Result Backend & Caching
- `qdrant` - Vector Database (nur mit --full)

### 2. Environment Variables

```bash
# .env
CELERY_BROKER_URL=amqp://${RABBITMQ_USER}:${RABBITMQ_PASSWORD}@rabbitmq:5672/
CELERY_RESULT_BACKEND=redis://redis:6379/1
RABBITMQ_USER=examcraft
RABBITMQ_PASSWORD=<strong_password>  # Siehe .env.example
```

### 3. RabbitMQ Management UI

Zugriff auf die RabbitMQ Management Console:

```
URL: http://localhost:15672
Username: examcraft
Password: ${RABBITMQ_PASSWORD}  # Siehe .env
```

**Wichtige Metriken:**
- **Queues**: Anzahl der wartenden Tasks
- **Connections**: Aktive Worker-Verbindungen
- **Channels**: Message-Kanäle
- **Messages**: Durchsatz und Latenz

## 📊 Monitoring & Debugging

### 1. Task Status Abrufen

```bash
# GET /api/v1/documents/{document_id}/status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/documents/123/status
```

**Response:**
```json
{
  "document_id": "123",
  "filename": "example.pdf",
  "status": "processing",
  "task_status": {
    "task_id": "abc-def-123",
    "state": "STARTED",
    "result": null,
    "error": null
  },
  "error_message": null,
  "processing_info": {
    "chunks_created": 45,
    "embedding_task_id": "xyz-789"
  },
  "created_at": "2025-11-03T14:00:00Z",
  "processed_at": null
}
```

### 2. Celery Worker Logs

```bash
# Logs des Celery Workers anschauen
docker compose logs -f celery_worker

# Nur Fehler anzeigen
docker compose logs celery_worker | grep ERROR
```

### 3. RabbitMQ Queue Status

```bash
# Über Management UI
http://localhost:15672 → Queues Tab

# Oder via CLI
docker exec examcraft-rabbitmq rabbitmqctl list_queues name messages consumers
```

### 4. Flower Monitoring Dashboard

Flower ist als Docker-Service integriert und startet automatisch mit `./start-dev.sh --full`.

```
URL: http://localhost:5555
```

**Features:**
- Aktive/abgeschlossene/fehlgeschlagene Tasks in Echtzeit
- Worker-Status, Concurrency und Ressourcen
- Task-Laufzeiten, Retry-History und Ergebnisse
- Queue-Auslastung pro Worker
- Task-Rate-Graphen und Statistiken

**Fly.io Deployment:**
```bash
# Flower deployen
make deploy-flower

# Secrets setzen (einmalig)
fly secrets set CELERY_BROKER_URL="amqp://..." -a examcraft-flower
fly secrets set FLOWER_BASIC_AUTH="admin:secure_password" -a examcraft-flower
```

## 🧪 Testing

### 1. Unit Tests

```bash
cd packages/core/backend

# Alle Celery Tests
pytest tests/test_celery_tasks.py -v

# Spezifischer Test
pytest tests/test_celery_tasks.py::TestDocumentProcessingTask::test_process_document_task_success -v
```

### 2. Integration Test (Manuell)

```bash
# 1. Docker starten
./start-dev.sh --full

# 2. Test-Datei hochladen
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_document.pdf" \
  http://localhost:8000/api/v1/documents/upload

# Response:
# {
#   "document_id": "abc-123",
#   "status": "queued",
#   "message": "Document queued for processing..."
# }

# 3. Status überprüfen (mehrmals)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/documents/abc-123/status

# Status-Progression:
# queued → processing → completed
```

### 3. Performance Test

```bash
# Mehrere Dokumente gleichzeitig hochladen
for i in {1..5}; do
  curl -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@test_document.pdf" \
    http://localhost:8000/api/v1/documents/upload &
done
wait

# RabbitMQ Queue sollte 5 Tasks zeigen
# Worker sollten diese parallel verarbeiten
```

## 🐛 Troubleshooting

### Problem: "Connection refused" zu RabbitMQ

```bash
# Lösung 1: RabbitMQ Service prüfen
docker ps | grep rabbitmq

# Lösung 2: RabbitMQ Logs anschauen
docker logs examcraft-rabbitmq

# Lösung 3: RabbitMQ neu starten
docker restart examcraft-rabbitmq
```

### Problem: Celery Worker startet nicht

```bash
# Logs anschauen
docker logs examcraft-celery-worker

# Häufige Fehler:
# - CELERY_BROKER_URL nicht gesetzt → .env prüfen
# - RabbitMQ nicht erreichbar → RabbitMQ starten
# - Import-Fehler → requirements.txt prüfen
```

### Problem: Tasks werden nicht verarbeitet

```bash
# 1. Queue-Status prüfen
docker exec examcraft-rabbitmq rabbitmqctl list_queues

# 2. Worker-Status prüfen
docker logs examcraft-celery-worker | grep "Ready to accept"

# 3. Task-Fehler prüfen
docker logs examcraft-celery-worker | grep ERROR

# 4. Database-Verbindung prüfen
docker logs examcraft-backend | grep "database"
```

### Problem: Lange Verarbeitungszeiten

```bash
# 1. Worker-Anzahl erhöhen
# docker-compose.yml: --concurrency=5 (statt 3)

# 2. Queue-Priorität prüfen
# Wichtige Tasks sollten höhere Priorität haben

# 3. Worker-Ressourcen prüfen
docker stats examcraft-celery-worker
```

## 📈 Performance-Metriken

### Erwartete Verarbeitungszeiten

| Dokument-Größe | Seiten | Verarbeitungszeit | Status |
|---|---|---|---|
| Klein | 1-10 | 5-10 Sekunden | ✅ |
| Mittel | 10-50 | 30-60 Sekunden | ✅ |
| Groß | 50-100 | 1-2 Minuten | ✅ |
| Sehr Groß | 100-350 | 3-5 Minuten | ✅ |

### Durchsatz

- **Single Worker**: ~10 Dokumente/Stunde
- **3 Worker**: ~30 Dokumente/Stunde
- **5 Worker**: ~50 Dokumente/Stunde

## 🔐 Security

### Best Practices

1. **RabbitMQ Credentials**
   - ✅ Verwende starke Passwörter
   - ✅ Speichere in `.env` (nicht in Git)
   - ✅ Ändere Default-Credentials in Production

2. **Task Timeouts**
   - ✅ Max 1 Stunde pro Task
   - ✅ Soft Timeout nach 55 Minuten
   - ✅ Verhindert Zombie-Prozesse

3. **Queue Security**
   - ✅ Queues sind durable (persistent)
   - ✅ Tasks werden nach Verarbeitung gelöscht
   - ✅ Fehlerhafte Tasks gehen in Dead Letter Queue

## 📚 Weitere Ressourcen

- [Celery Dokumentation](https://docs.celeryproject.io/)
- [RabbitMQ Dokumentation](https://www.rabbitmq.com/documentation.html)
- [Kombu Dokumentation](https://docs.celeryproject.org/projects/kombu/)
- [ExamCraft API Docs](http://localhost:8000/docs)

## 🚀 Nächste Schritte

1. **Frontend Multi-Upload UI** - Batch-Upload mit Progress-Anzeige
2. **WebSocket Real-time Updates** - Live Status-Updates statt Polling
3. **Batch Question Generation** - Fragen aus mehreren Dokumenten
4. ~~**Advanced Monitoring** - Flower Dashboard Integration~~ ✅ Implementiert
5. **Auto-Scaling** - Dynamische Worker-Skalierung basierend auf Queue-Länge
