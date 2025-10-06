# ExamCraft AI - Render.com Deployment Quick Start

## 🚀 5-Minuten Deployment

### Schritt 1: Render.com Account (1 Minute)

1. Gehe zu https://render.com
2. Registriere dich mit GitHub/GitLab Account
3. Verbinde dein ExamCraft Repository

### Schritt 2: Blueprint Deployment (2 Minuten)

1. **In Render.com Dashboard:**
   - Klicke auf "New" → "Blueprint"
   - Wähle dein ExamCraft Repository
   - Branch: `main` (oder `develop`)
   - Render erkennt automatisch `render.yaml`

2. **Environment Variables setzen:**
   
   Klicke auf "Advanced" und füge hinzu:
   
   ```bash
   # Backend Service
   CLAUDE_API_KEY=sk-ant-your_key_here
   QDRANT_URL=https://your-cluster.qdrant.io:6333
   ```

3. **Deployment starten:**
   - Klicke "Apply"
   - Render erstellt automatisch alle Services

### Schritt 3: Qdrant Cloud Setup (2 Minuten)

1. **Qdrant Cloud Account:**
   - Gehe zu https://cloud.qdrant.io
   - Erstelle kostenlosen Account
   - Erstelle neuen Cluster (Free Tier)

2. **Cluster URL kopieren:**
   ```bash
   # Beispiel URL:
   https://abc-xyz-123.qdrant.io:6333
   ```

3. **In Render.com einfügen:**
   - Gehe zu Backend Service → Environment
   - Setze `QDRANT_URL` auf deine Cluster URL

### Schritt 4: Deployment verifizieren (1 Minute)

1. **Warte auf Deployment:**
   - Backend: ~3-5 Minuten
   - Frontend: ~2-3 Minuten
   - Databases: ~1-2 Minuten

2. **Services testen:**
   ```bash
   # Backend Health Check
   curl https://your-backend.onrender.com/api/v1/health
   
   # Frontend öffnen
   open https://your-frontend.onrender.com
   ```

3. **Automatischer Health Check:**
   ```bash
   # Lokales Script ausführen
   python scripts/check-render-services.py \
     https://your-backend.onrender.com \
     https://your-frontend.onrender.com
   ```

## ✅ Fertig!

Deine ExamCraft AI Instanz läuft jetzt auf Render.com!

### Nächste Schritte:

- 📊 **Monitoring**: Render Dashboard → Metrics
- 🔍 **Logs**: Render Dashboard → Logs
- 🔧 **Updates**: Git Push → Auto-Deploy
- 📈 **Scaling**: Upgrade Plan für mehr Resources

## 🆘 Troubleshooting

### Backend startet nicht

**Problem:** Build failed oder Service crashed

**Lösung:**
```bash
# Logs prüfen
render logs examcraft-backend --tail 100

# Häufige Ursachen:
# 1. Fehlende CLAUDE_API_KEY
# 2. Ungültige QDRANT_URL
# 3. Database Connection Timeout
```

### Frontend zeigt Fehler

**Problem:** API Calls schlagen fehl

**Lösung:**
```bash
# CORS prüfen
# Backend muss Frontend URL in CORS_ORIGINS haben

# In Render.com Backend Environment:
CORS_ORIGINS=https://your-frontend.onrender.com
```

### Qdrant Connection Failed

**Problem:** Vector Database nicht erreichbar

**Lösung:**
```bash
# Qdrant URL testen
curl https://your-cluster.qdrant.io:6333/collections

# Fallback zu Mock Service (temporär):
VECTOR_SERVICE_TYPE=mock
```

## 📞 Support

- **Render Docs**: https://render.com/docs
- **Qdrant Docs**: https://qdrant.tech/documentation
- **ExamCraft Issues**: GitHub Issues

---

**Deployment Zeit**: ~10 Minuten
**Kosten**: Free Tier verfügbar
**Auto-Deploy**: ✅ Aktiviert

