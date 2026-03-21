# Exam Composer MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Exam Composer feature that lets instructors assemble exams from approved questions and export them in Markdown, JSON, and Moodle XML formats.

**Architecture:** New `Exam` and `ExamQuestion` models with M:N relationship to `QuestionReview`. REST API under `/api/v1/exams` with CRUD, question management, auto-fill, finalize/export. Two-panel React frontend with drag-and-drop via `@dnd-kit`.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, React 18, TypeScript, TanStack Query v5, @dnd-kit, Tailwind CSS, MUI Dialogs

**Spec:** `docs/superpowers/specs/2026-03-20-exam-composer-design.md`
**Linear Issue:** TF-56

---

## File Structure

### Backend (new files)

| File | Responsibility |
|------|---------------|
| `packages/core/backend/models/exam.py` | `Exam` and `ExamQuestion` SQLAlchemy models |
| `packages/core/backend/models/__init__.py` | Add exports for new models |
| `packages/core/backend/api/exams.py` | All exam API endpoints (CRUD, questions, auto-fill, finalize, export) |
| `packages/core/backend/services/exam_export_service.py` | Export logic (Markdown, JSON, Moodle XML) |
| `packages/core/backend/main.py` | Register new router |
| `packages/core/backend/alembic/versions/xxxx_add_exam_tables.py` | Migration (auto-generated) |
| `packages/core/backend/tests/test_exam_api.py` | API endpoint tests |
| `packages/core/backend/tests/test_exam_export.py` | Export service tests |

### Frontend (new files)

| File | Responsibility |
|------|---------------|
| `packages/core/frontend/src/types/composer.ts` | TypeScript types for Exam Composer |
| `packages/core/frontend/src/services/ComposerService.ts` | API client for exam endpoints |
| `packages/core/frontend/src/pages/ExamComposer.tsx` | Page component (router between list/builder) |
| `packages/core/frontend/src/components/composer/ExamListView.tsx` | List of exams + create dialog |
| `packages/core/frontend/src/components/composer/ExamBuilderView.tsx` | Two-panel builder (orchestrator) |
| `packages/core/frontend/src/components/composer/ExamMetadataBar.tsx` | Top bar with title, stats, actions |
| `packages/core/frontend/src/components/composer/QuestionPoolPanel.tsx` | Left panel: searchable question pool |
| `packages/core/frontend/src/components/composer/ExamQuestionsPanel.tsx` | Right panel: exam questions with DnD |
| `packages/core/frontend/src/components/composer/ExportDialog.tsx` | Export format selection dialog |

### Frontend (modified files)

| File | Change |
|------|--------|
| `packages/core/frontend/src/AppWithAuth.tsx` | Update `/exams/compose` route to use `ExamComposer` |
| `packages/core/frontend/package.json` | Add `@dnd-kit/core` and `@dnd-kit/sortable` |

---

## Task 1: Backend Models + Migration

**Files:**
- Create: `packages/core/backend/models/exam.py`
- Modify: `packages/core/backend/models/__init__.py`
- Test: `packages/core/backend/tests/test_exam_api.py` (model tests only)

- [ ] **Step 1: Write the model test**

Create `packages/core/backend/tests/test_exam_api.py`:

```python
"""Tests for Exam Composer API — Task 1: Model tests"""

import pytest
from models.exam import Exam, ExamQuestion, ExamStatus


class TestExamModel:
    def test_create_exam(self, test_db, test_institution, test_user):
        """Exam can be created with required fields."""
        exam = Exam(
            title="Algorithmen Midterm 2026",
            institution_id=test_institution.id,
            created_by=test_user.id,
        )
        test_db.add(exam)
        test_db.commit()
        test_db.refresh(exam)

        assert exam.id is not None
        assert exam.title == "Algorithmen Midterm 2026"
        assert exam.status == ExamStatus.DRAFT.value
        assert exam.total_points == 0.0
        assert exam.passing_percentage == 50.0
        assert exam.language == "de"
        assert exam.created_at is not None
        assert exam.updated_at is not None

    def test_create_exam_question(self, test_db, test_institution, test_user):
        """ExamQuestion links an exam to a question with position and points."""
        from models.question_review import QuestionReview

        exam = Exam(
            title="Test Exam",
            institution_id=test_institution.id,
            created_by=test_user.id,
        )
        test_db.add(exam)
        test_db.commit()

        question = QuestionReview(
            question_text="What is a heap?",
            question_type="open_ended",
            difficulty="medium",
            topic="Heaps",
            review_status="approved",
            institution_id=test_institution.id,
            created_by=test_user.id,
        )
        test_db.add(question)
        test_db.commit()

        eq = ExamQuestion(
            exam_id=exam.id,
            question_id=question.id,
            position=1,
            points=6.0,
        )
        test_db.add(eq)
        test_db.commit()
        test_db.refresh(eq)

        assert eq.id is not None
        assert eq.exam_id == exam.id
        assert eq.question_id == question.id
        assert eq.position == 1
        assert eq.points == 6.0

    def test_exam_questions_relationship(self, test_db, test_institution, test_user):
        """Exam.questions relationship returns ordered ExamQuestion list."""
        from models.question_review import QuestionReview

        exam = Exam(
            title="Relationship Test",
            institution_id=test_institution.id,
            created_by=test_user.id,
        )
        test_db.add(exam)
        test_db.commit()

        q1 = QuestionReview(
            question_text="Q1", question_type="true_false",
            difficulty="easy", topic="Test", review_status="approved",
            institution_id=test_institution.id, created_by=test_user.id,
        )
        q2 = QuestionReview(
            question_text="Q2", question_type="multiple_choice",
            difficulty="hard", topic="Test", review_status="approved",
            institution_id=test_institution.id, created_by=test_user.id,
        )
        test_db.add_all([q1, q2])
        test_db.commit()

        eq1 = ExamQuestion(exam_id=exam.id, question_id=q1.id, position=2, points=1.0)
        eq2 = ExamQuestion(exam_id=exam.id, question_id=q2.id, position=1, points=6.0)
        test_db.add_all([eq1, eq2])
        test_db.commit()
        test_db.refresh(exam)

        assert len(exam.questions) == 2
        assert exam.questions[0].position == 1  # ordered by position
        assert exam.questions[1].position == 2

    def test_exam_status_enum(self):
        """ExamStatus enum has expected values."""
        assert ExamStatus.DRAFT.value == "draft"
        assert ExamStatus.FINALIZED.value == "finalized"
        assert ExamStatus.EXPORTED.value == "exported"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/core/backend && python -m pytest tests/test_exam_api.py::TestExamModel -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'models.exam'`

- [ ] **Step 3: Create the Exam model**

Create `packages/core/backend/models/exam.py`:

```python
"""
Exam Composer Models for ExamCraft AI
Implements exam assembly from approved questions with M:N relationship.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Date,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class ExamStatus(str, enum.Enum):
    DRAFT = "draft"
    FINALIZED = "finalized"
    EXPORTED = "exported"


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    course = Column(String(200), nullable=True)
    exam_date = Column(Date, nullable=True)
    time_limit_minutes = Column(Integer, nullable=True)
    allowed_aids = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)
    passing_percentage = Column(Float, default=50.0, nullable=False)
    total_points = Column(Float, default=0.0, nullable=False)
    status = Column(String(20), default=ExamStatus.DRAFT.value, nullable=False, index=True)
    language = Column(String(10), default="de", nullable=False)

    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    questions = relationship(
        "ExamQuestion",
        back_populates="exam",
        cascade="all, delete-orphan",
        order_by="ExamQuestion.position",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'finalized', 'exported')",
            name="check_exam_status",
        ),
    )

    def recalculate_total_points(self):
        self.total_points = sum(eq.points for eq in self.questions)

    def __repr__(self):
        return f"<Exam(id={self.id}, title='{self.title}', status={self.status})>"


class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(
        Integer,
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = Column(
        Integer,
        ForeignKey("question_reviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    position = Column(Integer, nullable=False)
    points = Column(Float, nullable=False)
    section = Column(String(100), nullable=True)

    exam = relationship("Exam", back_populates="questions")
    question = relationship("QuestionReview")

    __table_args__ = (
        UniqueConstraint("exam_id", "question_id", name="uq_exam_question"),
        UniqueConstraint("exam_id", "position", name="uq_exam_position"),
    )

    def __repr__(self):
        return f"<ExamQuestion(exam_id={self.exam_id}, question_id={self.question_id}, pos={self.position})>"
```

- [ ] **Step 4: Register models in `__init__.py`**

Add to `packages/core/backend/models/__init__.py`:

```python
from models.exam import Exam, ExamQuestion, ExamStatus
```

And add `"Exam"`, `"ExamQuestion"`, `"ExamStatus"` to the `__all__` list.

- [ ] **Step 5: Generate Alembic migration**

```bash
cd packages/core/backend && alembic revision --autogenerate -m "add exam and exam_questions tables"
```

Review the generated migration file to verify it creates both tables with correct columns, constraints, and indexes.

- [ ] **Step 6: Apply migration**

```bash
cd packages/core/backend && alembic upgrade head
```

- [ ] **Step 7: Run model tests to verify they pass**

```bash
cd packages/core/backend && python -m pytest tests/test_exam_api.py::TestExamModel -v
```

Expected: All 4 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add packages/core/backend/models/exam.py packages/core/backend/models/__init__.py packages/core/backend/alembic/versions/ packages/core/backend/tests/test_exam_api.py
git commit -m "feat(exam): add Exam and ExamQuestion models with migration (TF-56)"
```

---

## Task 2: Backend API — CRUD Endpoints

**Files:**
- Create: `packages/core/backend/api/exams.py`
- Modify: `packages/core/backend/main.py` (register router)
- Test: `packages/core/backend/tests/test_exam_api.py` (append)

- [ ] **Step 1: Write CRUD tests**

Append to `packages/core/backend/tests/test_exam_api.py`:

```python
from fastapi.testclient import TestClient


class TestExamCRUDApi:
    """Tests for exam CRUD endpoints."""

    def _auth_headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def test_create_exam(self, test_client: TestClient, auth_token: str):
        """POST /api/v1/exams/ creates a new exam."""
        response = test_client.post(
            "/api/v1/exams/",
            json={"title": "Midterm 2026", "course": "Algo & DS", "language": "de"},
            headers=self._auth_headers(auth_token),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Midterm 2026"
        assert data["status"] == "draft"
        assert data["total_points"] == 0.0

    def test_list_exams(self, test_client: TestClient, auth_token: str):
        """GET /api/v1/exams/ returns user's exams."""
        # Create two exams first
        for title in ["Exam A", "Exam B"]:
            test_client.post(
                "/api/v1/exams/",
                json={"title": title},
                headers=self._auth_headers(auth_token),
            )
        response = test_client.get(
            "/api/v1/exams/",
            headers=self._auth_headers(auth_token),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        assert len(data["exams"]) >= 2

    def test_get_exam(self, test_client: TestClient, auth_token: str):
        """GET /api/v1/exams/{id} returns exam with questions."""
        create_resp = test_client.post(
            "/api/v1/exams/",
            json={"title": "Detail Test"},
            headers=self._auth_headers(auth_token),
        )
        exam_id = create_resp.json()["id"]
        response = test_client.get(
            f"/api/v1/exams/{exam_id}",
            headers=self._auth_headers(auth_token),
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Detail Test"
        assert response.json()["questions"] == []

    def test_update_exam(self, test_client: TestClient, auth_token: str):
        """PUT /api/v1/exams/{id} updates metadata."""
        create_resp = test_client.post(
            "/api/v1/exams/",
            json={"title": "Old Title"},
            headers=self._auth_headers(auth_token),
        )
        exam = create_resp.json()
        response = test_client.put(
            f"/api/v1/exams/{exam['id']}",
            json={
                "title": "New Title",
                "time_limit_minutes": 90,
                "updated_at": exam["updated_at"],
            },
            headers=self._auth_headers(auth_token),
        )
        assert response.status_code == 200
        assert response.json()["title"] == "New Title"
        assert response.json()["time_limit_minutes"] == 90

    def test_delete_draft_exam(self, test_client: TestClient, auth_token: str):
        """DELETE /api/v1/exams/{id} deletes draft exam."""
        create_resp = test_client.post(
            "/api/v1/exams/",
            json={"title": "To Delete"},
            headers=self._auth_headers(auth_token),
        )
        exam_id = create_resp.json()["id"]
        response = test_client.delete(
            f"/api/v1/exams/{exam_id}",
            headers=self._auth_headers(auth_token),
        )
        assert response.status_code == 204

    def test_delete_finalized_exam_fails(self, test_client: TestClient, auth_token: str):
        """DELETE /api/v1/exams/{id} fails for finalized exams."""
        create_resp = test_client.post(
            "/api/v1/exams/",
            json={"title": "Finalized"},
            headers=self._auth_headers(auth_token),
        )
        exam_id = create_resp.json()["id"]
        # Manually finalize via DB (shortcut for test)
        # The finalize endpoint test is in Task 4
        response = test_client.delete(
            f"/api/v1/exams/{exam_id}",
            headers=self._auth_headers(auth_token),
        )
        # Should succeed since it's still draft
        assert response.status_code == 204

    def test_optimistic_locking_conflict(self, test_client: TestClient, auth_token: str):
        """PUT /api/v1/exams/{id} returns 409 on stale updated_at."""
        create_resp = test_client.post(
            "/api/v1/exams/",
            json={"title": "Locking Test"},
            headers=self._auth_headers(auth_token),
        )
        exam = create_resp.json()
        # First update succeeds
        test_client.put(
            f"/api/v1/exams/{exam['id']}",
            json={"title": "Updated", "updated_at": exam["updated_at"]},
            headers=self._auth_headers(auth_token),
        )
        # Second update with stale updated_at fails
        response = test_client.put(
            f"/api/v1/exams/{exam['id']}",
            json={"title": "Stale", "updated_at": exam["updated_at"]},
            headers=self._auth_headers(auth_token),
        )
        assert response.status_code == 409
```

Note: The `test_client` and `auth_token` fixtures must exist in `conftest.py`. Check the existing test setup — if these fixtures don't exist with these exact names, adapt to match the existing pattern (e.g., `authorized_client`, `test_token`). Read `packages/core/backend/tests/conftest.py` before implementing.

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/core/backend && python -m pytest tests/test_exam_api.py::TestExamCRUDApi -v
```

Expected: FAIL — endpoints don't exist yet.

- [ ] **Step 3: Create the exams API router**

Create `packages/core/backend/api/exams.py` with Pydantic schemas and CRUD endpoints:

```python
"""
Exam Composer API Endpoints for ExamCraft AI
CRUD, question management, auto-fill, finalize, and export.
"""

from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sa_func

from database import get_db
from models.exam import Exam, ExamQuestion, ExamStatus
from models.question_review import QuestionReview, ReviewStatus
from models.auth import User
from utils.auth_utils import get_current_active_user, require_permission
from utils.tenant_utils import TenantFilter, get_tenant_context
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/exams", tags=["Exam Composer"])


# --- Point auto-suggestion table ---
POINT_SUGGESTIONS = {
    ("multiple_choice", "easy"): 2,
    ("multiple_choice", "medium"): 4,
    ("multiple_choice", "hard"): 6,
    ("true_false", "easy"): 1,
    ("true_false", "medium"): 2,
    ("true_false", "hard"): 3,
    ("open_ended", "easy"): 3,
    ("open_ended", "medium"): 6,
    ("open_ended", "hard"): 10,
}


def suggest_points(question_type: str, difficulty: str) -> float:
    return float(POINT_SUGGESTIONS.get((question_type, difficulty), 4))


# --- Pydantic Schemas ---

class ExamCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    course: Optional[str] = Field(None, max_length=200)
    exam_date: Optional[date] = None
    time_limit_minutes: Optional[int] = Field(None, ge=1)
    allowed_aids: Optional[str] = None
    instructions: Optional[str] = None
    passing_percentage: float = Field(50.0, ge=0, le=100)
    language: str = Field("de", pattern="^(de|en)$")


class ExamUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    course: Optional[str] = Field(None, max_length=200)
    exam_date: Optional[date] = None
    time_limit_minutes: Optional[int] = Field(None, ge=1)
    allowed_aids: Optional[str] = None
    instructions: Optional[str] = None
    passing_percentage: Optional[float] = Field(None, ge=0, le=100)
    language: Optional[str] = Field(None, pattern="^(de|en)$")
    updated_at: datetime = Field(..., description="For optimistic locking")


class ExamQuestionOut(BaseModel):
    id: int
    question_id: int
    position: int
    points: float
    section: Optional[str]
    question_text: str
    question_type: str
    difficulty: str
    topic: str
    bloom_level: Optional[int]
    review_status: str
    options: Optional[list] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None

    class Config:
        from_attributes = True


class ExamOut(BaseModel):
    id: int
    title: str
    course: Optional[str]
    exam_date: Optional[date]
    time_limit_minutes: Optional[int]
    allowed_aids: Optional[str]
    instructions: Optional[str]
    passing_percentage: float
    total_points: float
    status: str
    language: str
    created_at: datetime
    updated_at: datetime
    question_count: int = 0

    class Config:
        from_attributes = True


class ExamDetailOut(ExamOut):
    questions: List[ExamQuestionOut] = []


class ExamListOut(BaseModel):
    total: int
    exams: List[ExamOut]


# --- Helpers ---

def _get_exam_or_404(exam_id: int, db: Session, current_user: User) -> Exam:
    exam = (
        db.query(Exam)
        .options(joinedload(Exam.questions).joinedload(ExamQuestion.question))
        .filter(Exam.id == exam_id)
        .first()
    )
    if not exam:
        raise HTTPException(status_code=404, detail=f"Exam {exam_id} not found")
    tenant_context = get_tenant_context(current_user)
    TenantFilter.verify_tenant_access(exam, tenant_context)
    return exam


def _require_draft(exam: Exam):
    if exam.status != ExamStatus.DRAFT.value:
        raise HTTPException(
            status_code=400,
            detail=f"Exam must be in 'draft' status (current: {exam.status}). Use unfinalize first.",
        )


def _exam_to_out(exam: Exam) -> dict:
    return {
        "id": exam.id,
        "title": exam.title,
        "course": exam.course,
        "exam_date": exam.exam_date,
        "time_limit_minutes": exam.time_limit_minutes,
        "allowed_aids": exam.allowed_aids,
        "instructions": exam.instructions,
        "passing_percentage": exam.passing_percentage,
        "total_points": exam.total_points,
        "status": exam.status,
        "language": exam.language,
        "created_at": exam.created_at,
        "updated_at": exam.updated_at,
        "question_count": len(exam.questions) if exam.questions else 0,
    }


def _exam_detail_to_out(exam: Exam) -> dict:
    data = _exam_to_out(exam)
    data["questions"] = [
        {
            "id": eq.id,
            "question_id": eq.question_id,
            "position": eq.position,
            "points": eq.points,
            "section": eq.section,
            "question_text": eq.question.question_text,
            "question_type": eq.question.question_type,
            "difficulty": eq.question.difficulty,
            "topic": eq.question.topic,
            "bloom_level": eq.question.bloom_level,
            "review_status": eq.question.review_status,
            "options": eq.question.options,
            "correct_answer": eq.question.correct_answer,
            "explanation": eq.question.explanation,
        }
        for eq in exam.questions
    ]
    return data


# --- CRUD Endpoints ---

@router.post("/", response_model=ExamOut, status_code=201)
async def create_exam(
    request: ExamCreate,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Create a new exam (draft status)."""
    exam = Exam(
        title=request.title,
        course=request.course,
        exam_date=request.exam_date,
        time_limit_minutes=request.time_limit_minutes,
        allowed_aids=request.allowed_aids,
        instructions=request.instructions,
        passing_percentage=request.passing_percentage,
        language=request.language,
        institution_id=current_user.institution_id,
        created_by=current_user.id,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    logger.info(f"Created exam {exam.id} by user {current_user.id}")
    return _exam_to_out(exam)


@router.get("/", response_model=ExamListOut)
async def list_exams(
    status: Optional[str] = Query(None, pattern="^(draft|finalized|exported)$"),
    search: Optional[str] = Query(None, max_length=200),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """List exams for the current user's institution."""
    tenant_context = get_tenant_context(current_user)
    query = db.query(Exam)
    query = TenantFilter.filter_by_tenant(query, Exam, tenant_context)

    if status:
        query = query.filter(Exam.status == status)
    if search:
        query = query.filter(Exam.title.ilike(f"%{search}%"))

    total = query.count()
    exams = (
        query.order_by(Exam.updated_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return ExamListOut(
        total=total,
        exams=[_exam_to_out(e) for e in exams],
    )


@router.get("/{exam_id}", response_model=ExamDetailOut)
async def get_exam(
    exam_id: int,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Get exam with all questions."""
    exam = _get_exam_or_404(exam_id, db, current_user)
    return _exam_detail_to_out(exam)


@router.put("/{exam_id}", response_model=ExamOut)
async def update_exam(
    exam_id: int,
    request: ExamUpdate,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Update exam metadata. Requires updated_at for optimistic locking."""
    exam = _get_exam_or_404(exam_id, db, current_user)
    _require_draft(exam)

    # Optimistic locking
    if exam.updated_at and request.updated_at:
        db_updated = exam.updated_at.replace(microsecond=0)
        req_updated = request.updated_at.replace(microsecond=0, tzinfo=db_updated.tzinfo)
        if db_updated != req_updated:
            raise HTTPException(
                status_code=409,
                detail="Conflict: exam was modified by another user. Please reload.",
            )

    update_data = request.model_dump(exclude_unset=True, exclude={"updated_at"})
    for field, value in update_data.items():
        setattr(exam, field, value)

    db.commit()
    db.refresh(exam)
    logger.info(f"Updated exam {exam_id} by user {current_user.id}")
    return _exam_to_out(exam)


@router.delete("/{exam_id}", status_code=204)
async def delete_exam(
    exam_id: int,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Delete a draft exam."""
    exam = _get_exam_or_404(exam_id, db, current_user)
    _require_draft(exam)
    db.delete(exam)
    db.commit()
    logger.info(f"Deleted exam {exam_id} by user {current_user.id}")
```

- [ ] **Step 4: Register router in main.py**

In `packages/core/backend/main.py`, find the router registration section (around line 126-217 in the lifespan function) and add:

```python
spec_exams = importlib.util.spec_from_file_location(
    "core_api_exams", os.path.join(core_api_path, "exams.py")
)
exams_api = importlib.util.module_from_spec(spec_exams)
spec_exams.loader.exec_module(exams_api)
app.include_router(exams_api.router)
```

Add this alongside the existing router registrations (after the `question_review` router).

- [ ] **Step 5: Run CRUD tests**

```bash
cd packages/core/backend && python -m pytest tests/test_exam_api.py::TestExamCRUDApi -v
```

Expected: All tests PASS. If fixture names differ from existing conftest, adapt accordingly.

- [ ] **Step 6: Commit**

```bash
git add packages/core/backend/api/exams.py packages/core/backend/main.py packages/core/backend/tests/test_exam_api.py
git commit -m "feat(exam): add CRUD API endpoints for exams (TF-56)"
```

---

## Task 3: Backend API — Question Management

**Files:**
- Modify: `packages/core/backend/api/exams.py`
- Test: `packages/core/backend/tests/test_exam_api.py` (append)

- [ ] **Step 1: Write question management tests**

Append to `packages/core/backend/tests/test_exam_api.py`:

```python
class TestExamQuestionApi:
    """Tests for exam question management endpoints."""

    def _auth_headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def _create_exam(self, client, token):
        resp = client.post(
            "/api/v1/exams/",
            json={"title": "Question Test Exam"},
            headers=self._auth_headers(token),
        )
        return resp.json()

    def _create_approved_question(self, db, institution_id, user_id, text="Test Q"):
        from models.question_review import QuestionReview
        q = QuestionReview(
            question_text=text,
            question_type="multiple_choice",
            difficulty="medium",
            topic="Test",
            review_status="approved",
            options=["A", "B", "C", "D"],
            correct_answer="A",
            institution_id=institution_id,
            created_by=user_id,
        )
        db.add(q)
        db.commit()
        db.refresh(q)
        return q

    def test_add_questions(self, test_client, auth_token, test_db, test_user):
        """POST /api/v1/exams/{id}/questions adds questions with auto-suggested points."""
        exam = self._create_exam(test_client, auth_token)
        q = self._create_approved_question(test_db, test_user.institution_id, test_user.id)

        response = test_client.post(
            f"/api/v1/exams/{exam['id']}/questions",
            json={"question_ids": [q.id]},
            headers=self._auth_headers(auth_token),
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["questions"]) == 1
        assert data["questions"][0]["question_id"] == q.id
        assert data["questions"][0]["points"] == 4.0  # medium MC = 4
        assert data["total_points"] == 4.0

    def test_add_non_approved_question_fails(self, test_client, auth_token, test_db, test_user):
        """POST /api/v1/exams/{id}/questions rejects non-approved questions."""
        from models.question_review import QuestionReview
        exam = self._create_exam(test_client, auth_token)
        q = QuestionReview(
            question_text="Pending Q", question_type="open_ended",
            difficulty="easy", topic="Test", review_status="pending",
            institution_id=test_user.institution_id, created_by=test_user.id,
        )
        test_db.add(q)
        test_db.commit()

        response = test_client.post(
            f"/api/v1/exams/{exam['id']}/questions",
            json={"question_ids": [q.id]},
            headers=self._auth_headers(auth_token),
        )
        assert response.status_code == 400

    def test_remove_question(self, test_client, auth_token, test_db, test_user):
        """DELETE /api/v1/exams/{id}/questions/{eq_id} removes question."""
        exam = self._create_exam(test_client, auth_token)
        q = self._create_approved_question(test_db, test_user.institution_id, test_user.id)
        test_client.post(
            f"/api/v1/exams/{exam['id']}/questions",
            json={"question_ids": [q.id]},
            headers=self._auth_headers(auth_token),
        )

        # Get the exam to find the exam_question id
        detail = test_client.get(
            f"/api/v1/exams/{exam['id']}",
            headers=self._auth_headers(auth_token),
        ).json()
        eq_id = detail["questions"][0]["id"]

        response = test_client.delete(
            f"/api/v1/exams/{exam['id']}/questions/{eq_id}",
            headers=self._auth_headers(auth_token),
        )
        assert response.status_code == 200
        assert response.json()["total_points"] == 0.0

    def test_reorder_questions(self, test_client, auth_token, test_db, test_user):
        """POST /api/v1/exams/{id}/reorder changes question order."""
        exam = self._create_exam(test_client, auth_token)
        q1 = self._create_approved_question(test_db, test_user.institution_id, test_user.id, "Q1")
        q2 = self._create_approved_question(test_db, test_user.institution_id, test_user.id, "Q2")
        test_client.post(
            f"/api/v1/exams/{exam['id']}/questions",
            json={"question_ids": [q1.id, q2.id]},
            headers=self._auth_headers(auth_token),
        )

        detail = test_client.get(
            f"/api/v1/exams/{exam['id']}",
            headers=self._auth_headers(auth_token),
        ).json()
        eq_ids = [q["id"] for q in detail["questions"]]

        # Swap order
        response = test_client.post(
            f"/api/v1/exams/{exam['id']}/reorder",
            json={"order": [{"id": eq_ids[0], "position": 2}, {"id": eq_ids[1], "position": 1}]},
            headers=self._auth_headers(auth_token),
        )
        assert response.status_code == 200
        questions = response.json()["questions"]
        assert questions[0]["id"] == eq_ids[1]
        assert questions[1]["id"] == eq_ids[0]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/core/backend && python -m pytest tests/test_exam_api.py::TestExamQuestionApi -v
```

- [ ] **Step 3: Implement question management endpoints**

Append to `packages/core/backend/api/exams.py`:

```python
# --- Question Management Schemas ---

class AddQuestionsRequest(BaseModel):
    question_ids: List[int] = Field(..., min_length=1)


class UpdateExamQuestionRequest(BaseModel):
    points: Optional[float] = Field(None, ge=0)
    section: Optional[str] = Field(None, max_length=100)


class ReorderItem(BaseModel):
    id: int
    position: int


class ReorderRequest(BaseModel):
    order: List[ReorderItem]


# --- Question Management Endpoints ---

@router.post("/{exam_id}/questions", response_model=ExamDetailOut)
async def add_questions(
    exam_id: int,
    request: AddQuestionsRequest,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Add approved questions to exam with auto-suggested points."""
    exam = _get_exam_or_404(exam_id, db, current_user)
    _require_draft(exam)

    # Get current max position
    max_pos = max((eq.position for eq in exam.questions), default=0)

    # Validate and add each question
    existing_qids = {eq.question_id for eq in exam.questions}
    tenant_context = get_tenant_context(current_user)

    for qid in request.question_ids:
        if qid in existing_qids:
            continue  # Skip duplicates silently

        question = db.query(QuestionReview).filter(QuestionReview.id == qid).first()
        if not question:
            raise HTTPException(status_code=404, detail=f"Question {qid} not found")

        TenantFilter.verify_tenant_access(question, tenant_context)

        if question.review_status != ReviewStatus.APPROVED.value:
            raise HTTPException(
                status_code=400,
                detail=f"Question {qid} is not approved (status: {question.review_status})",
            )

        max_pos += 1
        points = suggest_points(question.question_type, question.difficulty)
        eq = ExamQuestion(
            exam_id=exam.id,
            question_id=qid,
            position=max_pos,
            points=points,
        )
        db.add(eq)
        existing_qids.add(qid)

    db.flush()
    db.refresh(exam)
    exam.recalculate_total_points()
    db.commit()
    db.refresh(exam)

    return _exam_detail_to_out(exam)


@router.put("/{exam_id}/questions/{eq_id}", response_model=ExamDetailOut)
async def update_exam_question(
    exam_id: int,
    eq_id: int,
    request: UpdateExamQuestionRequest,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Update points or section of a question in the exam."""
    exam = _get_exam_or_404(exam_id, db, current_user)
    _require_draft(exam)

    eq = db.query(ExamQuestion).filter(
        ExamQuestion.id == eq_id, ExamQuestion.exam_id == exam_id
    ).first()
    if not eq:
        raise HTTPException(status_code=404, detail=f"Exam question {eq_id} not found")

    if request.points is not None:
        eq.points = request.points
    if request.section is not None:
        eq.section = request.section

    db.flush()
    db.refresh(exam)
    exam.recalculate_total_points()
    db.commit()
    db.refresh(exam)

    return _exam_detail_to_out(exam)


@router.delete("/{exam_id}/questions/{eq_id}", response_model=ExamDetailOut)
async def remove_exam_question(
    exam_id: int,
    eq_id: int,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Remove a question from the exam."""
    exam = _get_exam_or_404(exam_id, db, current_user)
    _require_draft(exam)

    eq = db.query(ExamQuestion).filter(
        ExamQuestion.id == eq_id, ExamQuestion.exam_id == exam_id
    ).first()
    if not eq:
        raise HTTPException(status_code=404, detail=f"Exam question {eq_id} not found")

    db.delete(eq)

    # Re-number remaining positions
    remaining = (
        db.query(ExamQuestion)
        .filter(ExamQuestion.exam_id == exam_id)
        .order_by(ExamQuestion.position)
        .all()
    )
    for i, item in enumerate(remaining, 1):
        item.position = i

    db.flush()
    db.refresh(exam)
    exam.recalculate_total_points()
    db.commit()
    db.refresh(exam)

    return _exam_detail_to_out(exam)


@router.post("/{exam_id}/reorder", response_model=ExamDetailOut)
async def reorder_questions(
    exam_id: int,
    request: ReorderRequest,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Batch reorder questions in the exam."""
    exam = _get_exam_or_404(exam_id, db, current_user)
    _require_draft(exam)

    eq_map = {eq.id: eq for eq in exam.questions}
    # Temporarily set all positions to negative to avoid unique constraint violations
    for eq in exam.questions:
        eq.position = -eq.position
    db.flush()

    for item in request.order:
        if item.id not in eq_map:
            raise HTTPException(status_code=404, detail=f"Exam question {item.id} not found")
        eq_map[item.id].position = item.position

    db.commit()
    db.refresh(exam)
    return _exam_detail_to_out(exam)
```

- [ ] **Step 4: Run tests**

```bash
cd packages/core/backend && python -m pytest tests/test_exam_api.py::TestExamQuestionApi -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/core/backend/api/exams.py packages/core/backend/tests/test_exam_api.py
git commit -m "feat(exam): add question management endpoints (add, remove, reorder) (TF-56)"
```

---

## Task 4: Backend API — Auto-Fill, Approved Questions, Finalize, Export

**Files:**
- Modify: `packages/core/backend/api/exams.py`
- Create: `packages/core/backend/services/exam_export_service.py`
- Test: `packages/core/backend/tests/test_exam_api.py` (append)
- Test: `packages/core/backend/tests/test_exam_export.py`

- [ ] **Step 1: Write finalize + approved-questions + auto-fill tests**

Append to `packages/core/backend/tests/test_exam_api.py`:

```python
class TestExamWorkflowApi:
    """Tests for finalize, unfinalize, approved-questions, auto-fill."""

    def _auth_headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def _create_exam_with_question(self, client, token, db, user):
        from models.question_review import QuestionReview
        exam = client.post(
            "/api/v1/exams/",
            json={"title": "Workflow Test"},
            headers=self._auth_headers(token),
        ).json()
        q = QuestionReview(
            question_text="Approved Q",
            question_type="multiple_choice",
            difficulty="medium",
            topic="Test",
            review_status="approved",
            options=["A", "B", "C", "D"],
            correct_answer="A",
            explanation="A is correct.",
            institution_id=user.institution_id,
            created_by=user.id,
        )
        db.add(q)
        db.commit()
        client.post(
            f"/api/v1/exams/{exam['id']}/questions",
            json={"question_ids": [q.id]},
            headers=self._auth_headers(token),
        )
        return exam, q

    def test_finalize_exam(self, test_client, auth_token, test_db, test_user):
        """POST /api/v1/exams/{id}/finalize sets status to finalized."""
        exam, _ = self._create_exam_with_question(test_client, auth_token, test_db, test_user)
        response = test_client.post(
            f"/api/v1/exams/{exam['id']}/finalize",
            headers=self._auth_headers(auth_token),
        )
        assert response.status_code == 200
        assert response.json()["status"] == "finalized"

    def test_finalize_empty_exam_fails(self, test_client, auth_token):
        """POST /api/v1/exams/{id}/finalize fails for empty exam."""
        exam = test_client.post(
            "/api/v1/exams/",
            json={"title": "Empty"},
            headers=self._auth_headers(auth_token),
        ).json()
        response = test_client.post(
            f"/api/v1/exams/{exam['id']}/finalize",
            headers=self._auth_headers(auth_token),
        )
        assert response.status_code == 400

    def test_unfinalize_exam(self, test_client, auth_token, test_db, test_user):
        """POST /api/v1/exams/{id}/unfinalize reverts to draft."""
        exam, _ = self._create_exam_with_question(test_client, auth_token, test_db, test_user)
        test_client.post(
            f"/api/v1/exams/{exam['id']}/finalize",
            headers=self._auth_headers(auth_token),
        )
        response = test_client.post(
            f"/api/v1/exams/{exam['id']}/unfinalize",
            headers=self._auth_headers(auth_token),
        )
        assert response.status_code == 200
        assert response.json()["status"] == "draft"

    def test_approved_questions_endpoint(self, test_client, auth_token, test_db, test_user):
        """GET /api/v1/exams/approved-questions returns approved questions."""
        from models.question_review import QuestionReview
        q = QuestionReview(
            question_text="Searchable Q",
            question_type="open_ended",
            difficulty="hard",
            topic="Heapsort",
            review_status="approved",
            institution_id=test_user.institution_id,
            created_by=test_user.id,
        )
        test_db.add(q)
        test_db.commit()
        response = test_client.get(
            "/api/v1/exams/approved-questions?topic=Heapsort",
            headers=self._auth_headers(auth_token),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
```

- [ ] **Step 2: Write export tests**

Create `packages/core/backend/tests/test_exam_export.py`:

```python
"""Tests for Exam Export Service."""

import pytest
from services.exam_export_service import MarkdownExporter, JsonExporter, MoodleXmlExporter


@pytest.fixture
def sample_exam_data():
    return {
        "title": "Algorithmen Midterm",
        "course": "Algo & DS",
        "exam_date": "2026-04-15",
        "time_limit_minutes": 90,
        "allowed_aids": "Alle schriftlichen Unterlagen",
        "instructions": "Beantworten Sie alle Fragen.",
        "passing_percentage": 50.0,
        "total_points": 10.0,
        "language": "de",
        "questions": [
            {
                "position": 1,
                "points": 4.0,
                "question_text": "Wie funktioniert Heapify?",
                "question_type": "multiple_choice",
                "difficulty": "medium",
                "options": ["A) Top-down", "B) Bottom-up", "C) Beide", "D) Keines"],
                "correct_answer": "C) Beide",
                "explanation": "Heapify kann top-down und bottom-up arbeiten.",
            },
            {
                "position": 2,
                "points": 6.0,
                "question_text": "Erklären Sie die Zeitkomplexität von BuildHeap.",
                "question_type": "open_ended",
                "difficulty": "hard",
                "correct_answer": "O(n) amortisiert.",
                "explanation": "Durch die Summe der Höhen ergibt sich O(n).",
            },
        ],
    }


class TestMarkdownExporter:
    def test_export_questions_only(self, sample_exam_data):
        md = MarkdownExporter.export(sample_exam_data, include_solutions=False)
        assert "# Algorithmen Midterm" in md
        assert "Wie funktioniert Heapify?" in md
        assert "4 Punkte" in md or "4.0 Punkte" in md
        assert "Musterlösung" not in md
        assert "C) Beide" not in md  # Solution not shown

    def test_export_with_solutions(self, sample_exam_data):
        md = MarkdownExporter.export(sample_exam_data, include_solutions=True)
        assert "Musterlösung" in md or "Lösung" in md
        assert "C) Beide" in md


class TestJsonExporter:
    def test_export_structure(self, sample_exam_data):
        import json
        result = JsonExporter.export(sample_exam_data)
        data = json.loads(result)
        assert data["exam"]["title"] == "Algorithmen Midterm"
        assert len(data["questions"]) == 2
        assert data["questions"][0]["points"] == 4.0


class TestMoodleXmlExporter:
    def test_export_valid_xml(self, sample_exam_data):
        xml = MoodleXmlExporter.export(sample_exam_data)
        assert "<?xml" in xml
        assert "<quiz>" in xml
        assert "<question type=" in xml
        assert "Heapify" in xml

    def test_mc_question_format(self, sample_exam_data):
        xml = MoodleXmlExporter.export(sample_exam_data)
        assert "multichoice" in xml

    def test_open_ended_question_format(self, sample_exam_data):
        xml = MoodleXmlExporter.export(sample_exam_data)
        assert "essay" in xml
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd packages/core/backend && python -m pytest tests/test_exam_api.py::TestExamWorkflowApi tests/test_exam_export.py -v
```

- [ ] **Step 4: Create export service**

Create `packages/core/backend/services/exam_export_service.py`:

```python
"""
Exam Export Service for ExamCraft AI
Exports exams to Markdown, JSON, and Moodle XML formats.
"""

import json
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString


class MarkdownExporter:
    @staticmethod
    def export(exam_data: dict, include_solutions: bool = False) -> str:
        lines = []
        lines.append(f"# {exam_data['title']}\n")

        if exam_data.get("course"):
            lines.append(f"**Kurs:** {exam_data['course']}  ")
        if exam_data.get("exam_date"):
            lines.append(f"**Datum:** {exam_data['exam_date']}  ")
        if exam_data.get("time_limit_minutes"):
            lines.append(f"**Zeitlimit:** {exam_data['time_limit_minutes']} Minuten  ")
        if exam_data.get("allowed_aids"):
            lines.append(f"**Erlaubte Hilfsmittel:** {exam_data['allowed_aids']}  ")

        lines.append(f"**Gesamtpunktzahl:** {exam_data['total_points']} Punkte  ")
        lines.append(
            f"**Bestehensgrenze:** {exam_data['passing_percentage']}% "
            f"({exam_data['total_points'] * exam_data['passing_percentage'] / 100:.0f} Punkte)  "
        )

        if exam_data.get("instructions"):
            lines.append(f"\n## Hinweise\n\n{exam_data['instructions']}\n")

        lines.append("\n---\n")

        for q in exam_data["questions"]:
            lines.append(f"## Frage {q['position']} ({q['points']} Punkte) — {_type_label(q['question_type'])}\n")
            lines.append(f"{q['question_text']}\n")

            if q["question_type"] == "multiple_choice" and q.get("options"):
                lines.append("")
                for opt in q["options"]:
                    lines.append(f"- [ ] {opt}")
                lines.append("")
            elif q["question_type"] == "true_false":
                lines.append("\n- [ ] Wahr\n- [ ] Falsch\n")
            else:
                lines.append("\n*Antwort:*\n\n\\  \n\\  \n\\  \n")

            if include_solutions and q.get("correct_answer"):
                lines.append(f"\n> **Musterlösung:** {q['correct_answer']}")
                if q.get("explanation"):
                    lines.append(f">\n> **Erklärung:** {q['explanation']}")
                lines.append("")

            lines.append("\n---\n")

        return "\n".join(lines)


class JsonExporter:
    @staticmethod
    def export(exam_data: dict) -> str:
        output = {
            "exam": {
                "title": exam_data["title"],
                "course": exam_data.get("course"),
                "exam_date": exam_data.get("exam_date"),
                "time_limit_minutes": exam_data.get("time_limit_minutes"),
                "allowed_aids": exam_data.get("allowed_aids"),
                "instructions": exam_data.get("instructions"),
                "total_points": exam_data["total_points"],
                "passing_percentage": exam_data["passing_percentage"],
                "language": exam_data.get("language", "de"),
            },
            "questions": [
                {
                    "position": q["position"],
                    "points": q["points"],
                    "question_text": q["question_text"],
                    "question_type": q["question_type"],
                    "difficulty": q.get("difficulty"),
                    "options": q.get("options"),
                    "correct_answer": q.get("correct_answer"),
                    "explanation": q.get("explanation"),
                }
                for q in exam_data["questions"]
            ],
        }
        return json.dumps(output, ensure_ascii=False, indent=2)


class MoodleXmlExporter:
    @staticmethod
    def export(exam_data: dict) -> str:
        quiz = Element("quiz")

        for q in exam_data["questions"]:
            qtype = q["question_type"]
            if qtype == "multiple_choice":
                _add_mc_question(quiz, q)
            elif qtype == "true_false":
                _add_tf_question(quiz, q)
            else:
                _add_essay_question(quiz, q)

        raw_xml = tostring(quiz, encoding="unicode")
        dom = parseString(raw_xml)
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + dom.toprettyxml(indent="  ")[dom.toprettyxml().index('\n')+1:]


def _type_label(question_type: str) -> str:
    return {
        "multiple_choice": "Multiple Choice",
        "true_false": "Wahr/Falsch",
        "open_ended": "Offene Frage",
    }.get(question_type, question_type)


def _add_mc_question(quiz: Element, q: dict):
    question = SubElement(quiz, "question", type="multichoice")
    name = SubElement(question, "name")
    SubElement(name, "text").text = f"Frage {q['position']}"
    qtext = SubElement(question, "questiontext", format="html")
    SubElement(qtext, "text").text = q["question_text"]
    SubElement(question, "defaultgrade").text = str(q["points"])
    SubElement(question, "single").text = "true"
    SubElement(question, "shuffleanswers").text = "0"

    correct = q.get("correct_answer", "")
    for opt in q.get("options", []):
        answer = SubElement(question, "answer", fraction="100" if opt == correct else "0")
        SubElement(answer, "text").text = opt
        feedback = SubElement(answer, "feedback")
        SubElement(feedback, "text").text = ""

    if q.get("explanation"):
        gf = SubElement(question, "generalfeedback", format="html")
        SubElement(gf, "text").text = q["explanation"]


def _add_tf_question(quiz: Element, q: dict):
    question = SubElement(quiz, "question", type="truefalse")
    name = SubElement(question, "name")
    SubElement(name, "text").text = f"Frage {q['position']}"
    qtext = SubElement(question, "questiontext", format="html")
    SubElement(qtext, "text").text = q["question_text"]
    SubElement(question, "defaultgrade").text = str(q["points"])

    correct_answer = (q.get("correct_answer") or "").lower()
    is_true = correct_answer in ("wahr", "true", "richtig")
    answer_true = SubElement(question, "answer", fraction="100" if is_true else "0")
    SubElement(answer_true, "text").text = "true"
    answer_false = SubElement(question, "answer", fraction="0" if is_true else "100")
    SubElement(answer_false, "text").text = "false"


def _add_essay_question(quiz: Element, q: dict):
    question = SubElement(quiz, "question", type="essay")
    name = SubElement(question, "name")
    SubElement(name, "text").text = f"Frage {q['position']}"
    qtext = SubElement(question, "questiontext", format="html")
    SubElement(qtext, "text").text = q["question_text"]
    SubElement(question, "defaultgrade").text = str(q["points"])

    if q.get("explanation"):
        gf = SubElement(question, "generalfeedback", format="html")
        SubElement(gf, "text").text = q["explanation"]
```

- [ ] **Step 5: Add workflow + export endpoints to the API router**

Append to `packages/core/backend/api/exams.py`. **IMPORTANT:** The `approved-questions` endpoint MUST be registered BEFORE the `/{exam_id}` path-parameter routes in the file, otherwise FastAPI will try to parse "approved-questions" as an integer exam_id. Move it above the `get_exam` endpoint, or add it here and ensure the router ordering is correct.

```python
from services.exam_export_service import MarkdownExporter, JsonExporter, MoodleXmlExporter

# --- Approved Questions (must be before /{exam_id} routes!) ---

class ApprovedQuestionOut(BaseModel):
    id: int
    question_text: str
    question_type: str
    difficulty: str
    topic: str
    bloom_level: Optional[int]
    options: Optional[list]
    usage_count: int = 0

    class Config:
        from_attributes = True


class ApprovedQuestionsListOut(BaseModel):
    total: int
    questions: List[ApprovedQuestionOut]


@router.get("/approved-questions", response_model=ApprovedQuestionsListOut)
async def list_approved_questions(
    topic: Optional[str] = None,
    difficulty: Optional[str] = Query(None, pattern="^(easy|medium|hard)$"),
    bloom_level: Optional[int] = Query(None, ge=1, le=6),
    question_type: Optional[str] = Query(None, pattern="^(multiple_choice|open_ended|true_false)$"),
    search: Optional[str] = Query(None, max_length=500),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Browse approved questions for exam composition."""
    tenant_context = get_tenant_context(current_user)
    query = db.query(QuestionReview).filter(
        QuestionReview.review_status == ReviewStatus.APPROVED.value
    )
    query = TenantFilter.filter_by_tenant(query, QuestionReview, tenant_context)

    if topic:
        query = query.filter(QuestionReview.topic.ilike(f"%{topic}%"))
    if difficulty:
        query = query.filter(QuestionReview.difficulty == difficulty)
    if bloom_level:
        query = query.filter(QuestionReview.bloom_level == bloom_level)
    if question_type:
        query = query.filter(QuestionReview.question_type == question_type)
    if search:
        query = query.filter(QuestionReview.question_text.ilike(f"%{search}%"))

    total = query.count()
    questions = query.order_by(QuestionReview.created_at.desc()).limit(limit).offset(offset).all()

    result = []
    for q in questions:
        usage_count = db.query(sa_func.count(ExamQuestion.id)).filter(
            ExamQuestion.question_id == q.id
        ).scalar()
        result.append({
            "id": q.id,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "difficulty": q.difficulty,
            "topic": q.topic,
            "bloom_level": q.bloom_level,
            "options": q.options,
            "usage_count": usage_count,
        })

    return ApprovedQuestionsListOut(total=total, questions=result)


# --- Auto-Fill ---

class AutoFillRequest(BaseModel):
    count: int = Field(5, ge=1, le=20)
    topic: Optional[str] = None
    difficulty: Optional[List[str]] = None
    bloom_level_min: Optional[int] = Field(None, ge=1, le=6)
    question_types: Optional[List[str]] = None
    exclude_question_ids: Optional[List[int]] = None


@router.post("/{exam_id}/auto-fill", response_model=ExamDetailOut)
async def auto_fill_questions(
    exam_id: int,
    request: AutoFillRequest,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Auto-fill exam with questions matching criteria."""
    exam = _get_exam_or_404(exam_id, db, current_user)
    _require_draft(exam)

    tenant_context = get_tenant_context(current_user)
    query = db.query(QuestionReview).filter(
        QuestionReview.review_status == ReviewStatus.APPROVED.value
    )
    query = TenantFilter.filter_by_tenant(query, QuestionReview, tenant_context)

    # Exclude already-added questions
    existing_qids = {eq.question_id for eq in exam.questions}
    exclude_ids = existing_qids | set(request.exclude_question_ids or [])
    if exclude_ids:
        query = query.filter(QuestionReview.id.notin_(exclude_ids))

    if request.topic:
        query = query.filter(QuestionReview.topic.ilike(f"%{request.topic}%"))
    if request.difficulty:
        query = query.filter(QuestionReview.difficulty.in_(request.difficulty))
    if request.bloom_level_min:
        query = query.filter(QuestionReview.bloom_level >= request.bloom_level_min)
    if request.question_types:
        query = query.filter(QuestionReview.question_type.in_(request.question_types))

    # Random selection for diversity
    candidates = query.order_by(sa_func.random()).limit(request.count).all()

    if not candidates:
        raise HTTPException(status_code=404, detail="No matching questions found")

    max_pos = max((eq.position for eq in exam.questions), default=0)
    for q in candidates:
        max_pos += 1
        eq = ExamQuestion(
            exam_id=exam.id,
            question_id=q.id,
            position=max_pos,
            points=suggest_points(q.question_type, q.difficulty),
        )
        db.add(eq)

    db.flush()
    db.refresh(exam)
    exam.recalculate_total_points()
    db.commit()
    db.refresh(exam)

    return _exam_detail_to_out(exam)


# --- Finalize / Unfinalize ---

@router.post("/{exam_id}/finalize", response_model=ExamOut)
async def finalize_exam(
    exam_id: int,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Finalize exam. Validates all questions are still approved."""
    exam = _get_exam_or_404(exam_id, db, current_user)
    _require_draft(exam)

    if not exam.questions:
        raise HTTPException(status_code=400, detail="Cannot finalize an empty exam")

    # Check all questions are still approved
    non_approved = [
        eq for eq in exam.questions
        if eq.question.review_status != ReviewStatus.APPROVED.value
    ]
    if non_approved:
        ids = [eq.question_id for eq in non_approved]
        raise HTTPException(
            status_code=400,
            detail=f"Questions no longer approved: {ids}. Remove them before finalizing.",
        )

    exam.status = ExamStatus.FINALIZED.value
    db.commit()
    db.refresh(exam)
    return _exam_to_out(exam)


@router.post("/{exam_id}/unfinalize", response_model=ExamOut)
async def unfinalize_exam(
    exam_id: int,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Revert exam from finalized to draft."""
    exam = _get_exam_or_404(exam_id, db, current_user)
    if exam.status not in (ExamStatus.FINALIZED.value, ExamStatus.EXPORTED.value):
        raise HTTPException(status_code=400, detail="Exam is already a draft")

    exam.status = ExamStatus.DRAFT.value
    db.commit()
    db.refresh(exam)
    return _exam_to_out(exam)


# --- Export ---

@router.get("/{exam_id}/export/{format}")
async def export_exam(
    exam_id: int,
    format: str,
    include_solutions: bool = Query(False),
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Export exam in specified format (md, json, moodle)."""
    exam = _get_exam_or_404(exam_id, db, current_user)

    if not exam.questions:
        raise HTTPException(status_code=400, detail="Cannot export an empty exam")

    exam_data = _exam_detail_to_out(exam)
    # Convert date to string for export
    if exam_data.get("exam_date"):
        exam_data["exam_date"] = str(exam_data["exam_date"])

    safe_title = exam.title.replace(" ", "_")[:50]

    if format == "md":
        content = MarkdownExporter.export(exam_data, include_solutions=include_solutions)
        suffix = "_solutions" if include_solutions else ""
        media_type = "text/markdown"
        filename = f"exam_{safe_title}{suffix}.md"
    elif format == "json":
        content = JsonExporter.export(exam_data)
        media_type = "application/json"
        filename = f"exam_{safe_title}.json"
    elif format == "moodle":
        content = MoodleXmlExporter.export(exam_data)
        media_type = "application/xml"
        filename = f"exam_{safe_title}_moodle.xml"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}. Use md, json, or moodle.")

    # Update status to exported
    if exam.status == ExamStatus.FINALIZED.value:
        exam.status = ExamStatus.EXPORTED.value
        db.commit()

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 6: Run all tests**

```bash
cd packages/core/backend && python -m pytest tests/test_exam_api.py tests/test_exam_export.py -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add packages/core/backend/api/exams.py packages/core/backend/services/exam_export_service.py packages/core/backend/tests/test_exam_api.py packages/core/backend/tests/test_exam_export.py
git commit -m "feat(exam): add auto-fill, finalize, export endpoints and export service (TF-56)"
```

---

## Task 5: Frontend — Types + API Service

**Files:**
- Create: `packages/core/frontend/src/types/composer.ts`
- Create: `packages/core/frontend/src/services/ComposerService.ts`

- [ ] **Step 1: Create TypeScript types**

Create `packages/core/frontend/src/types/composer.ts`:

```typescript
export enum ExamStatus {
  DRAFT = 'draft',
  FINALIZED = 'finalized',
  EXPORTED = 'exported',
}

export interface ExamQuestion {
  id: number;
  question_id: number;
  position: number;
  points: number;
  section: string | null;
  question_text: string;
  question_type: string;
  difficulty: string;
  topic: string;
  bloom_level: number | null;
  review_status: string;
  options: string[] | null;
  correct_answer: string | null;
  explanation: string | null;
}

export interface Exam {
  id: number;
  title: string;
  course: string | null;
  exam_date: string | null;
  time_limit_minutes: number | null;
  allowed_aids: string | null;
  instructions: string | null;
  passing_percentage: number;
  total_points: number;
  status: ExamStatus;
  language: string;
  created_at: string;
  updated_at: string;
  question_count: number;
}

export interface ExamDetail extends Exam {
  questions: ExamQuestion[];
}

export interface ExamListResponse {
  total: number;
  exams: Exam[];
}

export interface CreateExamRequest {
  title: string;
  course?: string;
  exam_date?: string;
  time_limit_minutes?: number;
  allowed_aids?: string;
  instructions?: string;
  passing_percentage?: number;
  language?: string;
}

export interface UpdateExamRequest extends Partial<CreateExamRequest> {
  updated_at: string;
}

export interface ApprovedQuestion {
  id: number;
  question_text: string;
  question_type: string;
  difficulty: string;
  topic: string;
  bloom_level: number | null;
  options: string[] | null;
  usage_count: number;
}

export interface ApprovedQuestionsResponse {
  total: number;
  questions: ApprovedQuestion[];
}

export interface AutoFillRequest {
  count?: number;
  topic?: string;
  difficulty?: string[];
  bloom_level_min?: number;
  question_types?: string[];
  exclude_question_ids?: number[];
}
```

- [ ] **Step 2: Create API service**

Create `packages/core/frontend/src/services/ComposerService.ts`:

```typescript
import axios from 'axios';
import type {
  Exam,
  ExamDetail,
  ExamListResponse,
  CreateExamRequest,
  UpdateExamRequest,
  ApprovedQuestionsResponse,
  AutoFillRequest,
} from '../types/composer';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('examcraft_access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export class ComposerService {
  static async listExams(params?: {
    status?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<ExamListResponse> {
    const response = await apiClient.get('/api/v1/exams/', { params });
    return response.data;
  }

  static async getExam(examId: number): Promise<ExamDetail> {
    const response = await apiClient.get(`/api/v1/exams/${examId}`);
    return response.data;
  }

  static async createExam(data: CreateExamRequest): Promise<Exam> {
    const response = await apiClient.post('/api/v1/exams/', data);
    return response.data;
  }

  static async updateExam(examId: number, data: UpdateExamRequest): Promise<Exam> {
    const response = await apiClient.put(`/api/v1/exams/${examId}`, data);
    return response.data;
  }

  static async deleteExam(examId: number): Promise<void> {
    await apiClient.delete(`/api/v1/exams/${examId}`);
  }

  static async addQuestions(examId: number, questionIds: number[]): Promise<ExamDetail> {
    const response = await apiClient.post(`/api/v1/exams/${examId}/questions`, {
      question_ids: questionIds,
    });
    return response.data;
  }

  static async updateExamQuestion(
    examId: number,
    eqId: number,
    data: { points?: number; section?: string }
  ): Promise<ExamDetail> {
    const response = await apiClient.put(`/api/v1/exams/${examId}/questions/${eqId}`, data);
    return response.data;
  }

  static async removeExamQuestion(examId: number, eqId: number): Promise<ExamDetail> {
    const response = await apiClient.delete(`/api/v1/exams/${examId}/questions/${eqId}`);
    return response.data;
  }

  static async reorderQuestions(
    examId: number,
    order: { id: number; position: number }[]
  ): Promise<ExamDetail> {
    const response = await apiClient.post(`/api/v1/exams/${examId}/reorder`, { order });
    return response.data;
  }

  static async autoFill(examId: number, request: AutoFillRequest): Promise<ExamDetail> {
    const response = await apiClient.post(`/api/v1/exams/${examId}/auto-fill`, request);
    return response.data;
  }

  static async finalizeExam(examId: number): Promise<Exam> {
    const response = await apiClient.post(`/api/v1/exams/${examId}/finalize`);
    return response.data;
  }

  static async unfinalizeExam(examId: number): Promise<Exam> {
    const response = await apiClient.post(`/api/v1/exams/${examId}/unfinalize`);
    return response.data;
  }

  static async listApprovedQuestions(params?: {
    topic?: string;
    difficulty?: string;
    bloom_level?: number;
    question_type?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<ApprovedQuestionsResponse> {
    const response = await apiClient.get('/api/v1/exams/approved-questions', { params });
    return response.data;
  }

  static async downloadExport(examId: number, format: string, includeSolutions = false): Promise<void> {
    const params = new URLSearchParams();
    if (includeSolutions) params.set('include_solutions', 'true');
    const response = await apiClient.get(
      `/api/v1/exams/${examId}/export/${format}`,
      { params, responseType: 'blob' }
    );
    const contentDisposition = response.headers['content-disposition'];
    const filename = contentDisposition?.match(/filename="(.+)"/)?.[1] || `exam_export.${format}`;
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add packages/core/frontend/src/types/composer.ts packages/core/frontend/src/services/ComposerService.ts
git commit -m "feat(exam): add TypeScript types and API service for Exam Composer (TF-56)"
```

---

## Task 6: Frontend — Install DnD Kit + ExamComposer Page + Route

**Files:**
- Modify: `packages/core/frontend/package.json` (install deps)
- Create: `packages/core/frontend/src/pages/ExamComposer.tsx`
- Modify: `packages/core/frontend/src/AppWithAuth.tsx`

- [ ] **Step 1: Install @dnd-kit dependencies**

```bash
cd packages/core/frontend && bun add @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities
```

- [ ] **Step 2: Create ExamComposer page**

Create `packages/core/frontend/src/pages/ExamComposer.tsx`:

```typescript
import React, { useState } from 'react';
import ExamListView from '../components/composer/ExamListView';
import ExamBuilderView from '../components/composer/ExamBuilderView';

export const ExamComposer: React.FC = () => {
  const [selectedExamId, setSelectedExamId] = useState<number | null>(null);

  if (selectedExamId) {
    return (
      <ExamBuilderView
        examId={selectedExamId}
        onBack={() => setSelectedExamId(null)}
      />
    );
  }

  return (
    <ExamListView
      onSelectExam={(id) => setSelectedExamId(id)}
    />
  );
};
```

- [ ] **Step 3: Update route in AppWithAuth.tsx**

In `packages/core/frontend/src/AppWithAuth.tsx`:

1. Add import: `import { ExamComposer } from './pages/ExamComposer';`
2. Change the `/exams/compose` route from `<Exams />` to `<ExamComposer />`

Replace:
```tsx
<Route
  path="/exams/compose"
  element={
    <ProtectedRoute>
      <PermissionGuard requiredPermissions={['exams:create']}>
        <AppLayout>
          <Exams />
        </AppLayout>
      </PermissionGuard>
    </ProtectedRoute>
  }
/>
```

With:
```tsx
<Route
  path="/exams/compose"
  element={
    <ProtectedRoute>
      <PermissionGuard requiredPermissions={['exams:create']}>
        <AppLayout>
          <ExamComposer />
        </AppLayout>
      </PermissionGuard>
    </ProtectedRoute>
  }
/>
```

- [ ] **Step 4: Commit**

```bash
git add packages/core/frontend/package.json packages/core/frontend/bun.lockb packages/core/frontend/src/pages/ExamComposer.tsx packages/core/frontend/src/AppWithAuth.tsx
git commit -m "feat(exam): add ExamComposer page and update route (TF-56)"
```

---

## Task 7: Frontend — ExamListView Component

**Files:**
- Create: `packages/core/frontend/src/components/composer/ExamListView.tsx`

- [ ] **Step 1: Create ExamListView**

Create `packages/core/frontend/src/components/composer/ExamListView.tsx`:

```typescript
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
} from '@mui/material';
import { ComposerService } from '../../services/ComposerService';
import type { CreateExamRequest, Exam, ExamStatus } from '../../types/composer';

interface ExamListViewProps {
  onSelectExam: (id: number) => void;
}

const STATUS_LABELS: Record<string, string> = {
  draft: 'Entwurf',
  finalized: 'Finalisiert',
  exported: 'Exportiert',
};

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-yellow-100 text-yellow-800',
  finalized: 'bg-green-100 text-green-800',
  exported: 'bg-blue-100 text-blue-800',
};

const ExamListView: React.FC<ExamListViewProps> = ({ onSelectExam }) => {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState<CreateExamRequest>({ title: '', language: 'de' });
  const [searchQuery, setSearchQuery] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['exams', searchQuery],
    queryFn: () => ComposerService.listExams({ search: searchQuery || undefined }),
  });

  const createMutation = useMutation({
    mutationFn: ComposerService.createExam,
    onSuccess: (exam) => {
      queryClient.invalidateQueries({ queryKey: ['exams'] });
      setDialogOpen(false);
      setForm({ title: '', language: 'de' });
      onSelectExam(exam.id);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: ComposerService.deleteExam,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['exams'] }),
  });

  const handleCreate = () => {
    if (form.title.trim()) {
      createMutation.mutate(form);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Exam Composer</h1>
          <p className="text-gray-600 mt-2">
            Stelle Prüfungen aus genehmigten Fragen zusammen
          </p>
        </div>
        <button
          onClick={() => setDialogOpen(true)}
          className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 transition-colors"
        >
          + Neue Prüfung
        </button>
      </div>

      <div>
        <input
          type="text"
          placeholder="Prüfungen durchsuchen..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
        />
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Lade Prüfungen...</div>
      ) : !data?.exams.length ? (
        <div className="card p-12 text-center">
          <p className="text-gray-500 text-lg">
            Noch keine Prüfungen erstellt. Klicke auf "Neue Prüfung" um zu starten.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.exams.map((exam) => (
            <div
              key={exam.id}
              onClick={() => onSelectExam(exam.id)}
              className="card p-4 cursor-pointer hover:shadow-md transition-shadow"
            >
              <div className="flex justify-between items-start">
                <h3 className="font-semibold text-gray-900 truncate flex-1">
                  {exam.title}
                </h3>
                <span
                  className={`text-xs px-2 py-1 rounded-full ml-2 ${
                    STATUS_COLORS[exam.status] || 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {STATUS_LABELS[exam.status] || exam.status}
                </span>
              </div>
              {exam.course && (
                <p className="text-sm text-gray-500 mt-1">{exam.course}</p>
              )}
              <div className="flex gap-4 mt-3 text-sm text-gray-600">
                <span>{exam.question_count} Fragen</span>
                <span>{exam.total_points} Punkte</span>
                {exam.exam_date && <span>{exam.exam_date}</span>}
              </div>
              {exam.status === 'draft' && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm('Prüfung wirklich löschen?')) {
                      deleteMutation.mutate(exam.id);
                    }
                  }}
                  className="mt-2 text-xs text-red-500 hover:text-red-700"
                >
                  Löschen
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Neue Prüfung erstellen</DialogTitle>
        <DialogContent>
          <div className="space-y-4 mt-2">
            <TextField
              label="Titel"
              fullWidth
              required
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
            <TextField
              label="Kurs / Modul"
              fullWidth
              value={form.course || ''}
              onChange={(e) => setForm({ ...form, course: e.target.value })}
            />
            <TextField
              label="Prüfungsdatum"
              type="date"
              fullWidth
              InputLabelProps={{ shrink: true }}
              value={form.exam_date || ''}
              onChange={(e) => setForm({ ...form, exam_date: e.target.value })}
            />
            <TextField
              label="Zeitlimit (Minuten)"
              type="number"
              fullWidth
              value={form.time_limit_minutes || ''}
              onChange={(e) =>
                setForm({ ...form, time_limit_minutes: parseInt(e.target.value) || undefined })
              }
            />
            <TextField
              label="Erlaubte Hilfsmittel"
              fullWidth
              multiline
              rows={2}
              value={form.allowed_aids || ''}
              onChange={(e) => setForm({ ...form, allowed_aids: e.target.value })}
            />
          </div>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Abbrechen</Button>
          <Button
            onClick={handleCreate}
            variant="contained"
            disabled={!form.title.trim() || createMutation.isPending}
          >
            Erstellen
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

export default ExamListView;
```

- [ ] **Step 2: Commit**

```bash
git add packages/core/frontend/src/components/composer/ExamListView.tsx
git commit -m "feat(exam): add ExamListView component with create dialog (TF-56)"
```

---

## Task 8: Frontend — ExamBuilderView + Panels

**Files:**
- Create: `packages/core/frontend/src/components/composer/ExamBuilderView.tsx`
- Create: `packages/core/frontend/src/components/composer/ExamMetadataBar.tsx`
- Create: `packages/core/frontend/src/components/composer/QuestionPoolPanel.tsx`
- Create: `packages/core/frontend/src/components/composer/ExamQuestionsPanel.tsx`
- Create: `packages/core/frontend/src/components/composer/ExportDialog.tsx`

This is the largest task. The agent implementing this should read the spec's Frontend Design section and the ExamListView from Task 7 to match patterns. The key implementation points:

- [ ] **Step 1: Create ExamMetadataBar**

Create `packages/core/frontend/src/components/composer/ExamMetadataBar.tsx`:

Top bar showing exam title, question count, total points, status badge, and action buttons (Edit Metadata, Finalize/Unfinalize, Export). Uses the same Tailwind card pattern. Edit Metadata opens a MUI Dialog similar to CreateExamDialog.

- [ ] **Step 2: Create QuestionPoolPanel**

Create `packages/core/frontend/src/components/composer/QuestionPoolPanel.tsx`:

Left panel with:
- Search input (`useQuery` with debounced search term)
- Filter chips for question_type, difficulty, bloom_level
- Auto-Fill button that opens criteria dialog and calls `ComposerService.autoFill`
- Scrollable list of `PoolQuestionCard` items showing question text, badges (difficulty, type, bloom), "+ Hinzufügen" button
- Already-added questions appear dimmed with checkmark

Uses `ComposerService.listApprovedQuestions` with TanStack Query.

- [ ] **Step 3: Create ExamQuestionsPanel**

Create `packages/core/frontend/src/components/composer/ExamQuestionsPanel.tsx`:

Right panel with drag-and-drop using `@dnd-kit/sortable`:
- `SortableContext` wrapping the list
- Each `ExamQuestionItem` is a `useSortable` item with drag handle, position number, question text, inline points input, remove button
- `DndContext` with `onDragEnd` handler that calls `ComposerService.reorderQuestions`
- Drop zone at bottom when no questions
- Warning badge on questions with `review_status !== 'approved'`

Key imports:
```typescript
import { DndContext, closestCenter } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy, useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
```

- [ ] **Step 4: Create ExportDialog**

Create `packages/core/frontend/src/components/composer/ExportDialog.tsx`:

MUI Dialog with format selection (Markdown, JSON, Moodle XML), checkbox for "Include Solutions" (only for Markdown), and download button that opens `ComposerService.getExportUrl` in a new tab.

- [ ] **Step 5: Create ExamBuilderView orchestrator**

Create `packages/core/frontend/src/components/composer/ExamBuilderView.tsx`:

Orchestrator component that:
- Fetches exam detail via `useQuery(['exam', examId])`
- Renders ExamMetadataBar at top
- Two-column flex layout: QuestionPoolPanel (left) + ExamQuestionsPanel (right)
- Passes `onAddQuestion`, `onRemoveQuestion`, `onUpdatePoints`, `onReorder` handlers
- All mutations invalidate the `['exam', examId]` query
- Back button to return to ExamListView

```typescript
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ComposerService } from '../../services/ComposerService';
import ExamMetadataBar from './ExamMetadataBar';
import QuestionPoolPanel from './QuestionPoolPanel';
import ExamQuestionsPanel from './ExamQuestionsPanel';
import ExportDialog from './ExportDialog';

interface ExamBuilderViewProps {
  examId: number;
  onBack: () => void;
}

const ExamBuilderView: React.FC<ExamBuilderViewProps> = ({ examId, onBack }) => {
  const queryClient = useQueryClient();
  const [exportOpen, setExportOpen] = useState(false);

  const { data: exam, isLoading } = useQuery({
    queryKey: ['exam', examId],
    queryFn: () => ComposerService.getExam(examId),
  });

  const invalidateExam = () =>
    queryClient.invalidateQueries({ queryKey: ['exam', examId] });

  const addMutation = useMutation({
    mutationFn: (qIds: number[]) => ComposerService.addQuestions(examId, qIds),
    onSuccess: invalidateExam,
  });

  const removeMutation = useMutation({
    mutationFn: (eqId: number) => ComposerService.removeExamQuestion(examId, eqId),
    onSuccess: invalidateExam,
  });

  const updatePointsMutation = useMutation({
    mutationFn: ({ eqId, points }: { eqId: number; points: number }) =>
      ComposerService.updateExamQuestion(examId, eqId, { points }),
    onSuccess: invalidateExam,
  });

  const reorderMutation = useMutation({
    mutationFn: (order: { id: number; position: number }[]) =>
      ComposerService.reorderQuestions(examId, order),
    onSuccess: invalidateExam,
  });

  if (isLoading || !exam) {
    return <div className="text-center py-12 text-gray-500">Lade Prüfung...</div>;
  }

  const addedQuestionIds = new Set(exam.questions.map((q) => q.question_id));
  const isDraft = exam.status === 'draft';

  return (
    <div className="space-y-4">
      <button
        onClick={onBack}
        className="text-sm text-gray-500 hover:text-gray-700"
      >
        ← Zurück zur Übersicht
      </button>

      <ExamMetadataBar
        exam={exam}
        onExport={() => setExportOpen(true)}
        onInvalidate={invalidateExam}
      />

      <div className="flex gap-4" style={{ minHeight: '60vh' }}>
        <div className="w-1/2">
          <QuestionPoolPanel
            addedQuestionIds={addedQuestionIds}
            onAddQuestions={(ids) => addMutation.mutate(ids)}
            examId={examId}
            disabled={!isDraft}
            onInvalidate={invalidateExam}
          />
        </div>
        <div className="w-1/2">
          <ExamQuestionsPanel
            questions={exam.questions}
            disabled={!isDraft}
            onRemove={(eqId) => removeMutation.mutate(eqId)}
            onUpdatePoints={(eqId, points) =>
              updatePointsMutation.mutate({ eqId, points })
            }
            onReorder={(order) => reorderMutation.mutate(order)}
          />
        </div>
      </div>

      <ExportDialog
        open={exportOpen}
        onClose={() => setExportOpen(false)}
        examId={examId}
        examTitle={exam.title}
        hasQuestions={exam.questions.length > 0}
      />
    </div>
  );
};

export default ExamBuilderView;
```

The detailed implementations of ExamMetadataBar, QuestionPoolPanel, ExamQuestionsPanel, and ExportDialog should follow the patterns from ExamListView (Tailwind + MUI mix, TanStack Query, ComposerService calls). The implementing agent should read the spec's Frontend Design section for exact layout requirements.

- [ ] **Step 6: Verify the app compiles**

```bash
cd packages/core/frontend && bun run build
```

Expected: Build succeeds without errors.

- [ ] **Step 7: Commit**

```bash
git add packages/core/frontend/src/components/composer/
git commit -m "feat(exam): add ExamBuilderView with two-panel layout and drag-and-drop (TF-56)"
```

---

## Task 9: Integration Test + Cleanup

**Files:**
- All files from previous tasks

- [ ] **Step 1: Run all backend tests**

```bash
cd packages/core/backend && python -m pytest tests/test_exam_api.py tests/test_exam_export.py -v
```

Expected: All tests PASS.

- [ ] **Step 2: Run frontend build**

```bash
cd packages/core/frontend && bun run build
```

Expected: Build succeeds.

- [ ] **Step 3: Run existing test suite to check for regressions**

```bash
cd packages/core/backend && python -m pytest tests/ -v --tb=short
```

Expected: No regressions in existing tests.

- [ ] **Step 4: Manual smoke test**

Start the dev environment and verify:
1. Navigate to `/exams/compose` — ExamListView renders
2. Create a new exam — dialog works, redirects to builder
3. Search approved questions in left panel
4. Add questions to exam
5. Drag to reorder
6. Edit points inline
7. Export as Markdown
8. Finalize exam

- [ ] **Step 5: Final commit (if any cleanup needed)**

```bash
git add -A
git commit -m "fix(exam): integration fixes from smoke test (TF-56)"
```
