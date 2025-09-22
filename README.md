# ExamCraft AI 🚀

KI-gestützte Plattform zur automatischen Generierung von Prüfungsaufgaben für OpenBook-Prüfungen mit Claude API Integration.

## 🎯 Projektübersicht

ExamCraft AI ist eine moderne Webanwendung, die Dozierenden dabei hilft, qualitativ hochwertige Prüfungsaufgaben automatisch zu generieren. Die Plattform nutzt künstliche Intelligenz (Claude API) zur Erstellung von kontextbezogenen, durchdachten Fragen für verschiedene Schwierigkeitsgrade und Fragetypen.

### ✨ Features

- **🤖 KI-gestützte Fragenerstellung** mit Claude API
- **📝 Multiple Fragetypen**: Multiple Choice, Offene Fragen, etc.
- **🎚️ Anpassbare Schwierigkeitsgrade**: Einfach, Mittel, Schwer
- **🌐 Mehrsprachig**: Deutsch und Englisch
- **📊 Sofortige Auswertung** mit detailliertem Feedback
- **💾 Moderne Tech-Stack**: FastAPI + React + PostgreSQL + Redis
- **🐳 Docker-basiert** für einfache Entwicklung und Deployment

## 🏗️ Architektur

```
ExamCraft/
├── backend/           # FastAPI Backend
│   ├── main.py       # API Endpoints
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/          # React Frontend
│   ├── src/
│   │   ├── components/
│   │   ├── services/
│   │   └── types/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml # Orchestrierung
└── start-dev.sh      # Development Startup
```

## 🚀 Quick Start

### Voraussetzungen

- Docker & Docker Compose
- Git
- Claude API Key (optional für Demo)

### Installation

1. **Repository klonen**
   ```bash
   git clone <repository-url>
   cd ExamCraft
   ```

2. **Umgebung konfigurieren**
   ```bash
   cp .env.example .env
   # .env Datei bearbeiten und Claude API Key eintragen
   ```

3. **Entwicklungsumgebung starten**
   ```bash
   ./start-dev.sh
   ```

4. **Anwendung öffnen**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Dokumentation: http://localhost:8000/docs

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
- **API Docs**: http://localhost:8000/docs (während Entwicklung)

---

**ExamCraft AI** - Revolutioniere die Art, wie Prüfungen erstellt werden! 🎓✨