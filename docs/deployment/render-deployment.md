# ExamCraft AI - Render.com Deployment Guide

## 🎯 Übersicht

Dieses Dokument beschreibt das Production Deployment von ExamCraft AI auf Render.com.

## 📋 Voraussetzungen

### Render.com Account

- Kostenloses oder bezahltes Render.com Konto
- GitHub/GitLab Repository verbunden
- Zugriff auf Environment Variables

### Externe Services

- **Claude API Key** (Anthropic)
- **Qdrant Cloud** Account (optional, für Vector Database)

## 🚀 Deployment-Optionen

### Option 1: Blueprint Deployment (Empfohlen)

Der einfachste Weg ist die Verwendung der `render.yaml` Blueprint-Datei:

1. **Repository zu Render.com verbinden**

   ```bash
   # In Render.com Dashboard:
   # 1. "New" → "Blueprint"
   # 2. Repository auswählen
   # 3. Branch: main (oder develop)
   # 4. render.yaml wird automatisch erkannt
   ```

2. **Environment Variables konfigurieren**

   Folgende Secrets müssen manuell gesetzt werden:

   ```bash
   # Backend Service
   CLAUDE_API_KEY=sk-ant-...           # Anthropic API Key
   QDRANT_URL=https://xyz.qdrant.io   # Qdrant Cloud URL (optional)

   # Optional: Qdrant Cloud Credentials
   QDRANT_API_KEY=your_qdrant_api_key
   ```

3. **Deployment starten**
   - Render.com erstellt automatisch:
     - ✅ Backend Web Service (FastAPI)
     - ✅ Frontend Static Site (React)
     - ✅ PostgreSQL Database
     - ✅ Redis Cache
   - Alle Services werden automatisch verbunden

### Option 2: Manuelle Service-Erstellung

Falls Blueprint nicht verwendet wird:

#### Backend Service

```yaml
Name: examcraft-backend
Type: Web Service
Runtime: Python 3
Region: Frankfurt
Branch: main

Build Command:
pip install -r backend/requirements.txt

Start Command:
cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT

Health Check Path:
/api/v1/health
```

**Environment Variables:**

```bash
PYTHON_VERSION=3.11.0
ENVIRONMENT=production
DATABASE_URL=${{examcraft-postgres.DATABASE_URL}}
REDIS_URL=${{examcraft-redis.REDIS_URL}}
CLAUDE_API_KEY=<your_key>
QDRANT_URL=<your_qdrant_url>
VECTOR_SERVICE_TYPE=qdrant
FRONTEND_URL=${{examcraft-frontend.URL}}
```

#### Frontend Service

```yaml
Name: examcraft-frontend
Type: Static Site
Region: Frankfurt
Branch: main

Build Command:
cd frontend && npm install && npm run build

Publish Directory:
frontend/build
```

**Environment Variables:**

```bash
NODE_VERSION=18.18.0
REACT_APP_API_URL=${{examcraft-backend.URL}}
REACT_APP_ENVIRONMENT=production
```

#### PostgreSQL Database

```yaml
Name: examcraft-postgres
Type: PostgreSQL
Plan: Starter (Free)
Region: Frankfurt
Database Name: examcraft
```

#### Redis Cache

```yaml
Name: examcraft-redis
Type: Redis
Plan: Starter (Free)
Region: Frankfurt
Maxmemory Policy: allkeys-lru
```

## 🔧 Qdrant Vector Database Setup

### Option A: Qdrant Cloud (Empfohlen für Production)

1. **Qdrant Cloud Account erstellen**
   - Gehe zu <https://cloud.qdrant.io>
   - Erstelle kostenlosen Cluster
   - Notiere Cluster URL und API Key

2. **Environment Variables setzen**

   ```bash
   QDRANT_URL=https://xyz-abc.qdrant.io:6333
   QDRANT_API_KEY=your_api_key_here
   VECTOR_SERVICE_TYPE=qdrant
   ```

### Option B: Qdrant als Render Service

Qdrant kann auch als Docker-Container auf Render.com deployed werden:

```yaml
# In render.yaml hinzufügen:
- type: web
  name: examcraft-qdrant
  runtime: docker
  plan: starter
  region: frankfurt
  dockerfilePath: ./docker/Qdrant.Dockerfile
  dockerContext: .
  envVars:
    - key: QDRANT__SERVICE__HTTP_PORT
      value: 6333
```

**Qdrant Dockerfile** (`docker/Qdrant.Dockerfile`):

```dockerfile
FROM qdrant/qdrant:latest

EXPOSE 6333

CMD ["./qdrant"]
```

## 📊 Post-Deployment Checks

### 1. Service Health Checks

```bash
# Backend Health
curl https://examcraft-backend.onrender.com/api/v1/health

# Expected Response:
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "redis": "connected",
    "vector_db": "connected"
  }
}
```

### 2. Frontend Verfügbarkeit

```bash
# Frontend laden
curl https://examcraft-frontend.onrender.com

# Sollte HTML zurückgeben
```

### 3. API Funktionalität

```bash
# Test Document Upload
curl -X POST https://examcraft-backend.onrender.com/api/v1/documents/upload \
  -F "file=@test.pdf"

# Test Question Generation
curl -X POST https://examcraft-backend.onrender.com/api/v1/rag/generate-exam \
  -H "Content-Type: application/json" \
  -d '{
    "document_ids": ["doc_123"],
    "num_questions": 5,
    "difficulty": "medium"
  }'
```

## 🔍 Monitoring & Logging

### Render.com Dashboard

- **Logs**: Echtzeit-Logs für alle Services
- **Metrics**: CPU, Memory, Request Count
- **Alerts**: Email-Benachrichtigungen bei Fehlern

### Custom Monitoring

```python
# backend/main.py - Logging konfigurieren
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## 🛠️ Troubleshooting

### Backend startet nicht

```bash
# Logs prüfen
render logs examcraft-backend

# Häufige Probleme:
# 1. Fehlende Environment Variables
# 2. Database Connection Timeout
# 3. Qdrant nicht erreichbar
```

**Lösung:**

- Environment Variables überprüfen
- Database Connection String validieren
- Qdrant URL und API Key testen

### Frontend zeigt API-Fehler

```bash
# CORS-Probleme prüfen
# Backend muss Frontend-URL in CORS_ORIGINS haben
```

**Lösung:**

```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "*")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Qdrant Connection Failed

```bash
# Qdrant Erreichbarkeit testen
curl https://your-qdrant-url.qdrant.io:6333/collections
```

**Fallback zu Mock Service:**

```bash
# Temporär Mock Service verwenden
VECTOR_SERVICE_TYPE=mock
```

## 🔐 Security Best Practices

### 1. Environment Variables

- ✅ Niemals API Keys in Code committen
- ✅ Render.com Secret Management verwenden
- ✅ Regelmäßig Keys rotieren

### 2. CORS Configuration

```python
# Nur spezifische Origins erlauben
CORS_ORIGINS=https://examcraft-frontend.onrender.com
```

### 3. Rate Limiting

```python
# Claude API Rate Limiting bereits implementiert
CLAUDE_MAX_RPM=50
```

## 📈 Scaling

### Horizontal Scaling

```yaml
# render.yaml
services:
  - type: web
    name: examcraft-backend
    plan: standard  # Upgrade für Auto-Scaling
    scaling:
      minInstances: 1
      maxInstances: 3
      targetCPUPercent: 70
```

### Database Scaling

```yaml
databases:
  - name: examcraft-postgres
    plan: pro  # Upgrade für mehr Connections
```

## 💰 Cost Estimation

### Free Tier

- Backend: Free (750 hours/month)
- Frontend: Free (100 GB bandwidth)
- PostgreSQL: Free (90 days, dann $7/month)
- Redis: Free (25 MB)

### Starter Tier (~$20/month)

- Backend: $7/month
- Frontend: Free
- PostgreSQL: $7/month
- Redis: $7/month

### Production Tier (~$50/month)

- Backend: $25/month (Standard)
- Frontend: Free
- PostgreSQL: $20/month (Pro)
- Redis: $10/month (Standard)

## 🔄 CI/CD Pipeline

Render.com deployed automatisch bei Git Push:

```bash
# Automatisches Deployment
git push origin main

# Render.com:
# 1. Erkennt Push
# 2. Führt Build aus
# 3. Deployed neue Version
# 4. Health Checks
# 5. Traffic Umleitung
```

## 📞 Support

- **Render.com Docs**: <https://render.com/docs>
- **ExamCraft Issues**: GitHub Issues
- **Community**: Discord/Slack Channel

---

**Status**: ✅ Production Ready
**Last Updated**: 2025-10-06
**Maintained by**: Talent Factory Team
