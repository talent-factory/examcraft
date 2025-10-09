# Render.com Deployment Guide

## 🚀 ExamCraft AI auf Render.com

### Memory-Optimierung für Free/Starter Tier

**Problem**: Out of Memory (512 MB RAM Limit)

**Lösung**: Environment Variables für Memory-Reduktion

### 📋 Erforderliche Environment Variables

#### 1. **DOCUMENT_PROCESSOR_TYPE** (WICHTIG!)

```bash
DOCUMENT_PROCESSOR_TYPE=legacy
```

**Warum?**
- Docling ist sehr speicherintensiv (~300-400 MB)
- Legacy Processor benötigt nur ~50 MB
- Für Free Tier (512 MB) ist Legacy Processor erforderlich

**Optionen**:
- `legacy` - Leichtgewichtiger Processor (empfohlen für Free Tier)
- `docling` - Volle Features, benötigt >1 GB RAM
- `auto` - Automatische Erkennung (Standard)

#### 2. **Weitere Environment Variables**

```bash
# Database
DATABASE_URL=<your-postgres-url>

# Redis
REDIS_URL=<your-redis-url>

# Vector Database
VECTOR_SERVICE_TYPE=qdrant
QDRANT_URL=<your-qdrant-url>
QDRANT_API_KEY=<your-qdrant-key>

# Claude API
CLAUDE_API_KEY=<your-claude-key>

# CORS
CORS_ORIGINS=https://your-frontend.onrender.com,https://examcraft.com

# Environment
ENVIRONMENT=production
```

### 🔧 Render.com Setup

#### Backend Service

1. **Service Type**: Web Service
2. **Build Command**: 
   ```bash
   pip install -r backend/requirements.txt
   ```
3. **Start Command**:
   ```bash
   cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
4. **Instance Type**: 
   - **Free Tier**: 512 MB RAM (nur mit `DOCUMENT_PROCESSOR_TYPE=legacy`)
   - **Starter**: 512 MB RAM (nur mit `DOCUMENT_PROCESSOR_TYPE=legacy`)
   - **Starter Plus**: 2 GB RAM (empfohlen für `DOCUMENT_PROCESSOR_TYPE=docling`)

#### Frontend Service

1. **Service Type**: Static Site
2. **Build Command**:
   ```bash
   cd frontend && npm install && npm run build
   ```
3. **Publish Directory**: `frontend/build`

### 📊 Memory-Verbrauch

| Komponente | Legacy Processor | Docling Processor |
|------------|------------------|-------------------|
| Base FastAPI | ~100 MB | ~100 MB |
| Document Processor | ~50 MB | ~350 MB |
| Claude Service | ~30 MB | ~30 MB |
| Vector DB Client | ~40 MB | ~40 MB |
| PostgreSQL Client | ~20 MB | ~20 MB |
| **TOTAL** | **~240 MB** | **~540 MB** |

**Fazit**: 
- ✅ Free Tier (512 MB) funktioniert mit `DOCUMENT_PROCESSOR_TYPE=legacy`
- ❌ Free Tier (512 MB) funktioniert NICHT mit Docling
- ✅ Starter Plus (2 GB) funktioniert mit Docling

### 🐛 Troubleshooting

#### "Out of memory (used over 512Mi)"

**Lösung 1**: Environment Variable setzen
```bash
DOCUMENT_PROCESSOR_TYPE=legacy
```

**Lösung 2**: Upgrade auf Starter Plus ($7/Monat)
- 2 GB RAM
- Volle Docling-Features

#### "No open ports detected"

**Ursache**: App startet nicht wegen Memory-Fehler

**Lösung**: Siehe "Out of memory" oben

#### "Import Error: failed to find libmagic"

**Ursache**: System-Library fehlt

**Lösung**: Bereits in `requirements.txt` enthalten:
```txt
python-magic-bin==0.4.14  # Includes libmagic
```

### 📝 Deployment Checklist

- [ ] Environment Variables gesetzt
- [ ] `DOCUMENT_PROCESSOR_TYPE=legacy` für Free Tier
- [ ] Database URL konfiguriert
- [ ] Redis URL konfiguriert
- [ ] Claude API Key gesetzt
- [ ] CORS Origins konfiguriert
- [ ] Health Check funktioniert: `/health`
- [ ] API Docs erreichbar: `/docs`

### 🔗 Nützliche Links

- **Health Check**: `https://your-backend.onrender.com/health`
- **API Docs**: `https://your-backend.onrender.com/docs`
- **Detailed Health**: `https://your-backend.onrender.com/api/v1/health`

### 💡 Best Practices

1. **Monitoring**: Nutze `/api/v1/health` für Uptime-Monitoring
2. **Logs**: Aktiviere Render.com Logs für Debugging
3. **Auto-Deploy**: Aktiviere Auto-Deploy für `main` Branch
4. **Environment**: Nutze separate Environments für Staging/Production

