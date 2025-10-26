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
│   ├── models/          # SQLAlchemy Models
│   │   ├── auth.py      # User, Role, Institution, Session, AuditLog
│   │   ├── document.py  # Document Models
│   │   └── question_review.py  # Question Review Models
│   ├── api/             # API Endpoints
│   │   ├── auth.py      # Authentication Endpoints
│   │   ├── documents.py # Document Management
│   │   └── v1/          # Versioned API
│   ├── services/        # Business Logic
│   │   ├── auth_service.py    # JWT Authentication
│   │   ├── oauth_service.py   # Google/Microsoft OAuth
│   │   ├── redis_service.py   # Session Management
│   │   └── audit_service.py   # Security Logging
│   ├── middleware/      # Middleware
│   │   └── rate_limit.py      # Rate Limiting
│   ├── utils/           # Utilities
│   │   ├── auth_utils.py      # Auth Helpers
│   │   ├── tenant_utils.py    # Multi-Tenant Helpers
│   │   └── seed_roles.py      # Role Seeding
│   └── tests/           # pytest Tests
├── frontend/            # React 18 + TypeScript Frontend
│   ├── src/
│   │   ├── components/  # React Components
│   │   │   ├── auth/    # Login, Register, OAuth
│   │   │   ├── guards/  # Route Protection
│   │   │   ├── profile/ # User Profile
│   │   │   └── layout/  # Navigation
│   │   ├── contexts/    # React Context (Auth)
│   │   ├── services/    # API Services
│   │   ├── types/       # TypeScript Types
│   │   └── index.css    # Tailwind CSS Entry Point
│   ├── public/          # Static Assets
│   ├── tailwind.config.js  # Tailwind Configuration
│   ├── postcss.config.js   # PostCSS Configuration
│   ├── craco.config.js     # CRA Override Configuration
│   └── package.json        # NPM Dependencies
├── utils/               # Python Utilities
│   ├── extraction.py    # Document Processing
│   └── rag.py          # RAG System
├── demo/                # Workshop Demo Materials
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

### Aktueller Projektstatus (Stand: 22.10.2025)

**CORE FEATURES ABGESCHLOSSEN:**

- **Project Setup & Architecture** (TF-50) - Vollständig implementiert
- **Monorepo Structure** (TF-151) - Core/Premium/Enterprise Packages
- **React Frontend Dashboard** (TF-54) - Production-ready
- **Document Processing Pipeline** (TF-51) - PDF/DOC/Markdown Support
- **Question Generation Core API** (TF-52) - Claude API + PydanticAI
- **Semantic Search & Vector Storage** (TF-55) - Qdrant Integration (migrated from ChromaDB)
- **Claude API Integration** (TF-59) - Rate Limiting + Cost Tracking
- **Prompt Knowledge Base** (TF-122) - Centralized Prompt Management + Seeding
- **Prompt Template Selector UI** (TF-146) - Frontend Komponente für Prompt-Auswahl
- **Template-Variablen-System** (TF-145) - Dynamische Prompt-Konfiguration mit Jinja2
- **RAG Service Integration** (TF-147) - Prompt-Konfiguration in Question Generation
- **Question Review Interface** (TF-60) - MVP mit Review Workflow
- **Workshop Demo Materials** (TF-58) - Vollständig abgeschlossen
- **Authentication & User Management** (TF-57) - Backend + Frontend + Tests (100%)
- **RBAC & Subscription Tiers** - Unlimited Quotas (-1) Support
- **Avatar Proxy** - Redis Caching für Google OAuth Avatars
- **Institution Management** - Admin UI für Institution Creation

**RECENT BUG FIXES (22.10.2025):**

- ✅ Unlimited Quotas (-1) korrekt behandelt (Professional/Enterprise Tier)
- ✅ PackageTierBadge zeigt korrektes Tier (localStorage Key Fix)
- ✅ Avatar URLs 429 Rate Limiting behoben (Redis Proxy)
- ✅ Premium Models in Database Schema integriert
- ✅ Seed Prompts implementiert (5 Default Prompts)
- ✅ Premium Component Override via Docker Volumes

**TEST COVERAGE (NEW):**

- ✅ 52 neue Tests für alle Bug Fixes
- ✅ Backend: test_subscription_limits.py (12 Tests)
- ✅ Backend: test_avatar_proxy.py (10 Tests)
- ✅ Backend: test_seed_prompts.py (15 Tests)
- ✅ Frontend: PackageTierBadge.test.tsx (15 Tests)

**BACKLOG FEATURES:**

- Exam Composition & Export (TF-56)
- Open Source Vorbereitung (TF-112)
- Mintlify Dokumentation (TF-87)

### Implementierte Technologien

**VOLLSTÄNDIG IMPLEMENTIERT:**

- **Monorepo Architecture** - Core/Premium/Enterprise Packages mit Git Submodules
- **FastAPI + React 18 + TypeScript Stack**
- **PostgreSQL + Redis Integration**
- **Docker + Docker Compose Environment** - Multi-File Compose mit Overrides
- **Claude API Integration** mit PydanticAI
- **RAG System** mit Qdrant (migrated from ChromaDB)
- **Document Processing** (PDF, DOC, Markdown)
- **Semantic Search & Vector Storage** mit Qdrant
- **Prompt Knowledge Base** mit Versionierung & Seeding
- **Template-Variablen-System** mit Jinja2
- **Live-Preview** für Prompt-Rendering
- **RAG Service Prompt-Integration** mit Auto-Variable-Merging
- **Tailwind CSS v3 Integration** mit CRACO
- **Modern Authentication UI** (LoginForm, AuthPage)
- **JWT Authentication** mit bcrypt Password Hashing
- **OAuth Integration** (Google, Microsoft)
- **Avatar Proxy** mit Redis Caching (24h TTL)
- **Role-Based Access Control (RBAC)**
- **Subscription Tiers** (Free, Starter, Professional, Enterprise)
- **Quota Enforcement** mit Unlimited Support (-1)
- **Multi-Tenant Architecture**
- **Session Management** mit Redis
- **Rate Limiting Middleware**
- **Audit Logging** für Security Events
- **Admin User Management UI** (User List, Edit, Role Assignment)
- **Institution Management UI** (Create, Edit, Delete)
- **PackageTierBadge** mit dynamischer Tier-Erkennung
- **Premium Component Override** via Docker Volume Mounts

## Entwicklungsumgebung

### Produktive Befehle

```bash
# Development Stack starten (automatische Tier-Erkennung)
./start-dev.sh

# Environment-Variablen validieren
bash scripts/validate-env.sh

# Spezifische Services (Core + Premium)
docker compose --env-file .env -f docker-compose.yml -f docker-compose.premium.yml up -d

# Logs überwachen
docker compose --env-file .env -f docker-compose.yml -f docker-compose.premium.yml logs -f backend

# Services stoppen
docker compose --env-file .env -f docker-compose.yml -f docker-compose.premium.yml down

# Tests ausführen (Backend)
cd packages/core/backend
pytest tests/

# Tests ausführen (Frontend)
cd packages/core/frontend
npm test

# Code-Qualität prüfen
ruff check packages/core/backend/ utils/
ruff format packages/core/backend/ utils/
```

### ⚠️ WICHTIG: Docker Compose Environment Variables

**IMMER `--env-file .env` verwenden!**

Docker Compose lädt die `.env` Datei NICHT automatisch für alle Variablen.
Um sicherzustellen, dass alle Umgebungsvariablen (insbesondere `CLAUDE_API_KEY`,
`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) korrekt geladen werden, muss bei jedem
`docker compose` Befehl `--env-file .env` angegeben werden.

**Beispiele:**
```bash
# ✅ RICHTIG:
docker compose --env-file .env -f docker-compose.yml -f docker-compose.premium.yml up -d

# ❌ FALSCH (Variablen werden nicht geladen):
docker compose -f docker-compose.yml -f docker-compose.premium.yml up -d
```

**Das `start-dev.sh` Skript verwendet automatisch `--env-file .env`.**

### Code-Standards

- **Python**: PEP 8, Type Hints, Docstrings
- **TypeScript**: Strikte Types, ESLint + Prettier
- **Testing**: pytest (Backend), Jest (Frontend)
- **Documentation**: Automatisch via FastAPI + TypeDoc
- **CSS**: Tailwind CSS v3 Utility-First Approach

### Frontend Konfiguration

**Tailwind CSS Integration:**

- `frontend/tailwind.config.js` - Content Scanning & Theme Config
- `frontend/postcss.config.js` - PostCSS Plugins (Tailwind + Autoprefixer)
- `frontend/craco.config.js` - CRA Webpack Override für PostCSS
- `frontend/src/index.css` - Tailwind Directives (@tailwind base/components/utilities)

**Build-System:**

- Create React App (CRA) mit CRACO Override
- Tailwind CSS v3.3.0 (kompatibel mit CRA)
- PostCSS für CSS-Processing
- Autoprefixer für Browser-Kompatibilität

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
   - Material-UI (MUI) + Tailwind CSS v3
   - Tailwind CSS Integration mit CRACO
   - Responsive Multi-Device Support
   - Modern Authentication UI

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
