# ExamCraft AI - Workshop Demo Szenario 🎯

## Demo-Übersicht

Diese Demo zeigt die Kernfunktionalitäten von ExamCraft AI für die automatische Generierung von Prüfungsaufgaben.

## 🎬 Demo-Ablauf (15-20 Minuten)

### 1. Einführung (2 Minuten)

- **Problem**: Zeitaufwändige manuelle Erstellung von Prüfungsfragen
- **Lösung**: KI-gestützte automatische Generierung mit ExamCraft AI
- **Zielgruppe**: Dozierende, Trainer, Bildungseinrichtungen

### 2. Live-Demo der Anwendung (10 Minuten)

#### Schritt 1: Anwendung starten

```bash
./start-dev.sh
```

- Zeige Docker-Container Startup
- Öffne Frontend: <http://localhost:3000>
- Zeige API Dokumentation: <http://localhost:8000/docs>

#### Schritt 2: Prüfung erstellen

**Demo-Szenario**: "Python Programmierung für Anfänger"

1. **Thema eingeben**: "Python Grundlagen - Variablen und Datentypen"
2. **Einstellungen**:
   - Schwierigkeitsgrad: Mittel
   - Anzahl Fragen: 3
   - Sprache: Deutsch
3. **Prüfung generieren** (Button klicken)

#### Schritt 3: Generierte Prüfung zeigen

- **Multiple Choice Frage** mit 4 Antwortoptionen
- **Offene Frage** für detaillierte Antworten
- Moderne, benutzerfreundliche Oberfläche

#### Schritt 4: Prüfung durchführen

1. Fragen beantworten (als Teilnehmer)
2. **Auswertung** zeigen
3. **Feedback und Erklärungen** demonstrieren
4. **Ergebnis-Übersicht** mit Prozentangabe

### 3. Technische Highlights (5 Minuten)

#### Architektur zeigen

- **Frontend**: React + TypeScript + Material-UI
- **Backend**: FastAPI + Python
- **Datenbank**: PostgreSQL + Redis
- **KI-Integration**: Claude API (vorbereitet)
- **Deployment**: Docker Compose

#### Code-Beispiele

```python
# Backend API Endpoint
@app.post("/api/v1/generate-exam")
async def generate_exam(request: ExamRequest):
    # KI-Integration hier
    return ExamResponse(...)
```

```typescript
// Frontend Service
const response = await ExamService.generateExam(request);
```

### 4. Roadmap & Vision (3 Minuten)

#### Aktuelle Demo-Features ✅

- Vollständige UI für Prüfungserstellung
- Demo-Fragen Generation
- Interaktive Prüfungsansicht
- Sofortige Auswertung
- Docker-basierte Entwicklung

#### Geplante Features 🚀

- **Claude API Integration** für intelligente Fragenerstellung
- **Erweiterte Fragetypen** (True/False, Lückentext, etc.)
- **Export-Funktionen** (PDF, Word, Moodle)
- **Benutzerauthentifizierung** und Rollenverwaltung
- **Fragenkatalog-Verwaltung**
- **LMS-Integration** (Moodle, Canvas, etc.)

## 🎯 Demo-Szenarien

### Szenario A: "Python Programmierung"

- **Thema**: "Python Grundlagen - Variablen und Datentypen"
- **Schwierigkeit**: Mittel
- **Fragen**: 3-5
- **Zeigt**: Multiple Choice + Offene Fragen

### Szenario B: "Webentwicklung"

- **Thema**: "HTML und CSS Grundlagen"
- **Schwierigkeit**: Einfach
- **Fragen**: 4
- **Zeigt**: Verschiedene Schwierigkeitsgrade

### Szenario C: "Datenbanken"

- **Thema**: "SQL Abfragen und Joins"
- **Schwierigkeit**: Schwer
- **Fragen**: 5
- **Zeigt**: Komplexere Fragen für Fortgeschrittene

## 🛠️ Technische Demo-Vorbereitung

### Vor dem Workshop

1. **Repository klonen** und Setup testen
2. **Docker Services** einmal starten und testen
3. **Demo-Szenarien** durchspielen
4. **Backup-Plan**: Screenshots falls Live-Demo nicht funktioniert

### Während der Demo

1. **Terminal** für Docker-Befehle bereithalten
2. **Browser-Tabs** vorbereiten:
   - Frontend (<localhost:3000>)
   - API Docs (<localhost:8000/docs>)
   - GitHub Repository
3. **Code-Editor** mit wichtigen Dateien öffnen

### Troubleshooting

- **Docker nicht verfügbar**: Screenshots und Code-Walkthrough
- **Port-Konflikte**: Alternative Ports in docker-compose.yml
- **Langsame Verbindung**: Lokale Demo ohne API-Calls

## 📊 Erwartete Audience-Reaktionen

### Positive Punkte

- **Moderne UI/UX** mit Material Design
- **Schnelle Prüfungserstellung** (Demo zeigt sofortige Ergebnisse)
- **Vollständiger Tech-Stack** mit Docker
- **Professionelle Architektur**

### Mögliche Fragen

1. **"Wie intelligent sind die generierten Fragen?"**
   - Antwort: Demo zeigt Basis-Version, Claude API wird echte KI-Power bringen

2. **"Kann man eigene Fragenkataloge importieren?"**
   - Antwort: Geplant für Phase 2, aktuell Demo-Fokus

3. **"Integration mit bestehenden LMS-Systemen?"**
   - Antwort: Roadmap-Feature, API-first Design ermöglicht einfache Integration

4. **"Kosten für Claude API?"**
   - Antwort: Kosteneffizient, da nur bei Fragenerstellung verwendet

## 🎤 Demo-Script

### Eröffnung

> "Stellen Sie sich vor, Sie müssen für 50 Studierende eine Prüfung erstellen. Normalerweise dauert das Stunden. Mit ExamCraft AI dauert es Minuten."

### Durchführung der Demo

> "Hier sehen Sie, wie einfach es ist: Thema eingeben, Einstellungen wählen, und die KI generiert sofort passende Fragen."

### Technischer Teil

> "Die Architektur ist modern und skalierbar. FastAPI für die Performance, React für die Benutzerfreundlichkeit, und Docker für einfaches Deployment."

### Abschluss

> "Das ist erst der Anfang. Mit Claude API wird ExamCraft AI wirklich intelligent und kann kontextbezogene, durchdachte Fragen erstellen."

## 📋 Checkliste für Demo

- [ ] Docker läuft und Services sind erreichbar
- [ ] Frontend lädt korrekt (localhost:3000)
- [ ] Backend API antwortet (localhost:8000/health)
- [ ] Demo-Szenarien getestet
- [ ] Backup-Screenshots bereit
- [ ] Präsentation-Slides vorbereitet
- [ ] Fragen & Antworten vorbereitet
- [ ] Repository-Link zum Teilen bereit

---

**Ziel**: Zeigen, dass ExamCraft AI bereits jetzt eine funktionsfähige, professionelle Lösung ist, die mit KI-Integration revolutionär werden wird! 🚀
