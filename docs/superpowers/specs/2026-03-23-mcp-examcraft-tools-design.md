# MCP ExamCraft Tools Design

**Issue:** TF-290
**Date:** 2026-03-23
**Status:** Approved
**Depends on:** TF-289 (MCP Facade Server — Done)

## Summary

Implement five ExamCraft-specific MCP tools as an extension of the existing MCP Facade Server. These tools expose core ExamCraft features (document management, question generation, semantic search) via claude.ai, Claude Desktop, and Claude Code.

## Goals

- Enable ExamCraft users to manage documents, generate questions, and search the knowledge base via MCP
- Enforce the same RBAC/subscription-tier permissions as the web app
- Follow the established `BaseTool` pattern from TF-289

## Non-Goals

- New authentication mechanisms (uses existing MCP OAuth/Bearer token auth)
- Admin-level bulk operations
- Streaming question generation responses

## Tools

| Tool | File | Permission | Notes |
|------|------|------------|-------|
| `documents-list` | `examcraft_documents.py` | `view_documents` | Paginated, user-scoped |
| `documents-upload` | `examcraft_documents.py` | `create_documents` | URL-based download |
| `questions-generate` | `examcraft_questions.py` | `generate_questions` | Via RAG service |
| `questions-list` | `examcraft_questions.py` | `view_questions` | Paginated, user-scoped |
| `knowledge-search` | `examcraft_search.py` | `view_documents` | Full deployment only |

## Architecture

### Approach: Direct Service Import

Tools import backend services directly (same process), consistent with the existing `db_query.py` pattern. No HTTP overhead. Full reuse of existing business logic including RBAC and quota enforcement.

```
MCP Request
    └── Tool.execute(arguments, context)
            ├── _resolve_user(context, session)   # email → User
            ├── _check_permission(user, perm, db)  # RBAC check
            └── service.method(...)                # Business logic
```

### File Structure

New files under `packages/premium/backend/mcp/tools/`:

```
tools/
├── examcraft_documents.py   # documents-list, documents-upload
├── examcraft_questions.py   # questions-generate, questions-list
└── examcraft_search.py      # knowledge-search
```

Updated file:
```
tools/__init__.py            # Register new tools; conditional for knowledge-search
```

### Auth Helper Pattern

All ExamCraft tools use a shared helper at the top of each file:

```python
def _resolve_user(context: dict, session) -> User:
    """Load User from DB by email in MCP context. Raises PermissionError if not found."""
    email = context.get("email") if context else None
    if not email:
        raise PermissionError("Authentication required")
    user = session.query(User).filter(User.email == email).first()
    if not user:
        raise PermissionError(f"User not found: {email}")
    return user

def _check_permission(user: User, permission: str, session) -> None:
    """Check RBAC permission. Raises PermissionError if denied."""
    from utils.auth_utils import check_user_permission
    if not check_user_permission(user, permission, session):
        raise PermissionError(
            f"Permission denied: '{permission}' requires a higher subscription tier"
        )
```

## Tool Specifications

### `documents-list`

```python
name = "documents-list"
description = "List uploaded documents in ExamCraft"
input_schema = {
    "type": "object",
    "properties": {
        "limit":  {"type": "integer", "default": 20, "maximum": 100},
        "offset": {"type": "integer", "default": 0},
    },
}
```

**Implementation:**
1. Resolve user from context
2. Check `view_documents` permission
3. Query `Document` model filtered by `user_id`, apply `limit`/`offset`
4. Return list of `{id, title, filename, status, file_size, created_at}`

### `documents-upload`

```python
name = "documents-upload"
description = "Upload a document to ExamCraft by URL"
input_schema = {
    "type": "object",
    "properties": {
        "url":      {"type": "string", "description": "Public URL of the file to download"},
        "filename": {"type": "string", "description": "Optional filename override"},
    },
    "required": ["url"],
}
```

**Implementation:**
1. Resolve user from context
2. Check `create_documents` permission
3. Download file with `httpx.AsyncClient` (timeout 60s, follow redirects)
4. Derive filename from URL or `filename` argument
5. Wrap content in a minimal `UploadFile`-compatible object
6. Call `document_service.upload_document(file, user_id=user.id, db=session)`
7. Return `{document_id, filename, status, message}`

**Error cases:**
- URL not reachable → `ValueError: "Could not download file from URL: <reason>"`
- Unsupported MIME type → propagated from `document_service`
- File too large (>50 MB) → propagated from `document_service`

### `questions-generate`

```python
name = "questions-generate"
description = "Generate exam questions from documents using RAG"
input_schema = {
    "type": "object",
    "properties": {
        "topic":          {"type": "string", "description": "Exam topic"},
        "document_ids":   {"type": "array", "items": {"type": "integer"}, "description": "Optional document filter"},
        "question_count": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
        "difficulty":     {"type": "string", "enum": ["easy", "medium", "hard"], "default": "medium"},
        "language":       {"type": "string", "default": "de"},
    },
    "required": ["topic"],
}
```

**Implementation:**
1. Resolve user from context
2. Check `generate_questions` permission
3. Build `RAGExamRequest` from arguments
4. Call `rag_service.generate_exam(request, user_id=str(user.id))`
5. Return list of `{question_text, question_type, options, correct_answer, difficulty, explanation}`

### `questions-list`

```python
name = "questions-list"
description = "List generated exam questions"
input_schema = {
    "type": "object",
    "properties": {
        "limit":  {"type": "integer", "default": 20, "maximum": 100},
        "offset": {"type": "integer", "default": 0},
        "status": {"type": "string", "enum": ["pending", "approved", "rejected"], "description": "Optional status filter"},
    },
}
```

**Implementation:**
1. Resolve user from context
2. Check `view_questions` permission
3. Query `QuestionReview` filtered by `user_id`, optional `review_status`, apply pagination
4. Return list of `{id, question_text, question_type, difficulty, review_status, created_at}`

### `knowledge-search`

```python
name = "knowledge-search"
description = "Semantic search in the ExamCraft knowledge base (Full deployment only)"
input_schema = {
    "type": "object",
    "properties": {
        "query":        {"type": "string", "description": "Search query"},
        "n_results":    {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
        "document_ids": {"type": "array", "items": {"type": "integer"}, "description": "Optional document filter"},
    },
    "required": ["query"],
}
```

**Implementation:**
1. Resolve user from context
2. Check `view_documents` permission
3. Call `vector_service.search(query, n_results, document_ids)`
4. Return list of `{content, similarity_score, filename, chunk_index}`

**Deployment guard** — in `tools/__init__.py`:
```python
import os
if os.getenv("DEPLOYMENT_MODE", "core") == "full":
    from .examcraft_search import ExamcraftKnowledgeSearchTool
    _register(ExamcraftKnowledgeSearchTool())
```

## Tool Registry Update

`tools/__init__.py` additions:

```python
from .examcraft_documents import ExamcraftDocumentsListTool, ExamcraftDocumentsUploadTool
from .examcraft_questions import ExamcraftQuestionsGenerateTool, ExamcraftQuestionsListTool

# In get_tool_registry():
_register(ExamcraftDocumentsListTool())
_register(ExamcraftDocumentsUploadTool())
_register(ExamcraftQuestionsGenerateTool())
_register(ExamcraftQuestionsListTool())

# Conditional — Full deployment only:
if os.getenv("DEPLOYMENT_MODE", "core") == "full":
    from .examcraft_search import ExamcraftKnowledgeSearchTool
    _register(ExamcraftKnowledgeSearchTool())
```

## Error Handling

| Exception | Meaning | Handling |
|-----------|---------|----------|
| `PermissionError` | Not authenticated or no permission | Re-raise (MCP protocol surfaces as error) |
| `ValueError` | Invalid arguments (bad URL, unsupported format) | Re-raise with descriptive message |
| All others | Unexpected service/DB errors | Log with `logger.error(..., exc_info=True)`, re-raise |

DB sessions are always closed in a `finally` block.

## Testing

New file: `packages/premium/backend/mcp/tests/test_examcraft_tools.py`

| Test | What it checks |
|------|----------------|
| `test_documents_list_returns_user_scoped_results` | Only returns documents belonging to the authenticated user |
| `test_documents_list_pagination` | `limit` and `offset` are applied correctly |
| `test_documents_list_no_auth` | Raises `PermissionError` when context is empty |
| `test_documents_upload_downloads_and_saves` | `httpx` download + `document_service.upload_document` called correctly |
| `test_documents_upload_bad_url` | Raises `ValueError` on unreachable URL |
| `test_questions_generate_calls_rag_service` | `rag_service.generate_exam` called with correct `RAGExamRequest` |
| `test_questions_list_status_filter` | `status` argument filters `review_status` correctly |
| `test_knowledge_search_calls_vector_service` | `vector_service.search` called with correct arguments |
| `test_knowledge_search_not_registered_in_core_mode` | Tool absent from registry when `DEPLOYMENT_MODE=core` |
