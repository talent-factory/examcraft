# MCP ExamCraft Tools Design

**Issue:** TF-290
**Date:** 2026-03-23
**Status:** Approved
**Depends on:** TF-289 (MCP Facade Server — Done)

## Summary

Implement five ExamCraft-specific MCP tools as an extension of the existing MCP Facade Server. These tools expose core ExamCraft features (document management, question generation, semantic search) via claude.ai, Claude Desktop, and Claude Code.

## Goals

- Enable ExamCraft users to manage documents, generate questions, and search the knowledge base via MCP
- Enforce the same RBAC/subscription-tier permissions and quota limits as the web app
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
| `questions-generate` | `examcraft_questions.py` | `generate_questions` | Via RAG service + quota check |
| `questions-list` | `examcraft_questions.py` | `view_questions` | Paginated, user-scoped |
| `knowledge-search` | `examcraft_search.py` | `view_documents` | Full deployment only |

## Architecture

### Approach: Direct Service Import

Tools import backend services directly (same process), consistent with the existing `db_query.py` pattern. No HTTP overhead. Full reuse of existing business logic including RBAC and quota enforcement.

```
MCP Request
    └── Tool.execute(arguments, context)
            ├── _resolve_user(context, session)        # email → User (with roles eager-loaded)
            ├── _check_permission(user, perm)           # user.has_permission()
            └── service.method(...)                     # Business logic
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

All ExamCraft tools use shared helpers defined once per file:

```python
from sqlalchemy.orm import joinedload
from models.auth import User

def _resolve_user(context: dict, session) -> User:
    """Load User (with roles eager-loaded) from DB by email in MCP context.
    Raises PermissionError if not authenticated or user not found.
    """
    email = context.get("email") if context else None
    if not email:
        raise PermissionError("Authentication required")
    user = (
        session.query(User)
        .options(joinedload(User.roles))
        .filter(User.email == email)
        .first()
    )
    if not user:
        raise PermissionError(f"User not found: {email}")
    return user

def _check_permission(user: User, permission: str) -> None:
    """Check RBAC permission via User.has_permission().
    Raises PermissionError if denied.
    """
    if not user.has_permission(permission):
        raise PermissionError(
            f"Permission denied: '{permission}' is not available on your current plan"
        )
```

**Note:** `User.has_permission()` iterates `user.roles`. The `joinedload(User.roles)` in `_resolve_user` ensures roles are loaded within the same session query, avoiding N+1 queries and `DetachedInstanceError`.

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
1. Open `SessionLocal()`, resolve user (with `joinedload(User.roles)`)
2. Check `view_documents` permission
3. Query `Document` model filtered by `user_id=user.id`, apply `limit`/`offset`
4. Access `document.title` (computed Python property from `doc_metadata`, not a DB column — requires ORM-level access)
5. Return list of `{id, title, filename, status, file_size, created_at}`

**Scoping:** Intentionally user-scoped only (by `user_id`), not institution-scoped. This matches the self-service nature of the MCP interface. Institution-wide views are out of scope for this issue.

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
1. Open `SessionLocal()`, resolve user
2. Check `create_documents` permission
3. Download file with `httpx.AsyncClient` (timeout 60s, `follow_redirects=True`)
   - On any HTTP/connection error: raise `ValueError(f"Could not download file from URL: {reason}")`
4. Derive filename: use `filename` argument if provided, otherwise extract from URL using `urllib.parse.urlparse` + `os.path.basename`. If the result has no file extension (e.g. presigned S3 URLs), raise `ValueError("Could not determine filename from URL — provide an explicit filename")`
5. Wrap content in a minimal `UploadFile`-compatible object (`SpooledTemporaryFile` or `io.BytesIO`)
6. Call `document_service.upload_document(file, user_id=user.id, db=session)`
   - `document_service` raises `HTTPException` for unsupported MIME type or file too large. Catch `HTTPException` and re-raise as `ValueError(exc.detail)` to keep the MCP error surface consistent
7. Return `{document_id, filename, status, message}`

**Post-upload note:** `upload_document` creates a DB record with status `UPLOADED`. The actual content processing (Docling text extraction, vector embedding via Celery) runs asynchronously. The document will not appear in `knowledge-search` results until processing completes. Callers should poll `documents-list` until `status == "processed"`.

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
1. Open `SessionLocal()`, resolve user
2. Check `generate_questions` permission
3. Check monthly quota via `RBACService(db=session).check_resource_quota(institution_id=user.institution_id, resource_type="questions", requested_amount=1)` — same enforcement as the web API. If `result["allowed"]` is `False`, raise `ValueError` with the quota detail message. **Note:** Confirm with the DB seed that the `resource_type` key is `"questions"` (the service docs also mention `"questions_per_month"` as an example — use whichever matches the seeded `TierQuota` rows).
4. Build `RAGExamRequest(topic=..., document_ids=..., question_count=..., difficulty=..., language=...)`
5. `await rag_service.generate_rag_exam(request)` (premium method — **not** `generate_exam`; it is `async`, so `execute()` must also be `async` and must `await` this call)
6. On successful generation, call `RBACService(db=session).increment_resource_usage(institution_id=user.institution_id, resource_type="questions", amount=len(questions))` to update the usage counter. Without this step the quota check will always pass regardless of prior usage.
7. Return list of `{question_text, question_type, options, correct_answer, difficulty, explanation, source_documents, confidence_score}`. Source attribution fields (`source_documents`, `confidence_score`) are included as they help users trace question origins.

### `questions-list`

```python
name = "questions-list"
description = "List generated exam questions"
input_schema = {
    "type": "object",
    "properties": {
        "limit":  {"type": "integer", "default": 20, "maximum": 100},
        "offset": {"type": "integer", "default": 0},
        "status": {
            "type": "string",
            "enum": ["pending", "approved", "rejected", "edited", "in_review"],
            "description": "Optional status filter"
        },
    },
}
```

**Implementation:**
1. Open `SessionLocal()`, resolve user
2. Check `view_questions` permission
3. Query `QuestionReview` filtered by `created_by=user.id` (**not** `user_id` — the correct FK column is `created_by`)
4. If `status` argument provided, add filter `review_status == status`
5. Apply `limit`/`offset`
6. Return list of `{id, question_text, question_type, difficulty, review_status, created_at}`

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
1. Open `SessionLocal()`, resolve user
2. Check `view_documents` permission
3. Call `vector_service.similarity_search(query, n_results, document_ids)` (**not** `search` — the correct method on `QdrantVectorService` is `similarity_search`)
4. Return list of `{content, similarity_score, filename, chunk_index}`. Note: `filename` must be sourced from `result.metadata["filename"]`, not a direct `SearchResult` attribute (which has no `.filename` field).

**Deployment guard** — evaluated lazily inside `get_tool_registry()` (not at module import time, to ensure correct behavior in tests when `DEPLOYMENT_MODE` is patched via `monkeypatch.setenv`):

```python
# Inside get_tool_registry(), after other registrations:
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

# In get_tool_registry(), inside the `if not _initialized:` block:
_register(ExamcraftDocumentsListTool())
_register(ExamcraftDocumentsUploadTool())
_register(ExamcraftQuestionsGenerateTool())
_register(ExamcraftQuestionsListTool())

# knowledge-search: conditional, evaluated at registry-init time (not import time)
import os
if os.getenv("DEPLOYMENT_MODE", "core") == "full":
    from .examcraft_search import ExamcraftKnowledgeSearchTool
    _register(ExamcraftKnowledgeSearchTool())
```

## Error Handling

| Exception | Meaning | Handling |
|-----------|---------|----------|
| `PermissionError` | Not authenticated, user not found, or no RBAC permission | Re-raise (MCP protocol surfaces as error) |
| `ValueError` | Invalid arguments (bad URL, no extension, unsupported format, quota exceeded) | Re-raise with descriptive message |
| `HTTPException` (from `document_service`) | Unsupported MIME type, file too large | Catch and re-raise as `ValueError(exc.detail)` |
| All others | Unexpected service/DB errors | Log with `logger.error(..., exc_info=True)`, re-raise |

DB sessions are always opened at the start of `execute()` and closed in a `finally` block.

## Testing

New file: `packages/premium/backend/mcp/tests/test_examcraft_tools.py`

| Test | What it checks |
|------|----------------|
| `test_documents_list_returns_user_scoped_results` | Only returns documents belonging to the authenticated user (`user_id`) |
| `test_documents_list_pagination` | `limit` and `offset` are applied correctly |
| `test_documents_list_no_auth` | Raises `PermissionError` when context is empty |
| `test_documents_upload_downloads_and_saves` | `httpx` download + `document_service.upload_document` called correctly |
| `test_documents_upload_bad_url` | Raises `ValueError` on unreachable URL |
| `test_documents_upload_no_extension` | Raises `ValueError` when filename cannot be derived (no extension in URL, no `filename` arg) |
| `test_documents_upload_http_exception_converted` | `HTTPException` from `document_service` is converted to `ValueError` |
| `test_questions_generate_calls_rag_service` | `rag_service.generate_rag_exam` called with correct `RAGExamRequest` |
| `test_questions_generate_quota_enforced` | `RBACService.check_resource_quota` called before generation; mock asserts `institution_id=user.institution_id, resource_type="questions"` |
| `test_questions_list_filters_by_created_by` | Query uses `created_by`, not `user_id` |
| `test_questions_list_status_filter` | `status` argument filters `review_status` correctly |
| `test_questions_list_all_statuses_valid` | All five status enum values (`pending`, `approved`, `rejected`, `edited`, `in_review`) are accepted |
| `test_knowledge_search_calls_similarity_search` | `vector_service.similarity_search` called with correct arguments |
| `test_knowledge_search_not_registered_in_core_mode` | Tool absent from registry when `DEPLOYMENT_MODE=core` (env var patched before `get_tool_registry()` call) |
| `test_knowledge_search_registered_in_full_mode` | Tool present in registry when `DEPLOYMENT_MODE=full` |
