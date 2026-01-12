# Check Deployment Status

Überprüft den Status und die Funktionalität des Production Deployments auf Render.com.

## Was wird geprüft

1. **Service Status** - Alle Services laufen
2. **Health Checks** - Backend API ist erreichbar
3. **Frontend** - Website lädt korrekt
4. **Database** - PostgreSQL Verbindung
5. **Redis** - Cache verfügbar
6. **Qdrant** - Vector Database erreichbar
7. **API Endpoints** - Kritische Endpoints funktionieren

## Verwendung

```text
/check-deployment
```

## Optionale Parameter

- `--verbose` - Detaillierte Ausgabe
- `--url <custom-url>` - Prüfe spezifische URL statt Standard

## Beispiele

```text
/check-deployment
/check-deployment --verbose
/check-deployment --url https://examcraft.talent-factory.xyz
```

## Ausgabe

- ✅ Service Status
- ✅ Health Check Results
- ✅ API Endpoint Tests
- ⚠️ Warnungen (falls vorhanden)
- ❌ Fehler (falls vorhanden)

## Hinweis

Dieser Command verwendet die Render.com MCP API und HTTP-Requests, um die Deployment-Funktionalität zu überprüfen.
