# ExamCraft AI - Claude Code Dokumentation

## Projektübersicht

**ExamCraft AI** ist eine vollständig implementierte, OpenSource
KI-gestützte Plattform zur automatischen Generierung von Prüfungsaufgaben
für OpenBook-Prüfungen mit Claude API Integration und RAG-basierter
Dokumentenverarbeitung.

## Aktuelle Projektstruktur

```text
ExamCraft/
├── backend/              # FastAPI Backend
│   ├── main.py          # API Server
│   ├── database.py      # Database Connection
│   ├── models.py        # Pydantic Models
│   └── services/        # Business Logic
├── frontend/            # React 18 + TypeScript Frontend
│   ├── src/components/  # React Components
│   ├── src/services/    # API Services
│   └── public/          # Static Assets
├── utils/               # Python Utilities
│   ├── extraction.py    # Document Processing
│   └── rag.py          # RAG System
├── demo/                # Workshop Demo Materials
├── docs/                # Documentation
├── .claude/             # Claude Code Commands
├── docker-compose.yml   # Container Orchestration
└── pyproject.toml      # Python Dependencies
```

## Linear Integration

- **Team**: Talent Factory
- **Project ID**: 6eebcff0-9f2f-4bff-a4ea-2a68bb367577
- **Status**: **PRODUCTION READY**
- **Projektbeschreibung**: KI-gestützte Plattform zur automatischen
Generierung von Prüfungsaufgaben für OpenBook-Prüfungen mit Claude API
Integration

### Aktueller Projektstatus (Stand: 19.10.2025)

**CORE FEATURES ABGESCHLOSSEN:**

- **Project Setup & Architecture** (TF-50) - Vollständig implementiert
- **React Frontend Dashboard** (TF-54) - Production-ready
- **Document Processing Pipeline** (TF-51) - PDF/DOC/Markdown Support
- **Question Generation Core API** (TF-52) - Claude API + PydanticAI
- **Semantic Search & Vector Storage** (TF-55) - ChromaDB Integration
- **Claude API Integration** (TF-59) - Rate Limiting + Cost Tracking
- **Prompt Knowledge Base** (TF-122) - Centralized Prompt Management
- **Prompt Template Selector UI** (TF-146) - Frontend Komponente für Prompt-Auswahl
- **Template-Variablen-System** (TF-145) - Dynamische Prompt-Konfiguration mit Jinja2

**BACKLOG FEATURES:**

- RAG Service Integration (TF-147) - Prompt-Konfiguration in Question Generation
- Question Review Interface (TF-60)
- Exam Composition & Export (TF-56)
- Authentication & User Management (TF-57)
- Workshop Demo Materials (TF-58)

### Implementierte Technologien

**VOLLSTÄNDIG IMPLEMENTIERT:**

- FastAPI + React 18 + TypeScript Stack
- PostgreSQL + Redis Integration
- Docker + Docker Compose Environment
- Claude API Integration mit PydanticAI
- RAG System mit ChromaDB
- Document Processing (PDF, DOC, Markdown)
- Semantic Search & Vector Storage
- Prompt Knowledge Base mit Versionierung
- Template-Variablen-System mit Jinja2
- Live-Preview für Prompt-Rendering

## Entwicklungsumgebung

### Produktive Befehle

```bash
# Development Stack starten
./start-dev.sh

# Spezifische Services
docker-compose up -d backend frontend postgres redis

# Logs überwachen
docker-compose logs -f backend

# Tests ausführen
pytest backend/tests/

# Code-Qualität prüfen
ruff check backend/ utils/
ruff format backend/ utils/
```

### Code-Standards

- **Python**: PEP 8, Type Hints, Docstrings
- **TypeScript**: Strikte Types, ESLint + Prettier
- **Testing**: pytest (Backend), Jest (Frontend)
- **Documentation**: Automatisch via FastAPI + TypeDoc

## Implementierte Architektur

### Core Module (Implementiert)

1. **Backend API** (`backend/`)
   - FastAPI REST Server
   - Pydantic Models & Validation
   - Database ORM mit SQLAlchemy
   - Claude API Integration

2. **Document Processing** (`utils/extraction.py`)
   - PDF Text Extraction mit Docling
   - Markdown/DOC Processing
   - Structured Content Chunking

3. **RAG System** (`utils/rag.py`)
   - ChromaDB Vector Storage
   - Semantic Search mit sentence-transformers
   - Context Retrieval für Question Generation

4. **Frontend UI** (`frontend/`)
   - React 18 + TypeScript
   - TanStack Query für API State
   - Tailwind CSS + shadcn/ui Components
   - Responsive Multi-Device Support

### Design-Prinzipien (Umgesetzt)

- **Modularer Aufbau** - Getrennte Services
- **Lose Kopplung** - REST API + Docker Container
- **Erweiterbarkeit** - Plugin-artige Komponenten
- **Skalierbarkeit** - Container-basierte Architektur
- **Benutzerfreundlichkeit** - Intuitive Web-UI

## OpenSource Release Vorbereitung

### Erforderliche Schritte für Public Release

1. **Code Cleanup** - Production-ready Codebase
2. **Dokumentation** - README.md + API Docs
3. **License** - MIT License hinzufügen
4. **Contributing Guidelines** - CONTRIBUTING.md erstellen
5. **Security** - Secrets aus Repository entfernen
6. **CI/CD** - GitHub Actions für Testing

### Repository Vorbereitung

- **Branch Structure**: main (production) + develop (features)
- **Semantic Versioning**: v1.0.0 für Initial Release
- **Issue Templates**: Bug Reports + Feature Requests
- **Pull Request Template**: Code Review Guidelines

## Workshop Demo Materialien

### Fertiggestellte Demo-Komponenten

- **Live Question Generation**: PDF Upload → RAG → Claude Generation
- **Interactive UI**: Complete React Dashboard
- **Example Documents**: Academic PDFs für Demo
- **Generated Questions**: Heapsort & Priority Queues Beispiele

### Workshop-Bereitschaft

- **Technical Stack**: Vollständig funktional
- **Demo Scenario**: Definiert und getestet
- **Backup Materials**: Pre-generated Content verfügbar
- **Performance**: Optimiert für Live-Demo

## Technische Notizen

- **Environment**: Python 3.13+ Required
- **Dependencies**: Siehe pyproject.toml für vollständige Liste
- **Database**: PostgreSQL mit RAG Vector Search
- **AI Integration**: Claude API + PydanticAI Framework
- **Documentation**: Auto-generated via FastAPI unter /docs
