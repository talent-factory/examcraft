# Restart Development Environment

Führe einen intelligenten Neustart der ExamCraft AI Development Environment durch mit automatischer Problemdiagnose und schrittweisem Recovery.

## Aufgabe

Du sollst einen sauberen Development-Neustart durchführen:

1. **Aktuellen Zustand analysieren**:
   - Prüfe welche Services laufen
   - Identifiziere hängende Prozesse
   - Zeige an welche Ports belegt sind

2. **Graceful Shutdown**:
   - Stoppe alle Docker Compose Services ordnungsgemäß
   - Warte auf komplettes Herunterfahren
   - Prüfe ob alle Container gestoppt wurden

3. **Cleanup (falls nötig)**:
   - Entferne hängende Container
   - Räume ungenutzte Docker Volumes auf (nur wenn explizit problematisch)
   - Prüfe auf Port-Konflikte und löse sie

4. **Environment Validation**:
   - Prüfe ob .env Datei existiert
   - Validiere Docker-Installation
   - Überprüfe verfügbaren Speicherplatz

5. **Smart Restart**:
   - Starte Services in der richtigen Reihenfolge
   - Warte auf Database-Readiness vor Backend-Start
   - Führe Health Checks durch
   - Zeige detaillierte Startup-Logs bei Fehlern

6. **Post-Startup Validation**:
   - Führe vollständige Service-Checks durch
   - Teste alle API Endpoints
   - Verificare Frontend-Zugriff
   - Zeige finale Status-Übersicht

## Restart Strategie

```bash
# 1. Graceful Stop
echo "🛑 Stopping all services..."
docker-compose down

# 2. Force cleanup (nur bei Problemen)
docker system prune -f --volumes  # NUR bei hartnäckigen Problemen

# 3. Restart mit Build (bei Code-Änderungen)
docker-compose up --build -d

# 4. Health Monitoring
# Überwache Startup-Prozess und gib detailliertes Feedback
```

## Restart-Modi

**Standard Restart**:

- `docker-compose down && docker-compose up -d`

**Full Rebuild**:

- Wenn Code-Änderungen vorhanden sind
- `docker-compose down && docker-compose up --build -d`

**Clean Restart**:

- Bei persistenten Problemen
- Entfernt Volumes und Images (mit Bestätigung!)
- `docker-compose down -v && docker system prune -f`

## Environment Checks

Vor dem Restart prüfen:

- `.env` Datei vorhanden und konfiguriert
- Docker läuft und hat genug Ressourcen
- Ports 3000, 8000, 5432, 6379 sind frei
- Genug Festplattenspeicher verfügbar (min. 2GB frei)

## Troubleshooting during Restart

**Häufige Probleme**:

- Port already in use → Force kill Prozesse
- Volume permissions → `docker volume rm` problematischer Volumes
- Out of disk space → `docker system prune -a`
- Database won't start → Check PostgreSQL logs
- Build failures → `--no-cache` für affected services

## Expected Output Format

```
🔄 ExamCraft AI Development Environment Restart

📊 Pre-Restart Analysis:
  • Running containers: 4/4
  • Port conflicts: None detected
  • Environment: .env ✅

🛑 Shutdown Phase:
  • Stopping frontend... ✅
  • Stopping backend... ✅
  • Stopping postgres... ✅
  • Stopping redis... ✅

🧹 Cleanup Phase:
  • Container cleanup... ✅
  • Network cleanup... ✅

🚀 Restart Phase:
  • Starting postgres... ✅ (Ready in 3s)
  • Starting redis... ✅ (Ready in 1s)
  • Starting backend... ✅ (Ready in 8s)
  • Starting frontend... ✅ (Ready in 12s)

✅ All services restarted successfully!

🌐 Services Ready:
  • Frontend: http://localhost:3000 ✅
  • Backend: http://localhost:8000 ✅
  • API Docs: http://localhost:8000/docs ✅

Total restart time: 24 seconds
```

## Interaktive Optionen

Frage bei kritischen Aktionen nach:

- "Clean restart mit Volume-Löschung? (y/n)"
- "Force rebuild aller Images? (y/n)"
- "System cleanup vor Restart? (y/n)"

Zeige immer Alternativen auf, falls der Restart fehlschlägt, und leite zu `/check-services` weiter für detaillierte Diagnose.
