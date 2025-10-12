# ExamCraft AI 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

**KI-gestützte OpenSource-Plattform zur automatischen Generierung von Prüfungsaufgaben für OpenBook-Prüfungen mit Claude API Integration und RAG-basierter Dokumentenanalyse.**

## 🎯 Projektübersicht

ExamCraft AI ist eine vollständig implementierte, **produktionsreife** Webanwendung, die Dozierenden dabei hilft, qualitativ hochwertige Prüfungsaufgaben automatisch aus beliebigen Dokumenten zu generieren. Die Plattform kombiniert moderne KI (Claude API) mit RAG-Technologie (Retrieval-Augmented Generation) für kontextuelle, durchdachte Fragenerstellung.

## 📚 Dokumentation

### 📊 Für Stakeholder & Kunden

- **[📊 Executive Summary](docs/EXECUTIVE_SUMMARY.md)** - Business-Übersicht, Marktchancen, Finanzprognosen
- **[🎯 Feature-Übersicht](docs/FEATURES.md)** - Vollständige Feature-Liste mit Use Cases und Benefits
- **[📅 Release Timeline](docs/RELEASE_TIMELINE.md)** - Detaillierte Roadmap mit quartalsweisen Releases
- **[🗺️ Product Roadmap](docs/ROADMAP.md)** - Langfristige Vision und Feature-Vergleichsmatrix

### 👥 Für Benutzer

- **[📚 Benutzerhandbuch](docs/USER_GUIDE.md)** - Vollständige Anleitung für Dozenten und Lehrkräfte
- **[🎛️ Admin Guide: Prompt Management](docs/ADMIN_PROMPT_MANAGEMENT.md)** - Verwaltung der AI-Prompts

### 🔧 Für Entwickler

- **[🚀 Deployment Guide](docs/RENDER_DEPLOYMENT.md)** - Production Deployment auf Render.com
- **[📖 API Dokumentation](http://localhost:8000/docs)** - Interaktive API-Docs (lokal)
- **[🔧 Development Setup](#-quick-start)** - Lokale Entwicklungsumgebung (siehe unten)

### ✨ Kernfeatures

- **🤖 RAG-basierte KI-Fragenerstellung** mit Claude API + PydanticAI
- **💬 Interaktiver Document ChatBot** - Konversationen mit hochgeladenen Dokumenten
- **🎛️ Prompt Knowledge Base Management** - Zentrale Verwaltung aller AI-Prompts mit Versionierung
- **📄 Multi-Format Dokumentenverarbeitung**: PDF, Word, Markdown
- **🔬 IBM Docling Integration** - Advanced Document Processing mit automatischem Fallback
- **🔍 Semantische Suche** mit Qdrant Vector Database (Dokumente + Prompts)
- **🎯 Bloom Taxonomy Integration** für verschiedene Lernlevels
- **📝 Strukturierte Musterlösungen** mit A/B/C Qualitätsstufen
- **💾 Chat-Export Funktion** - Konversationen als Markdown-Dokumente speichern
- **📊 Usage Analytics** - Überwachung von Prompt-Performance und Token-Verbrauch
- **⚛️ Moderne Web-UI** mit React 18 + TypeScript + Material-UI
- **🐳 Container-basiert** für einfache Entwicklung und Deployment
- **🚀 Production-Ready** mit Rate Limiting, Error Handling & Monitoring

## 🏗️ Architektur

```text
ExamCraft/
├── backend/             # FastAPI Backend Server
│   ├── main.py          # REST API Endpoints
│   ├── database.py      # PostgreSQL Connection
│   ├── models.py        # Pydantic Data Models
│   └── services/        # Business Logic Services
├── frontend/            # React 18 + TypeScript Frontend
│   ├── src/components/  # React UI Components
│   ├── src/services/    # API Client Services
│   ├── src/types/       # TypeScript Definitions
│   └── public/          # Static Assets
├── utils/               # Python Core Utilities
│   ├── extraction.py    # Document Processing (PDF/DOC/MD)
│   └── rag.py           # RAG System (ChromaDB + Embeddings)
├── demo/                # Workshop Demo Materials
│   ├── *.pdf            # Example Academic Documents
│   └── *.md             # Generated Questions & Solutions
├── docs/                # Project Documentation
├── .claude/             # Claude Code Integration
├── docker-compose.yml   # Multi-Container Orchestration
├── start-dev.sh         # Development Environment Launcher
└── pyproject.toml       # Python Dependencies & Config
```

## 🚀 Quick Start

### Voraussetzungen

- **Docker & Docker Compose** (für Container-basierte Entwicklung)
- **Git** (für Repository-Management)
- **Claude API Key** (für KI-Fragenerstellung, optional für lokale Tests)
- **Python 3.13+** (für lokale Entwicklung ohne Docker)

### 🐳 Docker Installation (Empfohlen)

1. **Repository klonen**

   ```bash
   git clone https://github.com/yourusername/examcraft-ai.git
   cd examcraft-ai
   ```

2. **Umgebung konfigurieren**

   ```bash
   cp .env.example .env
   # .env bearbeiten und CLAUDE_API_KEY eintragen (optional)
   ```

3. **Entwicklungsstack starten**

   ```bash
   ./start-dev.sh
   # Oder manuell: docker-compose up -d
   ```

4. **Services verfügbar unter:**
   - **Frontend**: <http://localhost:3000> (React Dashboard)
   - **Backend API**: <http://localhost:8000> (FastAPI Server)
   - **API Dokumentation**: <http://localhost:8000/docs> (Swagger UI)
   - **Database**: localhost:5432 (PostgreSQL)
   - **Redis**: localhost:6379 (Caching)

### 🐍 Lokale Python Installation

```bash
# Python Dependencies installieren
pip install -e .

# Backend starten
cd backend && python main.py

# Frontend entwickeln (separates Terminal)
cd frontend && npm install && npm start
```

## 🛠️ Entwicklung

### Services

- **Frontend (React)**: Port 3000
- **Backend (FastAPI)**: Port 8000
- **PostgreSQL**: Port 5432
- **Redis**: Port 6379

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
