# 🔍 Sentry Integration - Error Tracking & Performance Monitoring

## Übersicht

ExamCraft AI nutzt [Sentry.io](https://sentry.io) für:
- **Error Tracking**: Automatische Erfassung von Fehlern in Frontend und Backend
- **Performance Monitoring**: Überwachung von API-Latenz und Datenbankabfragen
- **Release Tracking**: Fehlerrate nach Deployments überwachen
- **User Context**: Welche User sind von Fehlern betroffen?

---

## 🚀 Quick Start

### 1. Sentry DSNs erhalten

Die DSNs (Data Source Names) sind bereits in den `.env` Dateien konfiguriert:

**Backend DSN:**
```
https://3defbb903cfb9fc06437cdf23c812385@o4509606849019904.ingest.de.sentry.io/4510238621106256
```

**Frontend DSN:**
```
https://acc8ca397422d4f7be7c6e2271f304ef@o4509606849019904.ingest.de.sentry.io/4510238613831760
```

### 2. Sentry aktivieren

**Für Development (lokal testen):**
```bash
# In .env
ENABLE_SENTRY=true
REACT_APP_ENABLE_SENTRY=true
```

**Für Production:**
```bash
# In .env.production
ENABLE_SENTRY=true
REACT_APP_ENABLE_SENTRY=true
ENVIRONMENT=production
REACT_APP_ENVIRONMENT=production
```

### 3. Docker Container neu starten

```bash
docker compose down
docker compose up -d --build
```

---

## 🧪 Sentry testen

### Backend Test-Endpoints

Sentry stellt Test-Endpoints bereit (nur in development):

**1. Sentry Status prüfen:**
```bash
curl http://localhost:8000/api/sentry-test/status
```

**2. Test-Fehler auslösen:**
```bash
curl -X POST http://localhost:8000/api/sentry-test/error
```

**3. Test-Message senden:**
```bash
curl -X POST http://localhost:8000/api/sentry-test/message
```

**4. Performance-Test:**
```bash
curl -X POST http://localhost:8000/api/sentry-test/performance
```

### Frontend Test

Das Frontend hat einen Test-Button (nur in development):
- Öffnen Sie http://localhost:3000
- Klicken Sie auf den roten Button unten rechts: "🐛 Trigger Test Error"
- Der Fehler wird automatisch an Sentry gesendet

---

## 📊 Sentry Dashboard

### Fehler anzeigen

1. Gehen Sie zu: https://talent-factory.sentry.io/
2. Wählen Sie das Projekt:
   - **examcraft-frontend** für Frontend-Fehler
   - **examcraft-backend** für Backend-Fehler
3. Klicken Sie auf "Issues" → Alle Fehler werden angezeigt

### Performance Monitoring

1. Gehen Sie zu: https://talent-factory.sentry.io/
2. Klicken Sie auf "Performance"
3. Sehen Sie:
   - API Response Times (P95, P99)
   - Slow Database Queries
   - HTTP Request Counts

---

## 🔧 Konfiguration

### Environment Variables

**Backend (.env):**
```bash
SENTRY_DSN=https://...@o4509606849019904.ingest.de.sentry.io/...
ENABLE_SENTRY=false              # true für Production
ENVIRONMENT=development          # development, staging, production
APP_VERSION=1.0.0-dev           # Für Release Tracking
```

**Frontend (.env):**
```bash
REACT_APP_SENTRY_DSN=https://...@o4509606849019904.ingest.de.sentry.io/...
REACT_APP_ENABLE_SENTRY=false   # true für Production
REACT_APP_ENVIRONMENT=development
REACT_APP_VERSION=1.0.0-dev
```

### Sampling Rates

**Backend (config/sentry.py):**
```python
traces_sample_rate=1.0 if environment == "development" else 0.1
```
- Development: 100% aller Transaktionen
- Production: 10% aller Transaktionen (spart Kosten)

**Frontend (config/sentry.ts):**
```typescript
tracesSampleRate: environment === "production" ? 0.1 : 1.0
replaysSessionSampleRate: 0.1  // 10% aller Sessions
replaysOnErrorSampleRate: 1.0  // 100% bei Fehlern
```

---

## 🛡️ GDPR & Datenschutz

### PII (Personally Identifiable Information)

Sentry ist GDPR-konform konfiguriert:

**Backend:**
```python
send_default_pii=False  # Keine automatische PII-Erfassung
```

**Frontend:**
```typescript
maskAllText: true      // Alle Texte maskiert
blockAllMedia: true    // Alle Medien blockiert
```

### User Context

Nur minimale User-Informationen werden gesendet:
```python
{
    "id": "123",           # User ID (anonymisiert)
    "email": None,         # Kein Email (GDPR)
    "username": "user123"  # Optional
}
```

---

## 📝 Custom Error Capture

### Backend

```python
from config.sentry import capture_exception_with_context

try:
    result = await generate_exam_questions(topic, documents)
except Exception as e:
    capture_exception_with_context(
        exception=e,
        user_id=current_user.id,
        extra_context={
            "topic": topic,
            "document_count": len(documents),
        },
        tags={
            "feature": "question_generation",
            "bloom_level": bloom_level,
        }
    )
    raise
```

### Frontend

```typescript
import * as Sentry from '@sentry/react';

try {
  await generateQuestions(topic);
} catch (error) {
  Sentry.captureException(error, {
    tags: {
      feature: 'question_generation',
    },
    contexts: {
      topic: {
        name: topic,
        difficulty: difficulty,
      },
    },
  });
  throw error;
}
```

---

## 🔔 Alerts konfigurieren

### In Sentry Dashboard

1. Gehen Sie zu: https://talent-factory.sentry.io/settings/talent-factory/projects/examcraft-backend/alerts/
2. Klicken Sie auf "Create Alert Rule"
3. Beispiel-Regeln:
   - **>10 Fehler in 5 Minuten** → Email Alert
   - **Neue Fehler nach Release** → Slack/Email
   - **Performance Degradation >20%** → Alert

---

## 📈 Best Practices

### 1. Error Filtering

Nicht alle Fehler sind kritisch. Filtern Sie unwichtige Fehler:

**Backend:**
```python
# In config/sentry.py
def filter_errors(event, hint):
    # 404-Fehler nicht senden
    if hasattr(exc_value, "status_code") and exc_value.status_code == 404:
        return None
    return event
```

**Frontend:**
```typescript
// In config/sentry.ts
beforeSend(event, hint) {
  if (error?.message?.includes('404')) {
    return null;  // Nicht senden
  }
  return event;
}
```

### 2. Release Tracking

Setzen Sie immer die Version:
```bash
APP_VERSION=1.2.3
REACT_APP_VERSION=1.2.3
```

### 3. Environments

Nutzen Sie verschiedene Environments:
- `development` - Lokale Entwicklung
- `staging` - Test-Umgebung
- `production` - Live-System

---

## 🆘 Troubleshooting

### Fehler werden nicht gesendet

**Prüfen Sie:**
1. Ist `ENABLE_SENTRY=true`?
2. Ist der DSN korrekt?
3. Ist die Firewall offen für `*.sentry.io`?
4. Logs prüfen: `docker compose logs backend | grep Sentry`

### Source Maps fehlen (Frontend)

**Lösung:**
```bash
# In package.json
"build": "GENERATE_SOURCEMAP=true craco build"
```

### Performance-Daten fehlen

**Prüfen Sie:**
```python
# Backend
traces_sample_rate=1.0  # Für Testing

# Frontend
tracesSampleRate: 1.0  # Für Testing
```

---

## 📚 Weitere Ressourcen

- **Sentry Docs (React):** https://docs.sentry.io/platforms/javascript/guides/react/
- **Sentry Docs (FastAPI):** https://docs.sentry.io/platforms/python/integrations/fastapi/
- **Sentry Dashboard:** https://talent-factory.sentry.io/
- **Performance Monitoring:** https://docs.sentry.io/product/performance/

---

## 🎯 Zusammenfassung

✅ **Sentry ist vollständig integriert**
✅ **GDPR-konform konfiguriert**
✅ **Test-Endpoints verfügbar**
✅ **Error Filtering aktiv**
✅ **Performance Monitoring aktiv**

**Nächste Schritte:**
1. Sentry in Production aktivieren (`ENABLE_SENTRY=true`)
2. Alert-Rules konfigurieren
3. Team-Mitglieder zu Sentry hinzufügen
4. Regelmäßig Sentry Dashboard prüfen

