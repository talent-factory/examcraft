# Smart Help Widget & Docs-Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a two-pillar documentation system: Material for MkDocs static site (DE+EN) and an in-app Smart Help Widget with three modes (Onboarding, Context, Chat) plus a self-improving feedback loop.

**Architecture:** The widget is a React floating component integrated at the AppWithAuth level. Backend exposes a new `/api/v1/help/` router with RAG-based chat (reusing Qdrant + Claude), FAQ caching in PostgreSQL, and a feedback queue with clustering. The MkDocs site is a standalone build under `docs-site/`.

**Tech Stack:** React 18 + TypeScript, MUI + Tailwind, FastAPI, SQLAlchemy, Alembic, Qdrant, Claude API (Haiku/Sonnet), MkDocs Material, mkdocs-static-i18n, GitHub Actions

**Linear Issue:** [TF-308](https://linear.app/talent-factory/issue/TF-308)

**Design Spec:** `docs/superpowers/specs/2026-03-23-smart-help-widget-design.md`

**Dependencies:**
- `services/translation_service.py` with `get_request_locale()` already exists in the codebase (used by question_review and other modules)
- `langdetect` Python package must be added to `requirements.txt` for FAQ cache language detection

**Deferred to Phase 2 (separate plan):**
- Feedback clustering by embedding similarity (spec lines 249-250). Phase 1 uses flat list with manual `cluster_id` assignment by admins. Full embedding-based auto-clustering requires a background job and is better suited as a follow-up.
- FAQ cache embedding indexing in a `docs_faq` Qdrant collection. Phase 1 does NOT create the `docs_faq` collection -- the `_try_faq_cache` method will gracefully return `None` (all questions go to Standard Path via Claude). Phase 2 will add a management command to seed FAQ embeddings from `help_faq_cache` table into Qdrant, enabling the true Fast Path.

---

## Phase 1: Foundation (Database + MkDocs Scaffold)

### Task 1: Database Models and Migration

**Files:**
- Create: `packages/core/backend/models/help.py`
- Modify: `packages/core/backend/database.py` (import new models in `create_tables()`)
- Create: `packages/core/backend/alembic/versions/<auto>_add_help_tables.py`

- [ ] **Step 1: Write the help models file**

Create `packages/core/backend/models/help.py` with all six tables from the spec:

```python
import enum
from sqlalchemy import (
    Column, Integer, String, DateTime, Float, Boolean,
    ForeignKey, Text, JSON, CheckConstraint, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class OnboardingRole(str, enum.Enum):
    TEACHER = "teacher"
    ADMIN = "admin"


class FeedbackRating(str, enum.Enum):
    UP = "up"
    DOWN = "down"


class FeedbackStatus(str, enum.Enum):
    OPEN = "offen"
    IN_PROGRESS = "in_bearbeitung"
    DOCUMENTED = "dokumentiert"


class HelpOnboardingProgress(Base):
    __tablename__ = "help_onboarding_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)
    role = Column(String(20), nullable=False)
    current_step = Column(Integer, default=0, nullable=False)
    completed_steps = Column(JSON, default=list, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("role IN ('teacher', 'admin')", name="ck_onboarding_role"),
    )

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "role": self.role,
            "current_step": self.current_step,
            "completed_steps": self.completed_steps,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class HelpConversation(Base):
    __tablename__ = "help_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    messages = Column(JSON, default=list, nullable=False)
    route = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "messages": self.messages,
            "route": self.route,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class HelpFeedback(Base):
    __tablename__ = "help_feedback"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    rating = Column(String(10), nullable=True)
    user_role = Column(String(20), nullable=True)
    user_tier = Column(String(30), nullable=True)
    route = Column(String(255), nullable=True)
    language = Column(String(10), nullable=True)
    cluster_id = Column(Integer, nullable=True, index=True)
    status = Column(String(20), default="offen", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("rating IN ('up', 'down')", name="ck_feedback_rating"),
        CheckConstraint("status IN ('offen', 'in_bearbeitung', 'dokumentiert')", name="ck_feedback_status"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
            "confidence": self.confidence,
            "rating": self.rating,
            "user_role": self.user_role,
            "user_tier": self.user_tier,
            "route": self.route,
            "language": self.language,
            "cluster_id": self.cluster_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class HelpContextHint(Base):
    __tablename__ = "help_context_hints"

    id = Column(Integer, primary_key=True, index=True)
    route_pattern = Column(String(255), nullable=False)
    role = Column(String(20), nullable=True)
    tier = Column(String(30), nullable=True)
    hint_text_de = Column(Text, nullable=False)
    hint_text_en = Column(Text, nullable=False)
    priority = Column(Integer, default=0, nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    def to_dict(self, locale="de"):
        return {
            "id": self.id,
            "route_pattern": self.route_pattern,
            "hint_text": self.hint_text_de if locale == "de" else self.hint_text_en,
            "priority": self.priority,
        }


class HelpFaqCache(Base):
    __tablename__ = "help_faq_cache"

    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(Text, nullable=False)
    answer_de = Column(Text, nullable=False)
    answer_en = Column(Text, nullable=False)
    docs_links = Column(JSON, default=list, nullable=False)
    source_files = Column(JSON, default=list, nullable=False)
    hit_count = Column(Integer, default=0, nullable=False)
    last_used = Column(DateTime(timezone=True), nullable=True)
    stale = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "question_text": self.question_text,
            "answer_de": self.answer_de,
            "answer_en": self.answer_en,
            "docs_links": self.docs_links,
            "hit_count": self.hit_count,
            "stale": self.stale,
        }


class HelpDismissedHint(Base):
    __tablename__ = "help_dismissed_hints"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    hint_id = Column(Integer, ForeignKey("help_context_hints.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "hint_id", name="uq_dismissed_user_hint"),
    )


class HelpIndexState(Base):
    __tablename__ = "help_index_state"

    id = Column(Integer, primary_key=True, index=True)
    last_indexed_sha = Column(String(40), nullable=True)
    last_indexed_at = Column(DateTime(timezone=True), nullable=True)
    files_indexed = Column(Integer, default=0, nullable=False)
    files_deleted = Column(Integer, default=0, nullable=False)
```

- [ ] **Step 2: Register models in database.py**

In `packages/core/backend/database.py`, add the import inside `create_tables()`:

```python
from models.help import (
    HelpOnboardingProgress, HelpConversation, HelpFeedback,
    HelpContextHint, HelpFaqCache, HelpDismissedHint, HelpIndexState
)
```

- [ ] **Step 3: Generate Alembic migration**

Run:
```bash
cd packages/core/backend && alembic revision --autogenerate -m "add help tables"
```

- [ ] **Step 4: Review the generated migration**

Open the generated file in `alembic/versions/`. Verify it creates all six tables with correct column types and constraints. Add `_column_exists()` guard for idempotency following the existing pattern.

- [ ] **Step 5: Run migration locally**

Run:
```bash
cd packages/core/backend && alembic upgrade head
```
Expected: All six tables created without errors.

- [ ] **Step 6: Commit**

```bash
git add packages/core/backend/models/help.py packages/core/backend/database.py packages/core/backend/alembic/versions/
git commit -m "feat(help): add database models and migration for Smart Help Widget

Tables: help_onboarding_progress, help_conversations, help_feedback,
help_context_hints, help_faq_cache, help_dismissed_hints, help_index_state

Ref: TF-308"
```

---

### Task 2: Seed Context Hints

**Files:**
- Create: `packages/core/backend/utils/seed_help_hints.py`
- Modify: `packages/core/backend/main.py` (call seeder in lifespan)

- [ ] **Step 1: Write the seed script**

Create `packages/core/backend/utils/seed_help_hints.py`:

```python
import logging
from sqlalchemy.orm import Session
from models.help import HelpContextHint

logger = logging.getLogger(__name__)

DEFAULT_HINTS = [
    {
        "route_pattern": "/documents/upload",
        "role": "teacher",
        "hint_text_de": "Tipp: Strukturierte PDFs mit Überschriften liefern bessere Prüfungsfragen.",
        "hint_text_en": "Tip: Structured PDFs with headings produce better exam questions.",
        "priority": 10,
    },
    {
        "route_pattern": "/exam/create",
        "role": "teacher",
        "hint_text_de": "Neu hier? Wähle zuerst 3–5 Dokumente für optimale Qualität.",
        "hint_text_en": "New here? Select 3–5 documents first for optimal quality.",
        "priority": 10,
    },
    {
        "route_pattern": "/admin/users",
        "role": "admin",
        "hint_text_de": "Du kannst Benutzerrollen direkt in der Tabelle ändern.",
        "hint_text_en": "You can change user roles directly in the table.",
        "priority": 10,
    },
    {
        "route_pattern": "/prompts",
        "role": "admin",
        "hint_text_de": "Die Live-Vorschau zeigt dir, wie der Prompt mit echten Variablen aussieht.",
        "hint_text_en": "The live preview shows you how the prompt looks with real variables.",
        "priority": 10,
    },
    {
        "route_pattern": "/questions/review",
        "role": "teacher",
        "hint_text_de": "Überprüfe generierte Fragen und bewerte sie, um die Qualität zu verbessern.",
        "hint_text_en": "Review generated questions and rate them to improve quality.",
        "priority": 5,
    },
    {
        "route_pattern": "/exams/compose",
        "role": "teacher",
        "hint_text_de": "Wähle Fragen aus der Bibliothek und stelle deine Prüfung zusammen.",
        "hint_text_en": "Select questions from the library and compose your exam.",
        "priority": 5,
    },
]


def seed_help_hints(db: Session) -> None:
    existing_count = db.query(HelpContextHint).count()
    if existing_count > 0:
        logger.info(f"Help context hints already seeded ({existing_count} entries), skipping.")
        return

    for hint_data in DEFAULT_HINTS:
        hint = HelpContextHint(**hint_data, active=True)
        db.add(hint)

    db.commit()
    logger.info(f"Seeded {len(DEFAULT_HINTS)} help context hints.")
```

- [ ] **Step 2: Call seeder in main.py lifespan**

In `packages/core/backend/main.py`, inside the lifespan startup block (after existing seed calls), add:

```python
from utils.seed_help_hints import seed_help_hints
seed_help_hints(db)
```

- [ ] **Step 3: Test locally**

Start the backend, check logs for "Seeded X help context hints." Restart — should see "already seeded, skipping."

- [ ] **Step 4: Commit**

```bash
git add packages/core/backend/utils/seed_help_hints.py packages/core/backend/main.py
git commit -m "feat(help): seed default context hints for Smart Help Widget

Ref: TF-308"
```

---

### Task 3: Onboarding Steps Configuration

**Files:**
- Create: `packages/core/frontend/public/help-onboarding-steps.json`

- [ ] **Step 1: Write the onboarding steps JSON**

Create `packages/core/frontend/public/help-onboarding-steps.json`:

```json
{
  "teacher": [
    {
      "step": 0,
      "title_de": "Willkommen bei ExamCraft AI!",
      "title_en": "Welcome to ExamCraft AI!",
      "description_de": "Ich zeige dir in wenigen Schritten, wie du deine erste Prüfung erstellst.",
      "description_en": "I'll show you in a few steps how to create your first exam.",
      "route": null,
      "highlight_selector": null
    },
    {
      "step": 1,
      "title_de": "Dokument hochladen",
      "title_en": "Upload a Document",
      "description_de": "Lade dein Kursmaterial als PDF, Word oder Markdown hoch.",
      "description_en": "Upload your course material as PDF, Word, or Markdown.",
      "route": "/documents",
      "highlight_selector": "[data-testid='upload-area']"
    },
    {
      "step": 2,
      "title_de": "Dokumentenbibliothek",
      "title_en": "Document Library",
      "description_de": "Hier siehst du alle hochgeladenen Dokumente und kannst sie für Prüfungen auswählen.",
      "description_en": "Here you can see all uploaded documents and select them for exams.",
      "route": "/documents",
      "highlight_selector": "[data-testid='document-library']"
    },
    {
      "step": 3,
      "title_de": "Prüfung erstellen",
      "title_en": "Create an Exam",
      "description_de": "Gib ein Thema ein, wähle Schwierigkeitsgrad und Fragenanzahl — die KI erledigt den Rest.",
      "description_en": "Enter a topic, choose difficulty and number of questions — the AI does the rest.",
      "route": "/questions/generate",
      "highlight_selector": "[data-testid='exam-config']"
    },
    {
      "step": 4,
      "title_de": "Ergebnis reviewen und exportieren",
      "title_en": "Review and Export Results",
      "description_de": "Überprüfe die generierten Fragen, bewerte sie und exportiere deine Prüfung.",
      "description_en": "Review the generated questions, rate them, and export your exam.",
      "route": "/questions/review",
      "highlight_selector": "[data-testid='review-queue']"
    },
    {
      "step": 5,
      "title_de": "Fertig!",
      "title_en": "All Done!",
      "description_de": "Du bist startklar! Du kannst dieses Hilfe-Widget jederzeit über den Button unten rechts öffnen.",
      "description_en": "You're all set! You can open this help widget anytime via the button at the bottom right.",
      "route": null,
      "highlight_selector": null
    }
  ],
  "admin": [
    {
      "step": 0,
      "title_de": "Willkommen, Administrator!",
      "title_en": "Welcome, Administrator!",
      "description_de": "Lass uns die wichtigsten Admin-Funktionen einrichten.",
      "description_en": "Let's set up the most important admin functions.",
      "route": null,
      "highlight_selector": null
    },
    {
      "step": 1,
      "title_de": "Institution einrichten",
      "title_en": "Set Up Institution",
      "description_de": "Konfiguriere deine Bildungseinrichtung und Subscription-Tier.",
      "description_en": "Configure your educational institution and subscription tier.",
      "route": "/admin",
      "highlight_selector": "[data-testid='institution-section']"
    },
    {
      "step": 2,
      "title_de": "Benutzer verwalten",
      "title_en": "Manage Users",
      "description_de": "Lege Benutzer an und weise ihnen Rollen zu.",
      "description_en": "Create users and assign roles to them.",
      "route": "/admin",
      "highlight_selector": "[data-testid='user-management']"
    },
    {
      "step": 3,
      "title_de": "Prompt Management",
      "title_en": "Prompt Management",
      "description_de": "Verwalte die KI-Prompts für die Fragenerstellung.",
      "description_en": "Manage the AI prompts for question generation.",
      "route": "/prompts",
      "highlight_selector": null
    },
    {
      "step": 4,
      "title_de": "Monitoring",
      "title_en": "Monitoring",
      "description_de": "Überwache Nutzung, Kosten und System-Gesundheit.",
      "description_en": "Monitor usage, costs, and system health.",
      "route": "/admin",
      "highlight_selector": null
    },
    {
      "step": 5,
      "title_de": "Fertig!",
      "title_en": "All Done!",
      "description_de": "Dein System ist eingerichtet. Öffne das Hilfe-Widget jederzeit über den Button unten rechts.",
      "description_en": "Your system is set up. Open the help widget anytime via the button at the bottom right.",
      "route": null,
      "highlight_selector": null
    }
  ]
}
```

- [ ] **Step 2: Commit**

```bash
git add packages/core/frontend/public/help-onboarding-steps.json
git commit -m "feat(help): add onboarding steps configuration for teacher and admin roles

Ref: TF-308"
```

---

### Task 4: MkDocs Material Scaffold

**Files:**
- Create: `docs-site/mkdocs.yml`
- Create: `docs-site/docs/index.md`
- Create: `docs-site/docs/getting-started/quickstart.md`
- Create: `docs-site/docs/user-guide/documents.md`
- Create: `docs-site/docs/admin-guide/deployment.md`
- Create: `docs-site/docs/faq/general.md`
- Create: `.github/workflows/docs.yml`

- [ ] **Step 1: Create mkdocs.yml**

Create `docs-site/mkdocs.yml`:

```yaml
site_name: ExamCraft AI Dokumentation
site_url: https://talent-factory.github.io/examcraft/
site_description: Benutzerhandbuch und Admin-Guide für ExamCraft AI

theme:
  name: material
  language: de
  palette:
    - scheme: default
      primary: teal
      accent: teal
      toggle:
        icon: material/brightness-7
        name: Zum Dunkelmodus wechseln
    - scheme: slate
      primary: teal
      accent: teal
      toggle:
        icon: material/brightness-4
        name: Zum Hellmodus wechseln
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.indexes
    - navigation.top
    - search.suggest
    - search.highlight
    - content.tabs.link

plugins:
  - search:
      lang:
        - de
        - en
  - i18n:
      default_language: de
      languages:
        de: Deutsch
        en: English

markdown_extensions:
  - admonition
  - pymdownx.details
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true
  - attr_list
  - md_in_html
  - tables

nav:
  - Start:
      - index.md
      - getting-started/quickstart.md
      - getting-started/requirements.md
      - getting-started/registration.md
  - Benutzerhandbuch:
      - user-guide/documents.md
      - user-guide/exam-create.md
      - user-guide/rag-exam.md
      - user-guide/chatbot.md
      - user-guide/exam-export.md
      - user-guide/best-practices.md
  - Admin-Guide:
      - admin-guide/deployment.md
      - admin-guide/user-mgmt.md
      - admin-guide/institutions.md
      - admin-guide/prompts.md
      - admin-guide/subscription.md
      - admin-guide/monitoring.md
  - FAQ:
      - faq/general.md
      - faq/troubleshooting.md
  - Changelog: changelog.md
```

- [ ] **Step 2: Create placeholder docs**

Create the following files with placeholder content. Each file should have a title heading and a brief note "Inhalt folgt." / "Content follows.":

- `docs-site/docs/index.md` — Landing page with project overview
- `docs-site/docs/getting-started/quickstart.md` — "Erste Prüfung in 5 Minuten"
- `docs-site/docs/getting-started/requirements.md` — placeholder
- `docs-site/docs/getting-started/registration.md` — placeholder
- `docs-site/docs/user-guide/documents.md` — migrate content from existing `docs/USER_GUIDE.md` section "Dokumente hochladen"
- `docs-site/docs/user-guide/exam-create.md` — placeholder
- `docs-site/docs/user-guide/rag-exam.md` — placeholder
- `docs-site/docs/user-guide/chatbot.md` — placeholder
- `docs-site/docs/user-guide/exam-export.md` — placeholder
- `docs-site/docs/user-guide/best-practices.md` — placeholder
- `docs-site/docs/admin-guide/deployment.md` — placeholder
- `docs-site/docs/admin-guide/user-mgmt.md` — placeholder
- `docs-site/docs/admin-guide/institutions.md` — placeholder
- `docs-site/docs/admin-guide/prompts.md` — placeholder
- `docs-site/docs/admin-guide/subscription.md` — placeholder
- `docs-site/docs/admin-guide/monitoring.md` — placeholder
- `docs-site/docs/faq/general.md` — migrate content from existing `docs/USER_GUIDE.md` FAQ section
- `docs-site/docs/faq/troubleshooting.md` — placeholder
- `docs-site/docs/changelog.md` — link to or copy from `CHANGELOG.md`

- [ ] **Step 3: Create GitHub Actions workflow for docs**

Create `.github/workflows/docs.yml`:

```yaml
name: Deploy Docs

on:
  push:
    branches: [main]
    paths:
      - 'docs-site/**'

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - run: pip install mkdocs-material mkdocs-static-i18n
      - run: mkdocs build --config-file docs-site/mkdocs.yml
      - uses: actions/upload-pages-artifact@v3
        with:
          path: docs-site/site
      - uses: actions/deploy-pages@v4
```

- [ ] **Step 4: Test MkDocs build locally**

Run:
```bash
pip install mkdocs-material mkdocs-static-i18n && mkdocs build --config-file docs-site/mkdocs.yml
```
Expected: Build succeeds, `docs-site/site/` directory created.

- [ ] **Step 5: Commit**

```bash
git add docs-site/ .github/workflows/docs.yml
git commit -m "feat(docs): scaffold MkDocs Material docs-site with i18n support

Structure: getting-started, user-guide, admin-guide, faq
Languages: DE (default) + EN
Hosting: GitHub Pages via GitHub Actions

Ref: TF-308"
```

---

## Phase 2: Backend Help API

### Task 5: Help Status Endpoint (Health Check)

**Files:**
- Create: `packages/core/backend/api/v1/help.py`
- Modify: `packages/core/backend/main.py` (register router)

- [ ] **Step 1: Write test for status endpoint**

Create `packages/core/backend/tests/test_help_api.py`:

```python
import pytest
from unittest.mock import patch


def test_help_status_returns_available_modes(client):
    response = client.get("/api/v1/help/status")
    assert response.status_code == 200
    data = response.json()
    assert "modes" in data
    assert "onboarding" in data["modes"]
    assert "context" in data["modes"]
    assert isinstance(data["modes"]["chat"], bool)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/core/backend && pytest tests/test_help_api.py -v`
Expected: FAIL (endpoint not found)

- [ ] **Step 3: Implement help router with status endpoint**

Create `packages/core/backend/api/v1/help.py`:

```python
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from database import get_db
from utils.auth_utils import get_current_active_user
from models.auth import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/help", tags=["Help"])


class HelpStatusResponse(BaseModel):
    modes: Dict[str, bool]


@router.get("/status", response_model=HelpStatusResponse)
async def get_help_status():
    """Health check: returns which help modes are available."""
    qdrant_available = False
    try:
        from services.rag_service import rag_service
        qdrant_available = hasattr(rag_service, 'client') and rag_service.client is not None
    except Exception:
        pass

    return HelpStatusResponse(
        modes={
            "onboarding": True,
            "context": True,
            "chat": qdrant_available,
        }
    )
```

- [ ] **Step 4: Register router in main.py**

In `packages/core/backend/main.py`, add after the existing router registrations:

```python
from api.v1 import help as help_api
app.include_router(help_api.router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd packages/core/backend && pytest tests/test_help_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packages/core/backend/api/v1/help.py packages/core/backend/tests/test_help_api.py packages/core/backend/main.py
git commit -m "feat(help): add /api/v1/help/status health check endpoint

Returns available modes based on Qdrant availability.
Core mode: onboarding + context only. Full mode: all three.

Ref: TF-308"
```

---

### Task 6: Onboarding API Endpoints

**Files:**
- Modify: `packages/core/backend/api/v1/help.py`
- Modify: `packages/core/backend/tests/test_help_api.py`

- [ ] **Step 1: Write tests for onboarding endpoints**

Add to `tests/test_help_api.py`:

```python
def test_get_onboarding_status_new_user(client, auth_headers):
    response = client.get("/api/v1/help/onboarding/status", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["current_step"] == 0
    assert data["completed_steps"] == []
    assert data["completed"] is False


def test_complete_onboarding_step(client, auth_headers):
    response = client.put(
        "/api/v1/help/onboarding/step",
        json={"step": 0},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert 0 in data["completed_steps"]
    assert data["current_step"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/core/backend && pytest tests/test_help_api.py::test_get_onboarding_status_new_user -v`
Expected: FAIL

- [ ] **Step 3: Implement onboarding endpoints**

Add to `packages/core/backend/api/v1/help.py`:

```python
class OnboardingStatusResponse(BaseModel):
    role: str
    current_step: int
    completed_steps: List[int]
    completed: bool


class OnboardingStepRequest(BaseModel):
    step: int = Field(..., ge=0)


@router.get("/onboarding/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    from models.help import HelpOnboardingProgress

    progress = db.query(HelpOnboardingProgress).filter(
        HelpOnboardingProgress.user_id == current_user.id
    ).first()

    if not progress:
        role = "admin" if any(r.name == "admin" for r in current_user.roles) else "teacher"
        return OnboardingStatusResponse(
            role=role, current_step=0, completed_steps=[], completed=False
        )

    return OnboardingStatusResponse(
        role=progress.role,
        current_step=progress.current_step,
        completed_steps=progress.completed_steps or [],
        completed=progress.completed_at is not None,
    )


@router.put("/onboarding/step", response_model=OnboardingStatusResponse)
async def complete_onboarding_step(
    request: OnboardingStepRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    from models.help import HelpOnboardingProgress
    from datetime import datetime, timezone

    progress = db.query(HelpOnboardingProgress).filter(
        HelpOnboardingProgress.user_id == current_user.id
    ).first()

    role = "admin" if any(r.name == "admin" for r in current_user.roles) else "teacher"

    if not progress:
        progress = HelpOnboardingProgress(
            user_id=current_user.id,
            role=role,
            current_step=0,
            completed_steps=[],
        )
        db.add(progress)

    completed = list(progress.completed_steps or [])
    if request.step not in completed:
        completed.append(request.step)
    progress.completed_steps = completed
    progress.current_step = request.step + 1

    # Max steps loaded from onboarding config (teacher: 6, admin: 6)
    # Fallback to generous default if config unavailable
    import json, os
    max_steps = 10  # safe default
    try:
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "frontend", "public", "help-onboarding-steps.json"
        )
        if os.path.exists(config_path):
            with open(config_path) as f:
                steps_config = json.load(f)
            max_steps = len(steps_config.get(role, []))
    except Exception:
        pass
    if progress.current_step >= max_steps:
        progress.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(progress)

    return OnboardingStatusResponse(
        role=progress.role,
        current_step=progress.current_step,
        completed_steps=progress.completed_steps,
        completed=progress.completed_at is not None,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/core/backend && pytest tests/test_help_api.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/core/backend/api/v1/help.py packages/core/backend/tests/test_help_api.py
git commit -m "feat(help): add onboarding status and step completion endpoints

GET /api/v1/help/onboarding/status - get progress
PUT /api/v1/help/onboarding/step - complete a step

Ref: TF-308"
```

---

### Task 7: Context Hints Endpoint

**Files:**
- Modify: `packages/core/backend/api/v1/help.py`
- Create: `packages/core/backend/services/help_context_service.py`
- Modify: `packages/core/backend/tests/test_help_api.py`

- [ ] **Step 1: Write test**

Add to `tests/test_help_api.py`:

```python
def test_get_context_hint_returns_matching_hint(client, auth_headers, db_session):
    from models.help import HelpContextHint
    hint = HelpContextHint(
        route_pattern="/documents/upload",
        role="teacher",
        hint_text_de="Test-Hinweis",
        hint_text_en="Test hint",
        priority=10,
        active=True,
    )
    db_session.add(hint)
    db_session.commit()

    response = client.get(
        "/api/v1/help/context/documents%2Fupload",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["hint_text"] is not None


def test_get_context_hint_returns_null_when_no_match(client, auth_headers):
    response = client.get(
        "/api/v1/help/context/nonexistent%2Froute",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["hint_text"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/core/backend && pytest tests/test_help_api.py::test_get_context_hint_returns_matching_hint -v`
Expected: FAIL

- [ ] **Step 3: Implement context service**

Create `packages/core/backend/services/help_context_service.py`:

```python
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from models.help import HelpContextHint

logger = logging.getLogger(__name__)


class HelpContextService:
    def __init__(self, db: Session):
        self.db = db

    def get_hint_for_route(
        self, route: str, user_role: str, user_tier: str, locale: str = "de"
    ) -> Optional[Dict[str, Any]]:
        normalized = "/" + route.strip("/")

        hints = (
            self.db.query(HelpContextHint)
            .filter(HelpContextHint.active.is_(True))
            .order_by(HelpContextHint.priority.desc())
            .all()
        )

        for hint in hints:
            if not normalized.startswith(hint.route_pattern.rstrip("/")):
                continue
            if hint.role and hint.role != user_role:
                continue
            if hint.tier and hint.tier != user_tier:
                continue
            return hint.to_dict(locale=locale)

        return None
```

- [ ] **Step 4: Add context endpoint to router**

Add to `packages/core/backend/api/v1/help.py`:

```python
class ContextHintResponse(BaseModel):
    hint_text: Optional[str] = None
    hint_id: Optional[int] = None
    docs_link: Optional[str] = None


@router.get("/context/{route:path}", response_model=ContextHintResponse)
async def get_context_hint(
    route: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    from services.help_context_service import HelpContextService
    from services.translation_service import get_request_locale

    locale = get_request_locale(request, current_user)
    role = "admin" if any(r.name == "admin" for r in current_user.roles) else "teacher"
    tier = getattr(current_user.institution, "subscription_tier", "free") if current_user.institution else "free"

    service = HelpContextService(db)
    hint = service.get_hint_for_route(route, role, tier, locale)

    if hint:
        return ContextHintResponse(hint_text=hint["hint_text"], hint_id=hint["id"])
    return ContextHintResponse()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/core/backend && pytest tests/test_help_api.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add packages/core/backend/api/v1/help.py packages/core/backend/services/help_context_service.py packages/core/backend/tests/test_help_api.py
git commit -m "feat(help): add context hints endpoint with route/role matching

GET /api/v1/help/context/{route} - returns matching hint for route, role, tier

Ref: TF-308"
```

---

### Task 8: Help Chat Message Endpoint (RAG)

**Files:**
- Create: `packages/core/backend/services/help_service.py`
- Modify: `packages/core/backend/api/v1/help.py`
- Modify: `packages/core/backend/tests/test_help_api.py`

- [ ] **Step 1: Write test for chat message endpoint**

Add to `tests/test_help_api.py`:

```python
from unittest.mock import patch, MagicMock


def test_help_message_returns_answer(client, auth_headers):
    mock_result = {
        "answer": "Du kannst PDFs über den Upload-Tab hochladen.",
        "confidence": 0.85,
        "sources": [{"file": "documents.md", "section": "Upload"}],
        "docs_links": ["/user-guide/documents"],
    }
    with patch("services.help_service.HelpService.answer_question", return_value=mock_result):
        response = client.post(
            "/api/v1/help/message",
            json={"question": "Wie lade ich ein PDF hoch?", "route": "/documents"},
            headers=auth_headers,
        )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert data["confidence"] > 0


def test_help_message_requires_auth(client):
    response = client.post(
        "/api/v1/help/message",
        json={"question": "Test?"},
    )
    assert response.status_code in [401, 403]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/core/backend && pytest tests/test_help_api.py::test_help_message_returns_answer -v`
Expected: FAIL

- [ ] **Step 3: Implement HelpService**

Create `packages/core/backend/services/help_service.py`:

```python
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class HelpService:
    def __init__(self, db: Session):
        self.db = db

    async def answer_question(
        self,
        question: str,
        user_role: str,
        user_tier: str,
        route: str,
        conversation_history: Optional[List[Dict]] = None,
        locale: str = "de",
    ) -> Dict[str, Any]:
        # Step 1: Try FAQ cache (Fast Path)
        cached = await self._try_faq_cache(question, locale)
        if cached:
            return cached

        # Step 2: Search Qdrant docs_help collection
        chunks = await self._search_docs(question)

        if not chunks or chunks[0]["score"] < 0.3:
            return {
                "answer": self._no_answer_message(locale),
                "confidence": 0.0,
                "sources": [],
                "docs_links": [],
                "escalate": True,
            }

        # Step 3: Call Claude API with context
        result = await self._call_claude(
            question, chunks, user_role, user_tier, route, conversation_history, locale
        )

        # Step 4: If confidence low, retry with Sonnet
        if result["confidence"] < 0.6:
            result = await self._call_claude(
                question, chunks, user_role, user_tier, route,
                conversation_history, locale, model="sonnet"
            )

        result["escalate"] = result["confidence"] < 0.5
        return result

    async def _try_faq_cache(self, question: str, locale: str) -> Optional[Dict[str, Any]]:
        """Fast path: check FAQ cache for high-similarity match via embedding."""
        from models.help import HelpFaqCache
        from datetime import datetime, timezone

        # Detect question language
        detected_lang = self._detect_question_language(question)

        # Fast path only serves DE and EN; other languages go to Claude
        if detected_lang not in ("de", "en"):
            return None

        # Compute embedding for the question and search FAQ cache
        try:
            from services.rag_service import rag_service
            if not hasattr(rag_service, 'client') or rag_service.client is None:
                return None

            # Use Qdrant to find similar cached FAQ entries
            # FAQ entries are indexed in a separate "docs_faq" collection
            results = await rag_service.search_collection(
                collection_name="docs_faq",
                query=question,
                limit=1,
            )
            if not results or results[0].score < 0.92:
                return None

            faq_id = results[0].payload.get("faq_id")
            entry = self.db.query(HelpFaqCache).filter(
                HelpFaqCache.id == faq_id,
                HelpFaqCache.stale.is_(False),
            ).first()

            if not entry:
                return None

            entry.hit_count += 1
            entry.last_used = datetime.now(timezone.utc)
            self.db.commit()

            answer = entry.answer_de if detected_lang == "de" else entry.answer_en
            return {
                "answer": answer,
                "confidence": results[0].score,
                "sources": [],
                "docs_links": entry.docs_links or [],
                "escalate": False,
                "from_cache": True,
            }
        except Exception as e:
            logger.warning(f"FAQ cache lookup failed: {e}")
            return None

    def _detect_question_language(self, question: str) -> str:
        """Detect the language of the question."""
        try:
            from langdetect import detect
            return detect(question)
        except Exception:
            return "de"  # Default to German

    async def _search_docs(self, question: str) -> List[Dict[str, Any]]:
        """Search Qdrant docs_help collection."""
        try:
            from services.rag_service import rag_service
            if not hasattr(rag_service, 'client') or rag_service.client is None:
                return []

            results = await rag_service.search_collection(
                collection_name="docs_help",
                query=question,
                limit=5,
            )
            return [
                {
                    "content": r.payload.get("content_preview", ""),
                    "source_file": r.payload.get("source_file", ""),
                    "section": r.payload.get("section_title", ""),
                    "language": r.payload.get("language", "de"),
                    "score": r.score,
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Qdrant search failed: {e}")
            return []

    async def _call_claude(
        self,
        question: str,
        chunks: List[Dict],
        user_role: str,
        user_tier: str,
        route: str,
        history: Optional[List[Dict]],
        locale: str,
        model: str = "haiku",
    ) -> Dict[str, Any]:
        """Call Claude API with docs context."""
        import json

        context = "\n\n---\n\n".join(
            f"[{c['source_file']} > {c['section']}]\n{c['content']}"
            for c in chunks[:5]
        )

        system_prompt = (
            "You are ExamCraft AI's help assistant. Answer questions about using the ExamCraft application. "
            "Base your answers ONLY on the provided documentation context. "
            f"The user's role is '{user_role}', subscription tier is '{user_tier}', "
            f"and they are currently on the page '{route}'. "
            f"Always respond in the language of the user's question. "
            "Include a confidence score (0.0-1.0) based on how well the docs cover the question. "
            'Respond in JSON: {"answer": "...", "confidence": 0.X, "docs_links": ["/path"]}'
        )

        messages = []
        if history:
            for msg in history[-10:]:
                messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({
            "role": "user",
            "content": f"Documentation context:\n{context}\n\nQuestion: {question}",
        })

        try:
            from services.claude_service import claude_service
            model_id = "claude-haiku-4-5-20251001" if model == "haiku" else "claude-sonnet-4-6"

            response = await claude_service.create_message(
                model=model_id,
                system=system_prompt,
                messages=messages,
                max_tokens=1024,
            )

            import re
            text = response.content[0].text
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(), strict=False)
                return {
                    "answer": parsed.get("answer", text),
                    "confidence": float(parsed.get("confidence", 0.5)),
                    "sources": [{"file": c["source_file"], "section": c["section"]} for c in chunks[:3]],
                    "docs_links": parsed.get("docs_links", []),
                }

            return {
                "answer": text,
                "confidence": 0.5,
                "sources": [{"file": c["source_file"], "section": c["section"]} for c in chunks[:3]],
                "docs_links": [],
            }
        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            return {
                "answer": self._error_message(locale),
                "confidence": 0.0,
                "sources": [],
                "docs_links": [],
            }

    def _no_answer_message(self, locale: str) -> str:
        if locale == "de":
            return "Ich konnte leider keine passende Antwort in der Dokumentation finden. Möchtest du den Support kontaktieren?"
        return "I couldn't find a matching answer in the documentation. Would you like to contact support?"

    def _error_message(self, locale: str) -> str:
        if locale == "de":
            return "Die Anfrage hat zu lange gedauert. Bitte versuche es erneut oder besuche unsere Dokumentation."
        return "The request took too long. Please try again or visit our documentation."
```

- [ ] **Step 4: Add message endpoint to router**

Add to `packages/core/backend/api/v1/help.py`:

```python
class HelpMessageRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)
    route: str = Field(default="/")
    conversation_history: Optional[List[Dict[str, Any]]] = None


class HelpMessageResponse(BaseModel):
    answer: str
    confidence: float
    sources: List[Dict[str, Any]] = []
    docs_links: List[str] = []
    escalate: bool = False
    from_cache: bool = False


@router.post("/message", response_model=HelpMessageResponse)
async def send_help_message(
    request_body: HelpMessageRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    from services.help_service import HelpService
    from services.translation_service import get_request_locale

    locale = get_request_locale(request, current_user)
    role = "admin" if any(r.name == "admin" for r in current_user.roles) else "teacher"
    tier = getattr(current_user.institution, "subscription_tier", "free") if current_user.institution else "free"

    service = HelpService(db)
    result = await service.answer_question(
        question=request_body.question,
        user_role=role,
        user_tier=tier,
        route=request_body.route,
        conversation_history=request_body.conversation_history,
        locale=locale,
    )

    # Log to feedback if escalated
    if result.get("escalate"):
        from models.help import HelpFeedback
        feedback = HelpFeedback(
            question=request_body.question,
            answer=result["answer"],
            confidence=result["confidence"],
            user_role=role,
            user_tier=tier,
            route=request_body.route,
            language=locale,
            status="offen",
        )
        db.add(feedback)
        db.commit()

    return HelpMessageResponse(**result)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/core/backend && pytest tests/test_help_api.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add packages/core/backend/services/help_service.py packages/core/backend/api/v1/help.py packages/core/backend/tests/test_help_api.py
git commit -m "feat(help): add RAG-based chat message endpoint with two-tier cost optimization

POST /api/v1/help/message - FAQ cache fast path + Claude API fallback
Haiku for standard, Sonnet retry for low-confidence answers.
Auto-logs to feedback queue on escalation.

Ref: TF-308"
```

---

### Task 9: Feedback Endpoint

**Files:**
- Modify: `packages/core/backend/api/v1/help.py`
- Create: `packages/core/backend/services/help_feedback_service.py`
- Modify: `packages/core/backend/tests/test_help_api.py`

- [ ] **Step 1: Write test**

Add to `tests/test_help_api.py`:

```python
def test_submit_feedback(client, auth_headers):
    response = client.post(
        "/api/v1/help/feedback",
        json={
            "question": "Wie exportiere ich nach Moodle?",
            "answer": "Das geht leider noch nicht.",
            "confidence": 0.3,
            "rating": "down",
            "route": "/exam/export",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "offen"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/core/backend && pytest tests/test_help_api.py::test_submit_feedback -v`
Expected: FAIL

- [ ] **Step 3: Implement feedback service**

Create `packages/core/backend/services/help_feedback_service.py`:

```python
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.help import HelpFeedback

logger = logging.getLogger(__name__)


class HelpFeedbackService:
    def __init__(self, db: Session):
        self.db = db

    def submit_feedback(
        self,
        question: str,
        answer: Optional[str],
        confidence: Optional[float],
        rating: str,
        user_role: str,
        user_tier: str,
        route: str,
        language: str = "de",
    ) -> HelpFeedback:
        feedback = HelpFeedback(
            question=question,
            answer=answer,
            confidence=confidence,
            rating=rating,
            user_role=user_role,
            user_tier=user_tier,
            route=route,
            language=language,
            status="offen",
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    def get_feedback_queue(
        self, status: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        query = self.db.query(HelpFeedback)
        if status:
            query = query.filter(HelpFeedback.status == status)
        query = query.order_by(HelpFeedback.created_at.desc())
        items = query.offset(offset).limit(limit).all()
        return [item.to_dict() for item in items]

    def update_feedback_status(self, feedback_id: int, status: str, docs_link: Optional[str] = None) -> Optional[HelpFeedback]:
        feedback = self.db.query(HelpFeedback).filter(HelpFeedback.id == feedback_id).first()
        if not feedback:
            return None
        feedback.status = status
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    def get_metrics(self) -> Dict[str, Any]:
        total = self.db.query(HelpFeedback).count()
        positive = self.db.query(HelpFeedback).filter(HelpFeedback.rating == "up").count()
        open_count = self.db.query(HelpFeedback).filter(HelpFeedback.status == "offen").count()
        avg_confidence = self.db.query(func.avg(HelpFeedback.confidence)).scalar() or 0

        return {
            "total_questions": total,
            "positive_feedback_pct": round((positive / total * 100) if total > 0 else 0, 1),
            "open_feedback_count": open_count,
            "avg_confidence": round(float(avg_confidence), 2),
        }
```

- [ ] **Step 4: Add feedback endpoint to router**

Add to `packages/core/backend/api/v1/help.py`:

```python
class FeedbackRequest(BaseModel):
    question: str
    answer: Optional[str] = None
    confidence: Optional[float] = None
    rating: str = Field(..., pattern="^(up|down)$")
    route: str = Field(default="/")


class FeedbackResponse(BaseModel):
    id: int
    status: str


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request_body: FeedbackRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    from services.help_feedback_service import HelpFeedbackService
    from services.translation_service import get_request_locale

    locale = get_request_locale(request, current_user)
    role = "admin" if any(r.name == "admin" for r in current_user.roles) else "teacher"
    tier = getattr(current_user.institution, "subscription_tier", "free") if current_user.institution else "free"

    service = HelpFeedbackService(db)
    feedback = service.submit_feedback(
        question=request_body.question,
        answer=request_body.answer,
        confidence=request_body.confidence,
        rating=request_body.rating,
        user_role=role,
        user_tier=tier,
        route=request_body.route,
        language=locale,
    )

    return FeedbackResponse(id=feedback.id, status=feedback.status)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/core/backend && pytest tests/test_help_api.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add packages/core/backend/services/help_feedback_service.py packages/core/backend/api/v1/help.py packages/core/backend/tests/test_help_api.py
git commit -m "feat(help): add feedback submission endpoint and service

POST /api/v1/help/feedback - submit thumbs up/down with question context
HelpFeedbackService with queue, metrics, and status management.

Ref: TF-308"
```

---

### Task 10: Admin Feedback Queue and Metrics Endpoints

**Files:**
- Modify: `packages/core/backend/api/v1/help.py`
- Modify: `packages/core/backend/tests/test_help_api.py`

- [ ] **Step 1: Write tests for admin endpoints**

Add to `tests/test_help_api.py`:

```python
def test_admin_feedback_queue(client, admin_auth_headers, db_session):
    from models.help import HelpFeedback
    fb = HelpFeedback(question="Test?", rating="down", status="offen")
    db_session.add(fb)
    db_session.commit()

    response = client.get("/api/v1/help/admin/feedback-queue", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1


def test_admin_feedback_queue_requires_admin(client, auth_headers):
    response = client.get("/api/v1/help/admin/feedback-queue", headers=auth_headers)
    assert response.status_code == 403


def test_admin_metrics(client, admin_auth_headers):
    response = client.get("/api/v1/help/admin/metrics", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_questions" in data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/core/backend && pytest tests/test_help_api.py::test_admin_feedback_queue -v`
Expected: FAIL

- [ ] **Step 3: Implement admin endpoints**

Add to `packages/core/backend/api/v1/help.py`:

```python
from utils.auth_utils import require_permission


class FeedbackQueueResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int


class FeedbackUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(offen|in_bearbeitung|dokumentiert)$")


class MetricsResponse(BaseModel):
    total_questions: int
    positive_feedback_pct: float
    open_feedback_count: int
    avg_confidence: float


@router.get("/admin/feedback-queue", response_model=FeedbackQueueResponse)
async def get_feedback_queue(
    status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if not any(r.name == "admin" for r in current_user.roles):
        raise HTTPException(status_code=403, detail="Admin access required")

    from services.help_feedback_service import HelpFeedbackService
    service = HelpFeedbackService(db)
    items = service.get_feedback_queue(status=status, limit=limit, offset=offset)

    from models.help import HelpFeedback
    total = db.query(HelpFeedback).count()

    return FeedbackQueueResponse(items=items, total=total)


@router.put("/admin/feedback/{feedback_id}")
async def update_feedback(
    feedback_id: int,
    request_body: FeedbackUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if not any(r.name == "admin" for r in current_user.roles):
        raise HTTPException(status_code=403, detail="Admin access required")

    from services.help_feedback_service import HelpFeedbackService
    service = HelpFeedbackService(db)
    result = service.update_feedback_status(feedback_id, request_body.status)
    if not result:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return result.to_dict()


@router.get("/admin/metrics", response_model=MetricsResponse)
async def get_metrics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if not any(r.name == "admin" for r in current_user.roles):
        raise HTTPException(status_code=403, detail="Admin access required")

    from services.help_feedback_service import HelpFeedbackService
    service = HelpFeedbackService(db)
    return MetricsResponse(**service.get_metrics())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/core/backend && pytest tests/test_help_api.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/core/backend/api/v1/help.py packages/core/backend/tests/test_help_api.py
git commit -m "feat(help): add admin feedback queue and metrics endpoints

GET /api/v1/help/admin/feedback-queue - list feedback with filters
PUT /api/v1/help/admin/feedback/{id} - update status
GET /api/v1/help/admin/metrics - dashboard metrics
All admin endpoints require admin role.

Ref: TF-308"
```

---

### Task 11: Docs Indexer Service

**Files:**
- Create: `packages/core/backend/services/docs_indexer_service.py`
- Create: `packages/core/backend/tests/test_docs_indexer.py`

- [ ] **Step 1: Write test**

Create `packages/core/backend/tests/test_docs_indexer.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from services.docs_indexer_service import DocsIndexerService


def test_parse_markdown_into_chunks():
    service = DocsIndexerService.__new__(DocsIndexerService)
    content = "# Title\n\nFirst paragraph.\n\n## Section 2\n\nSecond paragraph."
    chunks = service._parse_markdown(content, "test.md", "de")

    assert len(chunks) >= 2
    assert chunks[0]["section_title"] == "Title"
    assert "First paragraph" in chunks[0]["content"]


def test_detect_language_from_filename():
    service = DocsIndexerService.__new__(DocsIndexerService)
    assert service._detect_language("docs.en.md") == "en"
    assert service._detect_language("docs.md") == "de"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/core/backend && pytest tests/test_docs_indexer.py -v`
Expected: FAIL

- [ ] **Step 3: Implement DocsIndexerService**

Create `packages/core/backend/services/docs_indexer_service.py`:

```python
import logging
import os
import re
import subprocess
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

DOCS_SITE_PATH = os.environ.get("DOCS_SITE_PATH", "docs-site/docs")


class DocsIndexerService:
    def __init__(self, db: Session):
        self.db = db

    def run_index(self, full_scan: bool = False) -> Dict[str, int]:
        from models.help import HelpIndexState

        state = self.db.query(HelpIndexState).first()
        if not state:
            state = HelpIndexState()
            self.db.add(state)
            self.db.commit()
            full_scan = True

        if not full_scan and state.last_indexed_sha:
            changed, deleted = self._get_changed_files(state.last_indexed_sha)
        else:
            changed = self._get_all_md_files()
            deleted = []

        indexed = 0
        for filepath in changed:
            self._index_file(filepath)
            indexed += 1

        deleted_count = 0
        for filepath in deleted:
            self._remove_file_from_index(filepath)
            deleted_count += 1

        current_sha = self._get_current_sha()
        state.last_indexed_sha = current_sha
        state.last_indexed_at = datetime.now(timezone.utc)
        state.files_indexed = indexed
        state.files_deleted = deleted_count
        self.db.commit()

        self._invalidate_stale_faq_cache(changed + deleted)

        logger.info(f"Indexing complete: {indexed} indexed, {deleted_count} deleted")
        return {"indexed": indexed, "deleted": deleted_count}

    def _get_all_md_files(self) -> List[str]:
        md_files = []
        for root, _, files in os.walk(DOCS_SITE_PATH):
            for f in files:
                if f.endswith(".md"):
                    md_files.append(os.path.join(root, f))
        return md_files

    def _get_changed_files(self, last_sha: str) -> tuple:
        try:
            result = subprocess.run(
                ["git", "diff", "--name-status", f"{last_sha}..HEAD", "--", DOCS_SITE_PATH],
                capture_output=True, text=True, check=True,
            )
            changed, deleted = [], []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("\t")
                status, filepath = parts[0], parts[-1]
                if status.startswith("D"):
                    deleted.append(filepath)
                else:
                    changed.append(filepath)
            return changed, deleted
        except subprocess.CalledProcessError:
            logger.warning("Git diff failed, falling back to full scan")
            return self._get_all_md_files(), []

    def _get_current_sha(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def _parse_markdown(self, content: str, filepath: str, language: str) -> List[Dict[str, Any]]:
        chunks = []
        current_section = os.path.basename(filepath).replace(".md", "").replace(".en", "")
        current_content = []

        for line in content.split("\n"):
            heading_match = re.match(r'^(#{1,3})\s+(.+)', line)
            if heading_match:
                if current_content:
                    text = "\n".join(current_content).strip()
                    if len(text) > 20:
                        chunks.append({
                            "source_file": filepath,
                            "section_title": current_section,
                            "content": text[:2000],
                            "language": language,
                        })
                current_section = heading_match.group(2)
                current_content = []
            else:
                current_content.append(line)

        if current_content:
            text = "\n".join(current_content).strip()
            if len(text) > 20:
                chunks.append({
                    "source_file": filepath,
                    "section_title": current_section,
                    "content": text[:2000],
                    "language": language,
                })

        return chunks

    def _detect_language(self, filepath: str) -> str:
        if ".en." in os.path.basename(filepath):
            return "en"
        return "de"

    def _index_file(self, filepath: str) -> None:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            logger.warning(f"File not found: {filepath}")
            return

        language = self._detect_language(filepath)
        chunks = self._parse_markdown(content, filepath, language)

        self._remove_file_from_index(filepath)

        try:
            from services.rag_service import rag_service
            for chunk in chunks:
                rag_service.index_document(
                    collection_name="docs_help",
                    content=chunk["content"],
                    payload={
                        "source_file": chunk["source_file"],
                        "section_title": chunk["section_title"],
                        "language": chunk["language"],
                        "content_preview": chunk["content"][:500],
                    },
                )
        except Exception as e:
            logger.error(f"Failed to index {filepath}: {e}")

    def _remove_file_from_index(self, filepath: str) -> None:
        try:
            from services.rag_service import rag_service
            rag_service.delete_by_payload(
                collection_name="docs_help",
                key="source_file",
                value=filepath,
            )
        except Exception as e:
            logger.error(f"Failed to remove {filepath} from index: {e}")

    def _invalidate_stale_faq_cache(self, changed_files: List[str]) -> None:
        if not changed_files:
            return
        from models.help import HelpFaqCache
        entries = self.db.query(HelpFaqCache).filter(
            HelpFaqCache.stale.is_(False)
        ).all()
        for entry in entries:
            if any(f in (entry.source_files or []) for f in changed_files):
                entry.stale = True
        self.db.commit()
```

- [ ] **Step 4: Add admin reindex endpoint**

Add to `packages/core/backend/api/v1/help.py`:

```python
@router.post("/admin/reindex")
async def trigger_reindex(
    full_scan: bool = Query(default=False, description="Force full re-scan instead of git-diff"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if not any(r.name == "admin" for r in current_user.roles):
        raise HTTPException(status_code=403, detail="Admin access required")

    from services.docs_indexer_service import DocsIndexerService
    service = DocsIndexerService(db)
    result = service.run_index(full_scan=full_scan)
    return {"status": "completed", **result}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/core/backend && pytest tests/test_docs_indexer.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add packages/core/backend/services/docs_indexer_service.py packages/core/backend/tests/test_docs_indexer.py packages/core/backend/api/v1/help.py
git commit -m "feat(help): add docs indexer service with git-diff-based smart reindexing

Markdown parsing, Qdrant indexing, FAQ cache invalidation.
POST /api/v1/help/admin/reindex for manual triggering.

Ref: TF-308"
```

---

## Phase 3: Frontend Widget

### Task 12: Help Service (Frontend API Client)

**Files:**
- Create: `packages/core/frontend/src/services/helpService.ts`

- [ ] **Step 1: Create the help service**

Create `packages/core/frontend/src/services/helpService.ts`:

```typescript
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface HelpStatus {
  modes: { onboarding: boolean; context: boolean; chat: boolean };
}

export interface OnboardingStatus {
  role: string;
  current_step: number;
  completed_steps: number[];
  completed: boolean;
}

export interface ContextHint {
  hint_text: string | null;
  hint_id: number | null;
}

export interface HelpMessage {
  answer: string;
  confidence: number;
  sources: Array<{ file: string; section: string }>;
  docs_links: string[];
  escalate: boolean;
  from_cache: boolean;
}

export interface FeedbackRequest {
  question: string;
  answer?: string;
  confidence?: number;
  rating: 'up' | 'down';
  route: string;
}

class HelpService {
  private getHeaders(token: string): HeadersInit {
    return {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    };
  }

  async getStatus(): Promise<HelpStatus> {
    const response = await fetch(`${API_BASE_URL}/api/v1/help/status`);
    if (!response.ok) throw new Error('Failed to fetch help status');
    return response.json();
  }

  async getOnboardingStatus(token: string): Promise<OnboardingStatus> {
    const response = await fetch(`${API_BASE_URL}/api/v1/help/onboarding/status`, {
      headers: this.getHeaders(token),
    });
    if (!response.ok) throw new Error('Failed to fetch onboarding status');
    return response.json();
  }

  async completeOnboardingStep(token: string, step: number): Promise<OnboardingStatus> {
    const response = await fetch(`${API_BASE_URL}/api/v1/help/onboarding/step`, {
      method: 'PUT',
      headers: this.getHeaders(token),
      body: JSON.stringify({ step }),
    });
    if (!response.ok) throw new Error('Failed to complete onboarding step');
    return response.json();
  }

  async getContextHint(token: string, route: string): Promise<ContextHint> {
    const encoded = encodeURIComponent(route.replace(/^\//, ''));
    const response = await fetch(`${API_BASE_URL}/api/v1/help/context/${encoded}`, {
      headers: this.getHeaders(token),
    });
    if (!response.ok) throw new Error('Failed to fetch context hint');
    return response.json();
  }

  async sendMessage(
    token: string,
    question: string,
    route: string,
    conversationHistory?: Array<{ role: string; content: string }>
  ): Promise<HelpMessage> {
    const response = await fetch(`${API_BASE_URL}/api/v1/help/message`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify({ question, route, conversation_history: conversationHistory }),
    });
    if (!response.ok) throw new Error('Failed to send help message');
    return response.json();
  }

  async submitFeedback(token: string, feedback: FeedbackRequest): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/v1/help/feedback`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify(feedback),
    });
    if (!response.ok) throw new Error('Failed to submit feedback');
  }
}

export const helpService = new HelpService();
```

- [ ] **Step 2: Commit**

```bash
git add packages/core/frontend/src/services/helpService.ts
git commit -m "feat(help): add frontend HelpService API client

Ref: TF-308"
```

---

### Task 13: useHelpContext Hook

**Files:**
- Create: `packages/core/frontend/src/components/help/useHelpContext.ts`

- [ ] **Step 1: Create the hook**

Create `packages/core/frontend/src/components/help/useHelpContext.ts`:

```typescript
import { useState, useEffect, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { helpService, HelpStatus, OnboardingStatus, ContextHint } from '../../services/helpService';

export function useHelpContext() {
  const { user, accessToken, hasRole } = useAuth();
  const location = useLocation();
  const { i18n } = useTranslation();

  const [helpStatus, setHelpStatus] = useState<HelpStatus | null>(null);
  const [onboardingStatus, setOnboardingStatus] = useState<OnboardingStatus | null>(null);
  const [contextHint, setContextHint] = useState<ContextHint | null>(null);
  const [loading, setLoading] = useState(true);

  const role = hasRole('admin') ? 'admin' : 'teacher';
  const tier = user?.institution?.subscription_tier || 'free';
  const locale = i18n.language?.substring(0, 2) || 'de';
  const route = location.pathname;

  // Fetch help system status
  useEffect(() => {
    helpService.getStatus().then(setHelpStatus).catch(() => {
      setHelpStatus({ modes: { onboarding: true, context: true, chat: false } });
    });
  }, []);

  // Fetch onboarding status
  useEffect(() => {
    if (!accessToken) return;
    helpService
      .getOnboardingStatus(accessToken)
      .then(setOnboardingStatus)
      .catch(() => setOnboardingStatus(null))
      .finally(() => setLoading(false));
  }, [accessToken]);

  // Fetch context hint when route changes
  useEffect(() => {
    if (!accessToken || !route) return;
    helpService
      .getContextHint(accessToken, route)
      .then(setContextHint)
      .catch(() => setContextHint(null));
  }, [accessToken, route]);

  const completeStep = useCallback(
    async (step: number) => {
      if (!accessToken) return;
      const updated = await helpService.completeOnboardingStep(accessToken, step);
      setOnboardingStatus(updated);
    },
    [accessToken]
  );

  return {
    role,
    tier,
    locale,
    route,
    helpStatus,
    onboardingStatus,
    contextHint,
    loading,
    completeStep,
    chatAvailable: helpStatus?.modes.chat ?? false,
    showOnboarding: onboardingStatus !== null && !onboardingStatus.completed,
    hasContextHint: contextHint?.hint_text !== null && contextHint?.hint_text !== undefined,
  };
}
```

- [ ] **Step 2: Commit**

```bash
git add packages/core/frontend/src/components/help/useHelpContext.ts
git commit -m "feat(help): add useHelpContext hook for route, role, and status awareness

Ref: TF-308"
```

---

### Task 14: HelpWidget Component (Container + Floating Button)

**Files:**
- Create: `packages/core/frontend/src/components/help/HelpWidget.tsx`
- Modify: `packages/core/frontend/src/AppWithAuth.tsx` (add widget)
- Add i18n keys to translation files

- [ ] **Step 1: Create HelpWidget component**

Create `packages/core/frontend/src/components/help/HelpWidget.tsx`:

```tsx
import React, { useState, useEffect, useCallback } from 'react';
import { Paper, IconButton, Badge, Slide, Box, Typography } from '@mui/material';
import { HelpOutline, Close } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useHelpContext } from './useHelpContext';
import HelpOnboarding from './HelpOnboarding';
import HelpContextHint from './HelpContextHint';
import HelpChat from './HelpChat';

const HelpWidget: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [contextHintDismissed, setContextHintDismissed] = useState(false);
  const { t } = useTranslation();
  const {
    showOnboarding,
    hasContextHint,
    contextHint,
    onboardingStatus,
    chatAvailable,
    completeStep,
    role,
    route,
  } = useHelpContext();

  // Auto-open for onboarding
  useEffect(() => {
    if (showOnboarding && onboardingStatus?.current_step === 0) {
      setOpen(true);
    }
  }, [showOnboarding, onboardingStatus?.current_step]);

  // Keyboard shortcut: Ctrl+/ or Cmd+/
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        const active = document.activeElement;
        if (active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || (active as HTMLElement).isContentEditable)) {
          return;
        }
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const toggle = useCallback(() => setOpen((prev) => !prev), []);

  return (
    <>
      {/* Floating Button */}
      <Box sx={{ position: 'fixed', bottom: 24, right: 24, zIndex: 1400 }}>
        <IconButton
          onClick={toggle}
          sx={{
            width: 56,
            height: 56,
            backgroundColor: 'primary.main',
            color: 'white',
            boxShadow: 3,
            '&:hover': { backgroundColor: 'primary.dark' },
          }}
        >
          <Badge
            variant="dot"
            color="error"
            invisible={!hasContextHint || open}
          >
            <HelpOutline />
          </Badge>
        </IconButton>
      </Box>

      {/* Slide-in Panel */}
      <Slide direction="left" in={open} mountOnEnter unmountOnExit>
        <Paper
          elevation={8}
          sx={{
            position: 'fixed',
            top: 0,
            right: 0,
            bottom: 0,
            width: { xs: '100vw', sm: 380 },
            zIndex: 1300,
            display: 'flex',
            flexDirection: 'column',
            borderRadius: 0,
          }}
        >
          {/* Header */}
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              p: 2,
              borderBottom: 1,
              borderColor: 'divider',
              backgroundColor: 'primary.main',
              color: 'white',
            }}
          >
            <Typography variant="h6">{t('help.title', 'Hilfe')}</Typography>
            <IconButton onClick={toggle} sx={{ color: 'white' }}>
              <Close />
            </IconButton>
          </Box>

          {/* Content */}
          <Box sx={{ flex: 1, overflow: 'auto' }}>
            {showOnboarding && onboardingStatus ? (
              <HelpOnboarding
                status={onboardingStatus}
                role={role}
                onCompleteStep={completeStep}
              />
            ) : hasContextHint && contextHint && !contextHintDismissed ? (
              <HelpContextHint
                hint={contextHint}
                onDismiss={() => setContextHintDismissed(true)}
                onDismissPermanently={() => setContextHintDismissed(true)}
              />
            ) : null}

            {chatAvailable && (
              <HelpChat route={route} />
            )}

            {!chatAvailable && !showOnboarding && (
              <Box sx={{ p: 3, textAlign: 'center' }}>
                <Typography color="text.secondary">
                  {t('help.chatUnavailable', 'Der Hilfe-Chat ist derzeit nicht verfügbar.')}
                </Typography>
              </Box>
            )}
          </Box>
        </Paper>
      </Slide>
    </>
  );
};

export default HelpWidget;
```

- [ ] **Step 2: Add HelpWidget to AppWithAuth**

In `packages/core/frontend/src/AppWithAuth.tsx`, inside the authenticated layout (next to where `GenerationTasksBar` is rendered), add:

```tsx
import HelpWidget from './components/help/HelpWidget';

// Inside the JSX, after GenerationTasksBar:
<HelpWidget />
```

- [ ] **Step 3: Add i18n keys**

Add to `packages/core/frontend/src/locales/de/translation.json`:

```json
{
  "help": {
    "title": "Hilfe",
    "chatUnavailable": "Der Hilfe-Chat ist derzeit nicht verfügbar.",
    "chatPlaceholder": "Stelle eine Frage...",
    "send": "Senden",
    "newConversation": "Neue Konversation",
    "onboarding": {
      "skip": "Überspringen",
      "next": "Weiter",
      "finish": "Fertig",
      "resume": "Später fortsetzen"
    },
    "context": {
      "understood": "Verstanden",
      "learnMore": "Mehr erfahren",
      "dontShowAgain": "Nicht mehr anzeigen"
    },
    "feedback": {
      "helpful": "War das hilfreich?",
      "thanks": "Danke für dein Feedback!"
    }
  }
}
```

Add the equivalent English keys to `packages/core/frontend/src/locales/en/translation.json`.

- [ ] **Step 4: Commit**

```bash
git add packages/core/frontend/src/components/help/HelpWidget.tsx packages/core/frontend/src/AppWithAuth.tsx packages/core/frontend/src/locales/
git commit -m "feat(help): add HelpWidget floating button with slide-in panel

Integrated at AppWithAuth level. Keyboard shortcut Ctrl+/.
Supports three modes: onboarding, context hints, chat.

Ref: TF-308"
```

---

### Task 15: HelpOnboarding Component

**Files:**
- Create: `packages/core/frontend/src/components/help/HelpOnboarding.tsx`
- Create: `packages/core/frontend/src/components/help/SpotlightOverlay.tsx`

- [ ] **Step 1: Create SpotlightOverlay**

Create `packages/core/frontend/src/components/help/SpotlightOverlay.tsx`:

```tsx
import React, { useEffect, useState } from 'react';
import { Box } from '@mui/material';

interface SpotlightOverlayProps {
  selector: string | null;
}

const SpotlightOverlay: React.FC<SpotlightOverlayProps> = ({ selector }) => {
  const [rect, setRect] = useState<DOMRect | null>(null);

  useEffect(() => {
    if (!selector) { setRect(null); return; }
    const el = document.querySelector(selector);
    if (el) {
      setRect(el.getBoundingClientRect());
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    } else {
      setRect(null);
    }
  }, [selector]);

  if (!rect) return null;

  return (
    <Box
      sx={{
        position: 'fixed',
        top: rect.top - 8,
        left: rect.left - 8,
        width: rect.width + 16,
        height: rect.height + 16,
        border: '3px solid',
        borderColor: 'primary.main',
        borderRadius: 2,
        zIndex: 1200,
        pointerEvents: 'none',
        boxShadow: '0 0 0 9999px rgba(0,0,0,0.3)',
        transition: 'all 0.3s ease',
      }}
    />
  );
};

export default SpotlightOverlay;
```

- [ ] **Step 2: Create HelpOnboarding component**

Create `packages/core/frontend/src/components/help/HelpOnboarding.tsx`:

```tsx
import React, { useState, useEffect } from 'react';
import { Box, Typography, Button, Stepper, Step, StepLabel } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { OnboardingStatus } from '../../services/helpService';
import SpotlightOverlay from './SpotlightOverlay';

interface OnboardingStep {
  step: number;
  title_de: string;
  title_en: string;
  description_de: string;
  description_en: string;
  route: string | null;
  highlight_selector: string | null;
}

interface HelpOnboardingProps {
  status: OnboardingStatus;
  role: string;
  onCompleteStep: (step: number) => Promise<void>;
}

const HelpOnboarding: React.FC<HelpOnboardingProps> = ({ status, role, onCompleteStep }) => {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [steps, setSteps] = useState<OnboardingStep[]>([]);
  const locale = i18n.language?.substring(0, 2) || 'de';

  useEffect(() => {
    fetch('/help-onboarding-steps.json')
      .then((res) => res.json())
      .then((data) => setSteps(data[role] || []))
      .catch(() => setSteps([]));
  }, [role]);

  const currentStep = steps[status.current_step];
  if (!currentStep || steps.length === 0) return null;

  const title = locale === 'en' ? currentStep.title_en : currentStep.title_de;
  const description = locale === 'en' ? currentStep.description_en : currentStep.description_de;

  const handleNext = async () => {
    if (currentStep.route) {
      navigate(currentStep.route);
    }
    await onCompleteStep(status.current_step);
  };

  return (
    <>
      <SpotlightOverlay selector={currentStep.highlight_selector} />
      <Box sx={{ p: 3 }}>
        <Stepper activeStep={status.current_step} alternativeLabel sx={{ mb: 3 }}>
          {steps.map((s) => (
            <Step key={s.step} completed={status.completed_steps.includes(s.step)}>
              <StepLabel />
            </Step>
          ))}
        </Stepper>

        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          {description}
        </Typography>

        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button variant="contained" onClick={handleNext}>
            {status.current_step < steps.length - 1
              ? t('help.onboarding.next')
              : t('help.onboarding.finish')}
          </Button>
          {status.current_step < steps.length - 1 && (
            <Button variant="text" onClick={() => onCompleteStep(steps.length - 1)}>
              {t('help.onboarding.skip')}
            </Button>
          )}
        </Box>
      </Box>
    </>
  );
};

export default HelpOnboarding;
```

- [ ] **Step 3: Commit**

```bash
git add packages/core/frontend/src/components/help/HelpOnboarding.tsx packages/core/frontend/src/components/help/SpotlightOverlay.tsx
git commit -m "feat(help): add onboarding flow with spotlight overlay and step navigation

Role-based steps loaded from JSON config. Stepper UI with progress.
SpotlightOverlay highlights relevant UI elements.

Ref: TF-308"
```

---

### Task 16: HelpContextHint Component

**Files:**
- Create: `packages/core/frontend/src/components/help/HelpContextHint.tsx`

- [ ] **Step 1: Create component**

Create `packages/core/frontend/src/components/help/HelpContextHint.tsx`:

```tsx
import React from 'react';
import { Box, Typography, Button, Alert, Link } from '@mui/material';
import { LightbulbOutlined } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { helpService, ContextHint } from '../../services/helpService';

interface HelpContextHintProps {
  hint: ContextHint;
  onDismiss: () => void;
  onDismissPermanently: () => void;
}

const HelpContextHint: React.FC<HelpContextHintProps> = ({ hint, onDismiss, onDismissPermanently }) => {
  const { t } = useTranslation();
  const { accessToken } = useAuth();

  if (!hint.hint_text) return null;

  const handleDismissPermanently = async () => {
    if (accessToken && hint.hint_id) {
      await helpService.dismissHint(accessToken, hint.hint_id);
    }
    onDismissPermanently();
  };

  return (
    <Box sx={{ p: 2 }}>
      <Alert icon={<LightbulbOutlined />} severity="info" sx={{ mb: 2 }}>
        <Typography variant="body2" sx={{ mb: 1 }}>{hint.hint_text}</Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Button size="small" variant="outlined" onClick={onDismiss}>
            {t('help.context.understood')}
          </Button>
          {hint.docs_link && (
            <Button size="small" component={Link} href={hint.docs_link} target="_blank">
              {t('help.context.learnMore')}
            </Button>
          )}
          <Button size="small" color="inherit" onClick={handleDismissPermanently}>
            {t('help.context.dontShowAgain')}
          </Button>
        </Box>
      </Alert>
    </Box>
  );
};

export default HelpContextHint;
```

Note: The `helpService.dismissHint()` method must be added to `helpService.ts` (see Task 12). It calls `POST /api/v1/help/context/dismiss` with `{ hint_id }`. The backend stores the dismissal in `help_dismissed_hints` and the `HelpContextService.get_hint_for_route()` must exclude dismissed hints for the current user.

- [ ] **Step 2: Commit**

```bash
git add packages/core/frontend/src/components/help/HelpContextHint.tsx
git commit -m "feat(help): add context hint component with dismiss action

Ref: TF-308"
```

---

### Task 17: HelpChat Component

**Files:**
- Create: `packages/core/frontend/src/components/help/HelpChat.tsx`
- Create: `packages/core/frontend/src/components/help/HelpMessage.tsx`
- Create: `packages/core/frontend/src/components/help/HelpFeedback.tsx`

- [ ] **Step 1: Create HelpFeedback component**

Create `packages/core/frontend/src/components/help/HelpFeedback.tsx`:

```tsx
import React, { useState } from 'react';
import { Box, IconButton, Typography } from '@mui/material';
import { ThumbUp, ThumbDown, ThumbUpOutlined, ThumbDownOutlined } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { helpService } from '../../services/helpService';

interface HelpFeedbackProps {
  question: string;
  answer: string;
  confidence: number;
  route: string;
}

const HelpFeedback: React.FC<HelpFeedbackProps> = ({ question, answer, confidence, route }) => {
  const { t } = useTranslation();
  const { accessToken } = useAuth();
  const [submitted, setSubmitted] = useState<'up' | 'down' | null>(null);

  const handleFeedback = async (rating: 'up' | 'down') => {
    if (!accessToken || submitted) return;
    setSubmitted(rating);
    await helpService.submitFeedback(accessToken, {
      question,
      answer,
      confidence,
      rating,
      route,
    });
  };

  if (submitted) {
    return (
      <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
        {t('help.feedback.thanks')}
      </Typography>
    );
  }

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
      <Typography variant="caption" color="text.secondary">
        {t('help.feedback.helpful')}
      </Typography>
      <IconButton size="small" onClick={() => handleFeedback('up')}>
        <ThumbUpOutlined fontSize="small" />
      </IconButton>
      <IconButton size="small" onClick={() => handleFeedback('down')}>
        <ThumbDownOutlined fontSize="small" />
      </IconButton>
    </Box>
  );
};

export default HelpFeedback;
```

- [ ] **Step 2: Create HelpMessage component**

Create `packages/core/frontend/src/components/help/HelpMessage.tsx`:

```tsx
import React from 'react';
import { Box, Typography, Chip } from '@mui/material';
import { SmartToy, Person } from '@mui/icons-material';
import HelpFeedback from './HelpFeedback';

interface HelpMessageProps {
  role: 'user' | 'assistant';
  content: string;
  confidence?: number;
  sources?: Array<{ file: string; section: string }>;
  docs_links?: string[];
  question?: string;
  route: string;
}

const HelpMessage: React.FC<HelpMessageProps> = ({
  role,
  content,
  confidence,
  sources,
  docs_links,
  question,
  route,
}) => {
  const isUser = role === 'user';

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: isUser ? 'flex-end' : 'flex-start',
        mb: 2,
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 1,
          flexDirection: isUser ? 'row-reverse' : 'row',
          maxWidth: '90%',
        }}
      >
        {isUser ? <Person fontSize="small" color="action" /> : <SmartToy fontSize="small" color="primary" />}
        <Box
          sx={{
            backgroundColor: isUser ? 'primary.50' : 'grey.100',
            borderRadius: 2,
            p: 1.5,
            maxWidth: '100%',
          }}
        >
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
            {content}
          </Typography>

          {sources && sources.length > 0 && (
            <Box sx={{ mt: 1, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
              {sources.map((s, i) => (
                <Chip key={i} label={s.section} size="small" variant="outlined" />
              ))}
            </Box>
          )}
        </Box>
      </Box>

      {!isUser && question && (
        <HelpFeedback
          question={question}
          answer={content}
          confidence={confidence || 0}
          route={route}
        />
      )}
    </Box>
  );
};

export default HelpMessage;
```

- [ ] **Step 3: Create HelpChat component**

Create `packages/core/frontend/src/components/help/HelpChat.tsx`:

```tsx
import React, { useState, useRef, useEffect } from 'react';
import { Box, TextField, IconButton, Typography, Divider, Button } from '@mui/material';
import { Send, RestartAlt } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { helpService, HelpMessage as HelpMessageType } from '../../services/helpService';
import HelpMessage from './HelpMessage';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  confidence?: number;
  sources?: Array<{ file: string; section: string }>;
  docs_links?: string[];
}

interface HelpChatProps {
  route: string;
}

const HelpChat: React.FC<HelpChatProps> = ({ route }) => {
  const { t } = useTranslation();
  const { accessToken } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || !accessToken || loading) return;

    const question = input.trim();
    setInput('');

    const userMessage: ChatMessage = { role: 'user', content: question };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const result = await helpService.sendMessage(accessToken, question, route, history);

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: result.answer,
        confidence: result.confidence,
        sources: result.sources,
        docs_links: result.docs_links,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: t('help.chatUnavailable') },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewConversation = () => {
    setMessages([]);
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Messages */}
      <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
        {messages.length === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', mt: 4 }}>
            {t('help.chatPlaceholder')}
          </Typography>
        )}
        {messages.map((msg, i) => (
          <HelpMessage
            key={i}
            role={msg.role}
            content={msg.content}
            confidence={msg.confidence}
            sources={msg.sources}
            docs_links={msg.docs_links}
            question={i > 0 ? messages[i - 1]?.content : undefined}
            route={route}
          />
        ))}
        {loading && (
          <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
            ...
          </Typography>
        )}
        <div ref={messagesEndRef} />
      </Box>

      <Divider />

      {/* New conversation button */}
      {messages.length > 0 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 0.5 }}>
          <Button size="small" startIcon={<RestartAlt />} onClick={handleNewConversation}>
            {t('help.newConversation')}
          </Button>
        </Box>
      )}

      {/* Input */}
      <Box sx={{ display: 'flex', alignItems: 'center', p: 1.5, gap: 1 }}>
        <TextField
          fullWidth
          size="small"
          placeholder={t('help.chatPlaceholder')}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          multiline
          maxRows={3}
        />
        <IconButton
          onClick={handleSend}
          disabled={!input.trim() || loading}
          color="primary"
        >
          <Send />
        </IconButton>
      </Box>
    </Box>
  );
};

export default HelpChat;
```

- [ ] **Step 4: Commit**

```bash
git add packages/core/frontend/src/components/help/HelpChat.tsx packages/core/frontend/src/components/help/HelpMessage.tsx packages/core/frontend/src/components/help/HelpFeedback.tsx
git commit -m "feat(help): add chat UI with message display, feedback buttons, and conversation management

HelpChat: multi-turn conversation with Enter-to-send
HelpMessage: user/assistant bubbles with source chips
HelpFeedback: thumbs up/down with API submission

Ref: TF-308"
```

---

## Phase 4: Admin Feedback Queue UI

### Task 18: Admin Help Feedback Page

**Files:**
- Create: `packages/core/frontend/src/components/admin/HelpFeedbackQueue.tsx`
- Modify: `packages/core/frontend/src/AppWithAuth.tsx` (add route)

- [ ] **Step 1: Create HelpFeedbackQueue component**

Create `packages/core/frontend/src/components/admin/HelpFeedbackQueue.tsx`:

```tsx
import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Paper, Chip, Select, MenuItem, FormControl,
  InputLabel, Button, Card, CardContent, Grid,
} from '@mui/material';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface FeedbackItem {
  id: number;
  question: string;
  answer: string | null;
  confidence: number | null;
  rating: string | null;
  user_role: string | null;
  route: string | null;
  status: string;
  created_at: string;
}

interface Metrics {
  total_questions: number;
  positive_feedback_pct: number;
  open_feedback_count: number;
  avg_confidence: number;
}

const statusColors: Record<string, 'warning' | 'info' | 'success'> = {
  offen: 'warning',
  in_bearbeitung: 'info',
  dokumentiert: 'success',
};

const HelpFeedbackQueue: React.FC = () => {
  const { t } = useTranslation();
  const { accessToken } = useAuth();
  const [items, setItems] = useState<FeedbackItem[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');

  const headers = { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' };

  const fetchQueue = async () => {
    const params = statusFilter ? `?status=${statusFilter}` : '';
    const res = await fetch(`${API_BASE_URL}/api/v1/help/admin/feedback-queue${params}`, { headers });
    const data = await res.json();
    setItems(data.items);
  };

  const fetchMetrics = async () => {
    const res = await fetch(`${API_BASE_URL}/api/v1/help/admin/metrics`, { headers });
    setMetrics(await res.json());
  };

  useEffect(() => {
    if (accessToken) {
      fetchQueue();
      fetchMetrics();
    }
  }, [accessToken, statusFilter]);

  const updateStatus = async (id: number, newStatus: string) => {
    await fetch(`${API_BASE_URL}/api/v1/help/admin/feedback/${id}`, {
      method: 'PUT',
      headers,
      body: JSON.stringify({ status: newStatus }),
    });
    fetchQueue();
    fetchMetrics();
  };

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
      <Typography variant="h5" gutterBottom>
        Help Feedback Queue
      </Typography>

      {/* Metrics Cards */}
      {metrics && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={6} md={3}>
            <Card><CardContent>
              <Typography variant="h4">{metrics.total_questions}</Typography>
              <Typography variant="caption">Total Fragen</Typography>
            </CardContent></Card>
          </Grid>
          <Grid item xs={6} md={3}>
            <Card><CardContent>
              <Typography variant="h4">{metrics.positive_feedback_pct}%</Typography>
              <Typography variant="caption">Positives Feedback</Typography>
            </CardContent></Card>
          </Grid>
          <Grid item xs={6} md={3}>
            <Card><CardContent>
              <Typography variant="h4">{metrics.open_feedback_count}</Typography>
              <Typography variant="caption">Offen</Typography>
            </CardContent></Card>
          </Grid>
          <Grid item xs={6} md={3}>
            <Card><CardContent>
              <Typography variant="h4">{metrics.avg_confidence}</Typography>
              <Typography variant="caption">Avg. Confidence</Typography>
            </CardContent></Card>
          </Grid>
        </Grid>
      )}

      {/* Filter */}
      <FormControl size="small" sx={{ mb: 2, minWidth: 200 }}>
        <InputLabel>Status</InputLabel>
        <Select value={statusFilter} label="Status" onChange={(e) => setStatusFilter(e.target.value)}>
          <MenuItem value="">Alle</MenuItem>
          <MenuItem value="offen">Offen</MenuItem>
          <MenuItem value="in_bearbeitung">In Bearbeitung</MenuItem>
          <MenuItem value="dokumentiert">Dokumentiert</MenuItem>
        </Select>
      </FormControl>

      {/* Table */}
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Frage</TableCell>
              <TableCell>Confidence</TableCell>
              <TableCell>Rating</TableCell>
              <TableCell>Route</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Aktion</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.map((item) => (
              <TableRow key={item.id}>
                <TableCell sx={{ maxWidth: 300 }}>
                  <Typography variant="body2" noWrap>{item.question}</Typography>
                </TableCell>
                <TableCell>{item.confidence?.toFixed(2) ?? '–'}</TableCell>
                <TableCell>
                  {item.rating === 'up' ? '👍' : item.rating === 'down' ? '👎' : '–'}
                </TableCell>
                <TableCell>
                  <Chip label={item.route || '–'} size="small" variant="outlined" />
                </TableCell>
                <TableCell>
                  <Chip label={item.status} size="small" color={statusColors[item.status] || 'default'} />
                </TableCell>
                <TableCell>
                  <Select
                    size="small"
                    value={item.status}
                    onChange={(e) => updateStatus(item.id, e.target.value)}
                  >
                    <MenuItem value="offen">Offen</MenuItem>
                    <MenuItem value="in_bearbeitung">In Bearbeitung</MenuItem>
                    <MenuItem value="dokumentiert">Dokumentiert</MenuItem>
                  </Select>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default HelpFeedbackQueue;
```

- [ ] **Step 2: Add route in AppWithAuth**

In `packages/core/frontend/src/AppWithAuth.tsx`, add a new route inside the admin section:

```tsx
import HelpFeedbackQueue from './components/admin/HelpFeedbackQueue';

// Inside routes, under admin:
<Route path="/admin/help-feedback" element={
  <ProtectedRoute>
    <RoleGuard allowedRoles={['admin']}>
      <AppLayout>
        <HelpFeedbackQueue />
      </AppLayout>
    </RoleGuard>
  </ProtectedRoute>
} />
```

- [ ] **Step 3: Add navigation link in sidebar**

In the admin navigation section of the sidebar/DashboardLayout, add a link to `/admin/help-feedback` with label "Help Feedback" / "Hilfe-Feedback".

- [ ] **Step 4: Commit**

```bash
git add packages/core/frontend/src/components/admin/HelpFeedbackQueue.tsx packages/core/frontend/src/AppWithAuth.tsx
git commit -m "feat(help): add admin feedback queue page with metrics dashboard

Table view with status filter, metrics cards, inline status updates.
Route: /admin/help-feedback (admin role required)

Ref: TF-308"
```

---

## Phase 5: Integration Testing

### Task 19: End-to-End Integration Test

**Files:**
- Create: `packages/core/backend/tests/test_help_integration.py`
- Modify: `packages/core/frontend/src/components/help/__tests__/HelpWidget.test.tsx`

- [ ] **Step 1: Write backend integration test**

Create `packages/core/backend/tests/test_help_integration.py`:

```python
import pytest


def test_full_help_flow(client, auth_headers, db_session):
    """Test the complete help widget flow: status -> onboarding -> context -> message -> feedback."""

    # 1. Check status
    r = client.get("/api/v1/help/status")
    assert r.status_code == 200

    # 2. Get onboarding status (new user)
    r = client.get("/api/v1/help/onboarding/status", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["current_step"] == 0

    # 3. Complete first step
    r = client.put("/api/v1/help/onboarding/step", json={"step": 0}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["current_step"] == 1

    # 4. Get context hint
    r = client.get("/api/v1/help/context/documents%2Fupload", headers=auth_headers)
    assert r.status_code == 200

    # 5. Submit feedback
    r = client.post(
        "/api/v1/help/feedback",
        json={"question": "Test?", "rating": "up", "route": "/test"},
        headers=auth_headers,
    )
    assert r.status_code == 200
```

- [ ] **Step 2: Write frontend widget test**

Create `packages/core/frontend/src/components/help/__tests__/HelpWidget.test.tsx`:

```tsx
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { BrowserRouter } from 'react-router-dom';

// Mock dependencies
jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1, roles: [{ name: 'teacher' }], institution: { subscription_tier: 'professional' } },
    accessToken: 'test-token',
    hasRole: (role: string) => role === 'teacher',
  }),
}));

jest.mock('../../../services/helpService', () => ({
  helpService: {
    getStatus: jest.fn().mockResolvedValue({ modes: { onboarding: true, context: true, chat: true } }),
    getOnboardingStatus: jest.fn().mockResolvedValue({ role: 'teacher', current_step: 0, completed_steps: [], completed: false }),
    getContextHint: jest.fn().mockResolvedValue({ hint_text: null, hint_id: null }),
    completeOnboardingStep: jest.fn().mockResolvedValue({ current_step: 1, completed_steps: [0], completed: false }),
  },
}));

import HelpWidget from '../HelpWidget';

const theme = createTheme();

const renderWidget = () =>
  render(
    <BrowserRouter>
      <ThemeProvider theme={theme}>
        <HelpWidget />
      </ThemeProvider>
    </BrowserRouter>
  );

describe('HelpWidget', () => {
  it('renders the floating help button', () => {
    renderWidget();
    expect(screen.getByTestId('HelpOutlineIcon')).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run all tests**

Run:
```bash
cd packages/core/backend && pytest tests/test_help_api.py tests/test_help_integration.py tests/test_docs_indexer.py -v
cd packages/core/frontend && npx craco test --watchAll=false -- --testPathPattern=help
```
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add packages/core/backend/tests/test_help_integration.py packages/core/frontend/src/components/help/__tests__/
git commit -m "test(help): add integration tests for help widget flow

Backend: full flow test (status -> onboarding -> context -> feedback)
Frontend: widget rendering test

Ref: TF-308"
```

---

## Phase 6: Spec Compliance Fixes

### Task 20: Hint Dismissal API and Session Throttling

**Addresses:** Spec items "Nicht mehr anzeigen" per-hint persistence (line 146), session hint limits (line 147), and "Mehr erfahren" link (line 145).

**Files:**
- Modify: `packages/core/backend/api/v1/help.py`
- Modify: `packages/core/backend/services/help_context_service.py`
- Modify: `packages/core/frontend/src/services/helpService.ts`
- Modify: `packages/core/frontend/src/components/help/useHelpContext.ts`

- [ ] **Step 1: Add dismiss endpoint to backend**

Add to `packages/core/backend/api/v1/help.py`:

```python
class DismissHintRequest(BaseModel):
    hint_id: int


@router.post("/context/dismiss")
async def dismiss_hint(
    request_body: DismissHintRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    from models.help import HelpDismissedHint
    existing = db.query(HelpDismissedHint).filter(
        HelpDismissedHint.user_id == current_user.id,
        HelpDismissedHint.hint_id == request_body.hint_id,
    ).first()
    if not existing:
        db.add(HelpDismissedHint(user_id=current_user.id, hint_id=request_body.hint_id))
        db.commit()
    return {"status": "dismissed"}
```

- [ ] **Step 2: Update HelpContextService to exclude dismissed hints**

In `help_context_service.py`, modify `get_hint_for_route()` to accept `user_id` and filter out dismissed hints:

```python
from models.help import HelpDismissedHint

dismissed_ids = {
    d.hint_id for d in
    self.db.query(HelpDismissedHint.hint_id).filter(
        HelpDismissedHint.user_id == user_id
    ).all()
}
# In the loop, add: if hint.id in dismissed_ids: continue
```

- [ ] **Step 3: Add `dismissHint()` to frontend helpService.ts**

```typescript
async dismissHint(token: string, hintId: number): Promise<void> {
  await fetch(`${API_BASE_URL}/api/v1/help/context/dismiss`, {
    method: 'POST',
    headers: this.getHeaders(token),
    body: JSON.stringify({ hint_id: hintId }),
  });
}
```

- [ ] **Step 4: Add session hint throttling in useHelpContext**

In `useHelpContext.ts`, add session-based throttling:

```typescript
// Track hints shown in this session via sessionStorage
const SESSION_HINTS_KEY = 'examcraft_help_hints_shown';

function getSessionHintCount(): number {
  return JSON.parse(sessionStorage.getItem(SESSION_HINTS_KEY) || '[]').length;
}

function recordSessionHint(hintId: number): void {
  const shown = JSON.parse(sessionStorage.getItem(SESSION_HINTS_KEY) || '[]');
  if (!shown.includes(hintId)) {
    shown.push(hintId);
    sessionStorage.setItem(SESSION_HINTS_KEY, JSON.stringify(shown));
  }
}

// In the context hint fetch effect, add:
// if (getSessionHintCount() >= 3) return; // Max 3 hints per session
// After setting hint: recordSessionHint(hint.hint_id);
```

- [ ] **Step 5: Commit**

```bash
git add packages/core/backend/api/v1/help.py packages/core/backend/services/help_context_service.py packages/core/frontend/src/services/helpService.ts packages/core/frontend/src/components/help/useHelpContext.ts
git commit -m "feat(help): add per-user hint dismissal and session throttling

POST /api/v1/help/context/dismiss - permanently dismiss a hint
Session limit: max 3 hints per browser session

Ref: TF-308"
```

---

### Task 21: Conversation Persistence

**Addresses:** Spec items: conversations persist within browser session, archived as read-only (lines 167-172).

**Files:**
- Modify: `packages/core/backend/api/v1/help.py`
- Modify: `packages/core/frontend/src/components/help/HelpChat.tsx`
- Modify: `packages/core/frontend/src/services/helpService.ts`

- [ ] **Step 1: Add conversation save/archive endpoints**

Add to `packages/core/backend/api/v1/help.py`:

```python
class SaveConversationRequest(BaseModel):
    messages: List[Dict[str, Any]]
    route: str = "/"


@router.post("/conversation")
async def save_conversation(
    request_body: SaveConversationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    from models.help import HelpConversation
    conv = HelpConversation(
        user_id=current_user.id,
        messages=request_body.messages,
        route=request_body.route,
    )
    db.add(conv)
    db.commit()
    return {"id": conv.id}
```

- [ ] **Step 2: Add `saveConversation()` to frontend helpService**

```typescript
async saveConversation(
  token: string,
  messages: Array<{ role: string; content: string }>,
  route: string
): Promise<void> {
  await fetch(`${API_BASE_URL}/api/v1/help/conversation`, {
    method: 'POST',
    headers: this.getHeaders(token),
    body: JSON.stringify({ messages, route }),
  });
}
```

- [ ] **Step 3: Archive conversation on "New Conversation"**

In `HelpChat.tsx`, modify `handleNewConversation` to archive before clearing:

```typescript
const handleNewConversation = async () => {
  if (messages.length > 0 && accessToken) {
    await helpService.saveConversation(accessToken, messages, route);
  }
  setMessages([]);
};
```

Also persist to sessionStorage on every message change (survives tab reload, no auth needed):

```typescript
const SESSION_CONV_KEY = 'examcraft_help_conversation';

// Save to sessionStorage on every message change
useEffect(() => {
  if (messages.length > 0) {
    sessionStorage.setItem(SESSION_CONV_KEY, JSON.stringify({ messages, route }));
  }
}, [messages, route]);

// Restore from sessionStorage on mount
useEffect(() => {
  const saved = sessionStorage.getItem(SESSION_CONV_KEY);
  if (saved) {
    try {
      const { messages: savedMessages } = JSON.parse(saved);
      setMessages(savedMessages);
    } catch {}
  }
}, []);

// Archive to backend when starting new conversation (auth is available here)
// The handleNewConversation function above handles this.
// On session end (tab close), sessionStorage is auto-cleared by the browser.
```

- [ ] **Step 4: Commit**

```bash
git add packages/core/backend/api/v1/help.py packages/core/frontend/src/components/help/HelpChat.tsx packages/core/frontend/src/services/helpService.ts
git commit -m "feat(help): add conversation persistence and archival

Conversations archived on new-conversation or page unload.
POST /api/v1/help/conversation

Ref: TF-308"
```

---

### Task 22: Rate Limiting for Help Endpoints

**Addresses:** Spec lines 320-328: rate limits per endpoint group.

**Files:**
- Modify: `packages/core/backend/api/v1/help.py`

- [ ] **Step 1: Add rate limit dependencies**

At the top of `packages/core/backend/api/v1/help.py`, add rate limit imports and configure:

```python
from middleware.rate_limit import rate_limit_dependency

# Rate limit dependencies (per spec)
help_message_limit = rate_limit_dependency(requests_per_minute=0, requests_per_hour=20)
help_feedback_limit = rate_limit_dependency(requests_per_minute=0, requests_per_hour=60)
help_admin_limit = rate_limit_dependency(requests_per_minute=0, requests_per_hour=120)
```

- [ ] **Step 2: Apply to endpoints**

Add `_: None = Depends(help_message_limit)` to `/message` endpoint.
Add `_: None = Depends(help_feedback_limit)` to `/feedback` endpoint.
Add `_: None = Depends(help_admin_limit)` to all `/admin/*` endpoints.

- [ ] **Step 3: Commit**

```bash
git add packages/core/backend/api/v1/help.py
git commit -m "feat(help): add rate limiting to help endpoints

/message: 20/hour, /feedback: 60/hour, /admin/*: 120/hour

Ref: TF-308"
```

---

### Task 23: Enhanced Metrics

**Addresses:** Spec lines 269-275: time-series, top topics, fast-path ratio.

**Files:**
- Modify: `packages/core/backend/services/help_feedback_service.py`

- [ ] **Step 1: Expand `get_metrics()` method**

Replace the `get_metrics` method in `help_feedback_service.py`:

```python
def get_metrics(self) -> Dict[str, Any]:
    from datetime import datetime, timedelta, timezone

    total = self.db.query(HelpFeedback).count()
    positive = self.db.query(HelpFeedback).filter(HelpFeedback.rating == "up").count()
    open_count = self.db.query(HelpFeedback).filter(HelpFeedback.status == "offen").count()
    avg_confidence = self.db.query(func.avg(HelpFeedback.confidence)).scalar() or 0

    # Questions per day (last 7 days)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    daily_counts = (
        self.db.query(
            func.date(HelpFeedback.created_at).label("date"),
            func.count().label("count"),
        )
        .filter(HelpFeedback.created_at >= week_ago)
        .group_by(func.date(HelpFeedback.created_at))
        .all()
    )

    # Top 10 unanswered topics (by route)
    top_topics = (
        self.db.query(HelpFeedback.route, func.count().label("count"))
        .filter(HelpFeedback.status == "offen")
        .group_by(HelpFeedback.route)
        .order_by(func.count().desc())
        .limit(10)
        .all()
    )

    # Fast-path ratio (from HelpFaqCache hit_count vs total)
    from models.help import HelpFaqCache
    cache_hits = self.db.query(func.sum(HelpFaqCache.hit_count)).scalar() or 0
    cache_ratio = round((cache_hits / total * 100) if total > 0 else 0, 1)

    return {
        "total_questions": total,
        "positive_feedback_pct": round((positive / total * 100) if total > 0 else 0, 1),
        "open_feedback_count": open_count,
        "avg_confidence": round(float(avg_confidence), 2),
        "questions_per_day": [{"date": str(d.date), "count": d.count} for d in daily_counts],
        "top_unanswered_topics": [{"route": t.route, "count": t.count} for t in top_topics],
        "cache_hit_ratio_pct": cache_ratio,
    }
```

- [ ] **Step 2: Update MetricsResponse model**

In `help.py`, expand the response model:

```python
class MetricsResponse(BaseModel):
    total_questions: int
    positive_feedback_pct: float
    open_feedback_count: int
    avg_confidence: float
    questions_per_day: List[Dict[str, Any]] = []
    top_unanswered_topics: List[Dict[str, Any]] = []
    cache_hit_ratio_pct: float = 0
```

- [ ] **Step 3: Commit**

```bash
git add packages/core/backend/services/help_feedback_service.py packages/core/backend/api/v1/help.py
git commit -m "feat(help): expand metrics with time-series, top topics, and cache ratio

Ref: TF-308"
```

---

### Task 24: Cron Job for Daily Re-Indexing

**Addresses:** Spec line 263: automatic daily re-indexing at 02:00 UTC.

**Files:**
- Create: `packages/core/backend/scripts/reindex_docs.py`
- Modify: `fly.toml` or document cron setup

- [ ] **Step 1: Create standalone reindex script**

Create `packages/core/backend/scripts/reindex_docs.py`:

```python
#!/usr/bin/env python3
"""Cron script for daily docs re-indexing. Run via: python scripts/reindex_docs.py"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from services.docs_indexer_service import DocsIndexerService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    db = SessionLocal()
    try:
        service = DocsIndexerService(db)
        result = service.run_index(full_scan=False)
        logger.info(f"Re-indexing complete: {result}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Document cron setup**

For Fly.io deployment, add to the deployment documentation:

```bash
# Option A: Fly.io scheduled machine (recommended)
fly machine run . --schedule "0 2 * * *" --command "python scripts/reindex_docs.py"

# Option B: External cron service (e.g., GitHub Actions)
# Add a scheduled workflow that calls POST /api/v1/help/admin/reindex
```

- [ ] **Step 3: Commit**

```bash
git add packages/core/backend/scripts/reindex_docs.py
git commit -m "feat(help): add cron script for daily docs re-indexing

Run via: python scripts/reindex_docs.py
Schedule: daily at 02:00 UTC

Ref: TF-308"
```

---

### Task 25: MkDocs Screenshots Directory and Expanded Frontend Tests

**Addresses:** Missing screenshots/ dir (spec line 432), minimal frontend tests.

**Files:**
- Create: `docs-site/docs/screenshots/.gitkeep`
- Modify: `packages/core/frontend/src/components/help/__tests__/HelpWidget.test.tsx`

- [ ] **Step 1: Create screenshots directory**

```bash
mkdir -p docs-site/docs/screenshots && touch docs-site/docs/screenshots/.gitkeep
```

- [ ] **Step 2: Expand frontend tests**

Expand `HelpWidget.test.tsx` with additional test cases:

```tsx
describe('HelpWidget', () => {
  it('renders the floating help button', () => {
    renderWidget();
    expect(screen.getByTestId('HelpOutlineIcon')).toBeInTheDocument();
  });

  it('opens panel when clicking help button', async () => {
    renderWidget();
    const button = screen.getByRole('button');
    fireEvent.click(button);
    await waitFor(() => {
      expect(screen.getByText('Hilfe')).toBeInTheDocument();
    });
  });

  it('shows onboarding for new users', async () => {
    renderWidget();
    const button = screen.getByRole('button');
    fireEvent.click(button);
    await waitFor(() => {
      // Onboarding auto-opens for step 0
      expect(screen.getByTestId('HelpOutlineIcon')).toBeInTheDocument();
    });
  });

  it('does not open panel on keyboard shortcut when input is focused', () => {
    renderWidget();
    const input = document.createElement('input');
    document.body.appendChild(input);
    input.focus();
    fireEvent.keyDown(window, { key: '/', ctrlKey: true });
    // Panel should NOT open because input is focused
    expect(screen.queryByText('Hilfe')).not.toBeInTheDocument();
    document.body.removeChild(input);
  });
});
```

- [ ] **Step 3: Commit**

```bash
git add docs-site/docs/screenshots/.gitkeep packages/core/frontend/src/components/help/__tests__/
git commit -m "test(help): expand widget tests and add screenshots directory

Ref: TF-308"
```

---

### Task 26: Update Linear Issue with Plan Link

- [ ] **Step 1: Update TF-308 description**

Update the Linear issue TF-308 to add a link to this implementation plan:

```
**Implementierungsplan:** `docs/superpowers/plans/2026-03-24-smart-help-widget.md`
```

- [ ] **Step 2: Final commit with all files**

Verify all files are committed:
```bash
git status
git log --oneline -20
```

Expected: Clean working directory, all tasks committed.
