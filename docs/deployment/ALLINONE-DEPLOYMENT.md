# ExamCraft AI - All-in-One Container Deployment

## 🎯 Übersicht

Dieser Ansatz deployed **alle Services in einem einzigen Docker Container**:
- ✅ Backend (FastAPI)
- ✅ Frontend (React)
- ✅ PostgreSQL Database
- ✅ Redis Cache
- ✅ Qdrant Vector Database
- ✅ Nginx Reverse Proxy

## 📊 Wann All-in-One verwenden?

### ✅ Gut für:

- Schnelles Deployment und Testing
- Proof-of-Concept / Demo
- Entwicklungsumgebung
- Kostengünstiges Setup (nur 1 Service)
- Einfache Wartung

### ❌ Nicht ideal für:

- High-Traffic Production
- Skalierbare Anwendungen
- Mission-Critical Systems
- Wenn einzelne Services skaliert werden müssen

## 🚀 Deployment auf Render.com

### Option 1: Manuelles Dashboard Setup

#### Schritt 1: Neuen Web Service erstellen

1. Gehe zu https://dashboard.render.com
2. Klicke "New +" → "Web Service"
3. Verbinde ExamCraft Repository

#### Schritt 2: Service konfigurieren

```yaml
Name: examcraft-allinone
Region: Frankfurt
Branch: feature/tf-108-render-deployment

Runtime: Docker
Dockerfile Path: Dockerfile.allinone
Docker Context: .

Plan: Starter ($7/month)
# Hinweis: Free Tier könnte zu wenig RAM haben
```

#### Schritt 3: Environment Variables

**Erforderlich:**
```bash
CLAUDE_API_KEY=sk-ant-your_api_key_here
```

**Optional (haben Defaults):**
```bash
ENVIRONMENT=production
VECTOR_SERVICE_TYPE=qdrant
CORS_ORIGINS=*
```

#### Schritt 4: Disk Storage hinzufügen

**Wichtig für Datenpersistenz!**

Im Dashboard unter "Disks":

```yaml
# PostgreSQL Data
Name: postgres-data
Mount Path: /var/lib/postgresql/15/main
Size: 1 GB

# Qdrant Data
Name: qdrant-data
Mount Path: /var/lib/qdrant/storage
Size: 1 GB
```

#### Schritt 5: Deploy starten

- Klicke "Create Web Service"
- Warte ~5-10 Minuten für Build
- Service wird verfügbar unter: `https://examcraft-allinone.onrender.com`

### Option 2: Via Render MCP Server

Leider unterstützt der MCP Server aktuell keine Disk-Konfiguration, daher ist manuelles Setup empfohlen.

## 🔍 Service URLs

Nach erfolgreichem Deployment:

```bash
# Frontend
https://examcraft-allinone.onrender.com

# Backend API
https://examcraft-allinone.onrender.com/api/v1/

# API Dokumentation
https://examcraft-allinone.onrender.com/docs

# Health Check
https://examcraft-allinone.onrender.com/health
```

## 🏥 Health Checks

Der Container startet 5 Services via Supervisor:

1. **PostgreSQL** (Port 5432) - Priority 1
2. **Redis** (Port 6379) - Priority 2
3. **Qdrant** (Port 6333) - Priority 3
4. **Backend** (Port 8000) - Priority 4
5. **Nginx** (Port 8080) - Priority 5

Health Check Endpoint: `/api/v1/health`

Prüft:
- ✅ Database Connection
- ✅ Redis Connection
- ✅ Qdrant Connection
- ✅ Claude API Configuration

## 📝 Logs überwachen

### Via Render Dashboard

```
https://dashboard.render.com/web/[service-id]/logs
```

### Logs für einzelne Services

Supervisor schreibt Logs nach:
```
/var/log/supervisor/postgresql.log
/var/log/supervisor/redis.log
/var/log/supervisor/qdrant.log
/var/log/supervisor/backend.log
/var/log/supervisor/nginx.log
```

## 🔧 Troubleshooting

### Container startet nicht

**Problem**: Build schlägt fehl

**Lösung**:
```bash
# Lokal testen:
docker build -f Dockerfile.allinone -t examcraft-allinone .
docker run -p 8080:8080 -e CLAUDE_API_KEY=your_key examcraft-allinone

# Logs prüfen:
docker logs [container-id]
```

### Services starten nicht

**Problem**: Supervisor kann Services nicht starten

**Lösung**:
```bash
# In Container Shell gehen (via Render Dashboard):
supervisorctl status

# Einzelnen Service neu starten:
supervisorctl restart backend
supervisorctl restart postgresql
```

### Daten gehen verloren

**Problem**: Nach Restart sind Daten weg

**Lösung**:
```bash
# Stelle sicher, dass Disks konfiguriert sind:
# - /var/lib/postgresql/15/main (PostgreSQL)
# - /var/lib/qdrant/storage (Qdrant)

# Prüfe Mount Points im Container:
df -h
```

### Out of Memory

**Problem**: Container crashed mit OOM

**Lösung**:
```bash
# Upgrade zu größerem Plan:
# Starter: 512MB RAM (zu wenig)
# Standard: 2GB RAM (empfohlen)
# Pro: 4GB RAM (ideal)

# Oder: Reduziere Services
# - Verwende Qdrant Cloud statt lokalem Qdrant
# - Verwende managed PostgreSQL
```

## 💰 Kosten

### All-in-One Container

```yaml
Starter Plan: $7/month
  - 512MB RAM (knapp)
  - 0.5 CPU
  - Disk: +$0.25/GB/month

Standard Plan: $25/month (empfohlen)
  - 2GB RAM
  - 1 CPU
  - Disk: +$0.25/GB/month

Total mit 2GB Disk: ~$25.50/month
```

### Vergleich: Multi-Service Setup

```yaml
Backend: $7/month
Frontend: Free
PostgreSQL: $7/month
Redis: $7/month
Qdrant: $7/month (oder Cloud)

Total: ~$28/month
```

**Ersparnis**: ~$2.50/month mit All-in-One

## 🔄 Migration zu Multi-Service

Falls Sie später zu Multi-Service wechseln möchten:

### Daten exportieren

```bash
# PostgreSQL Dump
pg_dump -h localhost -U examcraft examcraft > backup.sql

# Qdrant Export
curl http://localhost:6333/collections/examcraft_documents/snapshots \
  -X POST > qdrant_snapshot.json
```

### Zu managed Services migrieren

```bash
# PostgreSQL zu Render PostgreSQL
psql $DATABASE_URL < backup.sql

# Qdrant zu Qdrant Cloud
python scripts/migrate_to_qdrant_cloud.py
```

## 📈 Performance Optimierung

### RAM Optimierung

```bash
# PostgreSQL Memory Tuning
# In /etc/postgresql/15/main/postgresql.conf:
shared_buffers = 128MB
effective_cache_size = 256MB
```

### Nginx Caching

```nginx
# Bereits konfiguriert in nginx-allinone.conf:
- Static Assets: 1 Jahr Cache
- Gzip Compression: Aktiviert
```

## ✅ Empfehlung

### Für schnelles Testing/Demo:

→ **All-in-One Container** (dieser Ansatz)

### Für Production:

→ **Multi-Service Setup** (siehe render-deployment.md)

### Hybrid-Ansatz:

→ All-in-One für Backend+Frontend, managed DBs für PostgreSQL/Redis

## 🆘 Support

Bei Problemen:
1. Prüfe Render Dashboard Logs
2. Teste lokal mit Docker
3. Prüfe Supervisor Status
4. Kontaktiere Render Support

---

**Status**: ✅ Ready for Deployment
**Empfohlener Plan**: Standard ($25/month)
**Build Zeit**: ~5-10 Minuten
**Startup Zeit**: ~30-60 Sekunden
