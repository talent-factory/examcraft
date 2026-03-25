# Changelog

All notable changes to ExamCraft AI will be documented in this file.

The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

---

## [1.1.0] - 2026-03-23

### Added

- **Exam Composer (TF-56)**: Vollständige Prüfungszusammenstellung mit Drag-and-Drop, Auto-Fill, Export (Markdown/JSON/Moodle XML), Finalisierung und Zwei-Panel-Layout
- **Auto-Composition Engine (TF-299)**: Constraint-basierte automatische Prüfungszusammenstellung mit Schwierigkeitsgrad- und Themenverteilung
- **KI-geführter Prompt Wizard (TF-297)**: Interaktiver Chat-Assistent zur Template-Erstellung mit Quick-Options, Live-Vorschau und Session-Management
- **Internationalisierung i18n (TF-295)**: Vollständige Mehrsprachigkeit (DE/EN/FR/IT) für Backend-Fehlermeldungen und Frontend-UI
- **Sprachauswahl auf Profilseite**: Sprachwechsel von NavBar auf Profilseite verschoben mit Länderflaggen-Emojis
- **Parallele Fragengenerierung (TF-208)**: Async Celery Tasks mit persistenter Fortschrittsanzeige, WebSocket-Updates und Progress-Callback
- **Question Metadata Enrichment (TF-300)**: Bloom-Level und geschätzte Bearbeitungszeit werden automatisch bei Container-Start berechnet und persistiert
- **Admin-Vereinfachung**: Sidebar-Menü auf einzelnen Admin-Link mit 5 RBAC-Tabs reduziert (Users, Audit, Subscription, Institutions, Roles)

### Fixed

- Text-Overflow in MarkdownRenderer und Wizard Template-Preview Layout (word-break, pre-wrap, wrapLongLines)
- Frontend-Tests: i18n-Mock lädt echte deutsche Übersetzungen statt Translation-Keys zurückzugeben
- Google OAuth Login funktioniert jetzt beim ersten Versuch (Exchange-Endpoint repariert)
- CORS: Content-Disposition Header korrekt exponiert für Datei-Downloads
- Export-Dateinamen enthalten Prüfungsname (lowercase) und Timestamp
- Exam-Liste aktualisiert sich nach Statusänderung (Query Invalidation)
- Datum wird zweistellig formatiert (21.03.2026 statt 21.3.2026)
- Prompt-Erstellung: `created_by`-Fehler behoben
- SyntaxHighlighter Mock für Tests erweitert (vscDarkPlus Export)

### Changed

- Deployment: 2-Tier-Architektur (Core/Full) statt separater Premium/Enterprise Compose-Files
- Feature-Kontrolle zu 100 % über RBAC statt Environment-Feature-Flags
- CI/CD: Migration von GitLab zu GitHub Actions mit Fly.io Deployment
- MarkdownRenderer: wrapLongLines und word-break für bessere Code-Darstellung

## [1.0.0] - 2026-03-18

### Added - TF-57: Authentication UI Modernization & Tailwind CSS Integration (2025-01-20)

#### Frontend Improvements

- **Tailwind CSS v3 Integration** - Modern utility-first CSS framework
  - Configured CRACO for Create React App PostCSS integration
  - Added tailwind.config.js for content scanning and theme configuration
  - Configured postcss.config.js for Tailwind and Autoprefixer processing
  - Full utility classes support across all components
  - Production-ready build with CSS purging

- **Authentication UI Modernization**
  - Redesigned LoginForm with modern card-based layout
  - Updated AuthPage with improved visual hierarchy
  - Reduced icon size for better proportions (20x20 → 16x16)
  - Enhanced form inputs with focus states and transitions
  - Added "Welcome back" header with descriptive subtitle
  - Improved color scheme (gray-900 → blue-600 for branding)
  - Consistent spacing and typography throughout auth flow

#### Technical Changes

- **New Configuration Files**:
  - `frontend/tailwind.config.js` - Tailwind CSS configuration
  - `frontend/postcss.config.js` - PostCSS plugins setup
  - `frontend/craco.config.js` - CRA webpack override for PostCSS

- **Dependencies Updated**:
  - Added `tailwindcss@3.3.0` (downgraded from v4 for CRA compatibility)
  - Added `postcss@latest`
  - Added `autoprefixer@latest`
  - Added `@craco/craco@7.1.0` for CRA configuration override

- **CSS Changes**:
  - Updated `frontend/src/index.css` with Tailwind directives
  - Added `@tailwind base/components/utilities` for v3 syntax

#### Component Updates

- **LoginForm.tsx** (`frontend/src/components/auth/LoginForm.tsx`):
  - Removed self-contained card wrapper (delegated to AuthPage)
  - Added modern header section with title and subtitle
  - Enhanced input styling with gray-50 backgrounds and focus states
  - Improved button styling with transitions and hover effects
  - Better spacing with Tailwind utility classes

- **AuthPage.tsx** (`frontend/src/components/auth/AuthPage.tsx`):
  - Reduced document icon size for better visual balance
  - Changed icon background color to blue-600 for brand consistency
  - Maintained card wrapper for all auth forms

#### Bug Fixes

- Fixed Tailwind CSS not loading due to v4 incompatibility with CRA
- Resolved PostCSS configuration conflicts with CRACO
- Fixed double-card structure in authentication flow
- Corrected icon sizing issues in AuthPage

#### Documentation

- Configuration files properly documented inline
- All three config files (tailwind, postcss, craco) committed to repository

---

### Added - TF-111: Document ChatBot Feature (2025-01-09)

#### Features

- **Interactive Document ChatBot** - RAG-powered conversational interface
  - Real-time chat with uploaded documents
  - Context-aware responses using Claude API
  - Source citations with page references
  - Chat history persistence in PostgreSQL
  - Export conversations as Markdown documents

- **Chat-to-Document Export** - Convert conversations to reusable documents
  - Full conversation export with metadata
  - Automatic title generation from chat context
  - Integration with document library
  - Markdown formatting with timestamps
  - User attribution for library visibility

- **Enhanced Document Model** - Improved metadata handling
  - Dynamic `title` property from `doc_metadata`
  - Fallback to `original_filename` if no title
  - Support for chat-export source type
  - Full content storage in metadata for chat exports

#### Technical Changes

- New API Endpoints:
  - `POST /api/v1/chat/sessions` - Create chat session
  - `POST /api/v1/chat/message` - Send message
  - `GET /api/v1/chat/sessions/{id}` - Get session details
  - `POST /api/v1/chat/sessions/{id}/to-document` - Export to document
  - `GET /api/v1/chat/sessions/{id}/download` - Download as Markdown

- Enhanced Services:
  - `backend/services/chatbot_service.py` - PydanticAI-based chat logic
  - `backend/services/chat_export_service.py` - Conversation export
  - `backend/services/document_service.py` - Chat-export handling

- Database Models:
  - `backend/models/chat_db.py` - ChatSession & ChatMessage tables
  - Enhanced `Document` model with `@property title`

#### Frontend Components

- New React Components:
  - `ChatInterface.tsx` - Main chat UI
  - `ChatSidebar.tsx` - Session management
  - `MessageList.tsx` - Conversation display
  - `ChatInput.tsx` - Message input with file upload

#### Testing

- Comprehensive test suite with PostgreSQL integration:
  - `backend/tests/test_chat_api.py` - Chat API tests (3 tests)
  - `backend/tests/test_document_model.py` - Document model tests (6 tests)
  - `backend/tests/test_document_service.py` - Service tests (2 tests)
  - PostgreSQL-based integration tests with transaction isolation
  - 28/28 tests passing (100% pass rate)

#### Bug Fixes

- Fixed Markdown rendering in chat responses
- Fixed PydanticAI message history handling
- Fixed export button functionality (download & save)
- Fixed missing documents in library after export
- Fixed incomplete chat history in document preview
- Fixed SQLAlchemy deprecation warnings
- Removed obsolete test dependencies

#### Documentation

- Updated `backend/tests/README.md` - PostgreSQL test infrastructure
- Added comprehensive test documentation
- Updated `.claude/rules/CLAUDE.md` - Project status

---

### Added - TF-110: IBM Docling Integration (2025-01-06)

#### Features

- **IBM Docling Processor** - Modern document processing with advanced
features
  - Advanced PDF-Layout-Erkennung
  - Tabellen-Extraktion mit Strukturerhaltung
  - Multi-Format-Support (PDF, DOCX, PPTX, XLSX, Images)
  - OCR für gescannte Dokumente
  - Semantic Chunking basierend auf Dokumentstruktur
  - Erweiterte Metadaten-Extraktion (Sektionen, Tabellen, Bilder)

- **Legacy Processor Fallback** - Robust fallback implementation
  - PyPDF für PDF-Verarbeitung
  - python-docx für DOCX-Verarbeitung
  - Markdown-Support
  - Automatischer Fallback wenn Docling nicht verfügbar

- **Factory Pattern** - Dynamic processor selection
  - Environment-basierte Konfiguration (`DOCUMENT_PROCESSOR_TYPE`)
  - Auto-Detection mit Fallback
  - Backwards Compatible API

#### Technical Changes

- Neue Module:
  - `backend/services/document_processors/docling_processor.py`
  - `backend/services/document_processors/legacy_processor.py`
  - `backend/services/document_processors/processor_factory.py`
  - `backend/services/document_analyzers/` (für zukünftige Analyzer)

- Refactored `backend/services/docling_service.py`:
  - Delegiert Processing an Factory-Processor
  - Behält Backwards Compatible API

#### Dependencies

- Added:
  - `docling==2.23.0`
  - `docling-core==2.48.4`
  - `docling-ibm-models==3.9.1`
- Updated:
  - `python-docx==1.1.2` (required by Docling)
  - `numpy>=1.24.3` (flexible version for Docling compatibility)

#### Testing

- Added comprehensive test suite:
  - `backend/tests/test_docling_processor.py` - Unit tests for Docling
  - `backend/tests/test_legacy_processor.py` - Unit tests for Legacy
  - `backend/tests/test_processor_factory.py` - Integration tests
  - `backend/tests/test_processor_performance.py` - Performance benchmarks

#### Documentation

- Added `docs/features/DOCLING-INTEGRATION.md` - Complete integration guide
- Updated `README.md` - Added Docling to core features

#### Bug Fixes

- Fixed import paths in document processors
- Handled docling-core API changes with fallback imports
- Resolved dependency conflicts (python-docx, numpy)

### Added - TF-108: Production Deployment (2025-01-05)

#### Deployment Infrastructure

- **Render.com Multi-Service Architecture**
  - Backend API: <https://api.examcraft.talent-factory.xyz>
  - Frontend: <https://examcraft.talent-factory.xyz>
  - Qdrant Vector Database
  - PostgreSQL Database
  - Redis Cache

- **Environment Variables Management**
  - Environment sync tool (`scripts/sync_env_to_render.py`)
  - Production environment template (`.env.production`)
  - Comprehensive documentation (`docs/deployment/ENVIRONMENT-VARIABLES.md`)

- **Deployment Health Checks**
  - Health check script (`scripts/check_deployment.py`)
  - Automated testing of all endpoints
  - Service status monitoring

#### CI/CD Pipeline

- **GitLab CI/CD**
  - Automated testing on push
  - Pre-commit hooks for code quality
  - Deployment validation

#### Documentation

- Added deployment guides:
  - `docs/deployment/RENDER-DEPLOYMENT.md`
  - `docs/deployment/TESTING.md`
  - `docs/deployment/TROUBLESHOOTING.md`

### Fixed

- Database connection issues (missing password in DATABASE_URL)
- Health endpoint bugs (SQLAlchemy text() wrapper, async issues)
- Build timeout (removed sentence-transformers)
- Import errors (numpy always imported)

---

## [0.9.0] - 2024-12-20

### Added - TF-103: Qdrant Migration

#### Vector Database

- **Migrated from ChromaDB to Qdrant**
  - Better performance and scalability
  - Production-ready vector search
  - Improved embedding management

#### Features

- Qdrant client integration
- Vector search endpoints
- Document reindexing functionality

### Changed

- Removed ChromaDB dependencies
- Updated vector search implementation
- Optimized embedding storage

---

## [0.8.0] - 2024-12-15

### Added - Core Features

#### Document Processing

- PDF processing with PyPDF
- DOCX processing with python-docx
- Markdown support
- Text chunking with overlap

#### RAG System

- Qdrant vector storage
- Semantic search with OpenAI embeddings
- Context retrieval for question generation

#### Question Generation

- Claude API integration via PydanticAI
- Bloom Taxonomy support
- Structured answer generation
- Quality levels (A/B/C)

#### Frontend

- React 18 + TypeScript
- TanStack Query for API state
- Tailwind CSS + shadcn/ui components
- Responsive design

#### Backend

- FastAPI REST API
- PostgreSQL database
- Redis caching
- SQLAlchemy ORM

---

## [0.1.0] - 2024-11-01

### Added - Initial Setup

#### Project Structure

- Backend (FastAPI)
- Frontend (React)
- Database (PostgreSQL)
- Docker Compose setup

#### Basic Features

- Document upload
- Basic text extraction
- Simple question generation

---

## Release Notes

### Version 1.0.0 - Production Release

- Complete feature set implemented
- Production deployment on Render.com
- Comprehensive testing suite
- Full documentation
- CI/CD pipeline

### Version 0.9.0 - Qdrant Migration

- Improved vector search performance
- Production-ready database
- Better scalability

### Version 0.8.0 - Core Features

- RAG-based question generation
- Multi-format document support
- Modern web interface

---

## Roadmap

### Planned Features (TF-110 Continuation)

- [ ] Table Extractor Analyzer
- [ ] Layout Analyzer
- [ ] Metadata Enricher
- [ ] Custom Chunking Strategies
- [ ] Batch Processing
- [ ] Document Caching

### Future Enhancements

- [ ] User Authentication & Authorization (TF-57)
- [ ] Question Review Interface (TF-60)
- [ ] Exam Composition & Export (TF-56)
- [ ] Workshop Demo Materials (TF-58)
- [ ] Multi-language Support
- [ ] Advanced Analytics

---

## Contributors

- Daniel Senften (@dsenften) - Lead Developer
- Talent Factory Team

---

## License

MIT License - See LICENSE file for details
