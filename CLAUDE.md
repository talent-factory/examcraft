# ExamCraft AI - Claude Code Dokumentation

## Projektübersicht

ExamCraft ist ein AI-gestütztes System zur Erstellung und Verwaltung von Prüfungen und Bewertungen.

## Aktuelle Projektstruktur

```text
ExamCraft/
├── pyproject.toml       # Python-Projekt-Konfiguration
├── README.md            # Projekt-Dokumentation
└── CLAUDE.md           # Diese Datei
```

## Linear Integration

- Team: Talent Factory
- Project ID: 6eebcff0-9f2f-4bff-a4ea-2a68bb367577 ✅ (Verifiziert)
- Projektbeschreibung: KI-gestützte Plattform zur automatischen Generierung von Prüfungsaufgaben für OpenBook-Prüfungen mit Claude API Integration

### Aktuelle Issues (Stand: 22.09.2025)

#### 🚀 Workshop Demo Preparation (Urgent)

- **ID**: 4b0b8b8a-8b8a-4b8a-8b8a-8b8a8b8a8b8a
- **Status**: Todo
- **Priorität**: Urgent (1)
- **Beschreibung**: Vorbereitung einer funktionsfähigen Demo für den anstehenden Workshop
- **Deadline**: Kritisch für Workshop-Termin

#### 📋 Project Setup & Architecture (In Progress)

- **ID**: 67100db1-6053-4178-a0ed-6c7c11513bfc
- **Status**: In Progress
- **Priorität**: High (1)
- **Beschreibung**: Grundlegende Projektinfrastruktur und Architektur etablieren
- **Aufgaben**:
  - [ ] Repository-Struktur definieren
  - [ ] Docker-Umgebung setup
  - [ ] CI/CD Pipeline konfigurieren
  - [ ] Development Environment Documentation
  - [ ] API Dokumentation Framework

### Technische Anforderungen aus Linear

- FastAPI + React Stack
- PostgreSQL + Redis
- Docker Containerization
- Claude API Integration vorbereitet

## Technologie-Stack

- **Programmiersprache**: Python 3.13.1+
- **Projektmanagement**: pyproject.toml (moderne Python-Konfiguration)
- **Entwicklungsumgebung**: Noch zu definieren
  - Backend: FastAPI + Python, PydanticAI
  - Frontend: React 18 + TypeScript
  - Database: PostgreSQL + Redis

## Entwicklungsworkflow

### Häufige Befehle

```bash
# Projekt ausführen
python main.py

# Tests ausführen (noch zu implementieren)
# pytest

# Code-Qualität prüfen (noch zu implementieren)
# ruff check
# ruff format
```

### Code-Stil

- Python PEP 8 Standards befolgen
- Type Hints verwenden wo möglich
- Docstrings für alle öffentlichen Funktionen
- Tests für neue Funktionalitäten schreiben

## Projektphasen

### Phase 1: Grundlagen (Aktuell)

- [ ] Projektstruktur definieren
- [ ] Abhängigkeiten festlegen
- [ ] Basis-Architektur entwerfen
- [ ] Entwicklungsumgebung einrichten

### Phase 2: Core-Features

- [ ] Prüfungserstellung
- [ ] Fragenverwaltung
- [ ] AI-Integration
- [ ] Bewertungssystem

### Phase 3: Erweiterte Features

- [ ] Benutzeroberfläche
- [ ] Berichterstellung
- [ ] Export-Funktionen
- [ ] Integration mit externen Systemen

## Architektur-Überlegungen

### Geplante Module

1. **Core**: Basis-Klassen und Utilities
2. **Questions**: Fragenverwaltung und -typen
3. **Exams**: Prüfungserstellung und -verwaltung
4. **AI**: KI-Integration für automatische Fragenerstellung
5. **Evaluation**: Bewertung und Scoring
6. **Export**: Ausgabe in verschiedene Formate
7. **API**: REST-API für externe Integration

### Design-Prinzipien

- Modularer Aufbau
- Lose Kopplung zwischen Komponenten
- Erweiterbarkeit für neue Fragetypen
- Skalierbare AI-Integration
- Benutzerfreundliche APIs

## Nächste Schritte

### Priorität 1: Workshop Demo Preparation (URGENT)

1. **Sofortige Maßnahmen für Workshop-Demo**
   - Minimale funktionsfähige Demo erstellen
   - Core-Features für Präsentation vorbereiten
   - Demo-Szenario definieren und testen

### Priorität 2: Project Setup & Architecture (In Progress)

1. **Repository-Struktur definieren** ✅ (Teilweise erledigt)
2. **Docker-Umgebung setup**
   - Docker-Compose für FastAPI + React + PostgreSQL + Redis
   - Development Environment konfigurieren
3. **CI/CD Pipeline konfigurieren**
4. **API Dokumentation Framework** (FastAPI automatische Docs)

### Priorität 3: Core Development

1. **Claude API Integration implementieren**
2. **Basis-Architektur für Prüfungserstellung**
3. **Frontend-Grundgerüst (React + TypeScript)**

## Notizen

- Projekt befindet sich in früher Entwicklungsphase
- Basis-Setup mit Python 3.13.1 vorhanden
- Linear Project ID verifiziert: `6eebcff0-9f2f-4bff-a4ea-2a68bb367577`
- **URGENT**: Workshop-Demo Vorbereitung hat höchste Priorität
- MCP Linear Server hat Verbindungsprobleme - direkte API-Calls funktionieren
- Aktuelle Linear Issues erfolgreich abgerufen und dokumentiert (Stand: 22.09.2025)
