# ExamCraft AI - Test Suite

## Übersicht

Die Test Suite verwendet **PostgreSQL** für Integration Tests, um die
Produktionsumgebung genau zu replizieren.

## Voraussetzungen

### 1. PostgreSQL Database

Die Tests benötigen eine laufende PostgreSQL-Instanz. Verwenden Sie Docker
Compose:

```bash
# Starte PostgreSQL Container
docker-compose up -d postgres

# Prüfe ob PostgreSQL läuft
docker-compose ps postgres
```

### 2. Test-Datenbank

Die Test-Infrastruktur erstellt automatisch eine separate
`examcraft_test` Datenbank:

- **Produktions-DB**: `examcraft` (Port 5432)
- **Test-DB**: `examcraft_test` (Port 5432)

Die Test-DB wird vor jedem Test-Run neu erstellt und nach Abschluss
gelöscht.

## Tests ausführen

### Alle Tests

```bash
# Im Backend Container
docker exec examcraft_backend pytest

# Lokal (benötigt PostgreSQL auf localhost:5432)
cd backend
pytest
```

### Spezifische Test-Dateien

```bash
# Chat API Tests
docker exec examcraft_backend pytest tests/test_chat_api.py -v

# Document Model Tests
docker exec examcraft_backend pytest tests/test_document_model.py -v

# Document Service Tests
docker exec examcraft_backend pytest tests/test_document_service.py -v
```

### Tests mit Coverage

```bash
docker exec examcraft_backend pytest \
  --cov=services \
  --cov=api \
  --cov=models \
  --cov-report=html
```

### Nur Integration Tests

```bash
docker exec examcraft_backend pytest -m integration
```

## Test-Struktur

```text
backend/tests/
├── conftest.py              # Pytest Fixtures & PostgreSQL Setup
├── test_chat_api.py         # Chat API Endpoints
├── test_document_model.py   # Document Model & Properties
├── test_document_service.py # Document Service Logic
└── README.md               # Diese Datei
```

## Wichtige Fixtures

### `test_engine`

- **Scope**: Session
- **Funktion**: Erstellt PostgreSQL Test-Database Engine
- **Cleanup**: Löscht Test-DB nach allen Tests

### `test_db`

- **Scope**: Function
- **Funktion**: Erstellt DB Session mit Transaction Rollback
- **Isolation**: Jeder Test läuft in eigener Transaction

### `client`

- **Scope**: Function
- **Funktion**: FastAPI TestClient für API-Tests

## Umgebungsvariablen

```bash
# Standard (Docker Compose)
TEST_DATABASE_URL=postgresql://examcraft:examcraft_dev@localhost:5432/examcraft_test

# Custom PostgreSQL
export TEST_DATABASE_URL=postgresql://user:pass@host:port/dbname
```

## Test-Kategorien

### Unit Tests

```python
@pytest.mark.unit
def test_document_title_property():
    """Schnelle Tests ohne externe Dependencies"""
```

### Integration Tests

```python
@pytest.mark.integration
@pytest.mark.postgres
def test_chat_export_with_database():
    """Tests mit PostgreSQL Database"""
```

## Troubleshooting

### Problem: "Connection refused" Error

**Lösung**: PostgreSQL Container starten

```bash
docker-compose up -d postgres
```

### Problem: "Database already exists" Error

**Lösung**: Test-DB manuell löschen

```bash
docker exec examcraft_postgres psql -U examcraft -c \
  "DROP DATABASE IF EXISTS examcraft_test;"
```

### Problem: Tests hängen

**Lösung**: Aktive Verbindungen beenden

```bash
docker exec examcraft_postgres psql -U examcraft -d postgres -c "
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = 'examcraft_test'
AND pid <> pg_backend_pid();
"
```

## CI/CD Integration

### GitHub Actions Beispiel

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_DB: examcraft_test
          POSTGRES_USER: examcraft
          POSTGRES_PASSWORD: examcraft_dev
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run tests
        env:
          TEST_DATABASE_URL: postgresql://examcraft:examcraft_dev@localhost:5432/examcraft_test
        run: |
          cd backend
          pytest -v
```

## Best Practices

### 1. Test Isolation

- Jeder Test läuft in eigener Transaction
- Automatisches Rollback nach Test
- Keine Daten-Verschmutzung zwischen Tests

### 2. Fixtures verwenden

```python
def test_example(test_db, client):
    """Verwende Fixtures statt manuelle DB-Verbindungen"""
    # test_db ist bereits konfiguriert
    # client ist FastAPI TestClient
```

### 3. Async Tests

```python
@pytest.mark.asyncio
async def test_async_function(test_db):
    """Async Tests mit @pytest.mark.asyncio"""
    result = await some_async_function()
    assert result is not None
```

### 4. Mocking

```python
from unittest.mock import Mock, patch

def test_with_mock(test_db):
    """Mock externe Dependencies"""
    with patch('services.claude_api.call') as mock_call:
        mock_call.return_value = "Mocked response"
        # Test code
```

## Test Coverage Ziele

- **Gesamt**: >= 80%
- **Services**: >= 85%
- **API Endpoints**: >= 90%
- **Models**: >= 75%

## Weitere Ressourcen

- [pytest Documentation](<https://docs.pytest.org/>)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html)
- [FastAPI Testing](<https://fastapi.tiangolo.com/tutorial/testing/>)
