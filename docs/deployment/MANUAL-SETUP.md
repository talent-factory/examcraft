# ExamCraft AI - Manuelles Multi-Service Setup auf Render.com

## 🎯 Übersicht

Diese Anleitung zeigt, wie Sie ExamCraft AI **manuell** auf Render.com deployen, ohne Blueprint zu verwenden.

## ✅ Vorteile des manuellen Setups

- Mehr Kontrolle über jeden Service
- Einfacher zu debuggen
- Keine Blueprint-Syntax-Probleme
- Schrittweise Konfiguration

## 📋 Reihenfolge (wichtig!)

1. PostgreSQL Database
2. Redis Cache (optional, später)
3. Backend Service
4. Frontend Service
5. Qdrant (Qdrant Cloud empfohlen)

---

## Schritt 1: PostgreSQL Database erstellen

### Im Render Dashboard:

1. Klicke **"New +"** → **"PostgreSQL"**

2. Konfiguration:
   ```
   Name: examcraft-postgres
   Database: examcraft
   User: examcraft (automatisch)
   Region: Frankfurt
   Plan: Free
   ```

3. Klicke **"Create Database"**

4. **Warte ~2 Minuten** bis Status = "Available"

5. **Kopiere die Connection String:**
   - Gehe zu Database → "Info" Tab
   - Kopiere "Internal Database URL"
   - Format: `postgresql://examcraft_user:password@host/examcraft`

---

## Schritt 2: Backend Service erstellen

### Im Render Dashboard:

1. Klicke **"New +"** → **"Web Service"**

2. **Repository verbinden:**
   - Wähle dein GitHub/GitLab Repository
   - Repository: `examcraft` (oder dein Fork)

3. **Service Konfiguration:**
   ```
   Name: examcraft-backend
   Region: Frankfurt
   Branch: feature/tf-108-render-deployment
   Root Directory: (leer lassen)
   Runtime: Python 3
   ```

4. **Build & Start Commands:**
   ```bash
   Build Command:
   cd backend && pip install -r requirements.txt

   Start Command:
   cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

5. **Plan auswählen:**
   - Starter ($7/month) empfohlen
   - Free Tier funktioniert auch (schläft nach Inaktivität)

6. **Environment Variables hinzufügen:**

   Klicke "Advanced" → "Add Environment Variable"

   **Erforderlich:**
   ```bash
   # Database (aus Schritt 1)
   DATABASE_URL=postgresql://examcraft_user:password@host/examcraft

   # Claude API (WICHTIG!)
   CLAUDE_API_KEY=sk-ant-your_anthropic_api_key_here

   # Qdrant (später konfigurieren)
   QDRANT_URL=https://your-cluster.qdrant.io:6333
   VECTOR_SERVICE_TYPE=qdrant

   # Optional (haben Defaults)
   ENVIRONMENT=production
   PYTHON_VERSION=3.11.0
   CLAUDE_MODEL=claude-3-5-sonnet-20241022
   CLAUDE_MAX_RPM=50
   CLAUDE_MAX_TOKENS=4000
   CORS_ORIGINS=*
   ```

7. **Health Check Path:**
   ```
   /api/v1/health
   ```

8. Klicke **"Create Web Service"**

9. **Warte ~5-10 Minuten** für Build & Deploy

---

## Schritt 3: Frontend Service erstellen

### Im Render Dashboard:

1. Klicke **"New +"** → **"Static Site"**

2. **Repository verbinden:**
   - Wähle dasselbe Repository wie Backend

3. **Service Konfiguration:**
   ```
   Name: examcraft-frontend
   Branch: feature/tf-108-render-deployment
   Root Directory: (leer lassen)
   ```

4. **Build Settings:**
   ```bash
   Build Command:
   cd frontend && npm install && npm run build

   Publish Directory:
   frontend/build
   ```

5. **Environment Variables:**
   ```bash
   NODE_VERSION=18.18.0
   
   # Backend URL (aus Schritt 2)
   REACT_APP_API_URL=https://examcraft-backend.onrender.com
   
   REACT_APP_ENVIRONMENT=production
   ```

6. Klicke **"Create Static Site"**

7. **Warte ~3-5 Minuten** für Build

---

## Schritt 4: Qdrant Vector Database

### Option A: Qdrant Cloud (Empfohlen)

1. **Qdrant Cloud Account:**
   - Gehe zu https://cloud.qdrant.io
   - Registriere dich (kostenlos)

2. **Cluster erstellen:**
   ```
   Name: examcraft-production
   Region: EU-Central (Frankfurt)
   Plan: Free (1GB)
   ```

3. **Credentials kopieren:**
   ```
   Cluster URL: https://abc-xyz.qdrant.io:6333
   API Key: qdr_xxxxxxxxxxxxxxxx
   ```

4. **Backend Environment Variables aktualisieren:**
   
   Gehe zu Backend Service → Environment Tab:
   ```bash
   QDRANT_URL=https://abc-xyz.qdrant.io:6333
   QDRANT_API_KEY=qdr_xxxxxxxxxxxxxxxx
   VECTOR_SERVICE_TYPE=qdrant
   ```

5. Backend wird automatisch neu deployed

### Option B: Temporär Mock Service

Falls Sie Qdrant später konfigurieren möchten:

```bash
# Im Backend Service:
VECTOR_SERVICE_TYPE=mock
```

**Hinweis:** Mock Service hat keine echte Vector Search!

---

## Schritt 5: Redis Cache (Optional)

### Im Render Dashboard:

1. Klicke **"New +"** → **"Redis"**

2. Konfiguration:
   ```
   Name: examcraft-redis
   Region: Frankfurt
   Plan: Free (25MB)
   Maxmemory Policy: allkeys-lru
   ```

3. Klicke **"Create Redis"**

4. **Connection String kopieren:**
   - Gehe zu Redis → "Info" Tab
   - Kopiere "Internal Redis URL"

5. **Backend Environment Variable aktualisieren:**
   ```bash
   REDIS_URL=redis://red-xxxxx:6379
   ```

---

## ✅ Deployment verifizieren

### 1. Backend Health Check

```bash
curl https://examcraft-backend.onrender.com/api/v1/health
```

**Erwartete Antwort:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "redis": "connected",
    "vector_db": "connected",
    "claude_api": "configured"
  }
}
```

### 2. Frontend öffnen

```
https://examcraft-frontend.onrender.com
```

### 3. API Dokumentation

```
https://examcraft-backend.onrender.com/docs
```

---

## 🔧 Troubleshooting

### Backend Build schlägt fehl

**Problem:** `pip install` Fehler

**Lösung:**
```bash
# Prüfe Build Logs im Dashboard
# Häufige Ursachen:
# - Falsche Python Version
# - Fehlende System Dependencies

# Lösung: PYTHON_VERSION=3.11.0 setzen
```

### Backend startet nicht

**Problem:** Service crashed nach Start

**Lösung:**
```bash
# Prüfe Logs:
# - Fehlende DATABASE_URL?
# - Fehlende CLAUDE_API_KEY?
# - Qdrant Connection Failed?

# Temporär Mock Service verwenden:
VECTOR_SERVICE_TYPE=mock
```

### Frontend zeigt API Fehler

**Problem:** CORS oder Connection Refused

**Lösung:**
```bash
# Prüfe REACT_APP_API_URL:
# Muss HTTPS sein: https://examcraft-backend.onrender.com
# Nicht HTTP!

# Backend CORS prüfen:
CORS_ORIGINS=*
```

### Database Connection Failed

**Problem:** Backend kann nicht zu PostgreSQL verbinden

**Lösung:**
```bash
# Prüfe DATABASE_URL Format:
# Muss "Internal Database URL" sein
# Nicht "External Database URL"!

# Format: postgresql://user:pass@internal-host/db
```

---

## 💰 Kosten-Übersicht

```
Backend (Starter):    $7/Monat
Frontend (Static):    Free
PostgreSQL (Free):    $0 (90 Tage), dann $7/Monat
Redis (Free):         $0
Qdrant Cloud (Free):  $0 (1GB)
────────────────────────────
Total:                $7/Monat (erste 90 Tage)
                      $14/Monat (danach)
```

---

## 📊 Service URLs

Nach erfolgreichem Deployment:

```
Frontend:     https://examcraft-frontend.onrender.com
Backend API:  https://examcraft-backend.onrender.com
API Docs:     https://examcraft-backend.onrender.com/docs
Health:       https://examcraft-backend.onrender.com/api/v1/health
```

---

## 🚀 Nächste Schritte

1. ✅ Teste Document Upload
2. ✅ Teste Question Generation
3. ✅ Konfiguriere Custom Domain (optional)
4. ✅ Setup Monitoring & Alerts
5. ✅ Backup-Strategie definieren

---

**Geschätzte Setup-Zeit:** 20-30 Minuten
**Schwierigkeit:** Mittel
**Empfohlen für:** Production Deployments

