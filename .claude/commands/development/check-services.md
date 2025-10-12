# Check Services Status

Überprüfe den Status aller ExamCraft AI Development Services und biete Troubleshooting-Hilfe bei Problemen.

## Aufgabe

Du sollst:

1. **Docker Services prüfen**:
   - Prüfe ob Docker läuft
   - Liste alle ExamCraft Container auf
   - Zeige Status von allen Services (Backend, Frontend, PostgreSQL, Redis)
   - Identifiziere fehlgeschlagene oder nicht laufende Services

2. **Service Health Checks**:
   - Backend API Health Check (<http://localhost:8000/health>)
   - Frontend Erreichbarkeit (<http://localhost:3000>)
   - PostgreSQL Verbindung testen
   - Redis Verbindung testen

3. **Port-Verfügbarkeit prüfen**:
   - Prüfe ob Ports 3000, 8000, 5432, 6379 verfügbar/belegt sind
   - Identifiziere Port-Konflikte

4. **Log-Analyse bei Problemen**:
   - Bei fehlgeschlagenen Services: zeige die letzten 20 Zeilen der Logs
   - Identifiziere häufige Fehlermuster
   - Biete spezifische Lösungsvorschläge

5. **Status-Report**:
   - Zeige übersichtlichen Status aller Services
   - Verwende Emojis: ✅ (läuft), ❌ (fehler), ⏳ (startet), ⚠️ (warnung)
   - Gib konkrete nächste Schritte bei Problemen

## Nützliche Commands

```bash
# Docker Status
docker info
docker-compose ps

# Service Health Checks
curl -f http://localhost:8000/health
curl -f http://localhost:3000

# Database Checks
docker exec examcraft_postgres pg_isready -U examcraft
docker exec examcraft_redis redis-cli ping

# Port Checks
lsof -i :3000
lsof -i :8000
lsof -i :5432
lsof -i :6379

# Logs
docker-compose logs --tail=20 backend
docker-compose logs --tail=20 frontend
docker-compose logs --tail=20 postgres
docker-compose logs --tail=20 redis
```

## Häufige Probleme & Lösungen

- **Port bereits belegt**: `docker-compose down` und wieder `docker-compose up`
- **Backend startet nicht**: Prüfe .env Datei und Claude API Key
- **Frontend Build Fehler**: `docker-compose build frontend --no-cache`
- **Datenbank Connection Error**: Warte 10-30 Sekunden nach Start
- **Redis nicht erreichbar**: `docker-compose restart redis`

## Expected Output Format

```
🔍 ExamCraft AI Services Status Check

Docker Status: ✅ Running

Services:
  Backend (Port 8000):     ✅ Running & Healthy
  Frontend (Port 3000):    ✅ Running & Accessible
  PostgreSQL (Port 5432):  ✅ Connected & Ready
  Redis (Port 6379):       ✅ Connected & Responsive

All services are running normally! 🎉

Quick Access:
  • Frontend: http://localhost:3000
  • API Docs: http://localhost:8000/docs
  • Backend Health: http://localhost:8000/health
```

Bei Problemen gib spezifische Troubleshooting-Schritte und verwende `/restart-dev` wenn ein Neustart empfohlen wird.
