# Prompt Wizard — Design Specification

## Problem Statement

Creating a good prompt template for exam question generation is a difficult task for teachers and lecturers without AI experience. The current PromptEditor provides a raw textarea where users must write complex Markdown templates (like the 98-line `question_generator_academic.md` reference) from scratch. This creates a high barrier to entry.

## Solution

An AI-guided chat dialog ("Prompt Wizard") that interviews the user step by step, collecting all necessary information through natural conversation, then generates a complete prompt template automatically. The wizard uses Claude API to conduct an adaptive dialog — asking one question at a time and adjusting follow-up questions based on the user's answers.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Target audience | Teachers without AI experience | Wizard must hide all prompt-engineering complexity |
| UI placement | New tab in Prompt Library | Consistent with existing tab pattern (Prompt-Liste, Semantic Search, Datei-Upload) |
| AI engine | Claude API directly (PydanticAI) | Adaptive dialog, reuses existing integration |
| After generation | User chooses: save directly or open in editor | Flexibility for all skill levels |
| Session history | Full history persisted | Traceability of how templates were created |
| Dialog flow | Adaptive (Claude decides when enough info is collected) | More natural conversation than rigid question trees |
| Reference templates | Optional selection + few-shot in system prompt | Leverages existing high-quality templates as examples |
| Architecture | Standalone Wizard Service | Clean separation, follows DocumentChat pattern |

## UI Design

### Tab Integration

The wizard is integrated as a fourth tab ("KI-Assistent") in the Premium `PromptLibraryWithUpload` component. It is a Premium-only feature — the Core package does not include it.

### Layout

Two-panel layout within the tab:

- **Left panel (260px)**: Session sidebar
  - "Neue Session" button at top
  - Active sessions with "In Bearbeitung" badge
  - Completed sessions with "Gespeichert" badge
  - Click to load/resume a session

- **Right panel (flex)**: Chat area
  - Scrollable message area with AI/User bubbles
  - AI messages: white background, left-aligned with AI avatar
  - User messages: amber background, right-aligned with user avatar
  - Quick-select chips rendered below AI messages when provided
  - Input area at bottom: textarea + send button

### Special UI Elements

- **Quick-Select Chips**: Clickable option buttons that Claude can include in responses (e.g., question types, difficulty levels). User can always type freely instead.
- **Template Preview**: When generation is complete, the AI message contains a rendered Markdown preview of the template with two action buttons: "So speichern" and "Im Editor bearbeiten".
- **New Session Dialog**: Optional reference template selector (dropdown of active templates from the Prompt Library).

## Backend Architecture

### Data Model

#### Table: `wizard_sessions`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default uuid4 | Session identifier |
| `user_id` | UUID | FK → users, NOT NULL | Session owner |
| `title` | String(255) | | Auto-generated from first user answer |
| `status` | String(50) | CHECK IN ('active', 'completed', 'cancelled') | Session lifecycle state |
| `reference_prompt_id` | UUID | FK → prompts, nullable | Optional template used as starting point |
| `generated_prompt_id` | UUID | FK → prompts, nullable | The prompt created by this session |
| `collected_parameters` | JSONB | default {} | Structured data extracted during dialog |
| `created_at` | DateTime | default now | |
| `updated_at` | DateTime | default now, onupdate now | |

#### Table: `wizard_messages`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default uuid4 | Message identifier |
| `session_id` | UUID | FK → wizard_sessions, NOT NULL | Parent session |
| `role` | String(50) | CHECK IN ('system', 'assistant', 'user') | Message sender |
| `content` | Text | NOT NULL | Message content |
| `message_metadata` | JSONB | default {} | Quick-select options, extracted params, flags |
| `created_at` | DateTime | default now | |

### API Endpoints

All endpoints require authentication. Scoped to the authenticated user's sessions.

```
POST   /api/v1/wizard/sessions              — Create new session
GET    /api/v1/wizard/sessions              — List user's sessions
GET    /api/v1/wizard/sessions/{id}         — Get session with messages
POST   /api/v1/wizard/sessions/{id}/chat    — Send message, receive AI response
POST   /api/v1/wizard/sessions/{id}/generate — Generate template from collected params
POST   /api/v1/wizard/sessions/{id}/save    — Save generated template to Prompt Library
DELETE /api/v1/wizard/sessions/{id}         — Delete session
```

#### POST /api/v1/wizard/sessions

Request:
```json
{
  "reference_prompt_id": "uuid-optional"
}
```

Response:
```json
{
  "id": "uuid",
  "title": "Neue Session",
  "status": "active",
  "messages": [
    {
      "role": "assistant",
      "content": "Willkommen beim Prompt-Assistenten! ...",
      "message_metadata": {}
    }
  ]
}
```

The service creates the session, assembles the system prompt (with few-shot references), sends the initial prompt to Claude, and returns the first AI message.

#### POST /api/v1/wizard/sessions/{id}/chat

Request:
```json
{
  "message": "Informatik, speziell Datenbanken und SQL"
}
```

Response:
```json
{
  "role": "assistant",
  "content": "Welchen Fragetyp moechtest du generieren?",
  "message_metadata": {
    "quick_options": ["Multiple Choice", "Offene Frage", "Code-Vervollstaendigung", "Wahr/Falsch"],
    "ready_to_generate": false
  }
}
```

The `ready_to_generate` flag signals to the frontend that Claude has collected enough information. The frontend then shows a "Template generieren" button.

#### POST /api/v1/wizard/sessions/{id}/generate

No request body. Uses the full conversation history and collected parameters to generate the template.

Response:
```json
{
  "template_preview": "# Pruefungsfragen-Generator...\n\n## Aufgabe\n...",
  "suggested_name": "SQL Datenbanken MC-Fragen",
  "suggested_category": "template",
  "suggested_use_case": "question_generation_multiple_choice",
  "suggested_tags": ["sql", "datenbanken", "bsc-informatik"]
}
```

#### POST /api/v1/wizard/sessions/{id}/save

Saves the generated template to the Prompt Library. Only valid when the session has a generated template (after `/generate`).

Request:
```json
{
  "name": "SQL Datenbanken MC-Fragen",
  "category": "template",
  "use_case": "question_generation_multiple_choice",
  "tags": ["sql", "datenbanken", "bsc-informatik"],
  "description": "Generiert via KI-Assistent"
}
```

The `content` field is taken from the generated template stored in the session. The request body allows the user to override the suggested metadata. Returns the created Prompt object. Updates session status to `completed` and sets `generated_prompt_id`.

### Service Layer: PromptWizardService

Located at `packages/premium/backend/services/prompt_wizard_service.py`.

Responsibilities:

1. **System Prompt Assembly**: Builds the system prompt dynamically:
   - Base instructions (role, behavior, one-question-at-a-time rule)
   - Few-shot references: Top 1-2 active templates from Prompt Library (by usage_count or curated selection)
   - Optional: Content of the user-selected reference template
   - Output format instructions (JSON with message + quick_options + ready_to_generate)

2. **Chat Handling**: Maintains the full conversation history. On each `/chat` call:
   - Appends user message to DB
   - Sends full history (system + all messages) to Claude via PydanticAI
   - Parses Claude's structured response
   - Extracts `collected_parameters` from Claude's structured JSON response (Claude includes a `parameters` field alongside `message` and `quick_options`)
   - Saves assistant message to DB
   - Returns structured response to frontend

3. **Template Generation**: On `/generate`:
   - Builds a generation prompt combining all collected parameters
   - Includes the few-shot reference template structure
   - Calls Claude to generate the complete Markdown template
   - Returns preview + suggested metadata (name, category, use_case, tags)

4. **Template Saving**: When the user confirms "So speichern":
   - Creates a new Prompt record via the existing `prompt_service`
   - Links it to the session via `generated_prompt_id`
   - Updates session status to `completed`

## Frontend Architecture

### Component Structure

```
packages/premium/frontend/src/components/PromptWizard/
├── PromptWizardTab.tsx          — Main component (tab content, orchestrates layout)
├── WizardSessionList.tsx        — Left sidebar with session list
├── WizardChatInterface.tsx      — Chat area (messages + input)
├── WizardMessageBubble.tsx      — Single message bubble (AI/User styling)
├── WizardQuickOptions.tsx       — Clickable chip buttons
├── WizardTemplatePreview.tsx    — Markdown preview + save/edit buttons
├── WizardNewSessionDialog.tsx   — New session dialog with reference template selector
└── WizardService.ts             — API client for wizard endpoints
```

### Integration Point

`PromptLibraryWithUpload.tsx` adds the fourth tab:

```tsx
<Tab label="KI-Assistent" icon={<AutoAwesome />} {...a11yProps(3)} />
```

```tsx
<TabPanel value={currentTab} index={3}>
  <PromptWizardTab
    onEditInEditor={(templateData) => {
      setFormData(templateData);
      setViewMode('editor');
    }}
  />
</TabPanel>
```

### State Management

- Session list and current session managed in `PromptWizardTab` via `useState`
- Chat messages managed in `WizardChatInterface` with optimistic updates (user message appears immediately, AI message after response)
- Loading state during AI response (typing indicator)

### "Im Editor bearbeiten" Flow

When the user clicks "Im Editor bearbeiten":
1. `WizardTemplatePreview` calls `onEditInEditor` with pre-filled data:
   ```ts
   {
     name: suggested_name,
     content: template_preview,
     category: suggested_category,
     use_case: suggested_use_case,
     tags: suggested_tags,
     description: "Generiert via KI-Assistent"
   }
   ```
2. `PromptLibraryWithUpload` switches to editor view with this data pre-filled
3. User can modify and save normally via the existing PromptEditor

### Visual Consistency

The chat UI follows the same visual patterns as `DocumentChat/ChatInterface.tsx`:
- Auto-scroll to newest message
- Role-based avatar styling
- Loading indicator during AI response
- Consistent spacing and typography

But it is a separate implementation due to different logic requirements (quick-options, template generation, parameter tracking).

## Scope and Constraints

### In Scope (MVP)
- Wizard chat dialog with Claude API
- Session persistence with full history
- Adaptive dialog flow with quick-select options
- Template generation with Markdown preview
- Save directly or open in editor
- Optional reference template selection
- Few-shot references in system prompt

### Out of Scope
- Streaming responses (can be added later)
- Template versioning within wizard (iterating on generated template via chat)
- Multi-language wizard dialog (German only for MVP)
- Wizard in Core package (Premium only)
- RAG integration in wizard (using uploaded documents as context for template creation)

### Technical Constraints
- Claude API costs per wizard session (estimated 3-8 API calls per session)
- System prompt size with few-shot references (monitor token usage)
- PydanticAI structured output parsing for quick-options format
