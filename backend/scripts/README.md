# ExamCraft AI - Migration & Performance Scripts

## Übersicht

Diese Skripte unterstützen die Migration von ChromaDB zu Qdrant und die Performance-Validierung des neuen Vector Database Systems.

## Verfügbare Skripte

### 1. migrate_chromadb_to_qdrant.py

**Zweck**: Vollständige Migration von ChromaDB zu Qdrant

**Features**:
- ✅ Automatische Datenextraktion aus ChromaDB
- ✅ Batch-Processing für große Datenmengen
- ✅ Datenvalidierung und Integritätsprüfung
- ✅ Dry-Run Modus für sichere Tests
- ✅ Umfassende Logging und Fehlerbehandlung
- ✅ Rollback-Unterstützung

**Usage**:
```bash
# Vollständige Migration
python scripts/migrate_chromadb_to_qdrant.py

# Dry Run (keine Datenänderung)
python scripts/migrate_chromadb_to_qdrant.py --dry-run

# Custom Configuration
python scripts/migrate_chromadb_to_qdrant.py \
  --chromadb-dir ./custom_chroma_db \
  --qdrant-url http://production:6333 \
  --collection custom_collection \
  --batch-size 50

# Migration ohne Validierung
python scripts/migrate_chromadb_to_qdrant.py --no-validate
```

**Parameter**:
- `--chromadb-dir`: ChromaDB Verzeichnis (default: `./chroma_db`)
- `--qdrant-url`: Qdrant Server URL (default: `http://localhost:6333`)
- `--collection`: Collection Name (default: `examcraft_documents`)
- `--batch-size`: Batch-Größe (default: `100`)
- `--no-validate`: Validierung überspringen
- `--dry-run`: Nur Analyse, keine Migration

**Output**:
```
🚀 Starting ChromaDB to Qdrant migration...
Step 1: Checking source and target services...
Step 2: Extracting data from ChromaDB...
Step 3: Migrating data to Qdrant...
Step 4: Validating migration...
🎉 Migration completed successfully!

Migration Statistics:
  - Total Documents: 25
  - Total Chunks: 500
  - Migrated Chunks: 500
  - Failed Chunks: 0
  - Duration: 45.23 seconds
```

### 2. performance_test_qdrant.py

**Zweck**: Performance-Vergleich zwischen Qdrant und ChromaDB

**Features**:
- ✅ Automatische Testdaten-Generierung
- ✅ Document Addition Performance Tests
- ✅ Similarity Search Performance Tests
- ✅ Memory Usage Monitoring
- ✅ Detaillierte Performance-Metriken
- ✅ JSON Export der Ergebnisse

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
- `--output`: Output-Datei für Ergebnisse (default: `performance_results.json`)

**Output**:
```
📊 PERFORMANCE TEST SUMMARY
================================================================================

🔄 DOCUMENT ADDITION PERFORMANCE:
ChromaDB: 0.850s per doc, 23.5 chunks/s
Qdrant:   0.320s per doc, 62.5 chunks/s

🔍 SEARCH PERFORMANCE:
ChromaDB: 0.150s per query, 6.7 queries/s
Qdrant:   0.050s per query, 20.0 queries/s

🏆 PERFORMANCE WINNERS:
Addition: Qdrant (2.66x faster)
Search:   Qdrant (3.00x faster)
Memory:   Qdrant (1.40x more efficient)
================================================================================
```

## Voraussetzungen

### System Requirements

```bash
# Python Dependencies
pip install qdrant-client sentence-transformers chromadb

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

### Komplette Migration

```bash
# 1. Backup erstellen (optional)
cp -r ./chroma_db ./chroma_db_backup

# 2. Dry Run durchführen
python scripts/migrate_chromadb_to_qdrant.py --dry-run

# 3. Migration ausführen
python scripts/migrate_chromadb_to_qdrant.py

# 4. Performance validieren
python scripts/performance_test_qdrant.py

# 5. Service umstellen
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

# 2. Migration Status prüfen
python scripts/migrate_chromadb_to_qdrant.py --dry-run

# 3. Performance vergleichen
python scripts/performance_test_qdrant.py --docs 3 --chunks 5

# 4. Logs analysieren
docker compose logs qdrant
docker compose logs backend
```

## Monitoring & Debugging

### Migration Monitoring

```bash
# Real-time Migration Logs
python scripts/migrate_chromadb_to_qdrant.py 2>&1 | tee migration.log

# Progress Tracking
tail -f migration.log | grep "Migrating document"

# Error Analysis
grep "ERROR" migration.log
```

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

#### 2. ChromaDB Data Not Found
```bash
# Check ChromaDB Directory
ls -la ./chroma_db/

# Verify Collection
python -c "
from services.vector_service import VectorService
service = VectorService()
print(service.get_collection_stats())
"
```

#### 3. Migration Incomplete
```bash
# Check Migration Status
python scripts/migrate_chromadb_to_qdrant.py --dry-run

# Re-run Migration
python scripts/migrate_chromadb_to_qdrant.py --no-validate

# Validate Manually
curl http://localhost:6333/collections/examcraft_documents
```

#### 4. Performance Issues
```bash
# Check Resource Limits
docker stats

# Optimize Qdrant
curl -X POST http://localhost:6333/collections/examcraft_documents/index

# Test with Smaller Dataset
python scripts/performance_test_qdrant.py --docs 3 --chunks 5
```

## Best Practices

### Migration Best Practices

1. **Backup First**: Immer ChromaDB Daten sichern
2. **Dry Run**: Vor echter Migration testen
3. **Validation**: Datenintegrität prüfen
4. **Monitoring**: Migration-Logs überwachen
5. **Rollback Plan**: Fallback-Strategie bereit haben

### Performance Testing Best Practices

1. **Baseline**: Kleine Tests zuerst
2. **Realistic Data**: Produktionsähnliche Datenmengen
3. **Multiple Runs**: Mehrere Tests für Konsistenz
4. **Resource Monitoring**: System-Ressourcen überwachen
5. **Documentation**: Ergebnisse dokumentieren

### Production Deployment

1. **Staging First**: Migration in Staging-Umgebung testen
2. **Maintenance Window**: Migration während wartungsfreundlicher Zeit
3. **Health Monitoring**: Kontinuierliche Überwachung
4. **Gradual Rollout**: Schrittweise Umstellung
5. **Rollback Ready**: Schnelle Rollback-Möglichkeit

## Support

Bei Problemen:

1. **Logs prüfen**: Migration und Performance Logs analysieren
2. **Health Checks**: Service-Status überprüfen
3. **Dry Run**: Migration-Skript im Test-Modus ausführen
4. **Documentation**: Diese Anleitung und `docs/QDRANT_MIGRATION.md` konsultieren
5. **Fallback**: ChromaDB als Backup nutzen

---

**Version**: 1.0.0  
**Last Updated**: 2025-09-25  
**Maintainer**: ExamCraft AI Team
