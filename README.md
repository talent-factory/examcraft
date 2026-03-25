# ExamCraft AI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

**KI-gestützte Plattform zur automatischen Generierung von Prüfungsaufgaben für OpenBook-Prüfungen mit Claude API Integration und RAG-basierter Dokumentenanalyse.**

## Projektübersicht

ExamCraft AI ist eine produktionsreife Webanwendung, die Dozierenden dabei hilft, qualitativ hochwertige Prüfungsaufgaben automatisch aus beliebigen Dokumenten zu generieren. Die Plattform kombiniert moderne KI (Claude API) mit RAG-Technologie (Retrieval-Augmented Generation) für kontextuelle, durchdachte Fragenerstellung.

### Projektstruktur

```text
examcraft/
├── backend/               # FastAPI Backend
│   ├── main.py            # API Server
│   ├── database.py        # PostgreSQL Connection
│   ├── models/            # SQLAlchemy Models
│   ├── api/               # API Endpoints
│   ├── services/          # Business Logic
│   ├── middleware/         # Rate Limiting etc.
│   ├── celery_app.py      # Async Task Processing
│   ├── alembic/           # Database Migrations
│   └── tests/             # pytest Tests
├── frontend/              # React 18 + TypeScript Frontend
│   ├── src/
│   │   ├── components/    # React Components
│   │   ├── pages/         # Page Views
│   │   ├── contexts/      # React Context (Auth)
│   │   ├── api/           # API Client
│   │   ├── hooks/         # Custom Hooks
│   │   └── locales/       # i18n Translations
│   └── package.json       # NPM Dependencies
├── utils/                 # Python Utilities (RAG, Extraction)
├── docs-site/             # MkDocs Material Documentation
├── docker-compose.yml     # Docker Services
├── Makefile               # Development Commands
└── pyproject.toml         # Python Dependencies
```

## Dokumentation

- **[User Guide](https://docs.examcraft.ch/user-guide/documents/)** - Anleitung für Dozierende
- **[Admin Guide](https://docs.examcraft.ch/admin-guide/prompts/)** - Prompt-Management und Administration
- **[Quick Start](https://docs.examcraft.ch/getting-started/quickstart/)** - In 5 Minuten starten
- **[API Documentation](http://localhost:8000/docs)** - Interaktive API-Docs (lokal)

## Features

- **Multi-Format Dokumentenverarbeitung**: PDF, Word, Markdown (PyMuPDF)
- **KI-gestützte Fragengenerierung** mit Claude API + PydanticAI
- **RAG System** mit Qdrant Vector Storage und Semantic Search
- **Question Review Workflow** - Approve/Reject/Edit
- **Exam Composer** mit Drag-and-Drop und PDF-Export
- **Prompt Knowledge Base** mit Versionierung und Template-Variablen
- **User Management** - JWT Authentication, OAuth (Google, Microsoft)
- **RBAC & Subscription Tiers** (Free, Starter, Professional, Enterprise)
- **Multi-Tenant Architecture** mit Institution Management
- **Async Document Processing** mit Celery + RabbitMQ
- **Moderne Web-UI** mit React 18 + TypeScript + Tailwind CSS

## Quick Start

### Voraussetzungen

- **Docker & Docker Compose**
- **Git**
- **Python 3.13+** (für lokale Entwicklung ohne Docker)

### Installation

```bash
# Repository klonen
git clone https://github.com/talent-factory/examcraft.git
cd examcraft

# Umgebung konfigurieren
cp .env.example .env
# .env bearbeiten (ANTHROPIC_API_KEY setzen)

# Services starten
make dev

# Development-Daten laden
make seed
```

**Access Points:**

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Development Login

Nach `make seed` steht ein Admin-User zur Verfügung:

- Email: `admin@talent-factory.ch`
- Password: `admin123` (nur Development!)  <!-- pragma: allowlist secret -->

## Entwicklung

### Make-Befehle

```bash
# Development
make dev             # Services starten
make stop            # Services stoppen
make stop-volumes    # Services stoppen + Volumes löschen
make seed            # Development-Daten laden

# Lint & Format
make lint            # Alle Linter ausführen
make lint-fix        # Auto-Fix für alle Fehler

# Tests
make test            # Alle Tests ausführen
make test-backend    # Backend Tests (pytest)
make test-frontend   # Frontend Tests (bun test)

# E2E Tests (Playwright)
make e2e             # Alle E2E Tests
make e2e-ui          # Mit interaktiver UI

# Quality
make ci-check        # Alle CI-Checks lokal ausführen
make pre-commit      # Pre-Commit Hooks ausführen
make install-hooks   # Pre-Commit + Pre-Push Hooks installieren

# Setup
make setup           # Install + Hooks
```

### Manuelle Befehle

```bash
# Backend Lint
cd backend && ruff check . --fix && ruff format .

# Frontend Lint
cd frontend && bun run lint:fix

# Backend Tests
uv run pytest backend/tests/ -v

# Frontend Tests
cd frontend && bun test -- --watchAll=false

# Docker Logs
docker compose logs -f backend
```

### Troubleshooting

**Frontend Build Errors nach Git Pull:**

```bash
cd frontend
rm -rf node_modules/.cache build/
bun install
```

**Docker Container Probleme:**

```bash
docker compose down
docker compose up -d --build
```

## Technologie-Stack

### Backend

- **FastAPI** - Moderne Python Web API
- **SQLAlchemy** - ORM für Datenbankzugriff
- **PostgreSQL** - Relationale Datenbank
- **Redis** - Caching, Session Management und Avatar Proxy
- **Pydantic / PydanticAI** - Datenvalidierung und KI-Integration
- **Celery + RabbitMQ** - Asynchrone Task-Verarbeitung
- **Qdrant** - Vector Database für RAG / Semantic Search
- **PyMuPDF** - Schnelle PDF-Verarbeitung

### Frontend

- **React 18** - UI Framework
- **TypeScript** - Type-sichere Entwicklung
- **Material-UI (MUI)** - Komponenten-Bibliothek
- **Tailwind CSS v3** - Utility-First CSS mit CRACO
- **TanStack Query** - Server State Management

### DevOps

- **Docker & Docker Compose** - Containerisierung
- **uvicorn** - ASGI Server
- **GitHub Actions** - CI/CD und Docs Deployment
- **MkDocs Material** - Dokumentation mit i18n (DE/EN)

## Contributing

Siehe [CONTRIBUTING.md](CONTRIBUTING.md) für Details.

1. Fork das Repository
2. Feature Branch erstellen (`git checkout -b feature/amazing-feature`)
3. Änderungen committen (`git commit -m 'feat: Add amazing feature'`)
4. Branch pushen (`git push origin feature/amazing-feature`)
5. Pull Request erstellen

## Lizenz

Dieses Projekt ist unter der MIT Lizenz lizenziert - siehe [LICENSE](LICENSE) Datei für Details.

## Support

- **Issues**: [GitHub Issues](https://github.com/talent-factory/examcraft/issues) für Bug Reports und Feature Requests
- **Dokumentation**: [docs.examcraft.ch](https://docs.examcraft.ch)
- **API Docs**: http://localhost:8000/docs (während Entwicklung)
