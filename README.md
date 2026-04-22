# ExamCraft AI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

**KI-gestuetzte Plattform zur automatischen Generierung von Pruefungsaufgaben fuer OpenBook-Pruefungen mit Claude API Integration und RAG-basierter Dokumentenanalyse.**

> **Hinweis:** Dieses Repository ist der Open-Source-Core (MIT) von ExamCraft AI. Es wird automatisch aus dem privaten Monorepo gespiegelt. Premium- und Enterprise-Features sind proprietaer und in separaten Repositories verwaltet.

## Projektuebersicht

ExamCraft AI ist eine produktionsreife Webanwendung, die Dozierenden hilft, qualitativ hochwertige Pruefungsaufgaben automatisch aus Dokumenten zu generieren. Die Plattform kombiniert Claude API mit RAG-Technologie (Retrieval-Augmented Generation) fuer kontextuelle Fragenerstellung.

### Subscription Tiers

| Feature | Free (Core) | Starter | Professional | Enterprise |
|---------|-------------|---------|--------------|------------|
| **Dokumente** | 5 | 50 | Unbegrenzt | Unbegrenzt |
| **Fragen/Monat** | 20 | 200 | 1000 | Unbegrenzt |
| **Benutzer** | 1 | 3 | 10 | Unbegrenzt |
| **Dokumenten-Upload** | Ja | Ja | Ja | Ja |
| **Fragengenerierung** | Ja | Ja | Ja | Ja |
| **Question Review** | Ja | Ja | Ja | Ja |
| **RBAC** | Ja | Ja | Ja | Ja |
| **RAG-Generierung** | - | Ja | Ja | Ja |
| **Document ChatBot** | - | - | Ja | Ja |
| **Exam Composer** | - | - | Ja | Ja |
| **SSO/SAML** | - | - | - | Ja |
| **API Access** | - | - | - | Ja |

Alle Features werden ausschliesslich ueber RBAC gesteuert -- keine Environment-Feature-Flags.

## Core Features (Open Source)

- **Multi-Format Dokumentenverarbeitung**: PDF, Word, Markdown (PyMuPDF)
- **KI-Fragengenerierung** mit Claude API + PydanticAI
- **Parallele Fragengenerierung** mit Celery Tasks und Fortschrittsanzeige
- **Question Review Workflow** (Approve/Reject/Edit)
- **Exam Composer** mit Drag-and-Drop, Auto-Fill und Export (Markdown/JSON/Moodle XML)
- **Auto-Composition Engine** mit Constraint-basierter Pruefungszusammenstellung
- **KI-gefuehrter Prompt Wizard** fuer Template-Erstellung
- **Internationalisierung** (DE/EN/FR/IT)
- **User Management** mit Authentication, OAuth (Google/Microsoft), RBAC
- **Multi-Tenant Architecture** mit Institution Management
- **GDPR Compliance** (Data Export, Account Deletion)
- **Billing & Subscription Management** mit Stripe Integration

## Architektur

```text
core/
├── backend/                    # FastAPI Backend
│   ├── main.py                # API Server Entrypoint
│   ├── database.py            # PostgreSQL Connection (SQLAlchemy)
│   ├── celery_app.py          # Celery Worker Configuration
│   ├── api/                   # Route Handlers
│   │   ├── auth.py            # Authentication Endpoints
│   │   ├── documents.py       # Document Management
│   │   ├── exams.py           # Exam CRUD
│   │   ├── rag_exams.py       # RAG-based Question Generation
│   │   ├── question_review.py # Review Workflow
│   │   ├── admin.py           # Admin Endpoints
│   │   └── gdpr.py            # GDPR Compliance
│   ├── models/                # SQLAlchemy Models
│   │   ├── auth.py            # User, Role, Institution, Session
│   │   ├── document.py        # Document Models
│   │   ├── exam.py            # Exam Models
│   │   ├── subscription.py    # Subscription & Billing
│   │   └── rbac.py            # RBAC Models
│   ├── services/              # Business Logic
│   │   ├── claude_service.py  # Claude API Integration
│   │   ├── document_service.py# Document Processing
│   │   ├── rag_service.py     # RAG Pipeline
│   │   ├── auth_service.py    # JWT Authentication
│   │   ├── oauth_service.py   # Google/Microsoft OAuth
│   │   ├── payment_service.py # Stripe Integration
│   │   ├── exam_export_service.py # Export (MD/JSON/Moodle)
│   │   └── ...                # Redis, Audit, RBAC, etc.
│   ├── tasks/                 # Celery Async Tasks
│   │   ├── question_tasks.py  # Question Generation Tasks
│   │   ├── document_tasks.py  # Document Processing Tasks
│   │   └── rag_tasks.py       # RAG Processing Tasks
│   ├── middleware/            # Middleware
│   │   ├── rate_limit.py      # Rate Limiting
│   │   ├── rbac_middleware.py # RBAC Enforcement
│   │   ├── i18n_middleware.py # Internationalisierung
│   │   └── feature_gate.py    # Feature Gating
│   ├── schemas/               # Pydantic Schemas
│   ├── config/                # Feature & Subscription Config
│   ├── locales/               # i18n Translations (DE/EN/FR/IT)
│   ├── webhooks/              # Webhook Handlers (Resend)
│   ├── alembic/               # Database Migrations
│   └── tests/                 # pytest Tests
├── frontend/                  # React 18 + TypeScript
│   └── src/
│       ├── components/        # React Components
│       │   ├── auth/          # Login, Register, OAuth
│       │   ├── layout/        # Navigation, Sidebar, AppLayout
│       │   ├── guards/        # Route Protection
│       │   ├── admin/         # Admin UI
│       │   ├── composer/      # Exam Composer
│       │   ├── DocumentChat/  # Document ChatBot
│       │   └── ...            # Cards, Forms, Common
│       ├── pages/             # Page Components
│       │   ├── Dashboard.tsx
│       │   ├── Documents.tsx
│       │   ├── Exams.tsx
│       │   ├── ExamComposer.tsx
│       │   ├── BillingPage.tsx
│       │   └── ...
│       ├── contexts/          # React Context (Auth)
│       ├── services/          # API Client Services
│       ├── hooks/             # Custom React Hooks
│       ├── routes/            # Routing Configuration
│       ├── locales/           # Frontend i18n
│       ├── types/             # TypeScript Definitions
│       └── utils/             # Utility Functions
├── utils/                     # Shared Python Utilities
│   └── extraction.py          # Document Text Extraction
├── docs-site/                 # MkDocs Documentation Site
├── docker-compose.yml         # Core Services (PostgreSQL, Redis)
└── pyproject.toml             # Python Dependencies (uv)
```

## Technologie-Stack

### Backend

- **FastAPI** -- REST API mit automatischer OpenAPI-Dokumentation
- **SQLAlchemy** -- ORM mit Alembic Migrations
- **PostgreSQL 17** -- Relationale Datenbank
- **Redis 7** -- Caching, Session Management
- **Celery + RabbitMQ** -- Async Task Processing
- **PydanticAI** -- Claude API Integration
- **Stripe** -- Payment Processing
- **Sentry** -- Error Monitoring

### Frontend

- **React 18 + TypeScript** -- UI Framework
- **Tailwind CSS v3** -- Utility-First CSS (mit CRACO)
- **Material-UI (MUI)** -- Komponentenbibliothek
- **react-i18next** -- Internationalisierung
- **Bun** -- Package Manager

### Infrastructure

- **Docker & Docker Compose** -- Containerisierung
- **Fly.io** -- Production Deployment
- **Qdrant** -- Vector Database (Full Mode)
- **RabbitMQ** -- Message Broker (Full Mode)

## Quick Start

### Voraussetzungen

- **Docker & Docker Compose**
- **Git**
- **Python 3.13+** und **uv** (Backend)
- **Bun** (Frontend)
- **Claude API Key** (fuer KI-Fragenerstellung)

### Installation

```bash
# Repository klonen
git clone https://github.com/talent-factory/examcraft.git
cd examcraft

# Umgebung konfigurieren
cp .env.example .env
# .env anpassen (ANTHROPIC_API_KEY, Datenbank, etc.)

# Services starten
just dev                # Startet den Core-Stack

# Services stoppen
just stop
```

### Services & Ports

| Service    | Port  | Modus       |
|------------|-------|-------------|
| Frontend   | 3000  | Alle        |
| Backend    | 8000  | Alle        |
| API Docs   | 8000/docs | Alle    |
| PostgreSQL | 5432  | Alle        |
| Redis      | 6379  | Alle        |
| Qdrant     | 6333  | Full        |
| RabbitMQ   | 15672 | Full        |
| Flower     | 5555  | Full        |

### Development Login

`just dev` erstellt automatisch Test-Daten (beim ersten Start):

- **Admin**: `admin@talent-factory.ch` / `admin123`
- **Institution**: Talent Factory (Professional Tier)
- **Auto-Assignment**: Alle `@talent-factory.ch` E-Mails werden automatisch zugeordnet

Manuelles Seeding: `just seed`

## Entwicklung

### Befehle

```bash
# Tests
just test                    # Alle Tests
just test-backend            # uv run pytest backend/tests/ -v
just test-frontend           # cd frontend && bun test --watchAll=false

# Einzelne Tests
just test-file backend/tests/test_auth_service.py
just test-one backend/tests/test_auth_service.py::test_login

# Linting
just lint                    # Alle Linters
just lint-fix                # Auto-Fix
just lint-backend            # Ruff (check + format)
just lint-frontend           # ESLint

# Pre-Commit Hooks
just pre-commit              # Alle Hooks ausfuehren
just ci-check                # Vollstaendige CI-Checks lokal

# Alle verfügbaren Rezepte anzeigen
just
```

### Code-Standards

- **Python**: Ruff (Linting + Formatting), Type Hints, uv als Package Manager
- **TypeScript/JS**: ESLint + Prettier, Bun als Package Manager
- **CSS**: Tailwind CSS v3 Utility-First mit CRACO
- **Pre-commit Hooks**: Ruff, YAML/JSON/TOML Validation, detect-secrets
- **Sprache**: UI-Texte und Dokumentation auf Deutsch (Schweizer Orthographie), Code und API auf Englisch

### Git Workflow

- **Branch Naming**: `feature/tf-{linear-issue-number}-{description}`
- **Base Branch**: `develop`
- **Merge Strategy**: Squash Merge
- **Commit Style**: Conventional Commits mit optionalem Emoji-Prefix

### Two-Tier Deployment

- **Core** (`docker-compose.yml`): Community Edition, kein Qdrant, Free Tier
- **Full** (`docker-compose.full.yml`): Alle Services inkl. Qdrant, RabbitMQ, Celery, Flower

## API Endpoints

| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| `GET` | `/health` | Health Check |
| `POST` | `/api/v1/auth/login` | Benutzer-Login |
| `POST` | `/api/v1/auth/register` | Benutzer-Registrierung |
| `GET` | `/api/v1/documents` | Dokumente auflisten |
| `POST` | `/api/v1/documents/upload` | Dokument hochladen |
| `POST` | `/api/v1/exams/generate` | Pruefung generieren |
| `GET` | `/api/v1/exams/{exam_id}` | Pruefung abrufen |

Vollstaendige API-Dokumentation: http://localhost:8000/docs

## Contributing

Dieses Repository wird automatisch aus dem privaten Entwicklungs-Monorepo gespiegelt. Pull Requests koennen hier nicht direkt gemergt werden. Siehe [CONTRIBUTING.md](CONTRIBUTING.md) fuer Details.

## Lizenz

MIT License -- siehe [LICENSE](LICENSE).

---

**ExamCraft AI** -- entwickelt von [Talent Factory GmbH](https://talent-factory.ch)
