# Document ChatBot Feature (TF-111)

## Übersicht

Der **Document ChatBot** ist ein interaktives RAG-basiertes Konversations-Interface, das es Benutzern ermöglicht, natürlichsprachliche Fragen zu hochgeladenen Dokumenten zu stellen und kontextuelle Antworten mit Quellenangaben zu erhalten.

## Features

### 🤖 Interaktive Konversationen

- **Real-time Chat**: Sofortige Antworten auf Fragen zu Dokumenten
- **Context-Aware**: Nutzt RAG (Retrieval-Augmented Generation) für präzise Antworten
- **Source Citations**: Automatische Quellenangaben mit Seitenzahlen
- **Multi-Document Support**: Chat mit mehreren Dokumenten gleichzeitig
- **Chat History**: Persistente Speicherung aller Konversationen

### 💾 Chat-Export Funktionalität

- **Markdown Export**: Konversationen als formatierte Markdown-Dateien
- **Document Library Integration**: Exportierte Chats erscheinen in der Dokumentenbibliothek
- **Full Content Storage**: Vollständiger Chat-Verlauf in Metadaten gespeichert
- **Automatic Titling**: Intelligente Titel-Generierung aus Chat-Kontext
- **Download Option**: Direkter Download als `.md` Datei

### 📊 Session Management

- **Multiple Sessions**: Mehrere parallele Chat-Sessions
- **Session Persistence**: Automatisches Speichern in PostgreSQL
- **Session History**: Übersicht aller vergangenen Konversationen
- **Session Metadata**: Titel, Erstellungsdatum, Nachrichtenanzahl

## Architektur

### Backend Services

```
backend/
├── api/v1/chat.py              # REST API Endpoints
├── services/
│   ├── chatbot_service.py      # PydanticAI Chat Logic
│   ├── chat_export_service.py  # Conversation Export
│   └── document_service.py     # Enhanced with Chat Support
└── models/
    ├── chat_db.py              # ChatSession & ChatMessage Models
    └── document.py             # Enhanced Document Model
```text

### Frontend Components

```
frontend/src/
├── components/
│   ├── ChatInterface.tsx       # Main Chat UI
│   ├── ChatSidebar.tsx         # Session Management
│   ├── MessageList.tsx         # Conversation Display
│   └── ChatInput.tsx           # Message Input
└── services/
    └── chatService.ts          # API Client
```text

### Database Schema

#### ChatSession Table

```sql
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY,
    user_id VARCHAR(100),
    document_ids INTEGER[],
    title VARCHAR(255),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    is_exported_as_document BOOLEAN,
    exported_document_id INTEGER
);
```text

#### ChatMessage Table

```sql
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES chat_sessions(id),
    role VARCHAR(20),  -- 'user' or 'assistant'
    content TEXT,
    timestamp TIMESTAMP,
    sources JSONB,
    confidence FLOAT
);
```text

## API Endpoints

### Chat Session Management

#### Create Session

```http
POST /api/v1/chat/sessions
Content-Type: application/json

{
  "document_ids": [1, 2, 3],
  "title": "Optional Session Title"
}
```text

#### Get Session

```http
GET /api/v1/chat/sessions/{session_id}
```text

#### List Sessions

```http
GET /api/v1/chat/sessions
```text

### Chat Interaction

#### Send Message

```http
POST /api/v1/chat/message
Content-Type: application/json

{
  "session_id": "uuid",
  "message": "What is the main topic of this document?"
}
```text

**Response:**

```json
{
  "content": "The main topic is...",
  "sources": [
    {
      "document_id": 1,
      "document_title": "Example.pdf",
      "page_number": 5,
      "relevance_score": 0.95
    }
  ],
  "confidence": 0.92
}
```text

### Export Functions

#### Export to Document

```http
POST /api/v1/chat/sessions/{session_id}/to-document
Content-Type: application/json

{
  "document_title": "Optional Custom Title"
}
```text

#### Download as Markdown

```http
GET /api/v1/chat/sessions/{session_id}/download
```text

## Implementation Details

### RAG Pipeline

1. **User Query** → Semantic Search in Vector DB
2. **Context Retrieval** → Top-K relevant document chunks
3. **Prompt Construction** → Query + Context + Chat History
4. **Claude API Call** → Generate contextual response
5. **Source Attribution** → Map response to source documents
6. **Response Storage** → Save to PostgreSQL

### Chat Export Format

```markdown
# Chat: Session Title

**Erstellt am:** 2025-01-09 14:30:00  
**Dokumente:** Example.pdf, Tutorial.docx

---

## Konversation

### 👤 User (14:30:15)
What is the main topic?

### 🤖 Assistant (14:30:18)
The main topic is...

**Quellen:**
- Example.pdf (Seite 5)
- Tutorial.docx (Seite 2)

---

### 👤 User (14:31:22)
Can you explain more?

### 🤖 Assistant (14:31:25)
Certainly! ...
```text

### Document Model Enhancement

```python
class Document(Base):
    __tablename__ = "documents"
    
    # ... existing fields ...
    
    doc_metadata = Column(JSONB, nullable=True)
    
    @property
    def title(self) -> str:
        """
        Dynamic title property:
        1. Reads from doc_metadata["title"] if available
        2. Falls back to original_filename
        """
        if self.doc_metadata and "title" in self.doc_metadata:
            return self.doc_metadata["title"]
        return self.original_filename or "Untitled"
```text

## Testing

### Test Coverage

- **Chat API Tests**: 3 tests (100% pass rate)
  - `test_convert_chat_to_document_with_user_id`
  - `test_convert_chat_to_document_full_content`
  - `test_convert_chat_to_document_metadata`

- **Document Model Tests**: 6 tests (100% pass rate)
  - `test_document_title_property_from_metadata`
  - `test_document_title_property_fallback_to_filename`
  - `test_document_to_dict_uses_title_property`
  - `test_chat_export_document_structure`

- **Document Service Tests**: 2 chat-export tests (100% pass rate)
  - `test_get_full_document_content_chat_export`
  - `test_get_full_document_content_chat_export_fallback`

### Running Tests

```bash
# All ChatBot-related tests
docker exec examcraft_backend pytest tests/test_chat_api.py -v

# Document model tests
docker exec examcraft_backend pytest tests/test_document_model.py -v

# Integration tests
docker exec examcraft_backend pytest -m integration -v
```text

## Configuration

### Environment Variables

```bash
# Claude API Configuration
CLAUDE_API_KEY=your_api_key_here
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# Chat Settings
MAX_CHAT_HISTORY=10          # Maximum messages in context
CHAT_TIMEOUT_SECONDS=30      # Response timeout
```text

### Feature Flags

```python
# backend/config.py
ENABLE_CHAT_EXPORT = True
ENABLE_CHAT_DOWNLOAD = True
MAX_SESSIONS_PER_USER = 50
```text

## Usage Examples

### Frontend Integration

```typescript
import { chatService } from '@/services/chatService';

// Create session
const session = await chatService.createSession({
  document_ids: [1, 2],
  title: "My Research Chat"
});

// Send message
const response = await chatService.sendMessage({
  session_id: session.id,
  message: "What are the key findings?"
});

// Export to document
const doc = await chatService.exportToDocument(session.id);
```text

## Known Limitations

- Maximum 10 messages in chat history context (configurable)
- Claude API rate limits apply (10 requests/minute on free tier)
- Large documents may require chunking for context window
- Export limited to Markdown format (PDF export planned)

## Future Enhancements

- [ ] Multi-language support
- [ ] Voice input/output
- [ ] PDF export with formatting
- [ ] Chat templates for common questions
- [ ] Advanced filtering in session list
- [ ] Collaborative chat sessions
- [ ] Export to other formats (DOCX, HTML)

## Related Documentation

- [Testing Guide](../development/TESTING.md)
- [API Documentation](http://localhost:8000/docs)
- [Deployment Guide](../deployment/RENDER-DEPLOYMENT.md)

## Contributors

- Daniel Senften (@dsenften) - Lead Developer
- Talent Factory Team

## License

MIT License - See LICENSE file for details
