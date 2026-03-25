# ExamCraft AI - Claude Code Dokumentation

## Projektübersicht

**ExamCraft AI** ist eine vollständig implementierte, OpenSource
KI-gestützte Plattform zur automatischen Generierung von Prüfungsaufgaben
für OpenBook-Prüfungen mit Claude API Integration und RAG-basierter
Dokumentenverarbeitung.

## Aktuelle Projektstruktur

```text
examcraft/
├── backend/               # FastAPI Backend
│   ├── main.py            # API Server
│   ├── database.py        # PostgreSQL Connection
│   ├── models/            # SQLAlchemy Models
│   ├── api/               # API Endpoints (auth, documents, v1/)
│   ├── services/          # Business Logic (auth, oauth, redis, audit)
│   ├── middleware/         # Rate Limiting
│   ├── celery_app.py      # Async Task Processing
│   ├── alembic/           # Database Migrations
│   ├── config/            # Configuration
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
├── utils/                 # Python Utilities
│   ├── extraction.py      # Document Processing (PyMuPDF)
│   └── rag.py             # RAG System (Qdrant)
├── docs-site/             # MkDocs Material Documentation
│   ├── mkdocs.yml         # MkDocs Configuration
│   └── docs/              # Documentation Content (DE/EN)
├── docker-compose.yml     # Docker Services
├── Makefile               # Development Commands
└── pyproject.toml         # Python Dependencies
```

## Linear Integration

- **Team**: Talent Factory
- **Project ID**: 6eebcff0-9f2f-4bff-a4ea-2a68bb367577
- **Status**: **PRODUCTION READY**

## Implementierte Technologien

- **FastAPI + React 18 + TypeScript Stack**
- **PostgreSQL + Redis Integration**
- **Docker + Docker Compose**
- **Claude API Integration** mit PydanticAI
- **RAG System** mit Qdrant Vector Storage
- **Document Processing** (PDF, DOC, Markdown) mit PyMuPDF
- **Semantic Search & Vector Storage** mit Qdrant
- **Prompt Knowledge Base** mit Versionierung & Seeding
- **Template-Variablen-System** mit Jinja2
- **Async Task Processing** mit Celery + RabbitMQ
- **Tailwind CSS v3 Integration** mit CRACO
- **JWT Authentication** mit bcrypt Password Hashing
- **OAuth Integration** (Google, Microsoft)
- **Role-Based Access Control (RBAC)**
- **Subscription Tiers** (Free, Starter, Professional, Enterprise)
- **Multi-Tenant Architecture**
- **Rate Limiting Middleware**
- **Audit Logging**
- **MkDocs Material** Dokumentation mit i18n (DE/EN)

## Entwicklungsumgebung

### Make-Befehle (empfohlen)

```bash
# Development
make dev             # Services starten
make stop            # Services stoppen
make stop-volumes    # Services stoppen + Volumes löschen
make seed            # Development-Daten laden

# Lint & Format
make lint            # Alle Linter ausführen
make lint-fix        # Auto-Fix für alle Fehler
make lint-backend    # Nur Backend
make lint-frontend   # Nur Frontend

# Tests
make test            # Alle Tests
make test-backend    # Backend Tests (pytest)
make test-frontend   # Frontend Tests (bun test)

# E2E Tests (Playwright)
make e2e             # Alle E2E Tests
make e2e-ui          # Mit interaktiver UI

# Quality
make ci-check        # Alle CI-Checks lokal
make pre-commit      # Pre-Commit Hooks
make install-hooks   # Hooks installieren

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

### Code-Standards

- **Python**: PEP 8, Type Hints, Docstrings
- **TypeScript**: Strikte Types, ESLint
- **Testing**: pytest (Backend), Jest/Playwright (Frontend)
- **CSS**: Tailwind CSS v3 Utility-First Approach
- **Linting**: ruff (Backend), ESLint (Frontend)

## Implementierte Architektur

### Core Module

1. **Backend API** (`backend/`)
   - FastAPI REST Server
   - Pydantic Models & Validation
   - Database ORM mit SQLAlchemy
   - Claude API Integration
   - Celery Async Tasks

2. **Document Processing** (`utils/extraction.py`)
   - PDF Text Extraction mit PyMuPDF
   - Markdown/DOC Processing
   - Structured Content Chunking

3. **RAG System** (`utils/rag.py`)
   - Qdrant Vector Storage
   - Semantic Search mit OpenAI Embeddings
   - Context Retrieval für Question Generation

4. **Frontend UI** (`frontend/`)
   - React 18 + TypeScript
   - TanStack Query für API State
   - Material-UI (MUI) + Tailwind CSS v3
   - Responsive Multi-Device Support

5. **Documentation** (`docs-site/`)
   - MkDocs Material mit i18n (DE/EN)
   - Deployment via GitHub Actions auf docs.examcraft.ch

## Technische Notizen

- **Environment**: Python 3.13+ Required
- **Dependencies**: Siehe pyproject.toml für vollständige Liste
- **Database**: PostgreSQL mit Alembic Migrations
- **AI Integration**: Claude API + PydanticAI Framework
- **API Documentation**: Auto-generated via FastAPI unter /docs
- **Package Manager**: Bun (Frontend), uv (Backend)
