# Changelog

All notable changes to ExamCraft AI will be documented in this file.

The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.3.1] - 2026-04-30

### Fixed

- **TF-331 — DOCX-Vektorisierung extrahiert Tabellen, Header und Footer
  (#44):** `PyMuPDFProcessor._process_docx` iterierte bisher nur
  `doc.paragraphs` (Top-Level-Body) — Tabellen, geschachtelte Tabellen,
  Header, Footer, Textfelder und Fussnoten wurden übersprungen.
  Tabellenlastige `.docx`-Dateien lieferten 0 Chunks → Qdrant
  HTTP 400 „Empty update request" → stiller Fehlschlag mit
  `has_vectors=False`. Neue `_iter_docx_text_blocks()`-Funktion walkt
  alle `<w:t>`-Elemente plus Section-Header/Footer.
  Defense-in-Depth: `process_document_content` und
  `add_document_chunks` lösen jetzt bei 0 Chunks eine Exception aus,
  statt still fehlzuschlagen. Begleitend: `.doc` (OLE2/CFB) wird klar
  abgewiesen („Bitte als .docx speichern"), `.md`-MIME-Detection
  priorisiert die Datei-Endung über libmagic, `.txt`/`.md`-Encoding-Fallback
  (UTF-8 → Latin-1) mit Mojibake-Schutz.
  Title-Resolver filtert Office-Defaults (`"1"`, `"Untitled"`,
  `Document1`, `Mappe1`, `Tabelle1`, `Sheet1`, …) und User können
  Dokumenten-Titel via Inline-Edit überschreiben (neue
  `documents.display_name`-Spalte, `PATCH /api/v1/documents/{id}`).
  Strukturierte Error-Codes (`legacy_doc_format`, `empty_document`,
  `binary_content`, `unsupported_format`, `vectorization_failed`,
  `file_corrupt`, `unknown_error`) liefern lokalisierte UI-Meldungen
  in DE/EN/FR/IT statt englischer Raw-Strings. Migrationsskript
  `scripts/reprocess_documents_without_vectors.py` reprozessiert
  bestehende ungesicherte Dokumente. ~80 neue Tests, 214 grün.
- **Release-Pipeline überschreibt `http.extraheader` für
  Public-Repo-Pushes (#43):** Beim v1.3.0-Release schlug der Push des
  Tags zum Public-Repo mit 403 fehl, weil der `extraheader`, den
  `actions/checkout` mit dem privaten `github.token` setzt, die
  URL-eingebetteten `MIRROR_GITHUB_TOKEN`-Credentials überschreibt.
  Lösung: `git -c http.https://github.com/.extraheader=` pro
  Push-Kommando — bewahrt den `Create Git Tag`-Step zum privaten
  Repo, fixt aber den Public-Push.

### Changed

- **`.gitignore` neu strukturiert + `scheduled_tasks.lock` ergänzt:**
  Lock-File von Celery-Beat-Singleton-Tasks wird nicht mehr
  versioniert; bestehende Einträge gruppiert (Build-Artefakte, IDE,
  Logs, Caches, Secrets) für bessere Wartbarkeit.

## [1.3.0] - 2026-04-29

### Added

- **TF-319 — Dashboard-Statistiken & Aktivitätsfeed (#17):** Neuer
  Dashboard-Endpoint `/api/dashboard/stats` plus `/activity` mit den
  letzten 25 Aktivitäten pro Institution (Dokument-Upload, Fragen-
  Generierung, Review-Approve/Reject, Exam-Erstellung, Lösch-Events).
  Der Activity-Feed liest aus `audit_logs`, sodass auch gelöschte
  Ressourcen sichtbar bleiben.
- **TF-321 — Exam-Composer-Filter nach Quelldokument (#30):**
  Question-Pool im Composer kann jetzt auf einzelne oder mehrere
  Quelldokumente eingeschränkt werden (`?document_ids=1,2`). Neue
  `QuestionSourceDocument`-Join-Tabelle (Migration
  `2026_04_23_tf321_a_question_source_documents.py`) und ein optionales
  `Exam.default_document_ids`-Array für Composer-Vorbelegung.
- **TF-324 — Superuser-Vollzugriff mit Audit-Trail (#31):** Neue
  `is_superuser`-Rolle mit Tenant-übergreifendem Lesezugriff. Jede
  cross-owner-Aktion landet via `AuditService.log_superuser_bypass`
  bzw. `log_admin_cross_owner` im Audit-Log und schlägt fail-loud
  mit HTTP 500 fehl, wenn die Audit-Persistenz selbst kippt
  (DSGVO-Vertrag).
- **TF-329 — Watchdog für stuck PENDING-Jobs (#36):** Celery-Beat-
  Periodic-Task `tasks.maintenance_tasks.reconcile_stuck_jobs` läuft
  alle 5 Minuten und syncen `QuestionGenerationJob.status` mit dem
  echten Celery-Result-Backend. Counter
  `{reconciled, lost, skipped_in_progress, skipped_unexpected, errors}`
  geben Operatoren ehrliches Beat-Health-Signal.
- **HelpIndexState + `/admin/index-state`-Endpoint (#28):** Persistenter
  Status der Docs-Indexierung mit Admin-API für Beobachtbarkeit.
  Status-Übergänge `idle → in_progress → completed | partial | failed`
  mit `last_error`-Feld.
- **Help-Widget UX-Verbesserungen (#27):** Verbesserte
  Onboarding-Tour, klarere Empty-States, präzisere Status-Indikatoren.
- **Generation-Retry-Mechanismus:** Neuer Endpoint
  `POST /rag/retry-generation/{task_id}` plus Retry-Button in der
  `GenerationTasksBar`. Originalparameter werden in
  `QuestionGenerationJob.request_data` (neue JSON-Spalte) persistiert,
  so dass fehlgeschlagene Jobs ohne Datenverlust neu gestartet werden
  können. Exponentielles Backoff für Celery-Task-Retries (perf).
- **Billing — lokalisierte Fehlermeldungen:** Stripe-Checkout-Fehler
  in DE/EN/FR/IT mit spezifischen Stripe-Fehlercodes statt generischen
  Meldungen.

### Fixed

- **TF-325 — `_update_job_status` fail-loud + Retry (#32):** Status-
  Updates auf `QuestionGenerationJob` werden jetzt mit 4 Versuchen
  (Backoffs 2s/5s/10s) durchgeführt; nach Retry-Erschöpfung wird
  `JobStatusUpdateError` geraist statt schweigend weiterzulaufen. Deckt
  das 5-15s-Postgres-Restart-Fenster aus dem 2026-04-28-Incident ab.
- **TF-326 — `/active-tasks` reconcile gegen Celery-State (#33):**
  Jobs, deren DB-Status `PENDING` aber Celery-State `SUCCESS`/`FAILURE`/
  `REVOKED` ist, werden idempotent synchronisiert und aus der Antwort
  ausgefiltert. Eliminiert Phantom-Tasks im UI.
- **TF-327 — SQLAlchemy-Pool-Resilienz (#34):** `pool_recycle=1800`
  und `connect_timeout=5` gegen verlorene Verbindungen unter Last.
  `pool_size=10 + max_overflow=20 = 30 connections per process`.
- **TF-328 — WebSocket-Sticky-Terminal-State (#35):** `FAILURE`/
  `REVOKED` bleibt im Frontend sticky — kein Auto-Recovery in
  `RUNNING` mehr nach einem Late-PROGRESS-Frame. Backend schliesst
  die Verbindung nach Terminal-State.
- **TF-330 — `ReviewQueue` toleriert Legacy-Dict-Shape (#37):**
  `options` mit Letter-Keys (`'A'/'B'/'C'/'D'`) wird zu `List[str]`
  normalisiert; numeric/mixed Keys werden auf `None` gemappt mit
  ERROR-Log. Migration
  `2026_04_29_tf330_normalize_options_dict_to_list.py` zieht Legacy-Rows
  einmalig auf den kanonischen Shape um.
- **TF-331 — Silent-Failure-Patterns aus PR #38 Review beseitigen (#39):**
  Erste Iteration: `_safe_update_job_status` mit CRITICAL-Logs,
  `audit_service.log_action` fail-loud bei Bypass-Audits,
  `docs_indexer_service` Redis-Lock-Failure schlägt jetzt mit 503 durch
  statt locklos weiterzulaufen, `database._run_migrations_or_create_all`
  re-raised unter `AUTO_MIGRATE=true`.
- **TF-332 — PR #38 Second-Pass-Review-Findings (#40):** Zweite
  Iteration:
  - `docs_indexer` SHA-Poisoning beseitigt (per-File-Failures avancieren
    `last_indexed_sha` nicht mehr fälschlich).
  - `_persist_questions` fail-loud bei unrecoverbaren MC-Options.
  - `enforce_resource_access` blockiert Cross-Institution-Zugriff auf
    Orphan-Resources (Tenant-Check vor Orphan-Branch).
  - `retry_generation` bewahrt Original-Owner-Identität bei Superuser-
    Retry.
  - `/active-tasks`-Audit nur noch wenn fremder Job in der Antwort.
  - `QuestionPoolPanel` Error-Banner statt stilles "noQuestions".
  - Watchdog `skipped_unexpected`-Counter gegen State-Drift.
  - Dashboard WARNING bei korruptem `additional_data`-JSON.
- **document-chat:** Dokument-Auswahl im Neuer-Chat-Dialog wieder
  sichtbar.
- **Sidebar:** Versionsnummer und Release-Link auf spezifisches v-Tag
  korrigiert (Hotfixes #25, #26).
- **Docs-Indexer-Follow-ups:** Fail-Surfaces, Git-Robustness,
  Redis-Lock-Cleanup.

### Added — Tests

- 4 neue Test-Cases aus dem Second-Pass-Review (Multi-Doc-Filter UNION,
  REVOKED-WebSocket-Close, active-tasks audit-fail-aborts,
  Watchdog-SLA-Bound).
- 3 neue `enforce_resource_access`-Branch-Tests
  (Cross-Institution-Block, Superuser-Cross-Tenant-mit-Audit,
  Backwards-Compat ohne `institution_id`-Attribut).
- Pre-existing Test-Isolation-Flakes aufgelöst (quota-Fixture filtert
  per Slug, profile-permissions-Fixture filtert per Slug-Set,
  `sys.setrecursionlimit(3000)` für Pydantic-Schema-Rebuild).

### Migration Notes

Migrationen sind additiv und laufen via `AUTO_MIGRATE=true` automatisch
beim Backend-Start:

- `2026_04_23_tf321_a_question_source_documents.py` — neue Join-Tabelle
- `2026_04_23_tf321_b_exam_default_document_ids.py` —
  `Exam.default_document_ids`-Spalte
- `2026_04_29_tf330_normalize_options_dict_to_list.py` —
  Daten-Migration für Legacy-Dict-Shape (idempotent, downgrade
  `NotImplementedError`)
- `2026_04_29_9d70cdf25a49_merge_tf321_and_tf330_heads.py` —
  Alembic-Multi-Head-Merge

---

## [1.2.0] - 2026-04-23

### Added — Docs Deployment Pipeline

- **`docs.examcraft.ch` automatische Publikation:** Neuer GitHub-Actions-Workflow
  `.github/workflows/deploy-docs.yml` baut MkDocs bei jedem Merge auf `develop`
  (wenn `core/docs-site/**` oder Indexer-Code geändert wurde) und publiziert
  nach `talent-factory/examcraft:gh-pages` mit CNAME auf `docs.examcraft.ch`.
  Bisher war die gh-pages-Branch 30 Tage hinter dem Code — ab jetzt synchron
  mit jedem Docs-Merge.
- **LiveBot-Vektorisierung in Production:** `core/backend/Dockerfile.fly` kopiert
  jetzt `core/docs-site/` ins Runtime-Image. Zuvor enthielt das Backend-Image
  keine Docs-Files, der Startup-Indexer (`DocsIndexerService`, siehe
  `backend/main.py:103`) indexierte ins Leere. Nach dem Fix hat der LiveBot
  tatsächlich Zugriff auf die Dokumentation via Qdrant-Collection `docs_help`.
- **Automatischer Backend-Redeploy nach Docs-Change:** Der Deploy-Docs-Workflow
  triggert nach dem gh-pages-Push einen `flyctl deploy` des Backend-Apps. Das
  neue Image enthält die frischen Docs, und der Startup-Indexer läuft
  automatisch — der LiveBot ist innerhalb von ~5 Minuten aktuell.
- **`just reindex-docs`** in Root- und Core-Justfile: restartet den `api`-Container,
  um lokale Docs-Änderungen in Qdrant neu zu vektorisieren. Zeigt anschliessend
  die `Docs indexed: N files`-Zeile aus den Container-Logs.

### Fixed

- `fly.toml` setzt `DOCS_SITE_PATH=/app/docs-site/docs` passend zum neuen
  Dockerfile-Layout. In Production war dieser Pfad zuvor via Code-Default
  auf `core/docs-site/docs` (relativer Pfad, der im Container nicht existierte).

### Improved — Developer Experience

- Migrated Makefile-based developer workflow to [`just`](https://just.systems/).
  Most `make X` commands have a direct `just X` counterpart; see Added/Removed
  sections for diffs. Note that `just test-backend` in the root justfile now
  runs pytest **inside the compose container** (requires a running stack);
  use `just test-file <path>` or `just test-one <target>` for local-uv runs.
  `just --list` shows all recipes grouped by category, replacing the
  hand-maintained `help` target.
- `.env` is auto-loaded for all recipes via `set dotenv-load`; manual
  `--env-file .env` is no longer required for docker-compose invocations.
- `just dev` now includes the auto-detection, `.env` scaffolding, and Alembic
  migration retry logic previously only available via `./start-dev.sh`.

### Added

- `just test-file <path>` — run a single pytest file.
- `just test-one <target>` — run a single pytest function
  (e.g. `path::test_func`).
- `just deploy-app <name>` — deploy any Fly.io app by name (replaces the need
  for one recipe per service).
- `just logs [app]` — follow logs for any Fly.io app (defaults to
  `examcraft-api`).
- `just dev-core` / `just dev-full` preserved as aliases for
  `just dev core` / `just dev full`.

### Removed

- `start-dev.sh` — auto-detection logic moved into `just dev`.
- `stop-dev.sh` — inlined into `just stop` / `just stop-volumes`.
- `seed-dev-data.sh` — inlined into `just seed` (auto-detects full/core).
- Root and `core/` `Makefile` — replaced by `justfile` at each location.

### Fixed

- `make ci-check` (and the pre-push git hook) silently pointed at a
  non-existent `scripts/pre-push-lint-check.sh`. `just ci-check` is now a
  working shebang recipe that actually runs the CI check chain.
- Stale documentation references to `scripts/validate-env.sh` (never existed)
  and `scripts/setup-premium-symlinks.sh` (never existed) removed from
  `core/CLAUDE.md` and `docs/DEPLOYMENT.md`.

### Migration Notes

Install `just` locally before pulling this change:

- macOS: `brew install just`
- Linux: `cargo install just`
- Windows: `winget install --id Casey.Just` (+ Git Bash or WSL2)

The pre-push hook now invokes `just ci-check`; `git push` will fail with a
hook error if `just` is not on `PATH`.

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
