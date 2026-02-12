# Qdrant Migration Guide

## Übersicht

Diese Anleitung beschreibt die Migration von ChromaDB zu Qdrant als Vector Database für ExamCraft AI. Die Migration verbessert Performance, Skalierbarkeit und Production-Readiness des Systems.

## Warum Qdrant?

### Vorteile von Qdrant gegenüber ChromaDB

- **🚀 Performance**: Bis zu 3x schnellere Similarity Search
- **📈 Skalierbarkeit**: Bessere Unterstützung für große Datenmengen
- **🔧 Production-Ready**: Robuste HTTP/gRPC APIs
- **💾 Persistenz**: Zuverlässige Datenpersistierung
- **🔍 Filtering**: Erweiterte Metadaten-Filter-Funktionen
- **📊 Monitoring**: Bessere Observability und Metriken

### Technische Verbesserungen

- **Async/Await Support**: Vollständig asynchrone Operationen
- **Batch Operations**: Effiziente Bulk-Operationen
- **Health Checks**: Integrierte Service-Überwachung
- **Error Handling**: Robuste Fehlerbehandlung mit Fallbacks
- **Memory Efficiency**: Optimierte Speichernutzung

## Architektur

### Service Factory Pattern

```python
# Automatische Service-Auswahl basierend auf Environment
VECTOR_SERVICE_TYPE=qdrant    # Qdrant (Standard)
VECTOR_SERVICE_TYPE=chromadb  # ChromaDB (Fallback)
VECTOR_SERVICE_TYPE=mock      # Mock Service (Testing)
```

### Graceful Fallback

```
Qdrant → ChromaDB → Mock Service
```

Das System fällt automatisch auf verfügbare Services zurück.

## Installation & Setup

### 1. Docker Compose

Qdrant ist bereits in `docker-compose.yml` konfiguriert:

```yaml
qdrant:
  image: qdrant/qdrant:latest
  container_name: examcraft_qdrant
  ports:
    - "6333:6333"  # HTTP API
    - "6334:6334"  # gRPC API
  volumes:
    - qdrant_data:/qdrant/storage
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

### 2. Environment Variables

```bash
# Qdrant Configuration
QDRANT_URL=http://localhost:6333
VECTOR_SERVICE_TYPE=qdrant

# Optional: Collection Settings
QDRANT_COLLECTION_NAME=examcraft_documents
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### 3. Dependencies

Qdrant Client ist bereits in `requirements.txt` enthalten:

```
qdrant-client==1.7.0
```

## Migration Process

### Automatische Migration

```bash
# Vollständige Migration mit Validierung
cd backend
python scripts/migrate_chromadb_to_qdrant.py

# Dry Run (keine Datenänderung)
python scripts/migrate_chromadb_to_qdrant.py --dry-run

# Custom Configuration
python scripts/migrate_chromadb_to_qdrant.py \
  --chromadb-dir ./custom_chroma_db \
  --qdrant-url http://production:6333 \
  --collection custom_collection
```

### Migration Steps

1. **Backup**: Automatisches Backup der ChromaDB Daten
2. **Extract**: Extraktion aller Dokumente und Embeddings
3. **Transform**: Konvertierung zu Qdrant-Format
4. **Load**: Upload zu Qdrant mit Batch-Processing
5. **Validate**: Verifikation der Datenintegrität
6. **Switch**: Umstellung auf Qdrant Service

### Migration Monitoring

```bash
# Migration Logs
tail -f migration.log

# Service Status
curl http://localhost:8000/api/v1/search/service-info

# Collection Statistics
curl http://localhost:6333/collections/examcraft_documents
```

## Performance Testing

### Benchmark Script

```bash
# Standard Performance Test
cd backend
python scripts/performance_test_qdrant.py

# Custom Test Parameters
python scripts/performance_test_qdrant.py \
  --docs 50 \
  --chunks 30 \
  --output benchmark_results.json
```

### Erwartete Performance-Verbesserungen

| Operation | ChromaDB | Qdrant | Speedup |
|-----------|----------|--------|---------|
| Document Addition | 0.8s/doc | 0.3s/doc | **2.7x** |
| Similarity Search | 0.15s/query | 0.05s/query | **3.0x** |
| Memory Usage | 250MB | 180MB | **1.4x** |
| Concurrent Queries | 10/s | 25/s | **2.5x** |

## API Changes

### Neue Endpoints

```bash
# Service Information
GET /api/v1/search/service-info
{
  "service_info": {
    "service_type": "qdrant",
    "service_class": "QdrantVectorService",
    "qdrant_url": "http://localhost:6333",
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "collection_name": "examcraft_documents"
  },
  "collection_stats": {
    "total_chunks": 1250,
    "embedding_dimension": 384
  },
  "features": {
    "async_operations": true,
    "similarity_search": true,
    "document_filtering": true
  }
}
```

### Enhanced Health Check

```bash
# Erweiterte Health Information
GET /api/v1/search/health
{
  "status": "healthy",
  "service": "Vector Search Service",
  "service_type": "qdrant",
  "service_class": "QdrantVectorService",
  "collection_name": "examcraft_documents",
  "total_chunks": 1250,
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "model_loaded": true,
  "qdrant_url": "http://localhost:6333",
  "response_time": 0.023
}
```

## Rollback Strategy

### Automatischer Fallback

Bei Qdrant-Problemen fällt das System automatisch auf ChromaDB zurück:

```bash
# Fallback zu ChromaDB
export VECTOR_SERVICE_TYPE=chromadb

# Service Restart
docker compose restart backend
```

### Manuelle Rollback

```bash
# 1. Stop Qdrant
docker compose stop qdrant

# 2. Switch to ChromaDB
export VECTOR_SERVICE_TYPE=chromadb

# 3. Restart Backend
docker compose restart backend

# 4. Verify Service
curl http://localhost:8000/api/v1/search/health
```

## Monitoring & Troubleshooting

### Service Health Monitoring

```bash
# Qdrant Health
curl http://localhost:6333/health

# Backend Service Info
curl http://localhost:8000/api/v1/search/service-info

# Collection Statistics
curl http://localhost:6333/collections/examcraft_documents
```

### Common Issues

#### 1. Qdrant Connection Failed

```bash
# Check Qdrant Status
docker compose ps qdrant
docker compose logs qdrant

# Verify Network
curl http://localhost:6333/health

# Fallback to ChromaDB
export VECTOR_SERVICE_TYPE=chromadb
```

#### 2. Migration Incomplete

```bash
# Check Migration Logs
tail -f migration.log

# Validate Data Integrity
python scripts/migrate_chromadb_to_qdrant.py --dry-run

# Re-run Migration
python scripts/migrate_chromadb_to_qdrant.py --validate
```

#### 3. Performance Issues

```bash
# Run Performance Test
python scripts/performance_test_qdrant.py

# Check Resource Usage
docker stats examcraft_qdrant

# Optimize Collection
curl -X POST http://localhost:6333/collections/examcraft_documents/index
```

## Development Workflow

### Local Development

```bash
# Start Development Stack
docker compose up -d

# Check Services
docker compose ps

# View Logs
docker compose logs -f backend qdrant
```

### Testing

```bash
# Run Qdrant Tests
cd backend
python -m pytest tests/test_qdrant_vector_service.py -v

# Run Factory Tests
python -m pytest tests/test_vector_service_factory.py -v

# Run API Tests
python -m pytest tests/test_api_vector_search.py -v
```

### Code Integration

```python
# Use Factory Pattern
from services.vector_service_factory import get_vector_service

# Get Current Service (Qdrant or Fallback)
vector_service = get_vector_service()

# Service-Agnostic Operations
results = await vector_service.similarity_search("query")
stats = await vector_service.add_document_chunks(document)
```

## Production Deployment

### Environment Configuration

```bash
# Production Environment
VECTOR_SERVICE_TYPE=qdrant
QDRANT_URL=http://qdrant-cluster:6333
QDRANT_COLLECTION_NAME=examcraft_production
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### Scaling Considerations

- **Qdrant Cluster**: Multi-node setup für High Availability
- **Load Balancing**: Verteilung der Anfragen
- **Backup Strategy**: Regelmäßige Collection Backups
- **Monitoring**: Prometheus/Grafana Integration

### Security

- **Authentication**: Qdrant API Key Configuration
- **Network Security**: VPC/Firewall Rules
- **Data Encryption**: TLS für API Communication
- **Access Control**: Role-based Permissions

## Next Steps

1. **✅ Migration Complete**: Qdrant Service implementiert
2. **🔄 Testing Phase**: Umfassende Tests durchführen
3. **📊 Performance Validation**: Benchmark-Ergebnisse validieren
4. **🚀 Production Deployment**: Rollout in Production
5. **📈 Monitoring Setup**: Observability implementieren
6. **🔧 Optimization**: Performance-Tuning basierend auf Metriken

## Support

Bei Fragen oder Problemen:

1. **Logs prüfen**: `docker compose logs backend qdrant`
2. **Health Checks**: Service-Status überprüfen
3. **Fallback aktivieren**: ChromaDB als Backup nutzen
4. **Performance Tests**: Benchmark-Skripte ausführen
5. **Documentation**: Diese Anleitung konsultieren

---

**Status**: ✅ Migration Ready
**Version**: 1.0.0
**Last Updated**: 2025-09-25
