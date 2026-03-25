# ExamCraft AI 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Core Package](https://img.shields.io/badge/Core-Open%20Source-green.svg)]()
[![Premium Package](https://img.shields.io/badge/Premium-Closed%20Source-orange.svg)]()
[![Enterprise Package](https://img.shields.io/badge/Enterprise-Closed%20Source-red.svg)]()
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

**KI-gestützte Plattform zur automatischen Generierung von Prüfungsaufgaben für OpenBook-Prüfungen mit Claude API Integration und RAG-basierter Dokumentenanalyse.**

> **Monorepo-Architektur:** ExamCraft AI verwendet eine Monorepo-Struktur mit Git Submodules für Premium und Enterprise Features. Das Core Package ist Open Source (MIT), während Premium und Enterprise Features proprietär sind.

## 🎯 Projektübersicht

ExamCraft AI ist eine vollständig implementierte, **produktionsreife** Webanwendung, die Dozierenden dabei hilft, qualitativ hochwertige Prüfungsaufgaben automatisch aus beliebigen Dokumenten zu generieren. Die Plattform kombiniert moderne KI (Claude API) mit RAG-Technologie (Retrieval-Augmented Generation) für kontextuelle, durchdachte Fragenerstellung.

### 📦 Package-Struktur

```text
examcraft/
├── packages/
│   ├── core/          # ✅ Open Source (MIT) - Free Tier
│   ├── premium/       # 🔒 Closed Source - Starter/Professional Tier
│   └── enterprise/    # 🔒 Closed Source - Enterprise Tier
├── docker-compose.yml              # Core Services (OpenSource)
├── docker-compose.full.yml         # Full Services (Premium + Enterprise)
└── MONOREPO_SETUP.md               # Detailed Setup Guide
```

**Siehe [MONOREPO_SETUP.md](MONOREPO_SETUP.md) für detaillierte Informationen zur Monorepo-Struktur.**

## 📚 Dokumentation

### 📖 User Documentation

- **[📚 User Guide](https://docs.examcraft.ch/user-guide/documents/)** - Comprehensive guide for educators
- **[🎛️ Admin Guide](https://docs.examcraft.ch/admin-guide/prompts/)** - Prompt management and administration
- **[🚀 Quick Start](https://docs.examcraft.ch/getting-started/quickstart/)** - Get started in 5 minutes

### 🔧 Developer Documentation

- **[🚀 Deployment Guide](DEPLOYMENT.md)** - Production deployment on Fly.io
- **[📖 API Documentation](http://localhost:8000/docs)** - Interactive API docs (local)
- **[🔧 Development Setup](#-quick-start)** - Local development environment (see below)
- **[⚙️ Async Document Processing](docs/ASYNC_DOCUMENT_PROCESSING.md)** - RabbitMQ & Celery setup

### 🗺️ Public Roadmap

**Current Status:** Production-ready v1.0 with core features available

#### ✅ Released (v1.0)
- 📄 Multi-format document processing (PDF, Word, Markdown)
- 🤖 AI-powered question generation with Claude API
- 🔍 RAG-based semantic search (Premium)
- 💬 Interactive document chatbot (Premium)
- 👥 User management with RBAC
- 📝 Question review workflow

#### 🚧 In Progress (Q1 2026)
- 📊 Advanced analytics dashboard
- 🔄 Exam composition & export
- 🌐 Multi-language support
- 📱 Mobile-responsive UI improvements

#### 🔮 Planned (Q2-Q3 2026)
- 🔗 LMS integrations (Moodle, Canvas)
- 🎨 Custom branding (Enterprise)
- 🔐 SSO/SAML integration (Enterprise)
- 📈 Performance optimizations

**Want to influence our roadmap?** [Open a feature request](https://github.com/talent-factory/examcraft/issues/new?template=feature_request.md)

### 💎 Subscription Tiers

| Feature | Free (Core) | Starter (€19/mo) | Professional (€49/mo) | Enterprise (€149/mo) |
|---------|-------------|------------------|----------------------|---------------------|
| **Documents** | 5 | 50 | Unlimited | Unlimited |
| **Questions/Month** | 20 | 200 | 1000 | Unlimited |
| **Users** | 1 | 3 | 10 | Unlimited |
| **Document Upload** | ✅ | ✅ | ✅ | ✅ |
| **Basic Question Generation** | ✅ | ✅ | ✅ | ✅ |
| **Question Review** | ✅ | ✅ | ✅ | ✅ |
| **RBAC System** | ✅ | ✅ | ✅ | ✅ |
| **RAG Generation** | ❌ | ✅ | ✅ | ✅ |
| **Document ChatBot** | ❌ | ❌ | ✅ | ✅ |
| **Advanced Prompt Management** | ❌ | ❌ | ✅ | ✅ |
| **Analytics Dashboard** | ❌ | ❌ | ✅ | ✅ |
| **SSO/SAML** | ❌ | ❌ | ❌ | ✅ |
| **Custom Branding** | ❌ | ❌ | ❌ | ✅ |
| **API Access** | ❌ | ❌ | ❌ | ✅ |
| **Priority Support** | ❌ | ❌ | ❌ | ✅ |

### ✨ Core Features (Open Source)

- **📄 Multi-Format Dokumentenverarbeitung**: PDF, Word, Markdown
- **🔬 PyMuPDF Integration** - Fast Document Processing (10x schneller als Docling)
- **🤖 Basic Question Generation** mit Claude API + PydanticAI
- **📝 Question Review Workflow** - Approve/Reject/Edit
- **👥 User Management** - Authentication, Authorization, RBAC
- **🔒 GDPR Compliance** - Data Export, Account Deletion
- **⚛️ Moderne Web-UI** mit React 18 + TypeScript + Tailwind CSS
- **🐳 Container-basiert** für einfache Entwicklung und Deployment

### 🌟 Premium Features (Closed Source)

- **🤖 RAG-basierte KI-Fragenerstellung** mit Vector Database (ChromaDB/Qdrant)
- **💬 Interaktiver Document ChatBot** - NotebookLM-Style Konversationen
- **🎛️ Advanced Prompt Management** - Versionierung, Template Variables, Semantic Search
- **🔍 Semantische Suche** über Dokumente und Prompts
- **📊 Analytics Dashboard** - Usage Metrics, Performance Tracking

### 🏢 Enterprise Features (Closed Source)

- **🔐 SSO/SAML Integration** - Single Sign-On mit SAML 2.0
- **🎨 Custom Branding** - White-Label Lösung
- **🔑 API Access Management** - REST API für Integrationen
- **📈 Advanced Analytics** - BI Export, Custom Reports, Audit Logs
- **☁️ On-Premise Deployment** - Self-Hosted Option
- **🆘 Priority Support** - 24/7 Support, Dedicated Account Manager
- **🚀 Production-Ready** mit Rate Limiting, Error Handling & Monitoring

## 🏗️ Architektur

```text
ExamCraft/
├── packages/
│   ├── core/                       # ✅ Open Source (MIT License)
│   │   ├── backend/                # FastAPI Backend Server
│   │   │   ├── main.py             # REST API Endpoints
│   │   │   ├── database.py         # PostgreSQL Connection
│   │   │   ├── models/             # SQLAlchemy Models
│   │   │   ├── services/           # Business Logic Services
│   │   │   └── api/                # API Endpoints
│   │   └── frontend/               # React 18 + TypeScript Frontend
│   │       ├── src/components/     # React UI Components
│   │       ├── src/services/       # API Client Services
│   │       └── src/types/          # TypeScript Definitions
│   ├── premium/                    # 🔒 Private Submodule (Proprietary)
│   │   ├── backend/                # Premium Backend Features
│   │   │   ├── api/v1/             # RAG, Chat, Prompts APIs
│   │   │   ├── services/           # RAG, ChatBot, Vector Services
│   │   │   └── models/             # Chat, Prompt Models
│   │   └── frontend/               # Premium Frontend Components
│   │       └── src/components/     # ChatBot, PromptEditor, RAG UI
│   └── enterprise/                 # 🔒 Private Submodule (Proprietary)
│       ├── backend/                # Enterprise Backend Features
│       │   ├── api/v1/             # SSO, Branding, API Access, Analytics
│       │   └── services/           # SSO, OAuth, Branding Services
│       └── frontend/               # Enterprise Frontend Components
│           └── src/components/     # SSO Config, Branding, API Management
├── docker-compose.yml              # Core Services (PostgreSQL, Redis, RabbitMQ)
├── docker-compose.full.yml         # Full Services (Core + Premium + Enterprise + Qdrant)
├── start-dev.sh                    # 🚀 Smart Start Script (Auto-detects --core/--full)
├── stop-dev.sh                     # 🛑 Stop All Services
├── MONOREPO_SETUP.md               # Detailed Monorepo Setup Guide
└── .gitmodules                     # Git Submodules Configuration
```

## 🚀 Quick Start

### Voraussetzungen

- **Docker & Docker Compose** (für Container-basierte Entwicklung)
- **Git** (für Repository-Management)
- **Claude API Key** (für KI-Fragenerstellung, optional für Core)
- **Python 3.13+** (für lokale Entwicklung ohne Docker)

### 🐳 Installation

Das neue `start-dev.sh` Script erkennt automatisch, welche Packages verfügbar sind und startet die entsprechenden Services:

```bash
# Repository klonen
git clone https://github.com/talent-factory/examcraft.git
cd examcraft

# Umgebung konfigurieren
cp .env.example .env
# Edit .env with your configuration (ANTHROPIC_API_KEY für Premium/Enterprise)

# Services starten (erkennt automatisch Core/Premium/Enterprise)
./start-dev.sh

# Services stoppen
./stop-dev.sh
```

**Das Script erkennt automatisch:**

- ✅ **Core Only**: Wenn nur `packages/core` vorhanden ist
- ✅ **Premium**: Wenn `packages/premium` Submodule initialisiert ist
- ✅ **Enterprise**: Wenn `packages/enterprise` Submodule initialisiert ist

**Access Points:**

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Redis: localhost:6380 (external) / 6379 (internal)
- Qdrant: http://localhost:6333 (Premium/Enterprise)

#### Premium/Enterprise Features aktivieren

```bash
# Premium Submodule initialisieren (requires access)
git submodule update --init --recursive packages/premium

# Enterprise Submodule initialisieren (requires access, optional)
git submodule update --init --recursive packages/enterprise

# Services starten (erkennt automatisch verfügbare Packages)
./start-dev.sh
```

**Hinweis:** Features werden über User-Rollen und Institution-Settings gesteuert, nicht über die Package-Auswahl. Die Packages stellen nur die Code-Basis bereit.

### 🌱 Development Login

Das `start-dev.sh` Script erstellt automatisch Test-Daten für die Entwicklung:

**Talent Factory Institution (Professional Tier):**

- Domain: `talent-factory.ch` (Auto-Assignment für alle `@talent-factory.ch` E-Mails)
- Subscription: Professional (Unlimited Documents, 1000 Questions/Month)

**Admin User:**

- Email: `admin@talent-factory.ch`
- Password: `admin123` (nur Development!)  # pragma: allowlist secret
- Rollen: Admin, Dozent, Assistant
- Superuser: Ja

**Auto-Assignment:**

- Jeder User mit `@talent-factory.ch` E-Mail wird automatisch der Talent Factory Institution zugeordnet
- Funktioniert für OAuth (Google, Microsoft) und normale Registrierung

**Manuelles Seeding:**

```bash
# Falls automatisches Seeding fehlschlägt
./seed-dev-data.sh
```

### 📚 Weitere Informationen

Siehe [MONOREPO_SETUP.md](MONOREPO_SETUP.md) für:

- Detaillierte Setup-Anleitung
- Submodule-Verwaltung
- Docker Compose Befehle
- Troubleshooting

## 🛠️ Entwicklung

### Services

- **Frontend (React)**: Port 3000
- **Backend (FastAPI)**: Port 8000
- **PostgreSQL**: Port 5432
- **Redis**: Port 6379

### Code-Qualität & Lint-Checks

**Automatische Checks vor jedem Commit:**

```bash
# Pre-Commit-Hooks installieren (einmalig)
make install-hooks

# Jetzt laufen Checks automatisch bei jedem Commit
git commit -m "feat: Add feature"
```

**Manuelle Lint-Checks:**

```bash
# Alle Lint-Checks ausführen
make lint

# Auto-Fix für alle Fehler
make lint-fix

# Nur Backend
make lint-backend
make lint-fix-backend

# Nur Frontend
make lint-frontend
make lint-fix-frontend

# Pre-Commit-Hooks manuell ausführen
make pre-commit
```

**Vor jedem Pull Request:**

```bash
# Umfassende Lint-Checks
make pre-push

# Oder manuell:
cd packages/core/backend && ruff check . --fix && ruff format .
cd packages/core/frontend && bun run lint:fix
```

**Siehe [Lint Checks](docs/LINT_CHECKS.md) für detaillierte Informationen.**

### Nützliche Befehle

```bash
# Alle Services starten
docker-compose up -d

# Logs anzeigen
docker-compose logs -f

# Services neustarten
docker-compose restart

# Services stoppen
docker-compose down

# Backend Logs
docker-compose logs -f backend

# Frontend Logs
docker-compose logs -f frontend
```

### 🔧 Troubleshooting

#### Frontend Build Errors nach Git Pull/Branch Switch

**Problem:** `Module not found: Error: Can't resolve '@examcraft/premium'` oder ähnliche Webpack-Fehler

**Ursache:** Webpack cached alte Versionen von Dateien nach Branch-Wechsel oder Git Pull

**Lösung:**

```bash
# Option 1: Cache-Clearing Script (empfohlen)
./scripts/clean-frontend-cache.sh

# Option 2: Alle Caches löschen + Neuinstallation
./scripts/clean-frontend-cache.sh --all --reinstall

# Option 3: Manuell (Core Frontend)
cd packages/core/frontend
rm -rf node_modules/.cache build/
bun install
```

#### Bun

ExamCraft AI verwendet **Bun** als Package Manager:

```bash
# Bun installieren (10-100x schneller!)
curl -fsSL https://bun.sh/install | bash

# Dependencies installieren
bun install

# Scripts ausführen
bun run build:core
```

**Vorteile von Bun:**
- ⚡ 10-100x schnellere Installation
- 🚀 Schnellere Script-Ausführung
- 📦 Besseres Monorepo-Handling

#### Docker Container Probleme

```bash
# Alle Container stoppen und neu starten
docker-compose down
docker-compose up -d --build

# Volumes löschen (ACHTUNG: Löscht Datenbank!)
docker-compose down -v
docker-compose up -d

# Logs für Debugging
docker-compose logs -f backend
```

**Siehe [MONOREPO_SETUP.md](MONOREPO_SETUP.md) für weitere Troubleshooting-Tipps.**

### API Endpoints

- `GET /` - Health Check
- `GET /health` - Service Status
- `POST /api/v1/generate-exam` - Prüfung generieren
- `GET /api/v1/topics` - Verfügbare Themen
- `GET /api/v1/exam/{exam_id}` - Prüfung abrufen

## 📋 Workshop Demo

Diese Version enthält eine funktionsfähige Demo für Workshop-Zwecke:

- ✅ Vollständige UI für Prüfungserstellung
- ✅ Demo-Fragen Generation (ohne Claude API)
- ✅ Interaktive Prüfungsansicht mit Auswertung
- ✅ Responsive Design mit Material-UI
- ✅ Docker-basierte Entwicklungsumgebung

## 🔧 Technologie-Stack

### Backend

- **FastAPI** - Moderne Python Web API
- **SQLAlchemy** - ORM für Datenbankzugriff
- **PostgreSQL** - Relationale Datenbank
- **Redis** - Caching und Session Management
- **Pydantic** - Datenvalidierung und Serialisierung

### Frontend

- **React 18** - UI Framework
- **TypeScript** - Type-sichere Entwicklung
- **Material-UI (MUI)** - Komponenten-Bibliothek
- **Axios** - HTTP Client

### DevOps

- **Docker & Docker Compose** - Containerisierung
- **uvicorn** - ASGI Server
- **nginx** - Reverse Proxy (Produktion)

## 🎯 Roadmap

### Phase 1: Workshop Demo ✅

- [x] Grundlegende Projektstruktur
- [x] Docker-Umgebung Setup
- [x] FastAPI Backend mit Demo-Endpoints
- [x] React Frontend mit Material-UI
- [x] Prüfungserstellung und -anzeige

### Phase 2: Core Features

- [ ] Claude API Integration
- [ ] Benutzerauthentifizierung
- [ ] Prüfungsverwaltung (CRUD)
- [ ] Erweiterte Fragetypen
- [ ] Export-Funktionen (PDF, Word)

### Phase 3: Erweiterte Features

- [ ] Fragenkatalog-Verwaltung
- [ ] Statistiken und Analytics
- [ ] Benutzerrollen und Permissions
- [ ] Integration mit LMS-Systemen
- [ ] Mobile App

## 🤝 Contributing

1. Fork das Repository
2. Feature Branch erstellen (`git checkout -b feature/amazing-feature`)
3. Änderungen committen (`git commit -m 'feat: Add amazing feature'`)
4. Branch pushen (`git push origin feature/amazing-feature`)
5. Pull Request erstellen

## 📄 Lizenz

Dieses Projekt ist unter der MIT Lizenz lizenziert - siehe [LICENSE](LICENSE) Datei für Details.

## 📞 Support

- **Issues**: GitHub Issues für Bug Reports und Feature Requests
- **Dokumentation**: `/docs` Ordner für detaillierte Dokumentation
- **API Docs**: <http://localhost:8000/docs> (während Entwicklung)

---

**ExamCraft AI** - Revolutioniere die Art, wie Prüfungen erstellt werden! 🎓✨
