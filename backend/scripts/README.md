# ExamCraft AI - Performance Scripts

## Übersicht

Diese Skripte unterstützen die Performance-Validierung des Qdrant Vector Database Systems.

## Verfügbare Skripte

### 1. performance_test_qdrant.py

**Zweck**: Performance-Tests für Qdrant Vector Database

**Features**:

- Benchmark für Document Addition
- Benchmark für Similarity Search
- Memory Usage Tracking
- Latency Measurements
- Umfassende Metriken und Reporting

**Usage**:

```bash
# Standard Performance Test
python scripts/performance_test_qdrant.py

# Custom Configuration
python scripts/performance_test_qdrant.py \
  --docs 50 \
  --chunks 30 \
  --output benchmark_results.json
```

**Parameter**:

- `--docs`: Anzahl Test-Dokumente (default: `10`)
- `--chunks`: Chunks pro Dokument (default: `20`)
- `--output`: Output-Datei für Ergebnisse (default: `performance_results.json`)

**Output**:

```text
🚀 Starting Qdrant Performance Tests...
Step 1: Generating test data...
Step 2: Testing document addition...
Step 3: Testing similarity search...
Step 4: Analyzing results...
🎉 Performance tests completed!

Performance Statistics:
  - Total Documents: 10
  - Total Chunks: 200
  - Addition Time: 2.34 seconds
  - Search Time: 0.45 seconds
  - Memory Usage: 125 MB
```

**Features**:

- Automatische Testdaten-Generierung
- Document Addition Performance Tests
- Similarity Search Performance Tests
- Memory Usage Monitoring
- Detaillierte Performance-Metriken
- JSON Export der Ergebnisse

**Usage**:

```bash
# Standard Performance Test
python scripts/performance_test_qdrant.py

# Custom Test Parameters
python scripts/performance_test_qdrant.py \
  --docs 50 \
  --chunks 30 \
  --output benchmark_results.json

# Kleine Test-Suite
python scripts/performance_test_qdrant.py --docs 5 --chunks 10
```

**Parameter**:

- `--docs`: Anzahl Test-Dokumente (default: `10`)
- `--chunks`: Chunks pro Dokument (default: `20`)
- `--output`: Output-Datei für Ergebnisse (default:
  `performance_results.json`)

**Output**:

```text
📊 PERFORMANCE TEST SUMMARY
============================================================

🔄 DOCUMENT ADDITION PERFORMANCE:
Qdrant: 0.320s per doc, 62.5 chunks/s

🔍 SEARCH PERFORMANCE:
Qdrant: 0.050s per query, 20.0 queries/s

💾 MEMORY USAGE:
Peak Memory: 125 MB
Average Memory: 98 MB
============================================================
```

## Voraussetzungen

### System Requirements

```bash
# Python Dependencies
pip install qdrant-client sentence-transformers openai

# Optional: Memory Monitoring
pip install psutil
```

### Docker Services

```bash
# Starte alle Services
docker compose up -d

# Prüfe Service Status
docker compose ps
```

### Environment Variables

```bash
# Qdrant Configuration
export QDRANT_URL=http://localhost:6333
export VECTOR_SERVICE_TYPE=qdrant

# Optional
export QDRANT_COLLECTION_NAME=examcraft_documents
export EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

## Workflow Examples

### Qdrant Setup und Testing

```bash
# 1. Qdrant Service starten
docker compose up -d qdrant

# 2. Service Status prüfen
curl http://localhost:6333/health

# 3. Performance Tests ausführen
python scripts/performance_test_qdrant.py

# 4. Backend mit Qdrant starten
export VECTOR_SERVICE_TYPE=qdrant
docker compose restart backend
```

### Performance Benchmarking

```bash
# 1. Baseline Test (kleine Datenmenge)
python scripts/performance_test_qdrant.py --docs 5 --chunks 10

# 2. Standard Test
python scripts/performance_test_qdrant.py

# 3. Stress Test (große Datenmenge)
python scripts/performance_test_qdrant.py --docs 100 --chunks 50

# 4. Ergebnisse analysieren
cat performance_results.json | jq '.comparison'
```

### Troubleshooting

```bash
# 1. Service Status prüfen
curl http://localhost:6333/health
curl http://localhost:8000/api/v1/search/health

# 2. Performance Tests ausführen
python scripts/performance_test_qdrant.py --docs 3 --chunks 5

# 3. Logs analysieren
docker compose logs qdrant
docker compose logs backend
```

## Monitoring & Debugging

### Performance Monitoring

```bash
# Resource Usage während Tests
docker stats examcraft_qdrant examcraft_backend

# Memory Usage Tracking
python scripts/performance_test_qdrant.py | grep "Memory Usage"

# Detailed Metrics
cat performance_results.json | jq '.qdrant.addition'
```

### Health Checks

```bash
# Qdrant Health
curl http://localhost:6333/health

# Collection Info
curl http://localhost:6333/collections/examcraft_documents

# Backend Service Info
curl http://localhost:8000/api/v1/search/service-info
```

## Error Handling

### Common Issues

#### 1. Qdrant Connection Failed

```bash
# Check Qdrant Status
docker compose ps qdrant
docker compose logs qdrant

# Restart Qdrant
docker compose restart qdrant

# Verify Connection
curl http://localhost:6333/health
```

#### 2. Qdrant Collection Issues

```bash
# Check Collections
curl http://localhost:6333/collections

# Verify Collection
curl http://localhost:6333/collections/examcraft_documents

# Check Collection Stats
python -c "
from premium.services.qdrant_vector_service import QdrantVectorService
service = QdrantVectorService()
print(service.get_collection_info())
"
```

#### 3. Performance Issues

```bash
# Check Resource Limits
docker stats

# Optimize Qdrant
curl -X POST http://localhost:6333/collections/examcraft_documents/index

# Test with Smaller Dataset
python scripts/performance_test_qdrant.py --docs 3 --chunks 5
```

## Best Practices

### Qdrant Setup Best Practices

1. **Health Checks**: Regelmäßig Qdrant Health prüfen
2. **Collection Management**: Collections sauber strukturieren
3. **Monitoring**: Performance-Metriken überwachen
4. **Backup**: Regelmäßige Backups der Vector Database
5. **Optimization**: Index-Optimierung für bessere Performance

### Performance Testing Best Practices

1. **Baseline**: Kleine Tests zuerst
2. **Realistic Data**: Produktionsähnliche Datenmengen
3. **Multiple Runs**: Mehrere Tests für Konsistenz
4. **Resource Monitoring**: System-Ressourcen überwachen
5. **Documentation**: Ergebnisse dokumentieren

### Production Deployment

1. **Staging First**: Qdrant in Staging-Umgebung testen
2. **Maintenance Window**: Deployment während wartungsfreundlicher Zeit
3. **Health Monitoring**: Kontinuierliche Überwachung
4. **Gradual Rollout**: Schrittweise Umstellung
5. **Backup Strategy**: Regelmäßige Backups einrichten

## Support

Bei Problemen:

1. **Logs prüfen**: Qdrant und Backend Logs analysieren
2. **Health Checks**: Service-Status überprüfen
3. **Performance Tests**: Benchmark-Tests ausführen
4. **Documentation**: Diese Anleitung und `docs/QDRANT_MIGRATION.md` konsultieren
5. **Monitoring**: Qdrant Dashboard und Metriken überwachen

---

**Version**: 1.0.0
**Last Updated**: 2025-09-25
**Maintainer**: ExamCraft AI Team
