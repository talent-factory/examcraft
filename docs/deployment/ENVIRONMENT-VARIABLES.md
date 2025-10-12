# Environment Variables Management

Anleitung zum Setzen und Verwalten von Environment Variables für Production Deployment auf Render.com.

## 📋 Übersicht

Environment Variables müssen **einmalig manuell** im Render Dashboard gesetzt werden. Sie bleiben dann bei allen künftigen Deployments persistent.

## 🔧 Automatisches Sync-Tool

Wir haben ein Tool erstellt, das Ihre lokale `.env` Datei analysiert und zeigt, welche Variables in Render gesetzt werden müssen:

```bash
# Environment Variables analysieren
python scripts/sync_env_to_render.py

# Mit Template-Generierung
python scripts/sync_env_to_render.py --generate-template
```

**Output:**

- ✅ Liste aller Required Variables
- ✅ Liste aller Auto-Variables (von Render gesetzt)
- ✅ Liste aller Optional Variables
- ✅ `.env.render` Template-Datei

## 📝 Required Environment Variables

Diese Variables **müssen** Sie manuell im Render Dashboard setzen:

### 1. Claude API Configuration

```bash
CLAUDE_API_KEY=sk-ant-api03-YOUR_KEY_HERE
CLAUDE_MODEL=claude-3-5-sonnet-20241022
CLAUDE_MAX_RPM=50
CLAUDE_MAX_TOKENS=4000
CLAUDE_MAX_RETRIES=3
CLAUDE_RETRY_DELAY=1.0
CLAUDE_DEMO_MODE=false
```

### 2. Database URLs

**WICHTIG**: Diese URLs müssen Sie aus dem Render Dashboard kopieren!

#### PostgreSQL Database URL

1. Öffnen Sie: <https://dashboard.render.com/d/dpg-d3hnug7diees73cgu7gg-a>
2. Gehen Sie zum **"Info"** Tab
3. Kopieren Sie die **"Internal Database URL"**
4. Format: `postgresql://user:PASSWORD@host/database`

```bash
DATABASE_URL=postgresql://examcraft_postgres_jyxc_user:PASSWORD@dpg-d3hnug7diees73cgu7gg-a/examcraft_postgres_jyxc
```

#### Redis URL

1. Öffnen Sie: <https://dashboard.render.com/redis/red-d3hnug95pdvs73fe1u6g>
2. Kopieren Sie die **"Internal Redis URL"**

```bash
REDIS_URL=redis://red-d3hnug95pdvs73fe1u6g:6379
```

### 3. Vector Database (Qdrant)

```bash
VECTOR_SERVICE_TYPE=qdrant
QDRANT_URL=https://YOUR_CLUSTER.qdrant.io:6333
QDRANT_API_KEY=YOUR_QDRANT_API_KEY
```

### 4. Production Configuration

```bash
ENVIRONMENT=production
DEBUG=false
```

### 5. CORS & Frontend

```bash
CORS_ORIGINS=https://examcraft.talent-factory.xyz,https://api.examcraft.talent-factory.xyz
FRONTEND_URL=https://examcraft.talent-factory.xyz
REACT_APP_API_URL=https://api.examcraft.talent-factory.xyz
REACT_APP_ENVIRONMENT=production
```

### 6. Security

Generieren Sie einen zufälligen SECRET_KEY:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

```bash
SECRET_KEY=YOUR_GENERATED_SECRET_KEY
```

## 🚀 Environment Variables setzen

### Schritt 1: Backend Service

1. Öffnen Sie: <https://dashboard.render.com/web/srv-d3hnuk1r0fns73chrjsg/env>

2. Klicken Sie **"Add Environment Variable"** für jede Variable

3. Setzen Sie folgende Variables:

   | Key | Value | Secret? |
   |-----|-------|---------|
   | `ENVIRONMENT` | `production` | No |
   | `DEBUG` | `false` | No |
   | `CLAUDE_API_KEY` | `sk-ant-...` | **Yes** |
   | `CLAUDE_MODEL` | `claude-3-5-sonnet-20241022` | No |
   | `CLAUDE_MAX_RPM` | `50` | No |
   | `CLAUDE_MAX_TOKENS` | `4000` | No |
   | `CLAUDE_MAX_RETRIES` | `3` | No |
   | `CLAUDE_RETRY_DELAY` | `1.0` | No |
   | `CLAUDE_DEMO_MODE` | `false` | No |
   | `DATABASE_URL` | `postgresql://...` | **Yes** |
   | `REDIS_URL` | `redis://...` | **Yes** |
   | `VECTOR_SERVICE_TYPE` | `qdrant` | No |
   | `QDRANT_URL` | `https://...` | No |
   | `QDRANT_API_KEY` | `...` | **Yes** |
   | `CORS_ORIGINS` | `https://examcraft.talent-factory.xyz,...` | No |
   | `FRONTEND_URL` | `https://examcraft.talent-factory.xyz` | No |
   | `SECRET_KEY` | `...` | **Yes** |

4. Klicken Sie **"Save Changes"**

5. Neues Deployment wird automatisch getriggert

### Schritt 2: Frontend Service

1. Öffnen Sie: <https://dashboard.render.com/static/srv-d3hnupvdiees73cgudp0/env>

2. Setzen Sie:

   | Key | Value |
   |-----|-------|
   | `REACT_APP_API_URL` | `https://api.examcraft.talent-factory.xyz` |
   | `REACT_APP_ENVIRONMENT` | `production` |

3. Klicken Sie **"Save Changes"**

## ✅ Automatisch gesetzte Variables

Diese Variables werden **automatisch** von Render.com gesetzt und müssen **nicht** manuell konfiguriert werden:

- `PORT` - Port für den Service
- `RENDER` - Immer `true` auf Render
- `RENDER_SERVICE_NAME` - Name des Services
- `RENDER_INSTANCE_ID` - Unique Instance ID
- `RENDER_GIT_COMMIT` - Git Commit SHA
- `RENDER_GIT_BRANCH` - Git Branch Name

## 🔄 Bei künftigen Deployments

**Gute Nachricht**: Environment Variables bleiben persistent!

- ✅ Bei jedem neuen Deployment (Git Push) bleiben die Variables erhalten
- ✅ Sie müssen sie **nicht** erneut setzen
- ✅ Nur bei Änderungen müssen Sie sie aktualisieren

## 🔐 Secrets Management

**Best Practices:**

1. **Niemals Secrets in Git committen**
   - `.env` ist in `.gitignore`
   - `.env.production` ist in `.gitignore`
   - `.env.render` ist in `.gitignore`

2. **Secrets als "Secret" markieren**
   - Im Render Dashboard: Checkbox "Secret" aktivieren
   - Secrets werden dann maskiert angezeigt

3. **Secrets rotieren**
   - Regelmäßig API Keys erneuern
   - Alte Keys deaktivieren

## 🐛 Troubleshooting

### Problem: DATABASE_URL fehlt

**Symptom:**

```
psycopg2.OperationalError: fe_sendauth: no password supplied
```

**Lösung:**

1. Gehen Sie zu PostgreSQL Dashboard
2. Kopieren Sie "Internal Database URL"
3. Setzen Sie im Backend Service als `DATABASE_URL`

### Problem: Qdrant Connection Error

**Symptom:**

```
{"error":"forbidden"}
```

**Lösung:**

1. Prüfen Sie `QDRANT_URL` (muss HTTPS sein)
2. Prüfen Sie `QDRANT_API_KEY`
3. Prüfen Sie Qdrant Cloud Dashboard

### Problem: CORS Error

**Symptom:**

```
Access to fetch at '...' from origin '...' has been blocked by CORS policy
```

**Lösung:**

1. Prüfen Sie `CORS_ORIGINS` im Backend
2. Muss Frontend-URL enthalten
3. Format: `https://examcraft.talent-factory.xyz,https://api.examcraft.talent-factory.xyz`

## 📚 Weitere Ressourcen

- [Render.com Environment Variables Docs](https://render.com/docs/environment-variables)
- [Render.com Secrets Management](https://render.com/docs/secrets)
- [ExamCraft Deployment Guide](./render-deployment.md)
