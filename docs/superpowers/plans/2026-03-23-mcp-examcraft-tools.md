# MCP ExamCraft Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add five MCP tools (`documents-list`, `documents-upload`, `questions-generate`, `questions-list`, `knowledge-search`) to the existing MCP Facade Server so ExamCraft features are accessible via claude.ai, Claude Desktop, and Claude Code.

**Architecture:** Each tool subclasses `BaseTool`, imports backend services directly (same process), resolves the authenticated user from the MCP context email, checks RBAC permissions via `User.has_permission()`, and delegates to the existing service layer. `knowledge-search` is only registered when `DEPLOYMENT_MODE=full`.

**Tech Stack:** Python 3.11+, SQLAlchemy ORM, FastAPI `HTTPException`, `httpx` (async HTTP client), `pytest-anyio`, `unittest.mock`

**Spec:** `docs/superpowers/specs/2026-03-23-mcp-examcraft-tools-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `packages/premium/backend/mcp/tools/examcraft_documents.py` | **Create** | `ExamcraftDocumentsListTool`, `ExamcraftDocumentsUploadTool` |
| `packages/premium/backend/mcp/tools/examcraft_questions.py` | **Create** | `ExamcraftQuestionsListTool`, `ExamcraftQuestionsGenerateTool` |
| `packages/premium/backend/mcp/tools/examcraft_search.py` | **Create** | `ExamcraftKnowledgeSearchTool` |
| `packages/premium/backend/mcp/tests/test_examcraft_tools.py` | **Create** | All tests for the five tools |
| `packages/premium/backend/mcp/tools/__init__.py` | **Modify** | Register the four always-on tools + conditional `knowledge-search` |

---

## Shared Pattern (read before each task)

Every tool follows this skeleton:

```python
import logging
from typing import Any, Optional
from sqlalchemy.orm import joinedload
from .base import BaseTool
from models.auth import User

logger = logging.getLogger(__name__)


def _resolve_user(context: dict, session) -> User:
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
    if not user.has_permission(permission):
        raise PermissionError(
            f"Permission denied: '{permission}' is not available on your current plan"
        )


class MyTool(BaseTool):
    name = "..."
    description = "..."
    input_schema = {...}

    def _get_session(self):
        from database import SessionLocal
        return SessionLocal()

    async def execute(self, arguments: dict[str, Any], context: Optional[dict] = None) -> Any:
        session = self._get_session()
        try:
            user = _resolve_user(context, session)
            _check_permission(user, "some_permission")
            # ... business logic ...
        except (PermissionError, ValueError):
            raise
        except Exception as e:
            logger.error("Tool failed: %s", e, exc_info=True)
            raise
        finally:
            session.close()
```

Tests mock `_get_session` and `_resolve_user` separately:

```python
from unittest.mock import patch, MagicMock, AsyncMock
import pytest

pytestmark = pytest.mark.anyio

@pytest.fixture
def anyio_backend():
    return "asyncio"

def make_user(id=1, institution_id=1, has_permission=True):
    u = MagicMock(spec=["id", "institution_id", "has_permission"])
    u.id = id
    u.institution_id = institution_id
    u.has_permission.return_value = has_permission
    return u
```

---

## Task 1: `examcraft_documents.py` — documents-list

**Files:**
- Create: `packages/premium/backend/mcp/tools/examcraft_documents.py`
- Test: `packages/premium/backend/mcp/tests/test_examcraft_tools.py`

- [ ] **Step 1: Write failing tests for documents-list**

Create `packages/premium/backend/mcp/tests/test_examcraft_tools.py`:

```python
"""Tests for ExamCraft MCP tools."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def make_user(id=1, institution_id=1, has_permission=True):
    u = MagicMock()
    u.id = id
    u.institution_id = institution_id
    u.has_permission.return_value = has_permission
    return u


def make_document(id, title="Test Doc", filename="test.pdf", status="completed",
                  file_size=1024, created_at=None):
    doc = MagicMock()
    doc.id = id
    doc.title = title
    doc.filename = filename
    doc.status = status
    doc.file_size = file_size
    doc.created_at = created_at or datetime(2026, 3, 23, tzinfo=timezone.utc)
    return doc


class TestDocumentsList:
    def setup_method(self):
        from packages.premium.backend.mcp.tools.examcraft_documents import ExamcraftDocumentsListTool
        self.tool = ExamcraftDocumentsListTool()

    async def test_returns_user_scoped_documents(self):
        user = make_user(id=1)
        docs = [make_document(1), make_document(2)]
        mock_session = MagicMock()
        (mock_session.query.return_value.filter.return_value
         .offset.return_value.limit.return_value.all.return_value) = docs

        with patch.object(self.tool, "_get_session", return_value=mock_session), \
             patch("packages.premium.backend.mcp.tools.examcraft_documents._resolve_user",
                   return_value=user):
            result = await self.tool.execute({}, context={"email": "user@test.ch"})

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert "title" in result[0]
        assert "filename" in result[0]
        assert "status" in result[0]

    async def test_pagination_applied(self):
        user = make_user()
        mock_session = MagicMock()
        mock_chain = mock_session.query.return_value.filter.return_value
        mock_chain.offset.return_value.limit.return_value.all.return_value = []

        with patch.object(self.tool, "_get_session", return_value=mock_session), \
             patch("packages.premium.backend.mcp.tools.examcraft_documents._resolve_user",
                   return_value=user):
            await self.tool.execute({"limit": 10, "offset": 5},
                                    context={"email": "user@test.ch"})

        mock_chain.offset.assert_called_once_with(5)
        mock_chain.offset.return_value.limit.assert_called_once_with(10)

    async def test_no_auth_raises_permission_error(self):
        mock_session = MagicMock()
        with patch.object(self.tool, "_get_session", return_value=mock_session), \
             patch("packages.premium.backend.mcp.tools.examcraft_documents._resolve_user",
                   side_effect=PermissionError("Authentication required")):
            with pytest.raises(PermissionError, match="Authentication required"):
                await self.tool.execute({}, context=None)

    async def test_session_closed_on_success(self):
        user = make_user()
        mock_session = MagicMock()
        (mock_session.query.return_value.filter.return_value
         .offset.return_value.limit.return_value.all.return_value) = []

        with patch.object(self.tool, "_get_session", return_value=mock_session), \
             patch("packages.premium.backend.mcp.tools.examcraft_documents._resolve_user",
                   return_value=user):
            await self.tool.execute({}, context={"email": "user@test.ch"})

        mock_session.close.assert_called_once()
```

- [ ] **Step 2: Run tests — verify they FAIL**

```bash
cd /Users/rsenften/Git-Repositories/Work/examcraft
python -m pytest packages/premium/backend/mcp/tests/test_examcraft_tools.py::TestDocumentsList -v 2>&1 | head -30
```

Expected: `ImportError` or `ModuleNotFoundError` (file doesn't exist yet)

- [ ] **Step 3: Create `examcraft_documents.py` with documents-list**

Create `packages/premium/backend/mcp/tools/examcraft_documents.py`:

```python
"""ExamCraft document MCP tools."""

import logging
import os
import urllib.parse
from typing import Any, Optional

import httpx
from sqlalchemy.orm import joinedload

from .base import BaseTool
from models.auth import User

logger = logging.getLogger(__name__)


def _resolve_user(context: dict, session) -> User:
    """Load User (with roles eager-loaded) from MCP context email."""
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
    """Check RBAC via User.has_permission(). Raises PermissionError if denied."""
    if not user.has_permission(permission):
        raise PermissionError(
            f"Permission denied: '{permission}' is not available on your current plan"
        )


class ExamcraftDocumentsListTool(BaseTool):
    name = "documents-list"
    description = "List uploaded documents in ExamCraft"
    input_schema = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "default": 20, "maximum": 100},
            "offset": {"type": "integer", "default": 0},
        },
    }

    def _get_session(self):
        from database import SessionLocal
        return SessionLocal()

    async def execute(self, arguments: dict[str, Any], context: Optional[dict] = None) -> Any:
        session = self._get_session()
        try:
            user = _resolve_user(context, session)
            _check_permission(user, "view_documents")

            from models.document import Document
            limit = min(arguments.get("limit", 20), 100)
            offset = arguments.get("offset", 0)

            docs = (
                session.query(Document)
                .filter(Document.user_id == user.id)
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": doc.id,
                    "title": doc.title,
                    "filename": doc.filename,
                    "status": doc.status.value if hasattr(doc.status, "value") else doc.status,
                    "file_size": doc.file_size,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                }
                for doc in docs
            ]
        except (PermissionError, ValueError):
            raise
        except Exception as e:
            logger.error("documents-list failed: %s", e, exc_info=True)
            raise
        finally:
            session.close()
```

- [ ] **Step 4: Run tests — verify they PASS**

```bash
cd /Users/rsenften/Git-Repositories/Work/examcraft
python -m pytest packages/premium/backend/mcp/tests/test_examcraft_tools.py::TestDocumentsList -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/premium/backend/mcp/tools/examcraft_documents.py \
        packages/premium/backend/mcp/tests/test_examcraft_tools.py
git commit -m "feat(mcp): Add documents-list MCP tool TF-290"
```

---

## Task 2: `examcraft_documents.py` — documents-upload

**Files:**
- Modify: `packages/premium/backend/mcp/tools/examcraft_documents.py`
- Modify: `packages/premium/backend/mcp/tests/test_examcraft_tools.py`

- [ ] **Step 1: Add failing tests for documents-upload**

Append to `test_examcraft_tools.py`:

```python
class TestDocumentsUpload:
    def setup_method(self):
        from packages.premium.backend.mcp.tools.examcraft_documents import ExamcraftDocumentsUploadTool
        self.tool = ExamcraftDocumentsUploadTool()

    async def test_downloads_and_saves(self):
        user = make_user(id=1)
        mock_session = MagicMock()
        mock_doc = MagicMock()
        mock_doc.id = 42
        mock_doc.filename = "report.pdf"
        mock_doc.status = "uploaded"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b"%PDF fake content"

        with patch.object(self.tool, "_get_session", return_value=mock_session), \
             patch("packages.premium.backend.mcp.tools.examcraft_documents._resolve_user",
                   return_value=user), \
             patch("httpx.AsyncClient") as mock_client_cls, \
             patch("packages.premium.backend.mcp.tools.examcraft_documents.document_service") as mock_ds:
            mock_client_cls.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            mock_ds.upload_document = AsyncMock(return_value=mock_doc)

            result = await self.tool.execute(
                {"url": "https://example.com/report.pdf"},
                context={"email": "user@test.ch"},
            )

        assert result["document_id"] == 42
        assert result["filename"] == "report.pdf"

    async def test_bad_url_raises_value_error(self):
        user = make_user()
        mock_session = MagicMock()

        with patch.object(self.tool, "_get_session", return_value=mock_session), \
             patch("packages.premium.backend.mcp.tools.examcraft_documents._resolve_user",
                   return_value=user), \
             patch("httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.RequestError("connection refused", request=MagicMock())
            )

            with pytest.raises(ValueError, match="Could not download file from URL"):
                await self.tool.execute(
                    {"url": "https://unreachable.invalid/file.pdf"},
                    context={"email": "user@test.ch"},
                )

    async def test_no_extension_in_url_raises_value_error(self):
        user = make_user()
        mock_session = MagicMock()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b"data"

        with patch.object(self.tool, "_get_session", return_value=mock_session), \
             patch("packages.premium.backend.mcp.tools.examcraft_documents._resolve_user",
                   return_value=user), \
             patch("httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(ValueError, match="Could not determine filename"):
                await self.tool.execute(
                    {"url": "https://s3.amazonaws.com/bucket/object?X-Amz-Signature=abc123"},
                    context={"email": "user@test.ch"},
                )

    async def test_http_exception_from_service_converted_to_value_error(self):
        from fastapi import HTTPException
        user = make_user()
        mock_session = MagicMock()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b"data"

        with patch.object(self.tool, "_get_session", return_value=mock_session), \
             patch("packages.premium.backend.mcp.tools.examcraft_documents._resolve_user",
                   return_value=user), \
             patch("httpx.AsyncClient") as mock_client_cls, \
             patch("packages.premium.backend.mcp.tools.examcraft_documents.document_service") as mock_ds:
            mock_client_cls.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            mock_ds.upload_document = AsyncMock(
                side_effect=HTTPException(status_code=400, detail="Unsupported file type")
            )

            with pytest.raises(ValueError, match="Unsupported file type"):
                await self.tool.execute(
                    {"url": "https://example.com/file.exe"},
                    context={"email": "user@test.ch"},
                )
```

- [ ] **Step 2: Run tests — verify they FAIL**

```bash
python -m pytest packages/premium/backend/mcp/tests/test_examcraft_tools.py::TestDocumentsUpload -v 2>&1 | head -20
```

Expected: `ImportError` (class not defined yet)

- [ ] **Step 3: Add `ExamcraftDocumentsUploadTool` to `examcraft_documents.py`**

Add to `packages/premium/backend/mcp/tools/examcraft_documents.py`:

```python
# At top of file, add imports:
# import httpx  (already there)
# from services.document_service import document_service
from services.document_service import document_service


class ExamcraftDocumentsUploadTool(BaseTool):
    name = "documents-upload"
    description = "Upload a document to ExamCraft by URL"
    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Public URL of the file to download"},
            "filename": {"type": "string", "description": "Optional filename override"},
        },
        "required": ["url"],
    }

    def _get_session(self):
        from database import SessionLocal
        return SessionLocal()

    async def execute(self, arguments: dict[str, Any], context: Optional[dict] = None) -> Any:
        from fastapi import HTTPException
        from fastapi import UploadFile
        import io

        session = self._get_session()
        try:
            user = _resolve_user(context, session)
            _check_permission(user, "create_documents")

            url = arguments["url"]
            filename_override = arguments.get("filename")

            # 1. Derive filename
            if filename_override:
                filename = filename_override
            else:
                parsed = urllib.parse.urlparse(url)
                basename = os.path.basename(parsed.path)
                _, ext = os.path.splitext(basename)
                if not ext:
                    raise ValueError(
                        "Could not determine filename from URL — provide an explicit filename"
                    )
                filename = basename

            # 2. Download file
            try:
                async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    content = response.content
            except httpx.HTTPStatusError as e:
                raise ValueError(f"Could not download file from URL: HTTP {e.response.status_code}")
            except httpx.RequestError as e:
                raise ValueError(f"Could not download file from URL: {e}")

            # 3. Wrap in UploadFile-compatible object
            upload_file = UploadFile(
                filename=filename,
                file=io.BytesIO(content),
            )

            # 4. Upload via document_service
            try:
                doc = await document_service.upload_document(
                    file=upload_file,
                    user_id=user.id,
                    db=session,
                )
            except HTTPException as e:
                raise ValueError(e.detail)

            return {
                "document_id": doc.id,
                "filename": doc.filename,
                "status": doc.status.value if hasattr(doc.status, "value") else doc.status,
                "message": "Document uploaded. Processing runs asynchronously — poll documents-list until status is 'completed'.",
            }
        except (PermissionError, ValueError):
            raise
        except Exception as e:
            logger.error("documents-upload failed: %s", e, exc_info=True)
            raise
        finally:
            session.close()
```

- [ ] **Step 4: Run tests — verify they PASS**

```bash
python -m pytest packages/premium/backend/mcp/tests/test_examcraft_tools.py::TestDocumentsUpload -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/premium/backend/mcp/tools/examcraft_documents.py \
        packages/premium/backend/mcp/tests/test_examcraft_tools.py
git commit -m "feat(mcp): Add documents-upload MCP tool TF-290"
```

---

## Task 3: `examcraft_questions.py` — questions-list

**Files:**
- Create: `packages/premium/backend/mcp/tools/examcraft_questions.py`
- Modify: `packages/premium/backend/mcp/tests/test_examcraft_tools.py`

- [ ] **Step 1: Add failing tests for questions-list**

Append to `test_examcraft_tools.py`:

```python
class TestQuestionsList:
    def setup_method(self):
        from packages.premium.backend.mcp.tools.examcraft_questions import ExamcraftQuestionsListTool
        self.tool = ExamcraftQuestionsListTool()

    async def test_filters_by_created_by(self):
        user = make_user(id=5)
        mock_session = MagicMock()
        mock_q1 = MagicMock()
        mock_q1.id = 10
        mock_q1.question_text = "What is X?"
        mock_q1.question_type = "multiple_choice"
        mock_q1.difficulty = "medium"
        mock_q1.review_status = "pending"
        mock_q1.created_at = datetime(2026, 3, 23, tzinfo=timezone.utc)

        mock_chain = mock_session.query.return_value.filter.return_value
        mock_chain.offset.return_value.limit.return_value.all.return_value = [mock_q1]

        with patch.object(self.tool, "_get_session", return_value=mock_session), \
             patch("packages.premium.backend.mcp.tools.examcraft_questions._resolve_user",
                   return_value=user):
            result = await self.tool.execute({}, context={"email": "user@test.ch"})

        assert len(result) == 1
        assert result[0]["id"] == 10
        # Verify filter used created_by (not user_id)
        filter_call = mock_session.query.return_value.filter.call_args
        assert filter_call is not None

    async def test_status_filter_applied(self):
        user = make_user()
        mock_session = MagicMock()
        mock_chain = mock_session.query.return_value.filter.return_value
        # status filter adds another .filter()
        mock_chain.filter.return_value.offset.return_value.limit.return_value.all.return_value = []

        with patch.object(self.tool, "_get_session", return_value=mock_session), \
             patch("packages.premium.backend.mcp.tools.examcraft_questions._resolve_user",
                   return_value=user):
            await self.tool.execute(
                {"status": "approved"}, context={"email": "user@test.ch"}
            )

        # Second .filter() should have been called for the status
        mock_chain.filter.assert_called_once()

    async def test_all_status_values_accepted(self):
        user = make_user()
        mock_session = MagicMock()

        for status in ["pending", "approved", "rejected", "edited", "in_review"]:
            mock_chain = mock_session.query.return_value.filter.return_value
            mock_chain.filter.return_value.offset.return_value.limit.return_value.all.return_value = []
            mock_chain.offset.return_value.limit.return_value.all.return_value = []

            with patch.object(self.tool, "_get_session", return_value=mock_session), \
                 patch("packages.premium.backend.mcp.tools.examcraft_questions._resolve_user",
                       return_value=user):
                # Should not raise
                await self.tool.execute(
                    {"status": status}, context={"email": "user@test.ch"}
                )
```

- [ ] **Step 2: Run tests — verify they FAIL**

```bash
python -m pytest packages/premium/backend/mcp/tests/test_examcraft_tools.py::TestQuestionsList -v 2>&1 | head -20
```

Expected: `ImportError`

- [ ] **Step 3: Create `examcraft_questions.py` with questions-list**

Create `packages/premium/backend/mcp/tools/examcraft_questions.py`:

```python
"""ExamCraft question MCP tools."""

import logging
from typing import Any, Optional
from sqlalchemy.orm import joinedload

from .base import BaseTool
from models.auth import User

logger = logging.getLogger(__name__)

VALID_STATUSES = {"pending", "approved", "rejected", "edited", "in_review"}


def _resolve_user(context: dict, session) -> User:
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
    if not user.has_permission(permission):
        raise PermissionError(
            f"Permission denied: '{permission}' is not available on your current plan"
        )


class ExamcraftQuestionsListTool(BaseTool):
    name = "questions-list"
    description = "List generated exam questions"
    input_schema = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "default": 20, "maximum": 100},
            "offset": {"type": "integer", "default": 0},
            "status": {
                "type": "string",
                "enum": list(VALID_STATUSES),
                "description": "Optional status filter",
            },
        },
    }

    def _get_session(self):
        from database import SessionLocal
        return SessionLocal()

    async def execute(self, arguments: dict[str, Any], context: Optional[dict] = None) -> Any:
        session = self._get_session()
        try:
            user = _resolve_user(context, session)
            _check_permission(user, "view_questions")

            from models.question_review import QuestionReview
            limit = min(arguments.get("limit", 20), 100)
            offset = arguments.get("offset", 0)
            status = arguments.get("status")

            query = session.query(QuestionReview).filter(
                QuestionReview.created_by == user.id
            )
            if status:
                query = query.filter(QuestionReview.review_status == status)

            questions = query.offset(offset).limit(limit).all()
            return [
                {
                    "id": q.id,
                    "question_text": q.question_text,
                    "question_type": q.question_type,
                    "difficulty": q.difficulty,
                    "review_status": q.review_status,
                    "created_at": q.created_at.isoformat() if q.created_at else None,
                }
                for q in questions
            ]
        except (PermissionError, ValueError):
            raise
        except Exception as e:
            logger.error("questions-list failed: %s", e, exc_info=True)
            raise
        finally:
            session.close()
```

- [ ] **Step 4: Run tests — verify they PASS**

```bash
python -m pytest packages/premium/backend/mcp/tests/test_examcraft_tools.py::TestQuestionsList -v
```

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/premium/backend/mcp/tools/examcraft_questions.py \
        packages/premium/backend/mcp/tests/test_examcraft_tools.py
git commit -m "feat(mcp): Add questions-list MCP tool TF-290"
```

---

## Task 4: `examcraft_questions.py` — questions-generate

**Files:**
- Modify: `packages/premium/backend/mcp/tools/examcraft_questions.py`
- Modify: `packages/premium/backend/mcp/tests/test_examcraft_tools.py`

- [ ] **Step 1: Add failing tests for questions-generate**

Append to `test_examcraft_tools.py`:

```python
class TestQuestionsGenerate:
    def setup_method(self):
        from packages.premium.backend.mcp.tools.examcraft_questions import ExamcraftQuestionsGenerateTool
        self.tool = ExamcraftQuestionsGenerateTool()

    async def test_calls_rag_service(self):
        user = make_user()
        mock_session = MagicMock()

        mock_question = MagicMock()
        mock_question.question_text = "What is a heap?"
        mock_question.question_type = "multiple_choice"
        mock_question.options = ["A", "B", "C", "D"]
        mock_question.correct_answer = "A"
        mock_question.difficulty = "medium"
        mock_question.explanation = "A heap is..."
        mock_question.source_documents = ["doc1.pdf"]
        mock_question.confidence_score = 0.9

        mock_response = MagicMock()
        mock_response.questions = [mock_question]

        mock_rbac = MagicMock()
        mock_rbac.check_resource_quota.return_value = {"allowed": True}
        mock_rbac.increment_resource_usage = MagicMock()

        with patch.object(self.tool, "_get_session", return_value=mock_session), \
             patch("packages.premium.backend.mcp.tools.examcraft_questions._resolve_user",
                   return_value=user), \
             patch("packages.premium.backend.mcp.tools.examcraft_questions.rag_service") as mock_rag, \
             patch("packages.premium.backend.mcp.tools.examcraft_questions.RBACService",
                   return_value=mock_rbac):
            mock_rag.generate_rag_exam = AsyncMock(return_value=mock_response)

            result = await self.tool.execute(
                {"topic": "Heapsort", "question_count": 1},
                context={"email": "user@test.ch"},
            )

        mock_rag.generate_rag_exam.assert_called_once()
        call_args = mock_rag.generate_rag_exam.call_args[0][0]
        assert call_args.topic == "Heapsort"
        assert call_args.question_count == 1
        assert len(result) == 1
        assert result[0]["question_text"] == "What is a heap?"

    async def test_quota_checked_before_generation(self):
        user = make_user()
        mock_session = MagicMock()

        mock_rbac = MagicMock()
        mock_rbac.check_resource_quota.return_value = {
            "allowed": False,
            "remaining": 0,
            "quota_limit": 20,
        }

        with patch.object(self.tool, "_get_session", return_value=mock_session), \
             patch("packages.premium.backend.mcp.tools.examcraft_questions._resolve_user",
                   return_value=user), \
             patch("packages.premium.backend.mcp.tools.examcraft_questions.RBACService",
                   return_value=mock_rbac):
            with pytest.raises(ValueError, match="quota"):
                await self.tool.execute(
                    {"topic": "Heapsort"},
                    context={"email": "user@test.ch"},
                )

        mock_rbac.check_resource_quota.assert_called_once_with(
            institution_id=user.institution_id,
            resource_type="questions_per_month",
            requested_amount=1,
        )

    async def test_usage_incremented_after_generation(self):
        user = make_user()
        mock_session = MagicMock()

        mock_question = MagicMock()
        mock_response = MagicMock()
        mock_response.questions = [mock_question, mock_question]  # 2 questions

        mock_rbac = MagicMock()
        mock_rbac.check_resource_quota.return_value = {"allowed": True}

        with patch.object(self.tool, "_get_session", return_value=mock_session), \
             patch("packages.premium.backend.mcp.tools.examcraft_questions._resolve_user",
                   return_value=user), \
             patch("packages.premium.backend.mcp.tools.examcraft_questions.rag_service") as mock_rag, \
             patch("packages.premium.backend.mcp.tools.examcraft_questions.RBACService",
                   return_value=mock_rbac):
            mock_rag.generate_rag_exam = AsyncMock(return_value=mock_response)

            await self.tool.execute(
                {"topic": "Sorting", "question_count": 2},
                context={"email": "user@test.ch"},
            )

        mock_rbac.increment_resource_usage.assert_called_once_with(
            institution_id=user.institution_id,
            resource_type="questions_per_month",
            amount=2,
        )
```

- [ ] **Step 2: Run tests — verify they FAIL**

```bash
python -m pytest packages/premium/backend/mcp/tests/test_examcraft_tools.py::TestQuestionsGenerate -v 2>&1 | head -20
```

Expected: `ImportError` (class not defined yet)

- [ ] **Step 3: Add `ExamcraftQuestionsGenerateTool` to `examcraft_questions.py`**

Add to `packages/premium/backend/mcp/tools/examcraft_questions.py`:

```python
# Add at top of file:
from services.rag_service import rag_service
from services.rbac_service import RBACService


class ExamcraftQuestionsGenerateTool(BaseTool):
    name = "questions-generate"
    description = "Generate exam questions from documents using RAG"
    input_schema = {
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "Exam topic"},
            "document_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Optional document filter",
            },
            "question_count": {
                "type": "integer",
                "default": 5,
                "minimum": 1,
                "maximum": 20,
            },
            "difficulty": {
                "type": "string",
                "enum": ["easy", "medium", "hard"],
                "default": "medium",
            },
            "language": {"type": "string", "default": "de"},
        },
        "required": ["topic"],
    }

    def _get_session(self):
        from database import SessionLocal
        return SessionLocal()

    async def execute(self, arguments: dict[str, Any], context: Optional[dict] = None) -> Any:
        session = self._get_session()
        try:
            user = _resolve_user(context, session)
            _check_permission(user, "generate_questions")

            # Check quota (resource_type confirmed from rbac_middleware.py)
            rbac = RBACService(db=session)
            quota_result = rbac.check_resource_quota(
                institution_id=user.institution_id,
                resource_type="questions_per_month",
                requested_amount=1,
            )
            if not quota_result.get("allowed", False):
                remaining = quota_result.get("remaining", 0)
                limit = quota_result.get("quota_limit", "?")
                raise ValueError(
                    f"Monthly question quota exceeded (remaining: {remaining}, limit: {limit}). "
                    "Please upgrade your subscription."
                )

            from services.rag_service import RAGExamRequest
            request = RAGExamRequest(
                topic=arguments["topic"],
                document_ids=arguments.get("document_ids"),
                question_count=arguments.get("question_count", 5),
                difficulty=arguments.get("difficulty", "medium"),
                language=arguments.get("language", "de"),
            )

            response = await rag_service.generate_rag_exam(request)
            questions = response.questions

            # Increment usage counter
            rbac.increment_resource_usage(
                institution_id=user.institution_id,
                resource_type="questions_per_month",
                amount=len(questions),
            )

            return [
                {
                    "question_text": q.question_text,
                    "question_type": q.question_type,
                    "options": q.options,
                    "correct_answer": q.correct_answer,
                    "difficulty": q.difficulty,
                    "explanation": q.explanation,
                    "source_documents": q.source_documents,
                    "confidence_score": q.confidence_score,
                }
                for q in questions
            ]
        except (PermissionError, ValueError):
            raise
        except Exception as e:
            logger.error("questions-generate failed: %s", e, exc_info=True)
            raise
        finally:
            session.close()
```

- [ ] **Step 4: Run tests — verify they PASS**

```bash
python -m pytest packages/premium/backend/mcp/tests/test_examcraft_tools.py::TestQuestionsGenerate -v
```

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/premium/backend/mcp/tools/examcraft_questions.py \
        packages/premium/backend/mcp/tests/test_examcraft_tools.py
git commit -m "feat(mcp): Add questions-generate MCP tool TF-290"
```

---

## Task 5: `examcraft_search.py` — knowledge-search

**Files:**
- Create: `packages/premium/backend/mcp/tools/examcraft_search.py`
- Modify: `packages/premium/backend/mcp/tests/test_examcraft_tools.py`

- [ ] **Step 1: Add failing tests for knowledge-search**

Append to `test_examcraft_tools.py`:

```python
class TestKnowledgeSearch:
    def setup_method(self):
        from packages.premium.backend.mcp.tools.examcraft_search import ExamcraftKnowledgeSearchTool
        self.tool = ExamcraftKnowledgeSearchTool()

    async def test_calls_similarity_search(self):
        user = make_user()
        mock_session = MagicMock()

        mock_result = MagicMock()
        mock_result.content = "A heap is a complete binary tree..."
        mock_result.similarity_score = 0.87
        mock_result.chunk_index = 3
        mock_result.metadata = {"filename": "heapsort.pdf"}

        with patch.object(self.tool, "_get_session", return_value=mock_session), \
             patch("packages.premium.backend.mcp.tools.examcraft_search._resolve_user",
                   return_value=user), \
             patch("packages.premium.backend.mcp.tools.examcraft_search.vector_service") as mock_vs:
            mock_vs.similarity_search = AsyncMock(return_value=[mock_result])

            result = await self.tool.execute(
                {"query": "heap data structure", "n_results": 3},
                context={"email": "user@test.ch"},
            )

        mock_vs.similarity_search.assert_called_once_with("heap data structure", 3, None)
        assert len(result) == 1
        assert result[0]["content"] == "A heap is a complete binary tree..."
        assert result[0]["filename"] == "heapsort.pdf"
        assert result[0]["similarity_score"] == 0.87
        assert result[0]["chunk_index"] == 3

    async def test_document_ids_filter_passed(self):
        user = make_user()
        mock_session = MagicMock()

        with patch.object(self.tool, "_get_session", return_value=mock_session), \
             patch("packages.premium.backend.mcp.tools.examcraft_search._resolve_user",
                   return_value=user), \
             patch("packages.premium.backend.mcp.tools.examcraft_search.vector_service") as mock_vs:
            mock_vs.similarity_search = AsyncMock(return_value=[])

            await self.tool.execute(
                {"query": "sorting", "document_ids": [1, 2]},
                context={"email": "user@test.ch"},
            )

        mock_vs.similarity_search.assert_called_once_with("sorting", 5, [1, 2])


class TestKnowledgeSearchRegistry:
    """Test deployment-mode guard for knowledge-search registration."""

    def test_not_registered_in_core_mode(self, monkeypatch):
        import packages.premium.backend.mcp.tools as tools_pkg
        monkeypatch.setenv("DEPLOYMENT_MODE", "core")
        # Reset registry state
        tools_pkg._REGISTRY.clear()
        tools_pkg._initialized = False

        registry = tools_pkg.get_tool_registry()
        assert "knowledge-search" not in registry

    def test_registered_in_full_mode(self, monkeypatch):
        import packages.premium.backend.mcp.tools as tools_pkg
        monkeypatch.setenv("DEPLOYMENT_MODE", "full")
        tools_pkg._REGISTRY.clear()
        tools_pkg._initialized = False

        registry = tools_pkg.get_tool_registry()
        assert "knowledge-search" in registry
```

- [ ] **Step 2: Run tests — verify they FAIL**

```bash
python -m pytest packages/premium/backend/mcp/tests/test_examcraft_tools.py::TestKnowledgeSearch packages/premium/backend/mcp/tests/test_examcraft_tools.py::TestKnowledgeSearchRegistry -v 2>&1 | head -20
```

Expected: `ImportError`

- [ ] **Step 3: Create `examcraft_search.py`**

Create `packages/premium/backend/mcp/tools/examcraft_search.py`:

```python
"""ExamCraft knowledge search MCP tool."""

import logging
from typing import Any, Optional
from sqlalchemy.orm import joinedload

from .base import BaseTool
from models.auth import User

logger = logging.getLogger(__name__)

# Import premium vector service singleton
from services.vector_service_factory import vector_service


def _resolve_user(context: dict, session) -> User:
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
    if not user.has_permission(permission):
        raise PermissionError(
            f"Permission denied: '{permission}' is not available on your current plan"
        )


class ExamcraftKnowledgeSearchTool(BaseTool):
    name = "knowledge-search"
    description = "Semantic search in the ExamCraft knowledge base (Full deployment only)"
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "n_results": {
                "type": "integer",
                "default": 5,
                "minimum": 1,
                "maximum": 20,
            },
            "document_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Optional document filter",
            },
        },
        "required": ["query"],
    }

    def _get_session(self):
        from database import SessionLocal
        return SessionLocal()

    async def execute(self, arguments: dict[str, Any], context: Optional[dict] = None) -> Any:
        session = self._get_session()
        try:
            user = _resolve_user(context, session)
            _check_permission(user, "view_documents")

            query = arguments["query"]
            n_results = min(arguments.get("n_results", 5), 20)
            document_ids = arguments.get("document_ids")

            # similarity_search signature: (query, n_results, document_ids, collection_name=None)
            results = await vector_service.similarity_search(query, n_results, document_ids)

            return [
                {
                    "content": r.content,
                    "similarity_score": r.similarity_score,
                    "filename": r.metadata.get("filename"),  # filename lives in metadata dict
                    "chunk_index": r.chunk_index,
                }
                for r in results
            ]
        except (PermissionError, ValueError):
            raise
        except Exception as e:
            logger.error("knowledge-search failed: %s", e, exc_info=True)
            raise
        finally:
            session.close()
```

- [ ] **Step 4: Run tests — verify they PASS**

```bash
python -m pytest packages/premium/backend/mcp/tests/test_examcraft_tools.py::TestKnowledgeSearch packages/premium/backend/mcp/tests/test_examcraft_tools.py::TestKnowledgeSearchRegistry -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/premium/backend/mcp/tools/examcraft_search.py \
        packages/premium/backend/mcp/tests/test_examcraft_tools.py
git commit -m "feat(mcp): Add knowledge-search MCP tool TF-290"
```

---

## Task 6: Register tools in `tools/__init__.py`

**Files:**
- Modify: `packages/premium/backend/mcp/tools/__init__.py`

- [ ] **Step 1: Add failing registry tests**

The `TestKnowledgeSearchRegistry` tests in Task 5 already cover the conditional registration. Verify they still fail before the registry is updated:

```bash
python -m pytest packages/premium/backend/mcp/tests/test_examcraft_tools.py::TestKnowledgeSearchRegistry -v
```

Expected: FAIL (tools not registered yet)

- [ ] **Step 2: Update `tools/__init__.py`**

Open `packages/premium/backend/mcp/tools/__init__.py` and apply these changes:

Add imports at the top (after existing imports):

```python
from .examcraft_documents import ExamcraftDocumentsListTool, ExamcraftDocumentsUploadTool
from .examcraft_questions import ExamcraftQuestionsListTool, ExamcraftQuestionsGenerateTool
```

Inside `get_tool_registry()`, add inside the `if not _initialized:` block (after existing `_register(DbQueryTool())` line):

```python
        _register(ExamcraftDocumentsListTool())
        _register(ExamcraftDocumentsUploadTool())
        _register(ExamcraftQuestionsListTool())
        _register(ExamcraftQuestionsGenerateTool())
        # knowledge-search: Full deployment only — evaluated lazily here (not at import time)
        import os
        if os.getenv("DEPLOYMENT_MODE", "core") == "full":
            from .examcraft_search import ExamcraftKnowledgeSearchTool
            _register(ExamcraftKnowledgeSearchTool())
```

- [ ] **Step 3: Run ALL tests — verify they PASS**

```bash
python -m pytest packages/premium/backend/mcp/tests/ -v
```

Expected: All existing tests + all new tests PASS

- [ ] **Step 4: Commit**

```bash
git add packages/premium/backend/mcp/tools/__init__.py
git commit -m "feat(mcp): Register ExamCraft MCP tools in registry TF-290"
```

---

## Task 7: Final verification

- [ ] **Step 1: Run full MCP test suite**

```bash
python -m pytest packages/premium/backend/mcp/tests/ -v --tb=short
```

Expected: All tests PASS, no failures

- [ ] **Step 2: Verify tool names in registry (core mode)**

```bash
DEPLOYMENT_MODE=core python -c "
from packages.premium.backend.mcp.tools import get_tool_registry
r = get_tool_registry()
print('Registered tools:', sorted(r.keys()))
assert 'documents-list' in r
assert 'documents-upload' in r
assert 'questions-list' in r
assert 'questions-generate' in r
assert 'knowledge-search' not in r
print('Core mode: OK')
"
```

- [ ] **Step 3: Verify tool names in registry (full mode)**

```bash
DEPLOYMENT_MODE=full python -c "
import packages.premium.backend.mcp.tools as tools_pkg
tools_pkg._REGISTRY.clear()
tools_pkg._initialized = False
r = tools_pkg.get_tool_registry()
assert 'knowledge-search' in r
print('Full mode: OK')
"
```

- [ ] **Step 4: Final commit (if any cleanup needed)**

```bash
git add -p
git commit -m "feat(mcp): MCP ExamCraft Tools complete TF-290"
```
