# Prompt Wizard (TF-297) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an AI-guided chat dialog that helps teachers create prompt templates through natural conversation, integrated as a new tab in the Premium Prompt Library.

**Architecture:** Standalone Wizard Service with own DB tables (`wizard_sessions`, `wizard_messages`), FastAPI endpoints under `/api/v1/wizard/`, and a new `PromptWizard/` component directory in the Premium frontend. Follows existing DocumentChat pattern for session management and ChatInterface pattern for UI.

**Tech Stack:** FastAPI, SQLAlchemy, PydanticAI (Claude API), React 18, TypeScript, MUI, Markdown rendering

**Linear Issue:** TF-297

**Spec:** `docs/superpowers/specs/2026-03-20-prompt-wizard-design.md`

---

## File Structure

### Backend (new files)
- `packages/premium/backend/models/wizard.py` — SQLAlchemy models: WizardSession, WizardMessage
- `packages/premium/backend/services/prompt_wizard_service.py` — Business logic: system prompt assembly, chat handling, template generation, saving
- `packages/premium/backend/api/v1/wizard.py` — FastAPI router with 7 endpoints

### Backend (modify)
- `packages/core/backend/main.py` — Register wizard router in full deployment block

### Frontend (new files)
- `packages/premium/frontend/src/services/WizardService.ts` — API client
- `packages/premium/frontend/src/components/PromptWizard/PromptWizardTab.tsx` — Main tab component
- `packages/premium/frontend/src/components/PromptWizard/WizardSessionList.tsx` — Session sidebar
- `packages/premium/frontend/src/components/PromptWizard/WizardChatInterface.tsx` — Chat area
- `packages/premium/frontend/src/components/PromptWizard/WizardMessageBubble.tsx` — Message bubble
- `packages/premium/frontend/src/components/PromptWizard/WizardQuickOptions.tsx` — Quick-select chips
- `packages/premium/frontend/src/components/PromptWizard/WizardTemplatePreview.tsx` — Template preview + save/edit buttons
- `packages/premium/frontend/src/components/PromptWizard/WizardNewSessionDialog.tsx` — New session dialog

### Frontend (modify)
- `packages/premium/frontend/src/components/prompts/PromptLibraryWithUpload.tsx` — Add fourth tab
- `packages/premium/frontend/src/index.ts` — Export PromptWizardTab

---

## Task 1: Backend Models

**Files:**
- Create: `packages/premium/backend/models/wizard.py`

- [ ] **Step 1: Create WizardSession and WizardMessage models**

```python
"""
Prompt Wizard Models

SQLAlchemy models for AI-guided prompt template creation sessions.
"""

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database import Base


class WizardSession(Base):
    __tablename__ = "wizard_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), default="Neue Session")
    status = Column(String(50), nullable=False, default="active", index=True)
    reference_prompt_id = Column(UUID(as_uuid=True), ForeignKey("prompts.id"), nullable=True)
    generated_prompt_id = Column(UUID(as_uuid=True), ForeignKey("prompts.id"), nullable=True)
    collected_parameters = Column(JSONB, default=dict)
    generated_template = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("WizardMessage", back_populates="session", order_by="WizardMessage.created_at")
    reference_prompt = relationship("Prompt", foreign_keys=[reference_prompt_id])
    generated_prompt = relationship("Prompt", foreign_keys=[generated_prompt_id])

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'completed', 'cancelled')",
            name="check_wizard_session_status",
        ),
        {'extend_existing': True}
    )

    def __repr__(self):
        return f"<WizardSession {self.id} ({self.status})>"


class WizardMessage(Base):
    __tablename__ = "wizard_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("wizard_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    message_metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("WizardSession", back_populates="messages")

    __table_args__ = (
        CheckConstraint(
            "role IN ('system', 'assistant', 'user')",
            name="check_wizard_message_role",
        ),
        {'extend_existing': True}
    )

    def __repr__(self):
        return f"<WizardMessage {self.id} ({self.role})>"
```

Note: Added `generated_template` field to WizardSession to store the generated template text between `/generate` and `/save` calls.

- [ ] **Step 2: Verify models load without errors**

Run: `cd /Users/daniel/GitRepository/ExamCraft && python -c "from packages.premium.backend.models.wizard import WizardSession, WizardMessage; print('Models OK')"`

If import path doesn't work this way, check how other premium models are imported (e.g., `from premium.models.prompt import Prompt` in main.py) and adjust.

- [ ] **Step 3: Commit**

```bash
git add packages/premium/backend/models/wizard.py
git commit -m "feat(wizard): add WizardSession and WizardMessage models (TF-297)"
```

---

## Task 2: Wizard System Prompt

**Files:**
- Create: `packages/premium/backend/services/wizard_system_prompt.py`

- [ ] **Step 1: Create the system prompt module**

This module builds the system prompt for the wizard dialog. It contains:
1. Base instructions defining Claude's role and behavior
2. Output format specification (structured JSON)
3. A function to inject few-shot references and optional reference template

```python
"""
Wizard System Prompt

Builds the system prompt for the AI-guided prompt template creation wizard.
"""

import json
from typing import Optional


WIZARD_BASE_PROMPT = """Du bist ein erfahrener Prompt-Engineer und Didaktik-Experte. Du hilfst Dozenten und Lehrkraeften, perfekte Prompt-Templates fuer die automatische Generierung von Pruefungsfragen zu erstellen.

## Dein Verhalten

1. Stelle immer nur EINE Frage auf einmal
2. Passe deine Folgefragen an die bisherigen Antworten an
3. Sei freundlich, unterstuetzend und erklaere bei Bedarf Fachbegriffe
4. Biete bei geeigneten Fragen Quick-Select-Optionen an
5. Wenn du genug Informationen hast, signalisiere dies mit ready_to_generate: true

## Informationen die du sammeln musst

### Kernparameter (muessen geklaert werden)
- Fachgebiet und Thema
- Fragetyp (Multiple Choice, Offene Frage, Code-Vervollstaendigung, Wahr/Falsch, etc.)
- Zielgruppe und Niveau (z.B. BSc 3. Semester)
- Gewuenschtes Ausgabeformat

### Optionale Vertiefung (basierend auf Kontext entscheiden)
- Schwierigkeitsgrad und Bloom-Taxonomie-Stufe
- Bewertungskriterien und Punkteverteilung
- Code-Beispiele ja/nein und Programmiersprache
- Musterloesung und haeufige Fehler
- Spezifische Anforderungen des Dozenten

## Ausgabeformat

Antworte IMMER als JSON-Objekt mit dieser Struktur:

```json
{
  "message": "Deine Nachricht an den Benutzer (Markdown erlaubt)",
  "quick_options": ["Option 1", "Option 2"],
  "parameters": {
    "subject": "Informatik",
    "topic": "Datenbanken"
  },
  "ready_to_generate": false
}
```

- `message`: Deine Antwort/Frage (Pflichtfeld)
- `quick_options`: Optionale klickbare Vorschlaege (leeres Array wenn keine)
- `parameters`: Aktuell gesammelte Parameter (kumulativ, bei jeder Antwort den vollen Stand)
- `ready_to_generate`: true wenn du genug Informationen hast fuer ein gutes Template

Beginne das Gespraech mit einer freundlichen Begruessung und frage nach dem Fachgebiet."""


GENERATION_PROMPT = """Basierend auf dem bisherigen Gespraech, erstelle jetzt ein vollstaendiges Prompt-Template fuer die Fragengenerierung.

## Gesammelte Parameter
{parameters}

## Anforderungen an das Template
- Verwende Markdown-Formatierung
- Integriere Jinja2-Variablen fuer dynamische Werte: {{{{ topic }}}}, {{{{ difficulty }}}}, {{{{ context }}}}
- Das Template muss die Variable {{{{ context }}}} enthalten (wird automatisch mit RAG-Kontext befuellt)
- Strukturiere das Template mit klaren Sektionen (Aufgabe, Kontext, Anforderungen, Qualitaetskriterien, Ausgabeformat)
- Das Ausgabeformat sollte JSON sein mit den Feldern "question", "sample_answer", "evaluation_criteria"
- Passe Sprache, Stil und Detailtiefe an die Zielgruppe an

{reference_section}

Antworte als JSON-Objekt:
```json
{{
  "template": "Das vollstaendige Markdown-Template",
  "suggested_name": "Kurzer beschreibender Name",
  "suggested_category": "template",
  "suggested_use_case": "question_generation_<type>",
  "suggested_tags": ["tag1", "tag2"]
}}
```"""


def build_system_prompt(
    few_shot_templates: list[str] | None = None,
    reference_template: str | None = None,
) -> str:
    """Build the complete system prompt with optional references."""
    parts = [WIZARD_BASE_PROMPT]

    if few_shot_templates:
        parts.append("\n## Referenz-Templates (so sieht ein gutes Template aus)\n")
        for i, template in enumerate(few_shot_templates, 1):
            parts.append(f"### Beispiel {i}\n```\n{template}\n```\n")

    if reference_template:
        parts.append(
            "\n## Vom Benutzer gewaehltes Referenz-Template\n"
            "Der Benutzer moechte ein aehnliches Template erstellen. "
            "Nutze es als Orientierung fuer Struktur und Stil.\n"
            f"```\n{reference_template}\n```\n"
        )

    return "\n".join(parts)


def build_generation_prompt(
    collected_parameters: dict,
    reference_template: str | None = None,
) -> str:
    """Build the prompt for final template generation."""
    params_str = json.dumps(collected_parameters, indent=2, ensure_ascii=False)

    reference_section = ""
    if reference_template:
        reference_section = (
            "## Referenz-Template (als Orientierung fuer Struktur)\n"
            f"```\n{reference_template}\n```"
        )

    return GENERATION_PROMPT.format(
        parameters=params_str,
        reference_section=reference_section,
    )
```

- [ ] **Step 2: Commit**

```bash
git add packages/premium/backend/services/wizard_system_prompt.py
git commit -m "feat(wizard): add system prompt builder for wizard dialog (TF-297)"
```

---

## Task 3: PromptWizardService

**Files:**
- Create: `packages/premium/backend/services/prompt_wizard_service.py`

- [ ] **Step 1: Create the service with session management and chat handling**

```python
"""
Prompt Wizard Service

Handles AI-guided prompt template creation through conversational dialog.
"""

import json
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import desc

from premium.models.wizard import WizardSession, WizardMessage
from premium.models.prompt import Prompt
from premium.services.wizard_system_prompt import (
    build_system_prompt,
    build_generation_prompt,
)

logger = logging.getLogger(__name__)


class PromptWizardService:
    """Service for AI-guided prompt template creation."""

    def __init__(self, db: Session):
        self.db = db

    def _get_few_shot_templates(self, limit: int = 2) -> list[str]:
        """Get top templates from Prompt Library as few-shot references."""
        prompts = (
            self.db.query(Prompt)
            .filter(Prompt.is_active == True, Prompt.category == "template")
            .order_by(desc(Prompt.usage_count))
            .limit(limit)
            .all()
        )
        return [p.content for p in prompts]

    def _get_reference_template(self, prompt_id: UUID) -> Optional[str]:
        """Get the content of a reference template."""
        prompt = self.db.query(Prompt).filter(Prompt.id == prompt_id).first()
        return prompt.content if prompt else None

    async def _call_claude(self, messages: list[dict]) -> dict:
        """Send messages to Claude API and parse structured JSON response."""
        from pydantic_ai import Agent
        from pydantic_ai.models.anthropic import AnthropicModel

        model = AnthropicModel("claude-sonnet-4-20250514")
        agent = Agent(model=model)

        # Build message list for the agent
        # First message is system, rest are conversation
        system_prompt = messages[0]["content"] if messages[0]["role"] == "system" else ""
        conversation = messages[1:] if messages[0]["role"] == "system" else messages

        # Format conversation as a single prompt with history
        conversation_text = ""
        for msg in conversation:
            role_label = "Benutzer" if msg["role"] == "user" else "Assistent"
            conversation_text += f"\n{role_label}: {msg['content']}\n"
        conversation_text += "\nAssistent:"

        result = await agent.run(
            conversation_text,
            system_prompt=system_prompt,
        )

        # Parse JSON response
        response_text = result.output
        # Try to extract JSON from the response
        try:
            # Handle case where response is wrapped in ```json ... ```
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
            return json.loads(json_str)
        except (json.JSONDecodeError, IndexError):
            logger.warning(f"Failed to parse Claude response as JSON: {response_text[:200]}")
            return {
                "message": response_text,
                "quick_options": [],
                "parameters": {},
                "ready_to_generate": False,
            }

    def _build_message_history(self, session: WizardSession) -> list[dict]:
        """Build the full message history for Claude API call."""
        messages = []
        for msg in session.messages:
            if msg.role == "system":
                messages.append({"role": "system", "content": msg.content})
            elif msg.role == "user":
                messages.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                # Re-wrap assistant messages as the original JSON
                metadata = msg.message_metadata or {}
                assistant_json = {
                    "message": msg.content,
                    "quick_options": metadata.get("quick_options", []),
                    "parameters": metadata.get("parameters", {}),
                    "ready_to_generate": metadata.get("ready_to_generate", False),
                }
                messages.append({"role": "assistant", "content": json.dumps(assistant_json, ensure_ascii=False)})
        return messages

    async def create_session(
        self, user_id: UUID, reference_prompt_id: Optional[UUID] = None
    ) -> dict:
        """Create a new wizard session and get the first AI message."""
        # Build system prompt
        few_shot = self._get_few_shot_templates()
        ref_content = None
        if reference_prompt_id:
            ref_content = self._get_reference_template(reference_prompt_id)

        system_prompt = build_system_prompt(
            few_shot_templates=few_shot if few_shot else None,
            reference_template=ref_content,
        )

        # Create session
        session = WizardSession(
            user_id=user_id,
            reference_prompt_id=reference_prompt_id,
            status="active",
        )
        self.db.add(session)
        self.db.flush()

        # Save system message
        system_msg = WizardMessage(
            session_id=session.id,
            role="system",
            content=system_prompt,
        )
        self.db.add(system_msg)
        self.db.flush()

        # Get initial AI message
        messages = [{"role": "system", "content": system_prompt}]
        ai_response = await self._call_claude(messages)

        # Save assistant message
        assistant_msg = WizardMessage(
            session_id=session.id,
            role="assistant",
            content=ai_response.get("message", ""),
            message_metadata={
                "quick_options": ai_response.get("quick_options", []),
                "parameters": ai_response.get("parameters", {}),
                "ready_to_generate": ai_response.get("ready_to_generate", False),
            },
        )
        self.db.add(assistant_msg)

        # Update collected parameters
        session.collected_parameters = ai_response.get("parameters", {})
        self.db.commit()
        self.db.refresh(session)

        return self._session_to_dict(session)

    async def send_message(self, session_id: UUID, user_id: UUID, message: str) -> dict:
        """Send a user message and get AI response."""
        session = (
            self.db.query(WizardSession)
            .filter(WizardSession.id == session_id, WizardSession.user_id == user_id)
            .first()
        )
        if not session:
            raise ValueError("Session not found")
        if session.status != "active":
            raise ValueError("Session is not active")

        # Save user message
        user_msg = WizardMessage(
            session_id=session.id,
            role="user",
            content=message,
        )
        self.db.add(user_msg)
        self.db.flush()

        # Update title from first user message
        user_messages = [m for m in session.messages if m.role == "user"]
        if len(user_messages) <= 1:
            session.title = message[:100]

        # Build full history and call Claude
        history = self._build_message_history(session)
        history.append({"role": "user", "content": message})
        ai_response = await self._call_claude(history)

        # Save assistant message
        assistant_msg = WizardMessage(
            session_id=session.id,
            role="assistant",
            content=ai_response.get("message", ""),
            message_metadata={
                "quick_options": ai_response.get("quick_options", []),
                "parameters": ai_response.get("parameters", {}),
                "ready_to_generate": ai_response.get("ready_to_generate", False),
            },
        )
        self.db.add(assistant_msg)

        # Update collected parameters
        params = ai_response.get("parameters", {})
        if params:
            current = session.collected_parameters or {}
            current.update(params)
            session.collected_parameters = current

        self.db.commit()

        return {
            "role": "assistant",
            "content": ai_response.get("message", ""),
            "message_metadata": assistant_msg.message_metadata,
        }

    async def generate_template(self, session_id: UUID, user_id: UUID) -> dict:
        """Generate the final template from collected parameters."""
        session = (
            self.db.query(WizardSession)
            .filter(WizardSession.id == session_id, WizardSession.user_id == user_id)
            .first()
        )
        if not session:
            raise ValueError("Session not found")

        # Build generation prompt
        ref_content = None
        if session.reference_prompt_id:
            ref_content = self._get_reference_template(session.reference_prompt_id)

        gen_prompt = build_generation_prompt(
            collected_parameters=session.collected_parameters or {},
            reference_template=ref_content,
        )

        # Build history + generation request
        history = self._build_message_history(session)
        history.append({"role": "user", "content": gen_prompt})

        ai_response = await self._call_claude(history)

        # Store generated template
        template = ai_response.get("template", ai_response.get("message", ""))
        session.generated_template = template
        self.db.commit()

        return {
            "template_preview": template,
            "suggested_name": ai_response.get("suggested_name", session.title or "Neues Template"),
            "suggested_category": ai_response.get("suggested_category", "template"),
            "suggested_use_case": ai_response.get("suggested_use_case", "question_generation"),
            "suggested_tags": ai_response.get("suggested_tags", []),
        }

    def save_template(
        self, session_id: UUID, user_id: UUID, save_data: dict
    ) -> dict:
        """Save the generated template to the Prompt Library."""
        session = (
            self.db.query(WizardSession)
            .filter(WizardSession.id == session_id, WizardSession.user_id == user_id)
            .first()
        )
        if not session:
            raise ValueError("Session not found")
        if not session.generated_template:
            raise ValueError("No template generated yet")

        # Create prompt via direct model creation (follows existing pattern)
        prompt = Prompt(
            name=save_data["name"],
            content=session.generated_template,
            description=save_data.get("description", "Generiert via KI-Assistent"),
            category=save_data.get("category", "template"),
            use_case=save_data.get("use_case"),
            tags=save_data.get("tags", []),
            is_active=True,
            version=1,
            author_id=str(user_id),
        )
        self.db.add(prompt)
        self.db.flush()

        # Update session
        session.generated_prompt_id = prompt.id
        session.status = "completed"
        self.db.commit()
        self.db.refresh(prompt)

        return {
            "id": str(prompt.id),
            "name": prompt.name,
            "category": prompt.category,
            "status": "saved",
        }

    def list_sessions(self, user_id: UUID) -> list[dict]:
        """List all wizard sessions for a user."""
        sessions = (
            self.db.query(WizardSession)
            .filter(WizardSession.user_id == user_id)
            .order_by(desc(WizardSession.updated_at))
            .all()
        )
        return [
            {
                "id": str(s.id),
                "title": s.title,
                "status": s.status,
                "message_count": len(s.messages),
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in sessions
        ]

    def get_session(self, session_id: UUID, user_id: UUID) -> dict:
        """Get a session with all messages."""
        session = (
            self.db.query(WizardSession)
            .filter(WizardSession.id == session_id, WizardSession.user_id == user_id)
            .first()
        )
        if not session:
            raise ValueError("Session not found")
        return self._session_to_dict(session)

    def delete_session(self, session_id: UUID, user_id: UUID) -> None:
        """Delete a wizard session and its messages."""
        session = (
            self.db.query(WizardSession)
            .filter(WizardSession.id == session_id, WizardSession.user_id == user_id)
            .first()
        )
        if not session:
            raise ValueError("Session not found")
        self.db.delete(session)
        self.db.commit()

    def _session_to_dict(self, session: WizardSession) -> dict:
        """Convert session to API response dict."""
        return {
            "id": str(session.id),
            "title": session.title,
            "status": session.status,
            "reference_prompt_id": str(session.reference_prompt_id) if session.reference_prompt_id else None,
            "generated_prompt_id": str(session.generated_prompt_id) if session.generated_prompt_id else None,
            "collected_parameters": session.collected_parameters or {},
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
            "messages": [
                {
                    "id": str(m.id),
                    "role": m.role,
                    "content": m.content,
                    "message_metadata": m.message_metadata or {},
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in session.messages
                if m.role != "system"  # Don't expose system prompt to frontend
            ],
        }
```

- [ ] **Step 2: Commit**

```bash
git add packages/premium/backend/services/prompt_wizard_service.py
git commit -m "feat(wizard): add PromptWizardService with chat and generation logic (TF-297)"
```

---

## Task 4: API Router

**Files:**
- Create: `packages/premium/backend/api/v1/wizard.py`
- Modify: `packages/core/backend/main.py`

- [ ] **Step 1: Create the wizard API router**

```python
"""
Prompt Wizard API

Endpoints for AI-guided prompt template creation.
"""

import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.auth import User
from utils.auth_utils import require_permission
from premium.services.prompt_wizard_service import PromptWizardService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/wizard", tags=["wizard"])


# --- Request/Response Models ---

class CreateSessionRequest(BaseModel):
    reference_prompt_id: Optional[str] = None


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1)


class SaveTemplateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    category: str = Field(default="template")
    use_case: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = Field(default="Generiert via KI-Assistent")


# --- Dependency ---

def get_wizard_service(db: Session = Depends(get_db)) -> PromptWizardService:
    return PromptWizardService(db)


# --- Endpoints ---

@router.post("/sessions", response_model=dict)
async def create_session(
    request: CreateSessionRequest,
    current_user: User = Depends(require_permission("prompt:create")),
    service: PromptWizardService = Depends(get_wizard_service),
):
    """Create a new wizard session and get the first AI message."""
    try:
        ref_id = UUID(request.reference_prompt_id) if request.reference_prompt_id else None
        result = await service.create_session(
            user_id=current_user.id,
            reference_prompt_id=ref_id,
        )
        return result
    except Exception as e:
        logger.error(f"Failed to create wizard session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=list)
async def list_sessions(
    current_user: User = Depends(require_permission("prompt:read")),
    service: PromptWizardService = Depends(get_wizard_service),
):
    """List all wizard sessions for the current user."""
    return service.list_sessions(user_id=current_user.id)


@router.get("/sessions/{session_id}", response_model=dict)
async def get_session(
    session_id: str,
    current_user: User = Depends(require_permission("prompt:read")),
    service: PromptWizardService = Depends(get_wizard_service),
):
    """Get a wizard session with all messages."""
    try:
        return service.get_session(
            session_id=UUID(session_id),
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/sessions/{session_id}/chat", response_model=dict)
async def send_message(
    session_id: str,
    request: ChatMessageRequest,
    current_user: User = Depends(require_permission("prompt:create")),
    service: PromptWizardService = Depends(get_wizard_service),
):
    """Send a message and receive AI response."""
    try:
        return await service.send_message(
            session_id=UUID(session_id),
            user_id=current_user.id,
            message=request.message,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/generate", response_model=dict)
async def generate_template(
    session_id: str,
    current_user: User = Depends(require_permission("prompt:create")),
    service: PromptWizardService = Depends(get_wizard_service),
):
    """Generate the final template from the conversation."""
    try:
        return await service.generate_template(
            session_id=UUID(session_id),
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/save", response_model=dict)
async def save_template(
    session_id: str,
    request: SaveTemplateRequest,
    current_user: User = Depends(require_permission("prompt:create")),
    service: PromptWizardService = Depends(get_wizard_service),
):
    """Save the generated template to the Prompt Library."""
    try:
        return service.save_template(
            session_id=UUID(session_id),
            user_id=current_user.id,
            save_data=request.model_dump(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Save error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(require_permission("prompt:create")),
    service: PromptWizardService = Depends(get_wizard_service),
):
    """Delete a wizard session."""
    try:
        service.delete_session(
            session_id=UUID(session_id),
            user_id=current_user.id,
        )
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

- [ ] **Step 2: Register wizard router in main.py**

In `packages/core/backend/main.py`, find the block where premium routers are loaded (where `prompts_api` and `chat_api` are imported in the `if is_full_deployment` block). Add the wizard router in the same pattern:

```python
# Premium: Wizard API
from premium.api.v1 import wizard as wizard_api
app.include_router(wizard_api.router)
```

- [ ] **Step 3: Commit**

```bash
git add packages/premium/backend/api/v1/wizard.py packages/core/backend/main.py
git commit -m "feat(wizard): add API router with 7 endpoints (TF-297)"
```

---

## Task 5: Database Migration

- [ ] **Step 1: Create Alembic migration for wizard tables**

Run: `cd packages/core/backend && alembic revision --autogenerate -m "add wizard_sessions and wizard_messages tables"`

If Alembic is not configured or auto-generation doesn't pick up the premium models, create a manual migration. The key is that both tables get created. Verify the migration includes:
- `wizard_sessions` with all columns and check constraint
- `wizard_messages` with all columns, foreign key to wizard_sessions with CASCADE delete, and check constraint

- [ ] **Step 2: Apply migration**

Run: `cd packages/core/backend && alembic upgrade head`

- [ ] **Step 3: Verify tables exist**

Run: `docker compose --env-file .env -f docker-compose.full.yml exec db psql -U examcraft -c "\dt wizard_*"`

Expected: Both `wizard_sessions` and `wizard_messages` tables listed.

- [ ] **Step 4: Commit**

```bash
git add packages/core/backend/alembic/versions/
git commit -m "feat(wizard): add database migration for wizard tables (TF-297)"
```

---

## Task 6: Frontend API Client (WizardService.ts)

**Files:**
- Create: `packages/premium/frontend/src/services/WizardService.ts`

- [ ] **Step 1: Create the API client**

Follow the pattern from `ChatService.ts`:

```typescript
/**
 * Wizard Service
 * API client for the Prompt Wizard endpoints.
 */

const API_BASE_URL = '';

export interface WizardMessage {
  id?: string;
  role: 'assistant' | 'user';
  content: string;
  message_metadata: {
    quick_options?: string[];
    parameters?: Record<string, unknown>;
    ready_to_generate?: boolean;
  };
  created_at?: string;
}

export interface WizardSession {
  id: string;
  title: string;
  status: 'active' | 'completed' | 'cancelled';
  reference_prompt_id?: string | null;
  generated_prompt_id?: string | null;
  collected_parameters: Record<string, unknown>;
  messages: WizardMessage[];
  created_at?: string;
  updated_at?: string;
}

export interface WizardSessionSummary {
  id: string;
  title: string;
  status: 'active' | 'completed' | 'cancelled';
  message_count: number;
  created_at?: string;
  updated_at?: string;
}

export interface GenerateResult {
  template_preview: string;
  suggested_name: string;
  suggested_category: string;
  suggested_use_case: string;
  suggested_tags: string[];
}

export interface SaveTemplateRequest {
  name: string;
  category?: string;
  use_case?: string;
  tags?: string[];
  description?: string;
}

class WizardService {
  private async request<T>(
    accessToken: string,
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `Request failed with status ${response.status}`);
    }

    return response.json();
  }

  async createSession(
    accessToken: string,
    referencePromptId?: string
  ): Promise<WizardSession> {
    return this.request(accessToken, '/api/v1/wizard/sessions', {
      method: 'POST',
      body: JSON.stringify({
        reference_prompt_id: referencePromptId || null,
      }),
    });
  }

  async listSessions(accessToken: string): Promise<WizardSessionSummary[]> {
    return this.request(accessToken, '/api/v1/wizard/sessions');
  }

  async getSession(
    accessToken: string,
    sessionId: string
  ): Promise<WizardSession> {
    return this.request(accessToken, `/api/v1/wizard/sessions/${sessionId}`);
  }

  async sendMessage(
    accessToken: string,
    sessionId: string,
    message: string
  ): Promise<WizardMessage> {
    return this.request(accessToken, `/api/v1/wizard/sessions/${sessionId}/chat`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  }

  async generateTemplate(
    accessToken: string,
    sessionId: string
  ): Promise<GenerateResult> {
    return this.request(accessToken, `/api/v1/wizard/sessions/${sessionId}/generate`, {
      method: 'POST',
    });
  }

  async saveTemplate(
    accessToken: string,
    sessionId: string,
    data: SaveTemplateRequest
  ): Promise<{ id: string; name: string; status: string }> {
    return this.request(accessToken, `/api/v1/wizard/sessions/${sessionId}/save`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteSession(accessToken: string, sessionId: string): Promise<void> {
    await this.request(accessToken, `/api/v1/wizard/sessions/${sessionId}`, {
      method: 'DELETE',
    });
  }
}

export default new WizardService();
```

- [ ] **Step 2: Commit**

```bash
git add packages/premium/frontend/src/services/WizardService.ts
git commit -m "feat(wizard): add WizardService API client (TF-297)"
```

---

## Task 7: WizardMessageBubble + WizardQuickOptions Components

**Files:**
- Create: `packages/premium/frontend/src/components/PromptWizard/WizardMessageBubble.tsx`
- Create: `packages/premium/frontend/src/components/PromptWizard/WizardQuickOptions.tsx`

- [ ] **Step 1: Create WizardMessageBubble**

```tsx
import React from 'react';
import { Box, Avatar } from '@mui/material';
import { AutoAwesome } from '@mui/icons-material';
import { MarkdownRenderer } from '@examcraft/core';
import type { WizardMessage } from '../../services/WizardService';
import WizardQuickOptions from './WizardQuickOptions';

interface WizardMessageBubbleProps {
  message: WizardMessage;
  userInitials: string;
  onQuickOptionClick?: (option: string) => void;
  isLatest?: boolean;
}

const WizardMessageBubble: React.FC<WizardMessageBubbleProps> = ({
  message,
  userInitials,
  onQuickOptionClick,
  isLatest = false,
}) => {
  const isUser = message.role === 'user';
  const quickOptions = message.message_metadata?.quick_options || [];

  return (
    <Box
      sx={{
        display: 'flex',
        gap: 1.5,
        mb: 2.5,
        justifyContent: isUser ? 'flex-end' : 'flex-start',
      }}
    >
      {!isUser && (
        <Avatar
          sx={{
            width: 36,
            height: 36,
            background: 'linear-gradient(135deg, #f59e0b, #d97706)',
            flexShrink: 0,
          }}
        >
          <AutoAwesome sx={{ fontSize: 18 }} />
        </Avatar>
      )}

      <Box sx={{ maxWidth: '75%' }}>
        <Box
          sx={{
            bgcolor: isUser ? '#f59e0b' : 'background.paper',
            color: isUser ? 'white' : 'text.primary',
            border: isUser ? 'none' : '1px solid',
            borderColor: 'divider',
            borderRadius: 3,
            borderTopLeftRadius: isUser ? 12 : 4,
            borderTopRightRadius: isUser ? 4 : 12,
            px: 2.5,
            py: 2,
            boxShadow: isUser ? 'none' : '0 1px 2px rgba(0,0,0,0.05)',
          }}
        >
          {isUser ? (
            <Box sx={{ fontSize: 14, lineHeight: 1.6 }}>{message.content}</Box>
          ) : (
            <MarkdownRenderer content={message.content} variant="compact" />
          )}
        </Box>

        {!isUser && quickOptions.length > 0 && isLatest && onQuickOptionClick && (
          <WizardQuickOptions
            options={quickOptions}
            onClick={onQuickOptionClick}
          />
        )}
      </Box>

      {isUser && (
        <Avatar
          sx={{
            width: 36,
            height: 36,
            bgcolor: 'grey.300',
            color: 'grey.600',
            fontSize: 14,
            fontWeight: 'bold',
            flexShrink: 0,
          }}
        >
          {userInitials}
        </Avatar>
      )}
    </Box>
  );
};

export default WizardMessageBubble;
```

- [ ] **Step 2: Create WizardQuickOptions**

```tsx
import React from 'react';
import { Box, Chip } from '@mui/material';

interface WizardQuickOptionsProps {
  options: string[];
  onClick: (option: string) => void;
}

const WizardQuickOptions: React.FC<WizardQuickOptionsProps> = ({
  options,
  onClick,
}) => {
  return (
    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1.5 }}>
      {options.map((option) => (
        <Chip
          key={option}
          label={option}
          onClick={() => onClick(option)}
          sx={{
            bgcolor: '#fff7ed',
            border: '1px solid #fed7aa',
            color: '#9a3412',
            cursor: 'pointer',
            '&:hover': {
              bgcolor: '#ffedd5',
            },
          }}
        />
      ))}
    </Box>
  );
};

export default WizardQuickOptions;
```

- [ ] **Step 3: Commit**

```bash
git add packages/premium/frontend/src/components/PromptWizard/WizardMessageBubble.tsx packages/premium/frontend/src/components/PromptWizard/WizardQuickOptions.tsx
git commit -m "feat(wizard): add WizardMessageBubble and WizardQuickOptions components (TF-297)"
```

---

## Task 8: WizardTemplatePreview Component

**Files:**
- Create: `packages/premium/frontend/src/components/PromptWizard/WizardTemplatePreview.tsx`

- [ ] **Step 1: Create the template preview component**

```tsx
import React, { useState } from 'react';
import {
  Box,
  Button,
  TextField,
  Chip,
  Paper,
  Typography,
  Alert,
  CircularProgress,
} from '@mui/material';
import { Save, Edit } from '@mui/icons-material';
import { MarkdownRenderer } from '@examcraft/core';
import type { GenerateResult, SaveTemplateRequest } from '../../services/WizardService';

interface WizardTemplatePreviewProps {
  generateResult: GenerateResult;
  onSave: (data: SaveTemplateRequest) => Promise<void>;
  onEditInEditor: (data: {
    name: string;
    content: string;
    category: string;
    use_case: string;
    tags: string[];
    description: string;
  }) => void;
}

const WizardTemplatePreview: React.FC<WizardTemplatePreviewProps> = ({
  generateResult,
  onSave,
  onEditInEditor,
}) => {
  const [name, setName] = useState(generateResult.suggested_name);
  const [tags, setTags] = useState<string[]>(generateResult.suggested_tags);
  const [tagInput, setTagInput] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    if (!name.trim()) {
      setError('Bitte gib einen Namen ein');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSave({
        name: name.trim(),
        category: generateResult.suggested_category,
        use_case: generateResult.suggested_use_case,
        tags,
        description: 'Generiert via KI-Assistent',
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Speichern');
    } finally {
      setSaving(false);
    }
  };

  const handleEditInEditor = () => {
    onEditInEditor({
      name: name.trim(),
      content: generateResult.template_preview,
      category: generateResult.suggested_category,
      use_case: generateResult.suggested_use_case,
      tags,
      description: 'Generiert via KI-Assistent',
    });
  };

  const handleAddTag = () => {
    const trimmed = tagInput.trim();
    if (trimmed && !tags.includes(trimmed)) {
      setTags([...tags, trimmed]);
      setTagInput('');
    }
  };

  return (
    <Paper
      elevation={0}
      sx={{
        border: '2px solid #f59e0b',
        borderRadius: 3,
        overflow: 'hidden',
        mt: 2,
      }}
    >
      {/* Header */}
      <Box
        sx={{
          bgcolor: '#fffbeb',
          px: 3,
          py: 2,
          borderBottom: '1px solid #fde68a',
        }}
      >
        <Typography variant="subtitle1" fontWeight={600}>
          Generiertes Template
        </Typography>
      </Box>

      {/* Template Preview */}
      <Box sx={{ px: 3, py: 2, maxHeight: 400, overflowY: 'auto' }}>
        <MarkdownRenderer content={generateResult.template_preview} />
      </Box>

      {/* Metadata & Actions */}
      <Box sx={{ px: 3, py: 2, borderTop: '1px solid', borderColor: 'divider' }}>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <TextField
          label="Template Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          fullWidth
          size="small"
          sx={{ mb: 2 }}
        />

        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
          {tags.map((tag) => (
            <Chip
              key={tag}
              label={tag}
              size="small"
              onDelete={() => setTags(tags.filter((t) => t !== tag))}
            />
          ))}
          <TextField
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
            placeholder="Tag hinzufuegen..."
            size="small"
            variant="standard"
            sx={{ width: 140 }}
          />
        </Box>

        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
          <Button
            variant="outlined"
            startIcon={<Edit />}
            onClick={handleEditInEditor}
          >
            Im Editor bearbeiten
          </Button>
          <Button
            variant="contained"
            startIcon={saving ? <CircularProgress size={18} color="inherit" /> : <Save />}
            onClick={handleSave}
            disabled={saving}
            sx={{ bgcolor: '#f59e0b', '&:hover': { bgcolor: '#d97706' } }}
          >
            So speichern
          </Button>
        </Box>
      </Box>
    </Paper>
  );
};

export default WizardTemplatePreview;
```

- [ ] **Step 2: Commit**

```bash
git add packages/premium/frontend/src/components/PromptWizard/WizardTemplatePreview.tsx
git commit -m "feat(wizard): add WizardTemplatePreview component (TF-297)"
```

---

## Task 9: WizardChatInterface Component

**Files:**
- Create: `packages/premium/frontend/src/components/PromptWizard/WizardChatInterface.tsx`

- [ ] **Step 1: Create the chat interface**

```tsx
import React, { useState, useEffect, useRef } from 'react';
import { Box, TextField, IconButton, CircularProgress, Button } from '@mui/material';
import { Send, AutoAwesome } from '@mui/icons-material';
import { useAuth } from '@examcraft/core';
import WizardService from '../../services/WizardService';
import WizardMessageBubble from './WizardMessageBubble';
import WizardTemplatePreview from './WizardTemplatePreview';
import type {
  WizardMessage,
  WizardSession,
  GenerateResult,
  SaveTemplateRequest,
} from '../../services/WizardService';

interface WizardChatInterfaceProps {
  session: WizardSession;
  onSessionUpdate: () => void;
  onEditInEditor: (data: {
    name: string;
    content: string;
    category: string;
    use_case: string;
    tags: string[];
    description: string;
  }) => void;
}

const WizardChatInterface: React.FC<WizardChatInterfaceProps> = ({
  session,
  onSessionUpdate,
  onEditInEditor,
}) => {
  const { accessToken, user } = useAuth();
  const [messages, setMessages] = useState<WizardMessage[]>(session.messages || []);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateResult, setGenerateResult] = useState<GenerateResult | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const userInitials = user?.name
    ? user.name.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2)
    : 'U';

  // Check if the latest message signals ready_to_generate
  const latestAssistantMsg = [...messages].reverse().find((m) => m.role === 'assistant');
  const readyToGenerate = latestAssistantMsg?.message_metadata?.ready_to_generate === true;

  useEffect(() => {
    setMessages(session.messages || []);
    setGenerateResult(null);
  }, [session.id, session.messages]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, generateResult]);

  const sendMessage = async (text?: string) => {
    const messageText = text || inputMessage.trim();
    if (!messageText || isLoading || !accessToken) return;

    const userMessage: WizardMessage = {
      role: 'user',
      content: messageText,
      message_metadata: {},
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await WizardService.sendMessage(accessToken, session.id, messageText);
      setMessages((prev) => [...prev, response]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant' as const,
          content: 'Fehler beim Senden der Nachricht. Bitte versuche es erneut.',
          message_metadata: {},
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!accessToken || isGenerating) return;
    setIsGenerating(true);

    try {
      const result = await WizardService.generateTemplate(accessToken, session.id);
      setGenerateResult(result);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant' as const,
          content: 'Fehler bei der Template-Generierung. Bitte versuche es erneut.',
          message_metadata: {},
        },
      ]);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSave = async (data: SaveTemplateRequest) => {
    if (!accessToken) return;
    await WizardService.saveTemplate(accessToken, session.id, data);
    onSessionUpdate();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Messages */}
      <Box sx={{ flex: 1, overflowY: 'auto', px: 3, py: 2, bgcolor: '#fafafa' }}>
        {messages.map((msg, index) => (
          <WizardMessageBubble
            key={msg.id || index}
            message={msg}
            userInitials={userInitials}
            onQuickOptionClick={(option) => sendMessage(option)}
            isLatest={index === messages.length - 1}
          />
        ))}

        {isLoading && (
          <Box sx={{ display: 'flex', gap: 1.5, mb: 2.5, alignItems: 'center' }}>
            <Box
              sx={{
                width: 36,
                height: 36,
                background: 'linear-gradient(135deg, #f59e0b, #d97706)',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <AutoAwesome sx={{ fontSize: 18, color: 'white' }} />
            </Box>
            <CircularProgress size={20} sx={{ color: '#f59e0b' }} />
          </Box>
        )}

        {readyToGenerate && !generateResult && !isGenerating && (
          <Box sx={{ display: 'flex', justifyContent: 'center', my: 2 }}>
            <Button
              variant="contained"
              startIcon={<AutoAwesome />}
              onClick={handleGenerate}
              sx={{ bgcolor: '#f59e0b', '&:hover': { bgcolor: '#d97706' } }}
            >
              Template generieren
            </Button>
          </Box>
        )}

        {isGenerating && (
          <Box sx={{ display: 'flex', justifyContent: 'center', my: 2, gap: 1, alignItems: 'center' }}>
            <CircularProgress size={20} sx={{ color: '#f59e0b' }} />
            <Box sx={{ color: 'text.secondary', fontSize: 14 }}>Template wird generiert...</Box>
          </Box>
        )}

        {generateResult && (
          <WizardTemplatePreview
            generateResult={generateResult}
            onSave={handleSave}
            onEditInEditor={onEditInEditor}
          />
        )}

        <div ref={scrollRef} />
      </Box>

      {/* Input */}
      {session.status === 'active' && !generateResult && (
        <Box
          sx={{
            borderTop: '1px solid',
            borderColor: 'divider',
            p: 2,
            bgcolor: 'background.paper',
            display: 'flex',
            gap: 1.5,
            alignItems: 'flex-end',
          }}
        >
          <TextField
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Nachricht eingeben..."
            multiline
            maxRows={4}
            fullWidth
            size="small"
            disabled={isLoading}
            sx={{
              '& .MuiOutlinedInput-root': { borderRadius: 3 },
            }}
          />
          <IconButton
            onClick={() => sendMessage()}
            disabled={!inputMessage.trim() || isLoading}
            sx={{
              bgcolor: '#f59e0b',
              color: 'white',
              borderRadius: 3,
              width: 44,
              height: 44,
              '&:hover': { bgcolor: '#d97706' },
              '&.Mui-disabled': { bgcolor: 'grey.300' },
            }}
          >
            <Send />
          </IconButton>
        </Box>
      )}
    </Box>
  );
};

export default WizardChatInterface;
```

- [ ] **Step 2: Commit**

```bash
git add packages/premium/frontend/src/components/PromptWizard/WizardChatInterface.tsx
git commit -m "feat(wizard): add WizardChatInterface component (TF-297)"
```

---

## Task 10: WizardSessionList + WizardNewSessionDialog

**Files:**
- Create: `packages/premium/frontend/src/components/PromptWizard/WizardSessionList.tsx`
- Create: `packages/premium/frontend/src/components/PromptWizard/WizardNewSessionDialog.tsx`

- [ ] **Step 1: Create WizardSessionList**

```tsx
import React from 'react';
import { Box, Button, Typography, Chip, IconButton } from '@mui/material';
import { Add, Delete } from '@mui/icons-material';
import type { WizardSessionSummary } from '../../services/WizardService';

interface WizardSessionListProps {
  sessions: WizardSessionSummary[];
  currentSessionId?: string | null;
  onSelectSession: (sessionId: string) => void;
  onNewSession: () => void;
  onDeleteSession: (sessionId: string) => void;
}

const STATUS_CONFIG = {
  active: { label: 'In Bearbeitung', bgcolor: '#fef3c7', color: '#92400e' },
  completed: { label: 'Gespeichert', bgcolor: '#dcfce7', color: '#166534' },
  cancelled: { label: 'Abgebrochen', bgcolor: '#fee2e2', color: '#991b1b' },
} as const;

const WizardSessionList: React.FC<WizardSessionListProps> = ({
  sessions,
  currentSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
}) => {
  const activeSessions = sessions.filter((s) => s.status === 'active');
  const completedSessions = sessions.filter((s) => s.status !== 'active');

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 60) return `Vor ${diffMin} Min.`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `Vor ${diffHours} Std.`;
    return date.toLocaleDateString('de-CH', { day: 'numeric', month: 'short' });
  };

  const renderSession = (session: WizardSessionSummary) => {
    const isSelected = session.id === currentSessionId;
    const config = STATUS_CONFIG[session.status] || STATUS_CONFIG.active;

    return (
      <Box
        key={session.id}
        onClick={() => onSelectSession(session.id)}
        sx={{
          bgcolor: 'background.paper',
          border: isSelected ? '2px solid #f59e0b' : '1px solid',
          borderColor: isSelected ? '#f59e0b' : 'divider',
          borderRadius: 2,
          p: 1.5,
          mb: 1,
          cursor: 'pointer',
          position: 'relative',
          '&:hover': { borderColor: '#f59e0b' },
          '&:hover .delete-btn': { opacity: 1 },
        }}
      >
        <Typography variant="body2" fontWeight={600} noWrap>
          {session.title || 'Neue Session'}
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
          {formatDate(session.updated_at)} — {session.message_count} Nachrichten
        </Typography>
        <Chip
          label={config.label}
          size="small"
          sx={{ mt: 0.5, bgcolor: config.bgcolor, color: config.color, fontSize: 10, height: 20 }}
        />
        <IconButton
          className="delete-btn"
          size="small"
          onClick={(e) => {
            e.stopPropagation();
            onDeleteSession(session.id);
          }}
          sx={{ position: 'absolute', top: 4, right: 4, opacity: 0, transition: 'opacity 0.2s' }}
        >
          <Delete fontSize="small" />
        </IconButton>
      </Box>
    );
  };

  return (
    <Box
      sx={{
        width: 260,
        borderRight: '1px solid',
        borderColor: 'divider',
        bgcolor: '#f8fafc',
        p: 2,
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <Button
        variant="contained"
        startIcon={<Add />}
        onClick={onNewSession}
        fullWidth
        sx={{ mb: 2, bgcolor: '#f59e0b', '&:hover': { bgcolor: '#d97706' } }}
      >
        Neue Session
      </Button>

      {activeSessions.length > 0 && (
        <>
          <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5, mb: 1 }}>
            Aktive Sessions
          </Typography>
          {activeSessions.map(renderSession)}
        </>
      )}

      {completedSessions.length > 0 && (
        <>
          <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5, mt: 1.5, mb: 1 }}>
            Abgeschlossen
          </Typography>
          {completedSessions.map(renderSession)}
        </>
      )}

      {sessions.length === 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', mt: 4 }}>
          Noch keine Sessions vorhanden
        </Typography>
      )}
    </Box>
  );
};

export default WizardSessionList;
```

- [ ] **Step 2: Create WizardNewSessionDialog**

```tsx
import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  CircularProgress,
} from '@mui/material';
import { useAuth } from '@examcraft/core';
import { promptsApi } from '../../api/promptsApi';

interface WizardNewSessionDialogProps {
  open: boolean;
  onClose: () => void;
  onCreate: (referencePromptId?: string) => void;
}

interface PromptOption {
  id: string;
  name: string;
  use_case?: string;
}

const WizardNewSessionDialog: React.FC<WizardNewSessionDialogProps> = ({
  open,
  onClose,
  onCreate,
}) => {
  const { accessToken } = useAuth();
  const [templates, setTemplates] = useState<PromptOption[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || !accessToken) return;
    setLoading(true);
    promptsApi
      .listPrompts({ category: 'template', is_active: true })
      .then((data) => {
        const prompts = Array.isArray(data) ? data : data.prompts || [];
        setTemplates(prompts.map((p: any) => ({ id: String(p.id), name: p.name, use_case: p.use_case })));
      })
      .catch(() => setTemplates([]))
      .finally(() => setLoading(false));
  }, [open, accessToken]);

  const handleCreate = () => {
    onCreate(selectedTemplate || undefined);
    setSelectedTemplate('');
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Neue Wizard-Session</DialogTitle>
      <DialogContent sx={{ pt: 2 }}>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Optional: Waehle ein bestehendes Template als Ausgangspunkt. Der Wizard
          orientiert sich an Struktur und Stil dieses Templates.
        </Typography>

        {loading ? (
          <CircularProgress size={24} />
        ) : (
          <FormControl fullWidth size="small">
            <InputLabel>Referenz-Template (optional)</InputLabel>
            <Select
              value={selectedTemplate}
              onChange={(e) => setSelectedTemplate(e.target.value)}
              label="Referenz-Template (optional)"
            >
              <MenuItem value="">Kein Referenz-Template</MenuItem>
              {templates.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Abbrechen</Button>
        <Button
          variant="contained"
          onClick={handleCreate}
          sx={{ bgcolor: '#f59e0b', '&:hover': { bgcolor: '#d97706' } }}
        >
          Session starten
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default WizardNewSessionDialog;
```

Note: The `promptsApi.listPrompts` call may need to be adjusted to match the actual API client signature. Check `packages/core/frontend/src/api/promptsApi.ts` for the correct method name and parameters.

- [ ] **Step 3: Commit**

```bash
git add packages/premium/frontend/src/components/PromptWizard/WizardSessionList.tsx packages/premium/frontend/src/components/PromptWizard/WizardNewSessionDialog.tsx
git commit -m "feat(wizard): add WizardSessionList and WizardNewSessionDialog (TF-297)"
```

---

## Task 11: PromptWizardTab + Tab Integration

**Files:**
- Create: `packages/premium/frontend/src/components/PromptWizard/PromptWizardTab.tsx`
- Modify: `packages/premium/frontend/src/components/prompts/PromptLibraryWithUpload.tsx`
- Modify: `packages/core/frontend/src/components/admin/PromptEditor.tsx` (add `initialData` prop)
- Modify: `packages/premium/frontend/src/index.ts`

- [ ] **Step 1: Create PromptWizardTab**

```tsx
import React, { useState, useEffect, useCallback } from 'react';
import { Box, Alert } from '@mui/material';
import { useAuth } from '@examcraft/core';
import WizardService from '../../services/WizardService';
import WizardSessionList from './WizardSessionList';
import WizardChatInterface from './WizardChatInterface';
import WizardNewSessionDialog from './WizardNewSessionDialog';
import type { WizardSession, WizardSessionSummary } from '../../services/WizardService';

interface PromptWizardTabProps {
  onEditInEditor: (data: {
    name: string;
    content: string;
    category: string;
    use_case: string;
    tags: string[];
    description: string;
  }) => void;
}

export const PromptWizardTab: React.FC<PromptWizardTabProps> = ({ onEditInEditor }) => {
  const { accessToken } = useAuth();
  const [sessions, setSessions] = useState<WizardSessionSummary[]>([]);
  const [currentSession, setCurrentSession] = useState<WizardSession | null>(null);
  const [showNewDialog, setShowNewDialog] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSessions = useCallback(async () => {
    if (!accessToken) return;
    try {
      const data = await WizardService.listSessions(accessToken);
      setSessions(data);
    } catch {
      setSessions([]);
    }
  }, [accessToken]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const handleSelectSession = async (sessionId: string) => {
    if (!accessToken) return;
    try {
      const session = await WizardService.getSession(accessToken, sessionId);
      setCurrentSession(session);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Laden der Session');
    }
  };

  const handleCreateSession = async (referencePromptId?: string) => {
    if (!accessToken) return;
    try {
      const session = await WizardService.createSession(accessToken, referencePromptId);
      setCurrentSession(session);
      await loadSessions();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Erstellen der Session');
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    if (!accessToken) return;
    if (!window.confirm('Session wirklich loeschen?')) return;
    try {
      await WizardService.deleteSession(accessToken, sessionId);
      if (currentSession?.id === sessionId) {
        setCurrentSession(null);
      }
      await loadSessions();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Loeschen');
    }
  };

  const handleSessionUpdate = () => {
    loadSessions();
    setCurrentSession(null);
  };

  return (
    <Box sx={{ display: 'flex', height: 520, border: '1px solid', borderColor: 'divider', borderRadius: 2, overflow: 'hidden' }}>
      <WizardSessionList
        sessions={sessions}
        currentSessionId={currentSession?.id}
        onSelectSession={handleSelectSession}
        onNewSession={() => setShowNewDialog(true)}
        onDeleteSession={handleDeleteSession}
      />

      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {error && (
          <Alert severity="error" onClose={() => setError(null)} sx={{ m: 2 }}>
            {error}
          </Alert>
        )}

        {currentSession ? (
          <WizardChatInterface
            session={currentSession}
            onSessionUpdate={handleSessionUpdate}
            onEditInEditor={onEditInEditor}
          />
        ) : (
          <Box
            sx={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'text.secondary',
            }}
          >
            Waehle eine Session oder starte eine neue
          </Box>
        )}
      </Box>

      <WizardNewSessionDialog
        open={showNewDialog}
        onClose={() => setShowNewDialog(false)}
        onCreate={handleCreateSession}
      />
    </Box>
  );
};

export default PromptWizardTab;
```

- [ ] **Step 2: Add tab to PromptLibraryWithUpload.tsx**

In `packages/premium/frontend/src/components/prompts/PromptLibraryWithUpload.tsx`:

1. Add import at top:
```tsx
import { AutoAwesome } from '@mui/icons-material';
import { PromptWizardTab } from '../PromptWizard/PromptWizardTab';
```

2. Update the `ViewMode` type to include `'wizard'`:
```tsx
type ViewMode = 'library' | 'editor' | 'versions' | 'search' | 'upload' | 'wizard';
```

3. Add tab change handler for index 3 → wizard:
```tsx
} else if (newValue === 3) {
  setViewMode('wizard');
}
```

4. Add the Tab component after the Upload tab:
```tsx
<Tab
  icon={<AutoAwesome />}
  iconPosition="start"
  label="KI-Assistent"
  {...a11yProps(3)}
/>
```

5. Add a state variable for pre-filled editor data:
```tsx
const [editorInitialData, setEditorInitialData] = useState<Partial<any> | undefined>();
```

6. Add the TabPanel after the Upload TabPanel:
```tsx
<TabPanel value={currentTab} index={3}>
  <PromptWizardTab
    onEditInEditor={(templateData) => {
      setEditorInitialData({
        name: templateData.name,
        content: templateData.content,
        description: templateData.description,
        category: templateData.category,
        use_case: templateData.use_case,
        tags: templateData.tags,
        is_active: false,
      });
      setSelectedPromptId(undefined);
      setViewMode('editor');
    }}
  />
</TabPanel>
```

7. Pass `editorInitialData` to PromptEditor where it's rendered (in the editor view section). The `PromptEditor` component needs a new optional prop `initialData` that pre-fills the form when no `promptId` is provided. In the existing `PromptEditor` render:
```tsx
<PromptEditor
  promptId={selectedPromptId}
  initialData={editorInitialData}
  onSave={() => { handleSaveComplete(); setEditorInitialData(undefined); }}
  onCancel={() => { handleCancel(); setEditorInitialData(undefined); }}
/>
```

8. In `packages/core/frontend/src/components/admin/PromptEditor.tsx`, add the `initialData` prop to the interface and use it in the `useEffect` that initializes the form:
```tsx
interface PromptEditorProps {
  promptId?: string;
  initialData?: Partial<Prompt>;  // NEW: pre-fill from wizard
  onSave?: () => void;
  onCancel?: () => void;
}
```

In the component, add a `useEffect` that sets `formData` from `initialData` when present and no `promptId`:
```tsx
useEffect(() => {
  if (!promptId && initialData) {
    setFormData(prev => ({ ...prev, ...initialData }));
  }
}, [promptId, initialData]);
```

- [ ] **Step 3: Add export to index.ts**

In `packages/premium/frontend/src/index.ts`, add:
```tsx
export { PromptWizardTab } from './components/PromptWizard/PromptWizardTab';
```

- [ ] **Step 4: Commit**

```bash
git add packages/premium/frontend/src/components/PromptWizard/PromptWizardTab.tsx packages/premium/frontend/src/components/prompts/PromptLibraryWithUpload.tsx packages/core/frontend/src/components/admin/PromptEditor.tsx packages/premium/frontend/src/index.ts
git commit -m "feat(wizard): add PromptWizardTab and integrate into Prompt Library (TF-297)"
```

---

## Task 12: Manual Integration Test

- [ ] **Step 1: Start development environment**

Run: `./start-dev.sh --full`

- [ ] **Step 2: Verify backend loads wizard router**

Check logs: `docker compose --env-file .env -f docker-compose.full.yml logs -f backend | grep -i wizard`

Expected: No import errors, router registered.

- [ ] **Step 3: Test API endpoints**

Run: Get a valid access token, then test:
```bash
# Create session
curl -X POST http://localhost:8000/api/v1/wizard/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' | python -m json.tool

# Send message
curl -X POST http://localhost:8000/api/v1/wizard/sessions/$SESSION_ID/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Informatik, Datenbanken und SQL"}' | python -m json.tool
```

- [ ] **Step 4: Test frontend**

Navigate to http://localhost:3000 → Prompt Library → KI-Assistent tab. Verify:
- Tab visible and clickable
- "Neue Session" button works
- Chat dialog starts with AI welcome message
- Quick-select chips render and are clickable
- Messages send and AI responds

- [ ] **Step 5: Test full flow**

Complete a full wizard session:
1. Start session → answer questions → wait for `ready_to_generate`
2. Click "Template generieren"
3. Review preview
4. Test "So speichern" → verify prompt appears in Prompt Library
5. Start another session → test "Im Editor bearbeiten" flow

- [ ] **Step 6: Commit any fixes**

```bash
git add -A
git commit -m "fix(wizard): integration test fixes (TF-297)"
```
