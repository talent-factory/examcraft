# ExamCraft AI - Core Package (Open Source)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18-blue.svg)](https://reactjs.org/)

**ExamCraft AI Core** ist das Open Source Herzstück der ExamCraft AI Plattform - eine KI-gestützte Lösung zur automatischen Generierung von Prüfungsaufgaben für OpenBook-Prüfungen.

## 🎯 Features (Free Tier)

### ✅ Basis-Funktionalität

- **Document Upload**: PDF, DOC, Markdown Support (max. 5 Dokumente)
- **Document Library**: Verwaltung hochgeladener Dokumente
- **Basic Question Generation**: KI-gestützte Fragengenerierung (20 Fragen/Monat)
- **Question Review**: Manuelle Überprüfung und Bearbeitung generierter Fragen
- **User Management**: Basis-Authentifizierung und Benutzerverwaltung

### 🔒 Limitierungen (Free Tier)

- **Max. 5 Dokumente** pro Institution
- **20 Fragen pro Monat** generierbar
- **1 Benutzer** pro Institution
- **Keine RAG-Generation** (nur in Premium)
- **Kein Document ChatBot** (nur in Professional)
- **Kein SSO/SAML** (nur in Enterprise)

## 🏗️ Architektur

```
packages/core/
├── backend/          # FastAPI Backend (Python 3.13+)
│   ├── api/          # REST API Endpoints
│   ├── models/       # SQLAlchemy Models
│   ├── services/     # Business Logic
│   └── utils/        # Helper Functions
├── frontend/         # React 18 + TypeScript Frontend
│   ├── components/   # React Components
│   ├── pages/        # Page Components
│   └── services/     # API Services
└── docs/             # Documentation
```

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- Node.js 18+
- PostgreSQL 14+
- Redis 7+

### Installation

```bash
# Clone Repository
git clone https://github.com/talent-factory/examcraft.git
cd examcraft/packages/core

# Backend Setup
cd backend
pip install -r requirements.txt
alembic upgrade head

# Frontend Setup
cd ../frontend
npm install
npm start
```

### Environment Variables

```bash
# Backend (.env)
DATABASE_URL=postgresql://user:pass@localhost/examcraft
REDIS_URL=redis://localhost:6379
CLAUDE_API_KEY=your_api_key_here

# Frontend (.env)
REACT_APP_API_URL=http://localhost:8000
```

## 📦 Premium & Enterprise Features

Benötigen Sie mehr Features? Schauen Sie sich unsere Premium- und Enterprise-Editionen an:

### 🌟 Premium Features (€19-49/Monat)

- **RAG Generation**: Semantische Suche mit Qdrant (Premium)
- **Document ChatBot**: NotebookLM-Style Chatbot
- **Prompt Management**: Erweiterte Prompt-Verwaltung
- **Analytics Dashboard**: Nutzungsstatistiken
- **Unlimited Documents**: Keine Dokumenten-Limits
- **1000 Fragen/Monat**: Höheres Kontingent

### 🏢 Enterprise Features (€149/Monat)

- **SSO/SAML Integration**: Single Sign-On
- **Custom Branding**: White-Label Lösung
- **API Access**: REST API für Integrationen
- **Advanced Analytics**: Detaillierte Berichte
- **Priority Support**: 24/7 Support
- **On-Premise Deployment**: Self-Hosted Option

👉 **Mehr Informationen**: [examcraft.ai/pricing](https://examcraft.ai/pricing)

## 🛠️ Technologie-Stack

### Backend

- **FastAPI** - Modern Python Web Framework
- **SQLAlchemy** - ORM für PostgreSQL
- **Alembic** - Database Migrations
- **Pydantic** - Data Validation
- **Claude API** - AI Question Generation

### Frontend

- **React 18** - UI Framework
- **TypeScript** - Type Safety
- **Material-UI (MUI)** - Component Library
- **Tailwind CSS** - Utility-First CSS
- **TanStack Query** - API State Management

### Infrastructure

- **PostgreSQL** - Primary Database
- **Redis** - Session Management & Caching
- **Docker** - Containerization
- **Docker Compose** - Local Development

## 📖 Documentation

- **API Documentation**: `/docs` (FastAPI Swagger UI)
- **User Guide**: [docs/user-guide.md](docs/user-guide.md)
- **Developer Guide**: [docs/developer-guide.md](docs/developer-guide.md)
- **Contributing**: [CONTRIBUTING.md](../../CONTRIBUTING.md)

## 🤝 Contributing

Wir freuen uns über Contributions! Bitte lesen Sie unsere [Contributing Guidelines](../../CONTRIBUTING.md).

### Development Workflow

1. Fork das Repository
2. Erstellen Sie einen Feature Branch (`git checkout -b feature/amazing-feature`)
3. Commit Ihre Änderungen (`git commit -m 'Add amazing feature'`)
4. Push zum Branch (`git push origin feature/amazing-feature`)
5. Öffnen Sie einen Pull Request

## 📄 License

Dieses Projekt ist unter der **MIT License** lizenziert - siehe [LICENSE](../../LICENSE) für Details.

**Hinweis**: Premium und Enterprise Features sind **nicht** Open Source und unterliegen einer proprietären Lizenz.

## 🙏 Credits

Entwickelt von [Talent Factory](https://talent-factory.ch) mit ❤️

- **Claude API** by Anthropic
- **FastAPI** by Sebastián Ramírez
- **React** by Meta

## 📞 Support

- **Community Support**: [GitHub Discussions](https://github.com/talent-factory/examcraft/discussions)
- **Bug Reports**: [GitHub Issues](https://github.com/talent-factory/examcraft/issues)
- **Email**: support@examcraft.ai
- **Website**: [examcraft.ai](https://examcraft.ai)

---

**⭐ Wenn Ihnen ExamCraft AI gefällt, geben Sie uns einen Star auf GitHub!**
