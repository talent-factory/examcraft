# Changelog

All notable changes to ExamCraft AI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - TF-110: IBM Docling Integration (2025-01-06)

#### Features
- **IBM Docling Processor** - Modern document processing with advanced features
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

---

## [1.0.0] - 2025-01-05

### Added - TF-108: Production Deployment (2025-01-05)

#### Deployment Infrastructure
- **Render.com Multi-Service Architecture**
  - Backend API: https://api.examcraft.talent-factory.xyz
  - Frontend: https://examcraft.talent-factory.xyz
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
- ChromaDB vector storage (later migrated to Qdrant)
- Semantic search
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
- ✅ Complete feature set implemented
- ✅ Production deployment on Render.com
- ✅ Comprehensive testing suite
- ✅ Full documentation
- ✅ CI/CD pipeline

### Version 0.9.0 - Qdrant Migration
- ✅ Improved vector search performance
- ✅ Production-ready database
- ✅ Better scalability

### Version 0.8.0 - Core Features
- ✅ RAG-based question generation
- ✅ Multi-format document support
- ✅ Modern web interface

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

