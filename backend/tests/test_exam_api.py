"""
Tests for Exam Composer Models: Exam, ExamQuestion, ExamStatus
TDD: These tests are written before the model implementation.
"""

import re

import pytest
from unittest.mock import Mock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from models.auth import Institution, User, UserStatus
from models.question_review import QuestionReview, ReviewStatus
from models.exam import Exam, ExamQuestion, ExamStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_committable_session(test_engine, slug: str, email: str):
    """Yield a committable Session and clean its Institution+User on teardown.

    Endpoints under test call session.commit() — the ``test_db`` fixture from
    conftest.py has no SAVEPOINT mode, since a SAVEPOINT variant breaks
    optimistic-locking tests (updated_at refresh behavior). So we stick with
    a "real" session without an outer transaction. To avoid pollution for
    other test files (test_quota_enforcement_integration,
    test_profile_permissions_and_institution and others, which query
    ``Institution.first()``), we explicitly delete the Institution/User rows
    created specifically for this test class on teardown.
    """
    from sqlalchemy.orm import sessionmaker
    from models.auth import Institution, User

    TestSession = sessionmaker(bind=test_engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.rollback()  # in case the last test had an open transaction
        try:
            session.query(User).filter(User.email == email).delete()
            session.query(Institution).filter(Institution.slug == slug).delete()
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()


def make_user(test_db: Session, institution_id: int, suffix: str = "1") -> User:
    user = User(
        email=f"examuser{suffix}@test.com",
        first_name="Exam",
        last_name=f"User{suffix}",
        password_hash="dummy_hash",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
    )
    test_db.add(user)
    test_db.flush()
    return user


def make_question(
    test_db: Session, institution_id: int, created_by: int, suffix: str = "1"
) -> QuestionReview:
    question = QuestionReview(
        question_text=f"What is question {suffix}?",
        question_type="open_ended",
        difficulty="medium",
        topic="Test Topic",
        language="de",
        review_status=ReviewStatus.APPROVED.value,
        institution_id=institution_id,
        created_by=created_by,
    )
    test_db.add(question)
    test_db.flush()
    return question


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestExamStatus:
    """Verify ExamStatus enum values."""

    def test_exam_status_enum(self):
        assert ExamStatus.DRAFT.value == "draft"
        assert ExamStatus.FINALIZED.value == "finalized"
        assert ExamStatus.EXPORTED.value == "exported"

    def test_exam_status_is_str_enum(self):
        assert isinstance(ExamStatus.DRAFT, str)
        assert ExamStatus.DRAFT == "draft"


class TestExamModel:
    """Tests for the Exam ORM model."""

    def test_create_exam(self, test_db: Session, test_institution: Institution):
        """Creates exam with required fields and verifies defaults."""
        user = make_user(test_db, test_institution.id)

        exam = Exam(
            title="Midterm Exam 2025",
            institution_id=test_institution.id,
            created_by=user.id,
        )
        test_db.add(exam)
        test_db.commit()
        test_db.refresh(exam)

        # Required fields persisted
        assert exam.id is not None
        assert exam.title == "Midterm Exam 2025"
        assert exam.institution_id == test_institution.id
        assert exam.created_by == user.id

        # Defaults
        assert exam.status == ExamStatus.DRAFT.value
        assert exam.total_points == 0.0
        assert exam.passing_percentage == 50.0
        assert exam.language == "de"

        # Optional fields default to None
        assert exam.course is None
        assert exam.exam_date is None
        assert exam.time_limit_minutes is None
        assert exam.allowed_aids is None
        assert exam.instructions is None

        # Timestamps set
        assert exam.created_at is not None
        assert exam.updated_at is not None

    def test_create_exam_with_all_fields(
        self, test_db: Session, test_institution: Institution
    ):
        """Creates exam with all optional fields populated."""
        from datetime import date

        user = make_user(test_db, test_institution.id, suffix="2")

        exam = Exam(
            title="Final Exam",
            course="CS101",
            exam_date=date(2025, 6, 15),
            time_limit_minutes=90,
            allowed_aids="Calculator, Formula Sheet",
            instructions="Read all questions carefully.",
            passing_percentage=60.0,
            total_points=100.0,
            status=ExamStatus.FINALIZED.value,
            language="en",
            institution_id=test_institution.id,
            created_by=user.id,
        )
        test_db.add(exam)
        test_db.commit()
        test_db.refresh(exam)

        assert exam.course == "CS101"
        assert exam.exam_date == date(2025, 6, 15)
        assert exam.time_limit_minutes == 90
        assert exam.allowed_aids == "Calculator, Formula Sheet"
        assert exam.instructions == "Read all questions carefully."
        assert exam.passing_percentage == 60.0
        assert exam.total_points == 100.0
        assert exam.status == ExamStatus.FINALIZED.value
        assert exam.language == "en"

    def test_exam_repr(self, test_db: Session, test_institution: Institution):
        """Repr contains id, title, and status."""
        user = make_user(test_db, test_institution.id, suffix="3")
        exam = Exam(
            title="Repr Test Exam",
            institution_id=test_institution.id,
            created_by=user.id,
        )
        test_db.add(exam)
        test_db.commit()
        test_db.refresh(exam)

        r = repr(exam)
        assert "Exam" in r
        assert str(exam.id) in r
        assert "draft" in r

    def test_recalculate_total_points(
        self, test_db: Session, test_institution: Institution
    ):
        """recalculate_total_points sums points from all exam questions."""
        user = make_user(test_db, test_institution.id, suffix="4")
        q1 = make_question(test_db, test_institution.id, user.id, suffix="a")
        q2 = make_question(test_db, test_institution.id, user.id, suffix="b")

        exam = Exam(
            title="Points Recalc Exam",
            institution_id=test_institution.id,
            created_by=user.id,
        )
        test_db.add(exam)
        test_db.flush()

        eq1 = ExamQuestion(exam_id=exam.id, question_id=q1.id, position=1, points=5.0)
        eq2 = ExamQuestion(exam_id=exam.id, question_id=q2.id, position=2, points=10.0)
        test_db.add_all([eq1, eq2])
        test_db.commit()
        test_db.refresh(exam)

        exam.recalculate_total_points()
        assert exam.total_points == 15.0

    def test_default_document_ids_nullable(
        self, test_db: Session, test_institution: Institution
    ):
        """Exam.default_document_ids defaults to None and accepts a list of ints."""
        user = make_user(test_db, test_institution.id, suffix="ddi1")
        exam = Exam(
            title="Doc Filter Exam",
            institution_id=test_institution.id,
            created_by=user.id,
        )
        test_db.add(exam)
        test_db.flush()
        assert exam.default_document_ids is None

        exam.default_document_ids = [1, 2, 3]
        test_db.flush()
        test_db.refresh(exam)
        assert exam.default_document_ids == [1, 2, 3]


class TestExamQuestionModel:
    """Tests for the ExamQuestion join-table model."""

    def test_create_exam_question(
        self, test_db: Session, test_institution: Institution
    ):
        """Links exam to question with position and points."""
        user = make_user(test_db, test_institution.id, suffix="5")
        question = make_question(test_db, test_institution.id, user.id, suffix="c")

        exam = Exam(
            title="ExamQuestion Test",
            institution_id=test_institution.id,
            created_by=user.id,
        )
        test_db.add(exam)
        test_db.flush()

        eq = ExamQuestion(
            exam_id=exam.id,
            question_id=question.id,
            position=1,
            points=7.5,
            section="Section A",
        )
        test_db.add(eq)
        test_db.commit()
        test_db.refresh(eq)

        assert eq.id is not None
        assert eq.exam_id == exam.id
        assert eq.question_id == question.id
        assert eq.position == 1
        assert eq.points == 7.5
        assert eq.section == "Section A"

    def test_create_exam_question_without_section(
        self, test_db: Session, test_institution: Institution
    ):
        """Section is optional and defaults to None."""
        user = make_user(test_db, test_institution.id, suffix="6")
        question = make_question(test_db, test_institution.id, user.id, suffix="d")

        exam = Exam(
            title="No Section Exam",
            institution_id=test_institution.id,
            created_by=user.id,
        )
        test_db.add(exam)
        test_db.flush()

        eq = ExamQuestion(
            exam_id=exam.id,
            question_id=question.id,
            position=1,
            points=3.0,
        )
        test_db.add(eq)
        test_db.commit()
        test_db.refresh(eq)

        assert eq.section is None

    def test_exam_questions_relationship(
        self, test_db: Session, test_institution: Institution
    ):
        """Exam.questions relationship returns list ordered by position."""
        user = make_user(test_db, test_institution.id, suffix="7")
        q1 = make_question(test_db, test_institution.id, user.id, suffix="e")
        q2 = make_question(test_db, test_institution.id, user.id, suffix="f")
        q3 = make_question(test_db, test_institution.id, user.id, suffix="g")

        exam = Exam(
            title="Relationship Test Exam",
            institution_id=test_institution.id,
            created_by=user.id,
        )
        test_db.add(exam)
        test_db.flush()

        # Insert out of order intentionally
        eq3 = ExamQuestion(exam_id=exam.id, question_id=q3.id, position=3, points=1.0)
        eq1 = ExamQuestion(exam_id=exam.id, question_id=q1.id, position=1, points=1.0)
        eq2 = ExamQuestion(exam_id=exam.id, question_id=q2.id, position=2, points=1.0)
        test_db.add_all([eq3, eq1, eq2])
        test_db.commit()
        test_db.refresh(exam)

        questions = exam.questions
        assert len(questions) == 3
        assert questions[0].position == 1
        assert questions[1].position == 2
        assert questions[2].position == 3

    def test_exam_question_repr(self, test_db: Session, test_institution: Institution):
        """ExamQuestion repr contains exam_id, question_id, position."""
        user = make_user(test_db, test_institution.id, suffix="8")
        question = make_question(test_db, test_institution.id, user.id, suffix="h")

        exam = Exam(
            title="Repr Test",
            institution_id=test_institution.id,
            created_by=user.id,
        )
        test_db.add(exam)
        test_db.flush()

        eq = ExamQuestion(
            exam_id=exam.id, question_id=question.id, position=1, points=5.0
        )
        test_db.add(eq)
        test_db.commit()
        test_db.refresh(eq)

        r = repr(eq)
        assert "ExamQuestion" in r
        assert str(exam.id) in r
        assert str(question.id) in r

    def test_cascade_delete_exam_deletes_exam_questions(
        self, test_db: Session, test_institution: Institution
    ):
        """Deleting an Exam cascades to ExamQuestion rows."""
        from models.exam import ExamQuestion as EQ

        user = make_user(test_db, test_institution.id, suffix="9")
        question = make_question(test_db, test_institution.id, user.id, suffix="i")

        exam = Exam(
            title="Cascade Delete Exam",
            institution_id=test_institution.id,
            created_by=user.id,
        )
        test_db.add(exam)
        test_db.flush()
        exam_id = exam.id

        eq = ExamQuestion(
            exam_id=exam.id, question_id=question.id, position=1, points=5.0
        )
        test_db.add(eq)
        test_db.commit()

        test_db.delete(exam)
        test_db.commit()

        remaining = test_db.query(EQ).filter_by(exam_id=exam_id).all()
        assert remaining == []


# ---------------------------------------------------------------------------
# Task 1: QuestionSourceDocument join model
# ---------------------------------------------------------------------------


class TestQuestionSourceDocumentModel:
    """Tests for QuestionSourceDocument join model."""

    def test_create_link(self, test_db: Session, test_institution: Institution):
        from models.question_review import QuestionSourceDocument
        from models.document import Document

        user = make_user(test_db, test_institution.id, suffix="qsd1")
        doc = Document(
            filename="ds.pdf",
            original_filename="ds.pdf",
            file_path="/tmp/ds.pdf",
            file_size=1000,
            mime_type="application/pdf",
            institution_id=test_institution.id,
            user_id=user.id,
        )
        test_db.add(doc)
        test_db.flush()

        question = make_question(test_db, test_institution.id, user.id, suffix="qsd1")
        link = QuestionSourceDocument(question_id=question.id, document_id=doc.id)
        test_db.add(link)
        test_db.flush()

        assert link.id is not None
        assert link.question_id == question.id
        assert link.document_id == doc.id

    def test_unique_constraint(self, test_db: Session, test_institution: Institution):
        from models.question_review import QuestionSourceDocument
        from models.document import Document
        from sqlalchemy.exc import IntegrityError

        user = make_user(test_db, test_institution.id, suffix="qsd2")
        doc = Document(
            filename="ds2.pdf",
            original_filename="ds2.pdf",
            file_path="/tmp/ds2.pdf",
            file_size=1000,
            mime_type="application/pdf",
            institution_id=test_institution.id,
            user_id=user.id,
        )
        test_db.add(doc)
        test_db.flush()

        question = make_question(test_db, test_institution.id, user.id, suffix="qsd2")
        test_db.add(QuestionSourceDocument(question_id=question.id, document_id=doc.id))
        test_db.flush()

        test_db.add(QuestionSourceDocument(question_id=question.id, document_id=doc.id))
        with pytest.raises(IntegrityError):
            test_db.flush()


# ---------------------------------------------------------------------------
# Task 2: CRUD API Tests
# ---------------------------------------------------------------------------


def _make_mock_user(institution_id: int = 1, user_id: int = 1) -> Mock:
    """Create a mock user with full permission for exam endpoints."""
    mock_institution = Mock()
    mock_institution.id = institution_id
    mock_institution.name = "Test University"
    mock_institution.slug = "test-university"
    mock_institution.subscription_tier = "professional"
    mock_institution.max_users = -1
    mock_institution.max_documents = -1
    mock_institution.max_questions_per_month = -1

    user = Mock()
    user.id = user_id
    user.email = f"examuser{user_id}@test.com"
    user.first_name = "Exam"
    user.last_name = "User"
    user.institution_id = institution_id
    user.institution = mock_institution
    user.has_permission = Mock(return_value=True)
    user.is_superuser = True  # superuser bypasses tenant filter
    user.roles = []
    user.status = "active"
    return user


class TestExamCRUDApi:
    """Tests for exam CRUD endpoints — uses dependency overrides, real DB."""

    @pytest.fixture
    def exam_db(self, test_engine):
        yield from _make_committable_session(
            test_engine, slug="exam-test-university", email="examcrud@test.com"
        )

    @pytest.fixture
    def exam_institution(self, exam_db):
        """Institution created with a committable session."""
        from models.auth import Institution

        # Check for existing institution to allow fixture reuse across tests
        existing = (
            exam_db.query(Institution).filter_by(slug="exam-test-university").first()
        )
        if existing:
            return existing

        institution = Institution(
            name="Exam Test University",
            slug="exam-test-university",
            subscription_tier="professional",
            max_users=-1,
            max_documents=-1,
            max_questions_per_month=-1,
        )
        exam_db.add(institution)
        exam_db.commit()
        exam_db.refresh(institution)
        return institution

    @pytest.fixture
    def exam_user(self, exam_db, exam_institution):
        """Real user record in the test DB so FK constraints pass."""
        from models.auth import User, UserStatus

        existing = exam_db.query(User).filter_by(email="examcrud@test.com").first()
        if existing:
            return existing

        user = User(
            email="examcrud@test.com",
            first_name="Exam",
            last_name="CRUD",
            password_hash="dummy_hash",  # pragma: allowlist secret
            institution_id=exam_institution.id,
            status=UserStatus.ACTIVE.value,
        )
        exam_db.add(user)
        exam_db.commit()
        exam_db.refresh(user)
        return user

    @pytest.fixture
    def mock_user(self, exam_institution, exam_user):
        return _make_mock_user(institution_id=exam_institution.id, user_id=exam_user.id)

    @pytest.fixture
    def exam_client(self, exam_db, exam_institution, mock_user):
        """TestClient with auth overrides and committable DB session.

        Uses TestClient without context manager to avoid triggering the
        full lifespan event (which requires optional services like Celery).
        The exams router is included directly before creating the client.
        """
        from utils.auth_utils import get_current_user
        from database import get_db
        import api.exams as exams_module

        # Include the exams router (FastAPI deduplicates identical routes)
        app.include_router(exams_module.router)

        def override_get_db():
            yield exam_db

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = override_get_db

        # No context manager — avoids triggering the full lifespan
        client = TestClient(app, raise_server_exceptions=True)
        yield client
        app.dependency_overrides.clear()

    def test_create_exam(self, exam_client):
        """POST /api/v1/exams/ creates a new exam with defaults."""
        response = exam_client.post(
            "/api/v1/exams/",
            json={"title": "Midterm 2026", "course": "Algo & DS", "language": "de"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Midterm 2026"
        assert data["status"] == "draft"
        assert data["total_points"] == 0.0
        assert data["passing_percentage"] == 50.0
        assert data["language"] == "de"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_list_exams(self, exam_client):
        """GET /api/v1/exams/ returns list with total."""
        # Create two exams first
        for title in ["Exam A", "Exam B"]:
            exam_client.post("/api/v1/exams/", json={"title": title})

        response = exam_client.get("/api/v1/exams/")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "exams" in data
        assert data["total"] >= 2
        assert len(data["exams"]) >= 2

    def test_get_exam(self, exam_client):
        """GET /api/v1/exams/{id} returns exam with empty questions list."""
        create_resp = exam_client.post("/api/v1/exams/", json={"title": "Detail Test"})
        assert create_resp.status_code == 201
        exam_id = create_resp.json()["id"]

        response = exam_client.get(f"/api/v1/exams/{exam_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Detail Test"
        assert data["questions"] == []

    def test_update_exam(self, exam_client):
        """PUT /api/v1/exams/{id} updates metadata."""
        create_resp = exam_client.post("/api/v1/exams/", json={"title": "Old Title"})
        exam = create_resp.json()

        response = exam_client.put(
            f"/api/v1/exams/{exam['id']}",
            json={
                "title": "New Title",
                "time_limit_minutes": 90,
                "updated_at": exam["updated_at"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"
        assert data["time_limit_minutes"] == 90

    def test_delete_draft_exam_requires_archive_first(self, exam_client):
        """DELETE requires prior archiving (TF-398): the former one-click
        draft delete is gone. Unarchived → 409; after archiving → 204 and
        the exam is gone."""
        create_resp = exam_client.post("/api/v1/exams/", json={"title": "To Delete"})
        exam_id = create_resp.json()["id"]

        # Blocked without prior archiving (409).
        blocked = exam_client.delete(f"/api/v1/exams/{exam_id}")
        assert blocked.status_code == 409

        # Archive, then delete.
        archive_resp = exam_client.post(f"/api/v1/exams/{exam_id}/archive", json={})
        assert archive_resp.status_code == 200

        response = exam_client.delete(f"/api/v1/exams/{exam_id}")
        assert response.status_code == 204

        # Verify it's gone
        get_resp = exam_client.get(f"/api/v1/exams/{exam_id}")
        assert get_resp.status_code == 404

    def test_optimistic_locking_conflict(self, exam_client):
        """PUT /api/v1/exams/{id} returns 409 on stale updated_at."""
        create_resp = exam_client.post("/api/v1/exams/", json={"title": "Locking Test"})
        exam = create_resp.json()

        # First update succeeds
        first_update = exam_client.put(
            f"/api/v1/exams/{exam['id']}",
            json={"title": "Updated Once", "updated_at": exam["updated_at"]},
        )
        assert first_update.status_code == 200

        # Second update with the original (now stale) updated_at fails
        response = exam_client.put(
            f"/api/v1/exams/{exam['id']}",
            json={"title": "Stale Update", "updated_at": exam["updated_at"]},
        )
        assert response.status_code == 409

    def test_create_exam_with_default_document_ids(self, exam_client):
        """POST /api/v1/exams/ persists default_document_ids and returns them."""
        response = exam_client.post(
            "/api/v1/exams/",
            json={
                "title": "DS Exam",
                "language": "de",
                "default_document_ids": [10, 20],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["default_document_ids"] == [10, 20]

    def test_create_exam_without_document_ids_defaults_to_none(self, exam_client):
        """POST /api/v1/exams/ without default_document_ids returns null."""
        response = exam_client.post(
            "/api/v1/exams/",
            json={"title": "Plain Exam", "language": "de"},
        )
        assert response.status_code == 201
        assert response.json()["default_document_ids"] is None


# ---------------------------------------------------------------------------
# Task 3: Question Management API Tests
# ---------------------------------------------------------------------------


class TestExamQuestionApi:
    """Tests for exam question management endpoints — add, update, remove, reorder."""

    @pytest.fixture
    def exam_db(self, test_engine):
        yield from _make_committable_session(
            test_engine, slug="examq-test-university", email="examqcrud@test.com"
        )

    @pytest.fixture
    def exam_institution(self, exam_db):
        """Institution created with a committable session."""
        from models.auth import Institution

        existing = (
            exam_db.query(Institution).filter_by(slug="examq-test-university").first()
        )
        if existing:
            return existing

        institution = Institution(
            name="ExamQ Test University",
            slug="examq-test-university",
            subscription_tier="professional",
            max_users=-1,
            max_documents=-1,
            max_questions_per_month=-1,
        )
        exam_db.add(institution)
        exam_db.commit()
        exam_db.refresh(institution)
        return institution

    @pytest.fixture
    def exam_user(self, exam_db, exam_institution):
        """Real user record in the test DB so FK constraints pass."""
        from models.auth import User, UserStatus

        existing = exam_db.query(User).filter_by(email="examqcrud@test.com").first()
        if existing:
            return existing

        user = User(
            email="examqcrud@test.com",
            first_name="ExamQ",
            last_name="CRUD",
            password_hash="dummy_hash",  # pragma: allowlist secret
            institution_id=exam_institution.id,
            status=UserStatus.ACTIVE.value,
        )
        exam_db.add(user)
        exam_db.commit()
        exam_db.refresh(user)
        return user

    @pytest.fixture
    def mock_user(self, exam_institution, exam_user):
        return _make_mock_user(institution_id=exam_institution.id, user_id=exam_user.id)

    @pytest.fixture
    def exam_client(self, exam_db, exam_institution, mock_user):
        """TestClient with auth overrides and committable DB session."""
        from utils.auth_utils import get_current_user
        from database import get_db
        import api.exams as exams_module

        app.include_router(exams_module.router)

        def override_get_db():
            yield exam_db

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = override_get_db

        client = TestClient(app, raise_server_exceptions=True)
        yield client
        app.dependency_overrides.clear()

    def _create_approved_question(
        self,
        db,
        institution_id,
        user_id,
        text="Test Q",
        question_type="single_choice",
        difficulty="medium",
    ):
        from models.question_review import QuestionReview

        q = QuestionReview(
            question_text=text,
            question_type=question_type,
            difficulty=difficulty,
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

    def test_add_questions(self, exam_client, exam_db, exam_institution, exam_user):
        """POST /{exam_id}/questions adds approved question with auto-suggested points."""
        # Create exam
        create_resp = exam_client.post(
            "/api/v1/exams/", json={"title": "Add Questions Test"}
        )
        assert create_resp.status_code == 201
        exam_id = create_resp.json()["id"]

        # Create approved question (single_choice + medium => 4 pts)
        q = self._create_approved_question(
            exam_db,
            exam_institution.id,
            exam_user.id,
            question_type="single_choice",
            difficulty="medium",
        )

        response = exam_client.post(
            f"/api/v1/exams/{exam_id}/questions",
            json={"question_ids": [q.id]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["questions"]) == 1
        assert data["questions"][0]["question_id"] == q.id
        assert data["questions"][0]["points"] == 4.0  # medium MC = 4 pts
        assert data["total_points"] == 4.0

    def test_add_non_approved_question_fails(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """POST /{exam_id}/questions rejects non-approved (pending) questions."""
        from models.question_review import QuestionReview

        create_resp = exam_client.post(
            "/api/v1/exams/", json={"title": "Non-Approved Test"}
        )
        assert create_resp.status_code == 201
        exam_id = create_resp.json()["id"]

        q = QuestionReview(
            question_text="Pending Q",
            question_type="open_ended",
            difficulty="easy",
            topic="Test",
            review_status="pending",
            institution_id=exam_institution.id,
            created_by=exam_user.id,
        )
        exam_db.add(q)
        exam_db.commit()

        response = exam_client.post(
            f"/api/v1/exams/{exam_id}/questions",
            json={"question_ids": [q.id]},
        )
        assert response.status_code == 400

    def test_remove_question(self, exam_client, exam_db, exam_institution, exam_user):
        """DELETE /{exam_id}/questions/{eq_id} removes question and recalculates total_points."""
        create_resp = exam_client.post(
            "/api/v1/exams/", json={"title": "Remove Question Test"}
        )
        assert create_resp.status_code == 201
        exam_id = create_resp.json()["id"]

        q = self._create_approved_question(exam_db, exam_institution.id, exam_user.id)

        # Add question
        exam_client.post(
            f"/api/v1/exams/{exam_id}/questions",
            json={"question_ids": [q.id]},
        )

        # Get exam to find eq_id
        detail = exam_client.get(f"/api/v1/exams/{exam_id}").json()
        assert len(detail["questions"]) == 1
        eq_id = detail["questions"][0]["id"]

        # Remove it
        response = exam_client.delete(f"/api/v1/exams/{exam_id}/questions/{eq_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["questions"]) == 0
        assert data["total_points"] == 0.0

    def test_reorder_questions(self, exam_client, exam_db, exam_institution, exam_user):
        """POST /{exam_id}/reorder swaps positions of two questions."""
        create_resp = exam_client.post("/api/v1/exams/", json={"title": "Reorder Test"})
        assert create_resp.status_code == 201
        exam_id = create_resp.json()["id"]

        q1 = self._create_approved_question(
            exam_db, exam_institution.id, exam_user.id, text="Q1"
        )
        q2 = self._create_approved_question(
            exam_db, exam_institution.id, exam_user.id, text="Q2"
        )

        # Add both questions
        exam_client.post(
            f"/api/v1/exams/{exam_id}/questions",
            json={"question_ids": [q1.id, q2.id]},
        )

        # Get current order (q1 at pos 1, q2 at pos 2)
        detail = exam_client.get(f"/api/v1/exams/{exam_id}").json()
        eq_ids = [q["id"] for q in detail["questions"]]
        assert len(eq_ids) == 2

        # Swap: first eq gets position 2, second gets position 1
        response = exam_client.post(
            f"/api/v1/exams/{exam_id}/reorder",
            json={
                "order": [
                    {"id": eq_ids[0], "position": 2},
                    {"id": eq_ids[1], "position": 1},
                ]
            },
        )
        assert response.status_code == 200
        questions = response.json()["questions"]
        # After swap, former second question should now be first
        assert questions[0]["id"] == eq_ids[1]
        assert questions[1]["id"] == eq_ids[0]


# ---------------------------------------------------------------------------
# Task 4: Workflow API Tests (finalize, unfinalize, approved-questions)
# ---------------------------------------------------------------------------


class TestExamWorkflowApi:
    """Tests for finalize, unfinalize, and approved-questions endpoints."""

    @pytest.fixture
    def exam_db(self, test_engine):
        yield from _make_committable_session(
            test_engine, slug="examwf-test-university", email="examwfcrud@test.com"
        )

    @pytest.fixture
    def exam_institution(self, exam_db):
        """Institution created with a committable session."""
        from models.auth import Institution

        existing = (
            exam_db.query(Institution).filter_by(slug="examwf-test-university").first()
        )
        if existing:
            return existing

        institution = Institution(
            name="ExamWF Test University",
            slug="examwf-test-university",
            subscription_tier="professional",
            max_users=-1,
            max_documents=-1,
            max_questions_per_month=-1,
        )
        exam_db.add(institution)
        exam_db.commit()
        exam_db.refresh(institution)
        return institution

    @pytest.fixture
    def exam_user(self, exam_db, exam_institution):
        """Real user record in the test DB so FK constraints pass."""
        from models.auth import User, UserStatus

        existing = exam_db.query(User).filter_by(email="examwfcrud@test.com").first()
        if existing:
            return existing

        user = User(
            email="examwfcrud@test.com",
            first_name="ExamWF",
            last_name="CRUD",
            password_hash="dummy_hash",  # pragma: allowlist secret
            institution_id=exam_institution.id,
            status=UserStatus.ACTIVE.value,
        )
        exam_db.add(user)
        exam_db.commit()
        exam_db.refresh(user)
        return user

    @pytest.fixture
    def mock_user(self, exam_institution, exam_user):
        return _make_mock_user(institution_id=exam_institution.id, user_id=exam_user.id)

    @pytest.fixture
    def exam_client(self, exam_db, exam_institution, mock_user):
        """TestClient with auth overrides and committable DB session."""
        from utils.auth_utils import get_current_user
        from database import get_db
        import api.exams as exams_module

        app.include_router(exams_module.router)

        def override_get_db():
            yield exam_db

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = override_get_db

        client = TestClient(app, raise_server_exceptions=True)
        yield client
        app.dependency_overrides.clear()

    def _create_approved_question(
        self,
        db,
        institution_id,
        user_id,
        text="Test Q",
        question_type="single_choice",
        difficulty="medium",
        topic="Test",
    ):
        from models.question_review import QuestionReview

        q = QuestionReview(
            question_text=text,
            question_type=question_type,
            difficulty=difficulty,
            topic=topic,
            review_status="approved",
            options=["A", "B", "C", "D"] if question_type == "single_choice" else None,
            correct_answer="A" if question_type == "single_choice" else None,
            explanation="A is correct." if question_type == "single_choice" else None,
            institution_id=institution_id,
            created_by=user_id,
        )
        db.add(q)
        db.commit()
        db.refresh(q)
        return q

    def _create_exam_with_question(self, client, db, institution_id, user_id):
        """Helper: create exam + add one approved question."""
        create_resp = client.post("/api/v1/exams/", json={"title": "Workflow Test"})
        assert create_resp.status_code == 201
        exam = create_resp.json()

        q = self._create_approved_question(db, institution_id, user_id)

        add_resp = client.post(
            f"/api/v1/exams/{exam['id']}/questions",
            json={"question_ids": [q.id]},
        )
        assert add_resp.status_code == 200
        return exam, q

    def test_finalize_exam(self, exam_client, exam_db, exam_institution, exam_user):
        """POST /{exam_id}/finalize sets status to finalized."""
        exam, _ = self._create_exam_with_question(
            exam_client, exam_db, exam_institution.id, exam_user.id
        )
        response = exam_client.post(f"/api/v1/exams/{exam['id']}/finalize")
        assert response.status_code == 200
        assert response.json()["status"] == "finalized"

    def test_finalize_empty_exam_fails(self, exam_client):
        """POST /{exam_id}/finalize returns 400 for an exam with no questions."""
        create_resp = exam_client.post("/api/v1/exams/", json={"title": "Empty Exam"})
        assert create_resp.status_code == 201
        exam_id = create_resp.json()["id"]

        response = exam_client.post(f"/api/v1/exams/{exam_id}/finalize")
        assert response.status_code == 400
        detail = response.json()["detail"].lower()
        assert "leer" in detail or "empty" in detail

    def test_unfinalize_exam(self, exam_client, exam_db, exam_institution, exam_user):
        """POST /{exam_id}/unfinalize reverts status from finalized to draft."""
        exam, _ = self._create_exam_with_question(
            exam_client, exam_db, exam_institution.id, exam_user.id
        )
        # Finalize first
        fin_resp = exam_client.post(f"/api/v1/exams/{exam['id']}/finalize")
        assert fin_resp.status_code == 200
        assert fin_resp.json()["status"] == "finalized"

        # Then unfinalize
        response = exam_client.post(f"/api/v1/exams/{exam['id']}/unfinalize")
        assert response.status_code == 200
        assert response.json()["status"] == "draft"

    def test_approved_questions_endpoint(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """GET /approved-questions returns approved questions, filterable by topic."""
        self._create_approved_question(
            exam_db,
            exam_institution.id,
            exam_user.id,
            text="Searchable Q about Heapsort",
            topic="Heapsort",
            question_type="open_ended",
            difficulty="hard",
        )

        response = exam_client.get("/api/v1/exams/approved-questions?topic=Heapsort")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "questions" in data
        assert data["total"] >= 1
        topics = [q["topic"] for q in data["questions"]]
        assert any("Heapsort" in t for t in topics)


# ---------------------------------------------------------------------------
# Task 5: Additional coverage for untested paths in exams.py
# ---------------------------------------------------------------------------


def _make_exam_test_class_fixtures(slug: str, email: str):
    """Factory that returns the three shared fixtures used by all extra test classes."""

    class _Fixtures:
        @pytest.fixture
        def exam_db(self, test_engine):
            yield from _make_committable_session(test_engine, slug=slug, email=email)

        @pytest.fixture
        def exam_institution(self, exam_db):
            from models.auth import Institution

            existing = exam_db.query(Institution).filter_by(slug=slug).first()
            if existing:
                return existing

            institution = Institution(
                name=f"Extra Test University {slug}",
                slug=slug,
                subscription_tier="professional",
                max_users=-1,
                max_documents=-1,
                max_questions_per_month=-1,
            )
            exam_db.add(institution)
            exam_db.commit()
            exam_db.refresh(institution)
            return institution

        @pytest.fixture
        def exam_user(self, exam_db, exam_institution):
            from models.auth import User, UserStatus

            existing = exam_db.query(User).filter_by(email=email).first()
            if existing:
                return existing

            user = User(
                email=email,
                first_name="Extra",
                last_name="User",
                password_hash="dummy_hash",  # pragma: allowlist secret
                institution_id=exam_institution.id,
                status=UserStatus.ACTIVE.value,
            )
            exam_db.add(user)
            exam_db.commit()
            exam_db.refresh(user)
            return user

        @pytest.fixture
        def mock_user(self, exam_institution, exam_user):
            return _make_mock_user(
                institution_id=exam_institution.id, user_id=exam_user.id
            )

        @pytest.fixture
        def exam_client(self, exam_db, exam_institution, mock_user):
            from utils.auth_utils import get_current_user
            from database import get_db
            import api.exams as exams_module

            app.include_router(exams_module.router)

            def override_get_db():
                yield exam_db

            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_db] = override_get_db

            client = TestClient(app, raise_server_exceptions=True)
            yield client
            app.dependency_overrides.clear()

        def _create_approved_question(
            self,
            db,
            institution_id,
            user_id,
            text="Extra Q",
            question_type="single_choice",
            difficulty="medium",
            topic="General",
            bloom_level=None,
            review_status="approved",
        ):
            from models.question_review import QuestionReview

            q = QuestionReview(
                question_text=text,
                question_type=question_type,
                difficulty=difficulty,
                topic=topic,
                bloom_level=bloom_level,
                review_status=review_status,
                options=["A", "B", "C", "D"]
                if question_type == "single_choice"
                else None,
                correct_answer="A" if question_type == "single_choice" else None,
                institution_id=institution_id,
                created_by=user_id,
            )
            db.add(q)
            db.commit()
            db.refresh(q)
            return q

    return _Fixtures


# ---------------------------------------------------------------------------
# 5a: Additional CRUD coverage
# ---------------------------------------------------------------------------


class TestExamCRUDApiExtra(
    _make_exam_test_class_fixtures("examcrud2-uni", "examcrud2@test.com")
):
    """Extra coverage for CRUD edge cases: 404s, filter params, non-draft guards."""

    def test_get_exam_404(self, exam_client):
        """GET /api/v1/exams/{id} returns 404 for non-existent exam."""
        response = exam_client.get("/api/v1/exams/999999")
        assert response.status_code == 404

    def test_update_exam_404(self, exam_client):
        """PUT /api/v1/exams/{id} returns 404 for non-existent exam."""
        response = exam_client.put(
            "/api/v1/exams/999999",
            json={"title": "Ghost", "updated_at": "2026-01-01T00:00:00"},
        )
        assert response.status_code == 404

    def test_update_non_draft_exam_returns_400(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """PUT /api/v1/exams/{id} returns 400 when exam is already finalized."""
        # Create and finalize an exam
        create_resp = exam_client.post(
            "/api/v1/exams/", json={"title": "Finalized Exam"}
        )
        assert create_resp.status_code == 201
        exam = create_resp.json()
        exam_id = exam["id"]

        # Add a question so we can finalize
        q = self._create_approved_question(exam_db, exam_institution.id, exam_user.id)
        add_resp = exam_client.post(
            f"/api/v1/exams/{exam_id}/questions",
            json={"question_ids": [q.id]},
        )
        assert add_resp.status_code == 200

        # Finalize
        fin_resp = exam_client.post(f"/api/v1/exams/{exam_id}/finalize")
        assert fin_resp.status_code == 200

        # Now try to update — should 400
        response = exam_client.put(
            f"/api/v1/exams/{exam_id}",
            json={"title": "New Title", "updated_at": fin_resp.json()["updated_at"]},
        )
        assert response.status_code == 400
        detail = response.json()["detail"].lower()
        assert "entwurf" in detail or "draft" in detail

    def test_delete_exam_404(self, exam_client):
        """DELETE /api/v1/exams/{id} returns 404 for non-existent exam."""
        response = exam_client.delete("/api/v1/exams/999999")
        assert response.status_code == 404

    def test_delete_finalized_unarchived_exam_returns_409(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """DELETE of a finalized, NOT archived exam is blocked with 409
        (TF-398: archive first, then delete). A finalized exam — unlike an
        exported one — is generally deletable after archiving, as long as
        no submissions exist; without archiving, however, the guard applies."""
        create_resp = exam_client.post(
            "/api/v1/exams/", json={"title": "Finalized Delete"}
        )
        exam_id = create_resp.json()["id"]

        q = self._create_approved_question(exam_db, exam_institution.id, exam_user.id)
        exam_client.post(
            f"/api/v1/exams/{exam_id}/questions",
            json={"question_ids": [q.id]},
        )
        exam_client.post(f"/api/v1/exams/{exam_id}/finalize")

        response = exam_client.delete(f"/api/v1/exams/{exam_id}")
        assert response.status_code == 409

    def test_list_exams_with_status_filter(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """GET /api/v1/exams/?status=draft returns only draft exams."""
        # Create two draft exams and finalize one
        r1 = exam_client.post("/api/v1/exams/", json={"title": "Draft Filter A"})
        r2 = exam_client.post("/api/v1/exams/", json={"title": "Draft Filter B"})
        assert r1.status_code == 201
        assert r2.status_code == 201
        exam2_id = r2.json()["id"]

        q = self._create_approved_question(exam_db, exam_institution.id, exam_user.id)
        exam_client.post(
            f"/api/v1/exams/{exam2_id}/questions",
            json={"question_ids": [q.id]},
        )
        exam_client.post(f"/api/v1/exams/{exam2_id}/finalize")

        response = exam_client.get("/api/v1/exams/?status=draft")
        assert response.status_code == 200
        data = response.json()
        statuses = [e["status"] for e in data["exams"]]
        assert all(s == "draft" for s in statuses)

        response2 = exam_client.get("/api/v1/exams/?status=finalized")
        assert response2.status_code == 200
        data2 = response2.json()
        statuses2 = [e["status"] for e in data2["exams"]]
        assert all(s == "finalized" for s in statuses2)
        assert data2["total"] >= 1

    def test_list_exams_with_search_filter(self, exam_client):
        """GET /api/v1/exams/?search=UniqueTitle returns matching exams only."""
        unique_title = "UniqueSearchXY999"
        exam_client.post("/api/v1/exams/", json={"title": unique_title})
        exam_client.post("/api/v1/exams/", json={"title": "Unrelated Exam"})

        response = exam_client.get(f"/api/v1/exams/?search={unique_title}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        titles = [e["title"] for e in data["exams"]]
        assert all(unique_title in t for t in titles)


# ---------------------------------------------------------------------------
# 5b: Additional question management coverage
# ---------------------------------------------------------------------------


class TestExamQuestionApiExtra(
    _make_exam_test_class_fixtures("examq2-uni", "examq2@test.com")
):
    """Extra coverage: duplicate skip, 404 on non-existent question, update_exam_question,
    remove with position re-numbering."""

    def test_add_duplicate_question_skipped_silently(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """Adding the same question_id twice results in only one entry (silent skip)."""
        create_resp = exam_client.post(
            "/api/v1/exams/", json={"title": "Dup Skip Test"}
        )
        exam_id = create_resp.json()["id"]

        q = self._create_approved_question(exam_db, exam_institution.id, exam_user.id)

        # Add once
        exam_client.post(
            f"/api/v1/exams/{exam_id}/questions",
            json={"question_ids": [q.id]},
        )

        # Add again — should be silently ignored
        resp = exam_client.post(
            f"/api/v1/exams/{exam_id}/questions",
            json={"question_ids": [q.id]},
        )
        assert resp.status_code == 200
        assert len(resp.json()["questions"]) == 1

    def test_add_non_existent_question_returns_404(self, exam_client):
        """POST /{exam_id}/questions returns 404 for unknown question_id."""
        create_resp = exam_client.post(
            "/api/v1/exams/", json={"title": "Missing Q Test"}
        )
        exam_id = create_resp.json()["id"]

        response = exam_client.post(
            f"/api/v1/exams/{exam_id}/questions",
            json={"question_ids": [999999]},
        )
        assert response.status_code == 404
        detail = response.json()["detail"]
        assert (
            "nicht gefunden" in detail
            or "not found" in detail.lower()
            or "999999" in detail
        )

    def test_update_exam_question_points_and_section(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """PUT /{exam_id}/questions/{eq_id} updates points and section."""
        create_resp = exam_client.post(
            "/api/v1/exams/", json={"title": "UpdateEQ Test"}
        )
        exam_id = create_resp.json()["id"]

        q = self._create_approved_question(exam_db, exam_institution.id, exam_user.id)
        exam_client.post(
            f"/api/v1/exams/{exam_id}/questions",
            json={"question_ids": [q.id]},
        )

        detail = exam_client.get(f"/api/v1/exams/{exam_id}").json()
        eq_id = detail["questions"][0]["id"]

        response = exam_client.put(
            f"/api/v1/exams/{exam_id}/questions/{eq_id}",
            json={"points": 12.5, "section": "Section B"},
        )
        assert response.status_code == 200
        data = response.json()
        updated_q = next(q for q in data["questions"] if q["id"] == eq_id)
        assert updated_q["points"] == 12.5
        assert updated_q["section"] == "Section B"
        assert data["total_points"] == 12.5

    def test_update_exam_question_404_eq_id(self, exam_client):
        """PUT /{exam_id}/questions/{eq_id} returns 404 for unknown eq_id."""
        create_resp = exam_client.post("/api/v1/exams/", json={"title": "EQ 404 Test"})
        exam_id = create_resp.json()["id"]

        response = exam_client.put(
            f"/api/v1/exams/{exam_id}/questions/999999",
            json={"points": 5.0},
        )
        assert response.status_code == 404

    def test_remove_question_renumbers_positions(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """DELETE /{exam_id}/questions/{eq_id} re-numbers remaining positions from 1."""
        create_resp = exam_client.post(
            "/api/v1/exams/", json={"title": "Renumber Test"}
        )
        exam_id = create_resp.json()["id"]

        q1 = self._create_approved_question(
            exam_db, exam_institution.id, exam_user.id, text="Renumber Q1"
        )
        q2 = self._create_approved_question(
            exam_db, exam_institution.id, exam_user.id, text="Renumber Q2"
        )
        q3 = self._create_approved_question(
            exam_db, exam_institution.id, exam_user.id, text="Renumber Q3"
        )

        exam_client.post(
            f"/api/v1/exams/{exam_id}/questions",
            json={"question_ids": [q1.id, q2.id, q3.id]},
        )

        detail = exam_client.get(f"/api/v1/exams/{exam_id}").json()
        assert len(detail["questions"]) == 3
        # Remove the middle question (position 2)
        eq_id_pos2 = detail["questions"][1]["id"]

        response = exam_client.delete(f"/api/v1/exams/{exam_id}/questions/{eq_id_pos2}")
        assert response.status_code == 200
        remaining = response.json()["questions"]
        assert len(remaining) == 2
        # Positions must be 1 and 2 after re-numbering
        positions = sorted(q["position"] for q in remaining)
        assert positions == [1, 2]

    def test_remove_exam_question_404(self, exam_client):
        """DELETE /{exam_id}/questions/{eq_id} returns 404 for unknown eq_id."""
        create_resp = exam_client.post(
            "/api/v1/exams/", json={"title": "EQ Remove 404"}
        )
        exam_id = create_resp.json()["id"]

        response = exam_client.delete(f"/api/v1/exams/{exam_id}/questions/999999")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# 5c: Approved-questions filter coverage
# ---------------------------------------------------------------------------


class TestApprovedQuestionsFilters(
    _make_exam_test_class_fixtures("examaq-uni", "examaq@test.com")
):
    """Tests for all filter params on GET /approved-questions."""

    def test_filter_by_difficulty(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """Filter by difficulty=easy returns only easy questions."""
        self._create_approved_question(
            exam_db,
            exam_institution.id,
            exam_user.id,
            text="Easy Q AQ",
            difficulty="easy",
            topic="Filters",
        )
        self._create_approved_question(
            exam_db,
            exam_institution.id,
            exam_user.id,
            text="Hard Q AQ",
            difficulty="hard",
            topic="Filters",
        )

        response = exam_client.get("/api/v1/exams/approved-questions?difficulty=easy")
        assert response.status_code == 200
        data = response.json()
        difficulties = [q["difficulty"] for q in data["questions"]]
        assert all(d == "easy" for d in difficulties)
        assert data["total"] >= 1

    def test_filter_by_question_type(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """Filter by question_type=open_ended returns only open-ended questions."""
        self._create_approved_question(
            exam_db,
            exam_institution.id,
            exam_user.id,
            text="OE Q AQ",
            question_type="open_ended",
            topic="TypeFilter",
        )
        self._create_approved_question(
            exam_db,
            exam_institution.id,
            exam_user.id,
            text="MC Q AQ",
            question_type="single_choice",
            topic="TypeFilter",
        )

        response = exam_client.get(
            "/api/v1/exams/approved-questions?question_type=open_ended"
        )
        assert response.status_code == 200
        data = response.json()
        types = [q["question_type"] for q in data["questions"]]
        assert all(t == "open_ended" for t in types)
        assert data["total"] >= 1

    def test_filter_by_question_type_multiple_choice(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """TF-403: question_type=multiple_choice is accepted (not 422).

        The composer "Mehrfachauswahl" filter sends this value; the
        approved-questions query-param validator must allow the new
        multi-answer type alongside single_choice/open_ended/true_false.
        """
        self._create_approved_question(
            exam_db,
            exam_institution.id,
            exam_user.id,
            text="MR Q AQ",
            question_type="multiple_choice",
            topic="TypeFilterMC",
        )
        self._create_approved_question(
            exam_db,
            exam_institution.id,
            exam_user.id,
            text="SC Q AQ",
            question_type="single_choice",
            topic="TypeFilterMC",
        )

        response = exam_client.get(
            "/api/v1/exams/approved-questions?question_type=multiple_choice"
        )
        assert response.status_code == 200
        data = response.json()
        types = [q["question_type"] for q in data["questions"]]
        assert all(t == "multiple_choice" for t in types)
        assert data["total"] >= 1

    def test_filter_by_bloom_level(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """Filter by bloom_level=3 returns only questions with bloom_level=3."""
        self._create_approved_question(
            exam_db,
            exam_institution.id,
            exam_user.id,
            text="Bloom3 Q AQ",
            bloom_level=3,
            topic="BloomFilter",
        )
        self._create_approved_question(
            exam_db,
            exam_institution.id,
            exam_user.id,
            text="Bloom5 Q AQ",
            bloom_level=5,
            topic="BloomFilter",
        )

        response = exam_client.get("/api/v1/exams/approved-questions?bloom_level=3")
        assert response.status_code == 200
        data = response.json()
        bloom_levels = [q["bloom_level"] for q in data["questions"]]
        assert all(b == 3 for b in bloom_levels)
        assert data["total"] >= 1

    def test_filter_by_search_text(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """Filter by search returns questions whose text contains the query."""
        unique_phrase = "UniqueSearchPhraseAQ9871"
        self._create_approved_question(
            exam_db,
            exam_institution.id,
            exam_user.id,
            text=f"Question with {unique_phrase} inside",
            topic="SearchFilter",
        )
        self._create_approved_question(
            exam_db,
            exam_institution.id,
            exam_user.id,
            text="Unrelated question about nothing",
            topic="SearchFilter",
        )

        response = exam_client.get(
            f"/api/v1/exams/approved-questions?search={unique_phrase}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        texts = [q["question_text"] for q in data["questions"]]
        assert all(unique_phrase in t for t in texts)

    def test_approved_questions_usage_count(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """Approved questions endpoint returns usage_count reflecting exam membership."""
        create_resp = exam_client.post(
            "/api/v1/exams/", json={"title": "Usage Count Exam"}
        )
        exam_id = create_resp.json()["id"]

        q = self._create_approved_question(
            exam_db,
            exam_institution.id,
            exam_user.id,
            text="Usage Count Q AQ",
            topic="UsageCount",
        )

        # Before adding to exam: usage_count should be 0
        resp_before = exam_client.get(
            "/api/v1/exams/approved-questions?search=Usage Count Q AQ"
        )
        assert resp_before.status_code == 200
        questions_before = resp_before.json()["questions"]
        assert len(questions_before) >= 1
        assert questions_before[0]["usage_count"] == 0

        # Add to exam
        exam_client.post(
            f"/api/v1/exams/{exam_id}/questions",
            json={"question_ids": [q.id]},
        )

        resp_after = exam_client.get(
            "/api/v1/exams/approved-questions?search=Usage Count Q AQ"
        )
        assert resp_after.status_code == 200
        questions_after = resp_after.json()["questions"]
        assert len(questions_after) >= 1
        assert questions_after[0]["usage_count"] == 1


# ---------------------------------------------------------------------------
# 5d: Auto-fill coverage
# ---------------------------------------------------------------------------


class TestAutoFillQuestions(
    _make_exam_test_class_fixtures("examaf-uni", "examaf@test.com")
):
    """Tests for POST /{exam_id}/auto-fill."""

    def test_auto_fill_adds_questions(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """auto-fill adds up to `count` approved questions to the exam."""
        create_resp = exam_client.post(
            "/api/v1/exams/", json={"title": "AutoFill Test"}
        )
        exam_id = create_resp.json()["id"]

        for i in range(5):
            self._create_approved_question(
                exam_db,
                exam_institution.id,
                exam_user.id,
                text=f"AutoFill Q{i}",
                topic="AutoFill",
            )

        response = exam_client.post(
            f"/api/v1/exams/{exam_id}/auto-fill",
            json={"count": 3, "topic": "AutoFill"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["questions"]) == 3
        assert data["total_points"] > 0

    def test_auto_fill_with_difficulty_filter(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """auto-fill with difficulty filter only picks matching questions."""
        create_resp = exam_client.post(
            "/api/v1/exams/", json={"title": "AutoFill Difficulty"}
        )
        exam_id = create_resp.json()["id"]

        for i in range(3):
            self._create_approved_question(
                exam_db,
                exam_institution.id,
                exam_user.id,
                text=f"AF Hard Q{i}",
                difficulty="hard",
                topic="AFDiff",
            )
        for i in range(3):
            self._create_approved_question(
                exam_db,
                exam_institution.id,
                exam_user.id,
                text=f"AF Easy Q{i}",
                difficulty="easy",
                topic="AFDiff",
            )

        response = exam_client.post(
            f"/api/v1/exams/{exam_id}/auto-fill",
            json={"count": 2, "difficulty": ["hard"], "topic": "AFDiff"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["questions"]) == 2
        for q in data["questions"]:
            assert q["difficulty"] == "hard"

    def test_auto_fill_no_matching_questions_returns_404(self, exam_client):
        """auto-fill returns 404 when no questions match the criteria."""
        create_resp = exam_client.post(
            "/api/v1/exams/", json={"title": "AutoFill Empty"}
        )
        exam_id = create_resp.json()["id"]

        response = exam_client.post(
            f"/api/v1/exams/{exam_id}/auto-fill",
            json={"count": 5, "topic": "TopicThatDefinitelyDoesNotExistXYZ99"},
        )
        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "Keine passenden" in detail or "No matching questions" in detail

    def test_auto_fill_excludes_already_added_questions(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """auto-fill skips questions already in the exam."""
        create_resp = exam_client.post(
            "/api/v1/exams/", json={"title": "AutoFill Exclude"}
        )
        exam_id = create_resp.json()["id"]

        # Create exactly 2 questions
        q1 = self._create_approved_question(
            exam_db,
            exam_institution.id,
            exam_user.id,
            text="AF Excl Q1",
            topic="AFExclude",
        )
        self._create_approved_question(
            exam_db,
            exam_institution.id,
            exam_user.id,
            text="AF Excl Q2",
            topic="AFExclude",
        )

        # Manually add q1 first
        exam_client.post(
            f"/api/v1/exams/{exam_id}/questions",
            json={"question_ids": [q1.id]},
        )

        # auto-fill requesting 1 more — only q2 is available
        response = exam_client.post(
            f"/api/v1/exams/{exam_id}/auto-fill",
            json={"count": 5, "topic": "AFExclude"},
        )
        assert response.status_code == 200
        data = response.json()
        question_ids = [q["question_id"] for q in data["questions"]]
        # q1 should appear exactly once (not duplicated)
        assert question_ids.count(q1.id) == 1
        # total is 2 (q1 + q2)
        assert len(data["questions"]) == 2

    def test_auto_fill_with_question_types_filter(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """auto-fill with question_types filter picks only matching types."""
        create_resp = exam_client.post(
            "/api/v1/exams/", json={"title": "AutoFill Types"}
        )
        exam_id = create_resp.json()["id"]

        for i in range(2):
            self._create_approved_question(
                exam_db,
                exam_institution.id,
                exam_user.id,
                text=f"AF TF Q{i}",
                question_type="true_false",
                topic="AFTypes",
            )
        for i in range(2):
            self._create_approved_question(
                exam_db,
                exam_institution.id,
                exam_user.id,
                text=f"AF OE Q{i}",
                question_type="open_ended",
                topic="AFTypes",
            )

        response = exam_client.post(
            f"/api/v1/exams/{exam_id}/auto-fill",
            json={"count": 2, "question_types": ["true_false"], "topic": "AFTypes"},
        )
        assert response.status_code == 200
        for q in response.json()["questions"]:
            assert q["question_type"] == "true_false"


# ---------------------------------------------------------------------------
# 5e: Additional workflow coverage (finalize with non-approved, unfinalize edge cases)
# ---------------------------------------------------------------------------


class TestExamWorkflowApiExtra(
    _make_exam_test_class_fixtures("examwf2-uni", "examwf2@test.com")
):
    """Extra workflow coverage: non-approved finalize, unfinalize on draft, exported unfinalize."""

    def test_finalize_with_non_approved_question_fails(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """POST /{exam_id}/finalize returns 400 listing non-approved question IDs."""

        create_resp = exam_client.post(
            "/api/v1/exams/", json={"title": "Non-Approved Finalize"}
        )
        exam_id = create_resp.json()["id"]

        # Create an approved question and add it
        q = self._create_approved_question(exam_db, exam_institution.id, exam_user.id)
        exam_client.post(
            f"/api/v1/exams/{exam_id}/questions",
            json={"question_ids": [q.id]},
        )

        # Downgrade question status to pending directly in DB
        from models.question_review import QuestionReview

        question = exam_db.query(QuestionReview).filter_by(id=q.id).first()
        question.review_status = "pending"
        exam_db.commit()

        response = exam_client.post(f"/api/v1/exams/{exam_id}/finalize")
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert (
            str(q.id) in detail
            or "no longer approved" in detail.lower()
            or "genehmigt" in detail.lower()
        )

    def test_unfinalize_already_draft_returns_400(self, exam_client):
        """POST /{exam_id}/unfinalize returns 400 if exam is already a draft."""
        create_resp = exam_client.post(
            "/api/v1/exams/", json={"title": "Draft Unfinalize"}
        )
        exam_id = create_resp.json()["id"]

        response = exam_client.post(f"/api/v1/exams/{exam_id}/unfinalize")
        assert response.status_code == 400
        detail = response.json()["detail"].lower()
        assert "bereits" in detail or "already a draft" in detail

    def test_unfinalize_exported_exam_returns_to_draft(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """POST /{exam_id}/unfinalize also works on exported exams (reverts to draft)."""
        create_resp = exam_client.post(
            "/api/v1/exams/", json={"title": "Exported Unfinalize"}
        )
        exam_id = create_resp.json()["id"]

        q = self._create_approved_question(exam_db, exam_institution.id, exam_user.id)
        exam_client.post(
            f"/api/v1/exams/{exam_id}/questions",
            json={"question_ids": [q.id]},
        )
        # Finalize, then export (which sets status=exported)
        exam_client.post(f"/api/v1/exams/{exam_id}/finalize")
        exam_client.get(f"/api/v1/exams/{exam_id}/export/md")

        # Verify status is now exported
        detail = exam_client.get(f"/api/v1/exams/{exam_id}").json()
        assert detail["status"] == "exported"

        # Unfinalize exported -> draft
        response = exam_client.post(f"/api/v1/exams/{exam_id}/unfinalize")
        assert response.status_code == 200
        assert response.json()["status"] == "draft"


# ---------------------------------------------------------------------------
# 5f: Export endpoint coverage
# ---------------------------------------------------------------------------


class TestExamExportApi(
    _make_exam_test_class_fixtures("examexp-uni", "examexp@test.com")
):
    """Tests for GET /{exam_id}/export/{format}."""

    def _create_exam_with_question(
        self, client, db, institution_id, user_id, title="Export Exam"
    ):
        """Helper: create exam, add one approved MC question, and finalize."""
        create_resp = client.post("/api/v1/exams/", json={"title": title})
        assert create_resp.status_code == 201
        exam_id = create_resp.json()["id"]

        q = self._create_approved_question(db, institution_id, user_id)
        client.post(
            f"/api/v1/exams/{exam_id}/questions",
            json={"question_ids": [q.id]},
        )
        fin_resp = client.post(f"/api/v1/exams/{exam_id}/finalize")
        assert fin_resp.status_code == 200
        return exam_id

    def test_export_empty_exam_returns_400(self, exam_client):
        """GET /export/md returns 400 for a draft exam (not finalized)."""
        create_resp = exam_client.post("/api/v1/exams/", json={"title": "Empty Export"})
        exam_id = create_resp.json()["id"]

        response = exam_client.get(f"/api/v1/exams/{exam_id}/export/md")
        assert response.status_code == 400
        # Draft guard fires before the empty-check — message mentions finalisiert
        detail = response.json()["detail"].lower()
        assert "export" in detail or "finalisiert" in detail

    def test_export_unsupported_format_returns_400(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """An unknown format returns 400 (``pdf`` is supported since TF-656)."""
        exam_id = self._create_exam_with_question(
            exam_client, exam_db, exam_institution.id, exam_user.id
        )
        response = exam_client.get(f"/api/v1/exams/{exam_id}/export/docx")
        assert response.status_code == 400
        detail = response.json()["detail"].lower()
        assert "nicht unterstützt" in detail or "unsupported" in detail

    def test_export_pdf_format(self, exam_client, exam_db, exam_institution, exam_user):
        """GET /export/pdf returns a real PDF with an attachment filename."""
        exam_id = self._create_exam_with_question(
            exam_client,
            exam_db,
            exam_institution.id,
            exam_user.id,
            title="PDF Export Exam",
        )
        response = exam_client.get(f"/api/v1/exams/{exam_id}/export/pdf")
        assert response.status_code == 200
        assert "application/pdf" in response.headers["content-type"]
        disposition = response.headers["content-disposition"]
        assert disposition.startswith("attachment;")
        assert "PDF Export Exam" in disposition
        # Both the quoted filename and the RFC 5987 filename* carry .pdf
        assert '.pdf"' in disposition
        assert disposition.endswith(".pdf")
        assert response.content.startswith(b"%PDF-")

    def test_export_pdf_exporter_failure_returns_translated_500(
        self, exam_client, exam_db, exam_institution, exam_user, monkeypatch
    ):
        """A ReportLab/exporter exception must not propagate as a bare,
        unlocalized FastAPI 500 — it should be caught, logged, and turned
        into a translated error (mirroring grade_export.py's pattern)."""
        import api.exams as exams_api

        def _boom(*args, **kwargs):
            raise ValueError("simulated exporter failure")

        monkeypatch.setattr(exams_api.PdfExporter, "export", staticmethod(_boom))

        exam_id = self._create_exam_with_question(
            exam_client, exam_db, exam_institution.id, exam_user.id
        )
        response = exam_client.get(f"/api/v1/exams/{exam_id}/export/pdf")
        assert response.status_code == 500
        detail = response.json()["detail"]
        assert "simulated exporter failure" not in detail
        assert detail.strip() != ""

    def test_export_pdf_with_solutions_uses_solutions_suffix(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        exam_id = self._create_exam_with_question(
            exam_client,
            exam_db,
            exam_institution.id,
            exam_user.id,
            title="PDF Solutions Exam",
        )
        response = exam_client.get(
            f"/api/v1/exams/{exam_id}/export/pdf?include_solutions=true"
        )
        assert response.status_code == 200
        # German exam → German suffix (the suffix follows the exam language)
        assert "_L%C3%B6sungen.pdf" in response.headers["content-disposition"]
        assert response.content.startswith(b"%PDF-")

    @pytest.mark.parametrize(
        "language,suffix",
        [
            ("de", "_Lösungen"),
            ("en", "_solutions"),
            ("fr", "_corrigé"),
            ("it", "_soluzioni"),
        ],
    )
    def test_solutions_suffix_follows_the_exam_language(
        self, exam_client, exam_db, exam_institution, exam_user, language, suffix
    ):
        """The suffix labels the document, so it speaks the document's
        language — not the exporting user's UI locale."""
        from models.exam import Exam

        exam_id = self._create_exam_with_question(
            exam_client,
            exam_db,
            exam_institution.id,
            exam_user.id,
            title="Sprachtest",
        )
        exam = exam_db.query(Exam).filter_by(id=exam_id).first()
        exam.language = language
        exam_db.commit()

        response = exam_client.get(
            f"/api/v1/exams/{exam_id}/export/pdf?include_solutions=true"
        )
        assert response.status_code == 200

        _ascii, real_name = self._disposition_names(
            response.headers["content-disposition"]
        )
        assert real_name == f"Sprachtest{suffix}.pdf"

    def test_export_pdf_draft_exam_returns_400(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        create_resp = exam_client.post("/api/v1/exams/", json={"title": "PDF Draft"})
        exam_id = create_resp.json()["id"]
        q = self._create_approved_question(exam_db, exam_institution.id, exam_user.id)
        exam_client.post(
            f"/api/v1/exams/{exam_id}/questions", json={"question_ids": [q.id]}
        )

        response = exam_client.get(f"/api/v1/exams/{exam_id}/export/pdf")
        assert response.status_code == 400
        detail = response.json()["detail"].lower()
        assert "export" in detail or "finalisiert" in detail

    def test_export_pdf_without_questions_returns_400(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """The empty-exam guard also covers PDF."""
        from models.exam import Exam

        create_resp = exam_client.post("/api/v1/exams/", json={"title": "PDF Empty"})
        exam_id = create_resp.json()["id"]
        # Bypass finalize (which requires questions) to reach the empty guard.
        exam = exam_db.query(Exam).filter_by(id=exam_id).first()
        exam.status = "finalized"
        exam_db.commit()

        response = exam_client.get(f"/api/v1/exams/{exam_id}/export/pdf")
        assert response.status_code == 400

    def test_export_pdf_sets_status_to_exported(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        exam_id = self._create_exam_with_question(
            exam_client,
            exam_db,
            exam_institution.id,
            exam_user.id,
            title="PDF Status Export",
        )
        assert exam_client.get(f"/api/v1/exams/{exam_id}").json()["status"] == (
            "finalized"
        )

        assert exam_client.get(f"/api/v1/exams/{exam_id}/export/pdf").status_code == 200

        detail = exam_client.get(f"/api/v1/exams/{exam_id}").json()
        assert detail["status"] == "exported"

    @staticmethod
    def _disposition_names(disposition: str) -> tuple[str, str]:
        """Return ``(ascii_filename, decoded_filename_star)`` from the header."""
        from urllib.parse import unquote

        ascii_name = re.search(r'filename="([^"]*)"', disposition).group(1)
        encoded = re.search(r"filename\*=UTF-8''(\S+)", disposition).group(1)
        return ascii_name, unquote(encoded)

    def test_export_filename_keeps_spaces_capitals_and_ampersand(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """A download should look like the exam, not like a slug."""
        exam_id = self._create_exam_with_question(
            exam_client,
            exam_db,
            exam_institution.id,
            exam_user.id,
            title="Algorithmen & Datenstrukturen FS 2026",
        )
        response = exam_client.get(f"/api/v1/exams/{exam_id}/export/pdf")
        assert response.status_code == 200

        ascii_name, real_name = self._disposition_names(
            response.headers["content-disposition"]
        )
        assert real_name == "Algorithmen & Datenstrukturen FS 2026.pdf"
        # The ASCII fallback keeps spaces, capitals and & too — only
        # non-ASCII gets transliterated.
        assert ascii_name == "Algorithmen & Datenstrukturen FS 2026.pdf"

    def test_export_filename_carries_no_export_timestamp(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """The server runs in UTC while users sit in CET/CEST, so an export
        timestamp reads two hours off. The exam's own date is in the document;
        the filename stays clean (and matches the grade export's convention).
        """
        exam_id = self._create_exam_with_question(
            exam_client,
            exam_db,
            exam_institution.id,
            exam_user.id,
            title="Zeitlose Prüfung",
        )
        response = exam_client.get(f"/api/v1/exams/{exam_id}/export/pdf")
        assert response.status_code == 200

        ascii_name, real_name = self._disposition_names(
            response.headers["content-disposition"]
        )
        assert real_name == "Zeitlose Prüfung.pdf"
        assert not re.search(r"\d{6,}", ascii_name)

    def test_export_solutions_variant_stays_distinguishable(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """Without a timestamp the two PDF variants must still differ by name."""
        exam_id = self._create_exam_with_question(
            exam_client,
            exam_db,
            exam_institution.id,
            exam_user.id,
            title="Doppelte Prüfung",
        )
        plain = exam_client.get(f"/api/v1/exams/{exam_id}/export/pdf")
        solutions = exam_client.get(
            f"/api/v1/exams/{exam_id}/export/pdf?include_solutions=true"
        )
        assert self._disposition_names(plain.headers["content-disposition"])[1] == (
            "Doppelte Prüfung.pdf"
        )
        assert self._disposition_names(solutions.headers["content-disposition"])[1] == (
            "Doppelte Prüfung_Lösungen.pdf"
        )

    @pytest.mark.parametrize("reserved", ["CON", "nul", "Com1"])
    def test_export_filename_avoids_windows_reserved_device_names(
        self, exam_client, exam_db, exam_institution, exam_user, reserved
    ):
        """CON, NUL, COM1 … are device names on Windows and cannot be saved,
        extension or not. Without a timestamp the stem is the bare title, so
        this is reachable again."""
        exam_id = self._create_exam_with_question(
            exam_client,
            exam_db,
            exam_institution.id,
            exam_user.id,
            title=reserved,
        )
        response = exam_client.get(f"/api/v1/exams/{exam_id}/export/pdf")
        assert response.status_code == 200

        for name in self._disposition_names(response.headers["content-disposition"]):
            stem = name.rsplit(".", 1)[0]
            assert stem.upper() != reserved.upper()
            assert reserved.lower() in name.lower()

    def test_export_filename_drops_characters_windows_forbids(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        r"""``\ / : * ? " < > |`` are illegal in Windows filenames; leaving
        them in would hand the user a file they cannot save."""
        exam_id = self._create_exam_with_question(
            exam_client,
            exam_db,
            exam_institution.id,
            exam_user.id,
            title="Prüfung: Kapitel 3? <A/B> 100%|ok*",
        )
        response = exam_client.get(f"/api/v1/exams/{exam_id}/export/pdf")
        assert response.status_code == 200

        ascii_name, real_name = self._disposition_names(
            response.headers["content-disposition"]
        )
        for name in (ascii_name, real_name):
            assert not set(name) & set('\\/:*?"<>|')
        # The readable parts survive.
        assert "Kapitel 3" in real_name
        assert "100%" in real_name

    def test_export_filename_has_no_leading_or_trailing_space_or_dot(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """Windows silently rejects names that begin or end with a space or dot."""
        exam_id = self._create_exam_with_question(
            exam_client,
            exam_db,
            exam_institution.id,
            exam_user.id,
            title="  .Randfall.  ",
        )
        response = exam_client.get(f"/api/v1/exams/{exam_id}/export/pdf")
        assert response.status_code == 200

        for name in self._disposition_names(response.headers["content-disposition"]):
            assert name == name.strip()
            assert not name.startswith(".")
            assert "Randfall" in name

    @pytest.mark.parametrize("export_format", ["md", "pdf", "json", "moodle"])
    def test_export_title_with_non_latin1_characters(
        self, exam_client, exam_db, exam_institution, exam_user, export_format
    ):
        """A title with an em dash must not break the download.

        HTTP headers are latin-1; "—" (U+2014) is not in latin-1, so naively
        interpolating the title into Content-Disposition raises
        UnicodeEncodeError and the export 500s for every format.
        """
        exam_id = self._create_exam_with_question(
            exam_client,
            exam_db,
            exam_institution.id,
            exam_user.id,
            title="Algorithmen — Semesterprüfung FS 2026",
        )
        response = exam_client.get(f"/api/v1/exams/{exam_id}/export/{export_format}")
        assert response.status_code == 200

        disposition = response.headers["content-disposition"]
        # The whole header must survive the latin-1 round trip.
        disposition.encode("latin-1")
        # Plain filename stays ASCII for old clients, filename* carries UTF-8.
        assert 'filename="' in disposition
        assert "filename*=UTF-8''" in disposition
        # The umlaut survives verbatim in filename* as UTF-8 percent-encoding…
        assert "Semesterpr%C3%BCfung" in disposition
        # …while the ASCII fallback transliterates it instead of dropping it.
        assert "Semesterprufung" in disposition

    def test_export_title_without_any_ascii_still_yields_a_filename(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        exam_id = self._create_exam_with_question(
            exam_client,
            exam_db,
            exam_institution.id,
            exam_user.id,
            title="試験",
        )
        response = exam_client.get(f"/api/v1/exams/{exam_id}/export/pdf")
        assert response.status_code == 200

        disposition = response.headers["content-disposition"]
        disposition.encode("latin-1")
        ascii_name, real_name = self._disposition_names(disposition)
        # Transliteration leaves nothing, so the fallback must still name a
        # usable .pdf rather than a bare extension.
        assert ascii_name == "export.pdf"
        assert real_name == "試験.pdf"

    def test_export_title_cannot_inject_response_headers(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """Quotes and CRLF in a title must never reach the header verbatim."""
        exam_id = self._create_exam_with_question(
            exam_client,
            exam_db,
            exam_institution.id,
            exam_user.id,
            title='ev"il\r\nX-Injected: yes',
        )
        response = exam_client.get(f"/api/v1/exams/{exam_id}/export/pdf")
        assert response.status_code == 200
        assert "x-injected" not in {k.lower() for k in response.headers}

        disposition = response.headers["content-disposition"]
        quoted = disposition.split('filename="', 1)[1].split('"', 1)[0]
        assert '"' not in quoted
        assert "\r" not in disposition and "\n" not in disposition

    def test_export_pdf_without_create_exams_permission_returns_403(
        self, exam_client, exam_db, exam_institution, exam_user, mock_user
    ):
        exam_id = self._create_exam_with_question(
            exam_client,
            exam_db,
            exam_institution.id,
            exam_user.id,
            title="PDF Forbidden",
        )
        mock_user.has_permission = lambda permission: permission != "create_exams"

        response = exam_client.get(f"/api/v1/exams/{exam_id}/export/pdf")
        assert response.status_code == 403

    def test_export_markdown_format(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """GET /export/md returns markdown content with correct Content-Disposition."""
        exam_id = self._create_exam_with_question(
            exam_client,
            exam_db,
            exam_institution.id,
            exam_user.id,
            title="MD Export Exam",
        )
        response = exam_client.get(f"/api/v1/exams/{exam_id}/export/md")
        assert response.status_code == 200
        assert "text/markdown" in response.headers["content-type"]
        assert ".md" in response.headers["content-disposition"]
        assert "# MD Export Exam" in response.text

    def test_export_markdown_with_solutions(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """GET /export/md?include_solutions=true includes solutions section and _solutions suffix."""
        exam_id = self._create_exam_with_question(
            exam_client,
            exam_db,
            exam_institution.id,
            exam_user.id,
            title="MD Solutions Exam",
        )
        response = exam_client.get(
            f"/api/v1/exams/{exam_id}/export/md?include_solutions=true"
        )
        assert response.status_code == 200
        assert "_L%C3%B6sungen.md" in response.headers["content-disposition"]
        # Markdown exporter uses "Musterlösung" heading for solutions
        assert "Musterlösung" in response.text

    def test_export_json_format(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """GET /export/json returns valid JSON with exam and questions keys."""
        import json

        exam_id = self._create_exam_with_question(
            exam_client, exam_db, exam_institution.id, exam_user.id, title="JSON Export"
        )
        response = exam_client.get(f"/api/v1/exams/{exam_id}/export/json")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        assert ".json" in response.headers["content-disposition"]
        data = json.loads(response.text)
        assert "exam" in data
        assert "questions" in data
        assert data["exam"]["title"] == "JSON Export"

    def test_export_moodle_format(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """GET /export/moodle returns XML with quiz root element."""
        exam_id = self._create_exam_with_question(
            exam_client,
            exam_db,
            exam_institution.id,
            exam_user.id,
            title="Moodle Export",
        )
        response = exam_client.get(f"/api/v1/exams/{exam_id}/export/moodle")
        assert response.status_code == 200
        assert "application/xml" in response.headers["content-type"]
        assert "_moodle.xml" in response.headers["content-disposition"]
        assert "<quiz>" in response.text

    def test_export_sets_status_to_exported(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """Exporting a finalized exam changes its status to 'exported'."""
        # _create_exam_with_question already finalizes the exam
        exam_id = self._create_exam_with_question(
            exam_client,
            exam_db,
            exam_institution.id,
            exam_user.id,
            title="Status Export",
        )

        # Verify it is finalized
        detail = exam_client.get(f"/api/v1/exams/{exam_id}").json()
        assert detail["status"] == "finalized"

        # Export
        export_resp = exam_client.get(f"/api/v1/exams/{exam_id}/export/md")
        assert export_resp.status_code == 200

        # Status should now be 'exported'
        detail = exam_client.get(f"/api/v1/exams/{exam_id}").json()
        assert detail["status"] == "exported"

    def test_export_draft_exam_returns_400(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """GET /export/json returns 400 when the exam is still in draft status."""
        # Create an exam with a question but do NOT finalize
        create_resp = exam_client.post(
            "/api/v1/exams/", json={"title": "Draft Export Status"}
        )
        exam_id = create_resp.json()["id"]
        q = self._create_approved_question(exam_db, exam_institution.id, exam_user.id)
        exam_client.post(
            f"/api/v1/exams/{exam_id}/questions",
            json={"question_ids": [q.id]},
        )

        # Attempt export without finalizing — must be rejected
        response = exam_client.get(f"/api/v1/exams/{exam_id}/export/json")
        assert response.status_code == 400
        detail = response.json()["detail"].lower()
        assert "export" in detail or "finalisiert" in detail

        # Status remains draft
        detail = exam_client.get(f"/api/v1/exams/{exam_id}").json()
        assert detail["status"] == "draft"

    def test_export_404_non_existent_exam(self, exam_client):
        """GET /export/md returns 404 for a non-existent exam."""
        response = exam_client.get("/api/v1/exams/999999/export/md")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# 5g: Composition mode auto-fill
# ---------------------------------------------------------------------------


class TestAutoComposeQuestions(
    _make_exam_test_class_fixtures("compose-uni", "compose@test.com")
):
    """Tests for POST /{exam_id}/auto-fill in composition mode."""

    def _seed_diverse_questions(self, exam_db, institution_id, user_id):
        """Create a diverse set of questions with metadata."""
        questions = []
        configs = [
            ("single_choice", "easy", 1, 1),
            ("single_choice", "medium", 2, 2),
            ("single_choice", "hard", 3, 3),
            ("open_ended", "easy", 1, 3),
            ("open_ended", "medium", 2, 5),
            ("open_ended", "hard", 3, 8),
            ("true_false", "easy", 1, 1),
            ("true_false", "medium", 2, 1),
            ("true_false", "hard", 3, 2),
        ]
        for i, (qtype, diff, bloom, time) in enumerate(configs):
            q = QuestionReview(
                question_text=f"Compose question {i}",
                question_type=qtype,
                difficulty=diff,
                topic="Compose Topic",
                bloom_level=bloom,
                estimated_time_minutes=time,
                language="de",
                review_status=ReviewStatus.APPROVED.value,
                institution_id=institution_id,
                created_by=user_id,
            )
            exam_db.add(q)
            questions.append(q)
        exam_db.flush()
        return questions

    def test_preview_returns_proposal_without_modifying(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        self._seed_diverse_questions(exam_db, exam_institution.id, exam_user.id)
        create_resp = exam_client.post("/api/v1/exams/", json={"title": "Preview Test"})
        exam_id = create_resp.json()["id"]

        response = exam_client.post(
            f"/api/v1/exams/{exam_id}/auto-fill",
            json={"target_points": 20.0, "preview": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "preview"
        assert "questions" in data
        assert "constraint_report" in data
        assert data["total_points"] <= 20.0

        # Exam should be unchanged
        exam_resp = exam_client.get(f"/api/v1/exams/{exam_id}")
        assert len(exam_resp.json()["questions"]) == 0

    def test_composition_adds_questions(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        self._seed_diverse_questions(exam_db, exam_institution.id, exam_user.id)
        create_resp = exam_client.post(
            "/api/v1/exams/", json={"title": "Compose Apply"}
        )
        exam_id = create_resp.json()["id"]

        response = exam_client.post(
            f"/api/v1/exams/{exam_id}/auto-fill",
            json={"target_points": 20.0, "preview": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["questions"]) > 0
        assert data["total_points"] > 0

        # Verify questions are actually persisted by re-fetching the exam
        get_resp = exam_client.get(f"/api/v1/exams/{exam_id}")
        assert get_resp.status_code == 200
        exam_data = get_resp.json()
        assert len(exam_data["questions"]) == len(data["questions"])

    def test_backward_compat_simple_mode(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        self._seed_diverse_questions(exam_db, exam_institution.id, exam_user.id)
        create_resp = exam_client.post(
            "/api/v1/exams/", json={"title": "Simple Compat"}
        )
        exam_id = create_resp.json()["id"]

        response = exam_client.post(
            f"/api/v1/exams/{exam_id}/auto-fill",
            json={"count": 3},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["questions"]) <= 3

    def test_distribution_validation_rejects_bad_sum(self, exam_client):
        create_resp = exam_client.post("/api/v1/exams/", json={"title": "Bad Sum"})
        exam_id = create_resp.json()["id"]

        response = exam_client.post(
            f"/api/v1/exams/{exam_id}/auto-fill",
            json={
                "target_points": 50.0,
                "bloom_distribution": {"1": 50, "2": 20},
            },
        )
        assert response.status_code == 422

    def test_null_bloom_excluded_when_distribution_active(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """Questions with NULL bloom_level excluded when bloom_distribution is set."""
        for i, bloom in enumerate([1, 2, None]):
            q = QuestionReview(
                question_text=f"Null test q{i}",
                question_type="open_ended",
                difficulty="medium",
                topic="NullTest",
                bloom_level=bloom,
                estimated_time_minutes=5,
                language="de",
                review_status=ReviewStatus.APPROVED.value,
                institution_id=exam_institution.id,
                created_by=exam_user.id,
            )
            exam_db.add(q)
        exam_db.flush()

        create_resp = exam_client.post("/api/v1/exams/", json={"title": "Null Bloom"})
        exam_id = create_resp.json()["id"]

        response = exam_client.post(
            f"/api/v1/exams/{exam_id}/auto-fill",
            json={
                "target_points": 50.0,
                "bloom_distribution": {"1": 50, "2": 50},
                "preview": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        for q in data["questions"]:
            assert q["bloom_level"] is not None

    def test_constraint_report_in_preview(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        self._seed_diverse_questions(exam_db, exam_institution.id, exam_user.id)
        create_resp = exam_client.post("/api/v1/exams/", json={"title": "Report Test"})
        exam_id = create_resp.json()["id"]

        response = exam_client.post(
            f"/api/v1/exams/{exam_id}/auto-fill",
            json={
                "target_points": 30.0,
                "bloom_distribution": {"1": 33, "2": 34, "3": 33},
                "preview": True,
            },
        )
        assert response.status_code == 200
        report = response.json()["constraint_report"]
        assert "points_target" in report
        assert "bloom_distribution" in report
        assert "overall_satisfaction" in report
        assert report["points_achieved"] <= 30.0


# ---------------------------------------------------------------------------
# Task 5 (TF-321): GET /documents-with-questions endpoint
# ---------------------------------------------------------------------------


class TestDocumentsWithQuestionsEndpoint:
    """Tests for GET /api/v1/exams/documents-with-questions."""

    @pytest.fixture
    def dwq_db(self, test_engine):
        from sqlalchemy.orm import sessionmaker

        TestSession = sessionmaker(bind=test_engine)
        session = TestSession()
        yield session
        session.close()

    @pytest.fixture
    def dwq_institution(self, dwq_db):
        existing = dwq_db.query(Institution).filter_by(slug="dwq-test-inst").first()
        if existing:
            return existing
        inst = Institution(
            name="DWQ Test University",
            slug="dwq-test-inst",
            subscription_tier="professional",
            max_users=-1,
            max_documents=-1,
            max_questions_per_month=-1,
        )
        dwq_db.add(inst)
        dwq_db.commit()
        dwq_db.refresh(inst)
        return inst

    @pytest.fixture
    def dwq_user(self, dwq_db, dwq_institution):
        existing = dwq_db.query(User).filter_by(email="dwq@test.com").first()
        if existing:
            return existing
        user = User(
            email="dwq@test.com",
            first_name="DWQ",
            last_name="User",
            password_hash="dummy_hash",  # pragma: allowlist secret
            institution_id=dwq_institution.id,
            status=UserStatus.ACTIVE.value,
        )
        dwq_db.add(user)
        dwq_db.commit()
        dwq_db.refresh(user)
        return user

    @pytest.fixture
    def dwq_client(self, dwq_db, dwq_institution, dwq_user):
        from utils.auth_utils import get_current_user
        from database import get_db
        import api.exams as exams_module

        app.include_router(exams_module.router)

        mock_user = _make_mock_user(
            institution_id=dwq_institution.id, user_id=dwq_user.id
        )
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: dwq_db
        client = TestClient(app, raise_server_exceptions=True)
        yield client
        app.dependency_overrides.clear()

    def test_returns_documents_with_approved_questions(
        self, dwq_client, dwq_db, dwq_institution, dwq_user
    ):
        from models.document import Document
        from models.question_review import QuestionSourceDocument

        doc = Document(
            filename="algo.pdf",
            original_filename="algo.pdf",
            file_path="/tmp/algo.pdf",
            file_size=1000,
            mime_type="application/pdf",
            institution_id=dwq_institution.id,
            user_id=dwq_user.id,
        )
        dwq_db.add(doc)
        dwq_db.flush()

        q = QuestionReview(
            question_text="What is Big-O?",
            question_type="open_ended",
            difficulty="medium",
            topic="Algorithms",
            language="de",
            review_status=ReviewStatus.APPROVED.value,
            institution_id=dwq_institution.id,
            created_by=dwq_user.id,
        )
        dwq_db.add(q)
        dwq_db.flush()
        dwq_db.add(QuestionSourceDocument(question_id=q.id, document_id=doc.id))
        dwq_db.commit()

        response = dwq_client.get("/api/v1/exams/documents-with-questions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        ids = [d["id"] for d in data]
        assert doc.id in ids
        entry = next(d for d in data if d["id"] == doc.id)
        # TF-331: title now resolves via Document.title (extension stripped,
        # display_name override respected). Filename "algo.pdf" → "algo".
        assert entry["title"] == "algo"
        assert entry["approved_question_count"] >= 1

    def test_returns_display_name_override_when_set(
        self, dwq_client, dwq_db, dwq_institution, dwq_user
    ):
        """TF-331: a user-set display_name surfaces through the composer endpoint."""
        from models.document import Document
        from models.question_review import QuestionSourceDocument

        doc = Document(
            filename="algo.pdf",
            original_filename="algo.pdf",
            file_path="/tmp/algo_renamed.pdf",
            file_size=1000,
            mime_type="application/pdf",
            display_name="Algorithmen-Cheatsheet",
            institution_id=dwq_institution.id,
            user_id=dwq_user.id,
        )
        dwq_db.add(doc)
        dwq_db.flush()

        q = QuestionReview(
            question_text="What is Big-O?",
            question_type="open_ended",
            difficulty="medium",
            topic="Algorithms",
            language="de",
            review_status=ReviewStatus.APPROVED.value,
            institution_id=dwq_institution.id,
            created_by=dwq_user.id,
        )
        dwq_db.add(q)
        dwq_db.flush()
        dwq_db.add(QuestionSourceDocument(question_id=q.id, document_id=doc.id))
        dwq_db.commit()

        response = dwq_client.get("/api/v1/exams/documents-with-questions")
        assert response.status_code == 200
        entry = next(d for d in response.json() if d["id"] == doc.id)
        assert entry["title"] == "Algorithmen-Cheatsheet"

    def test_includes_documents_without_approved_questions(
        self, dwq_client, dwq_db, dwq_institution, dwq_user
    ):
        """All institution documents appear; approved_question_count is 0 when none approved."""
        from models.document import Document

        doc_empty = Document(
            filename="empty.pdf",
            original_filename="empty.pdf",
            file_path="/tmp/empty.pdf",
            file_size=500,
            mime_type="application/pdf",
            institution_id=dwq_institution.id,
            user_id=dwq_user.id,
        )
        dwq_db.add(doc_empty)
        dwq_db.commit()

        response = dwq_client.get("/api/v1/exams/documents-with-questions")
        assert response.status_code == 200
        data = response.json()
        ids = [d["id"] for d in data]
        assert doc_empty.id in ids
        entry = next(d for d in data if d["id"] == doc_empty.id)
        assert entry["approved_question_count"] == 0


# ---------------------------------------------------------------------------
# Task 6: document_ids filter on GET /approved-questions
# ---------------------------------------------------------------------------


class TestApprovedQuestionsDocumentFilter:
    """Tests for document_ids filter on GET /approved-questions."""

    @pytest.fixture
    def aqdf_db(self, test_engine):
        from sqlalchemy.orm import sessionmaker

        TestSession = sessionmaker(bind=test_engine)
        session = TestSession()
        yield session
        session.close()

    @pytest.fixture
    def aqdf_institution(self, aqdf_db):
        existing = aqdf_db.query(Institution).filter_by(slug="aqdf-test-inst").first()
        if existing:
            return existing
        inst = Institution(
            name="AQDF Test University",
            slug="aqdf-test-inst",
            subscription_tier="professional",
            max_users=-1,
            max_documents=-1,
            max_questions_per_month=-1,
        )
        aqdf_db.add(inst)
        aqdf_db.commit()
        aqdf_db.refresh(inst)
        return inst

    @pytest.fixture
    def aqdf_user(self, aqdf_db, aqdf_institution):
        existing = aqdf_db.query(User).filter_by(email="aqdf@test.com").first()
        if existing:
            return existing
        user = User(
            email="aqdf@test.com",
            first_name="AQDF",
            last_name="User",
            password_hash="dummy_hash",  # pragma: allowlist secret
            institution_id=aqdf_institution.id,
            status=UserStatus.ACTIVE.value,
        )
        aqdf_db.add(user)
        aqdf_db.commit()
        aqdf_db.refresh(user)
        return user

    @pytest.fixture
    def aqdf_client(self, aqdf_db, aqdf_institution, aqdf_user):
        from utils.auth_utils import get_current_user
        from database import get_db
        import api.exams as exams_module

        app.include_router(exams_module.router)

        mock_user = _make_mock_user(
            institution_id=aqdf_institution.id, user_id=aqdf_user.id
        )
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: aqdf_db
        client = TestClient(app, raise_server_exceptions=True)
        yield client
        app.dependency_overrides.clear()

    def test_filter_by_document_id_returns_only_linked_questions(
        self, aqdf_client, aqdf_db, aqdf_institution, aqdf_user
    ):
        from models.document import Document
        from models.question_review import QuestionSourceDocument

        doc = Document(
            filename="heap.pdf",
            original_filename="heap.pdf",
            file_path="/tmp/heap.pdf",
            file_size=1000,
            mime_type="application/pdf",
            institution_id=aqdf_institution.id,
            user_id=aqdf_user.id,
        )
        aqdf_db.add(doc)
        aqdf_db.flush()

        q_linked = QuestionReview(
            question_text="Explain heapsort.",
            question_type="open_ended",
            difficulty="hard",
            topic="Sorting",
            language="de",
            review_status=ReviewStatus.APPROVED.value,
            institution_id=aqdf_institution.id,
            created_by=aqdf_user.id,
        )
        q_other = QuestionReview(
            question_text="What is a stack?",
            question_type="open_ended",
            difficulty="easy",
            topic="Data Structures",
            language="de",
            review_status=ReviewStatus.APPROVED.value,
            institution_id=aqdf_institution.id,
            created_by=aqdf_user.id,
        )
        aqdf_db.add_all([q_linked, q_other])
        aqdf_db.flush()
        aqdf_db.add(QuestionSourceDocument(question_id=q_linked.id, document_id=doc.id))
        aqdf_db.commit()

        response = aqdf_client.get(
            f"/api/v1/exams/approved-questions?document_ids={doc.id}"
        )
        assert response.status_code == 200
        data = response.json()
        returned_ids = [q["id"] for q in data["questions"]]
        assert q_linked.id in returned_ids
        assert q_other.id not in returned_ids

    def test_no_document_ids_returns_all_questions(
        self, aqdf_client, aqdf_db, aqdf_institution, aqdf_user
    ):
        q = QuestionReview(
            question_text="What is recursion?",
            question_type="open_ended",
            difficulty="medium",
            topic="Programming",
            language="de",
            review_status=ReviewStatus.APPROVED.value,
            institution_id=aqdf_institution.id,
            created_by=aqdf_user.id,
        )
        aqdf_db.add(q)
        aqdf_db.commit()

        response = aqdf_client.get("/api/v1/exams/approved-questions")
        assert response.status_code == 200
        ids = [x["id"] for x in response.json()["questions"]]
        assert q.id in ids

    def test_filter_by_multiple_document_ids_returns_union(
        self, aqdf_client, aqdf_db, aqdf_institution, aqdf_user
    ):
        """Multi-document filter (?document_ids=1,2 — comma-separated, as
        serialized by ComposerService.listApprovedQuestions) returns the
        UNION of questions linked to any of the requested documents. The
        SQLAlchemy ``IN`` clause is the most likely break point, so verify
        it directly with a multi-doc selection.
        """
        from models.document import Document
        from models.question_review import QuestionSourceDocument

        doc_a = Document(
            filename="a.pdf",
            original_filename="a.pdf",
            file_path="/tmp/a.pdf",
            file_size=1000,
            mime_type="application/pdf",
            institution_id=aqdf_institution.id,
            user_id=aqdf_user.id,
        )
        doc_b = Document(
            filename="b.pdf",
            original_filename="b.pdf",
            file_path="/tmp/b.pdf",
            file_size=1000,
            mime_type="application/pdf",
            institution_id=aqdf_institution.id,
            user_id=aqdf_user.id,
        )
        aqdf_db.add_all([doc_a, doc_b])
        aqdf_db.flush()

        q_a = QuestionReview(
            question_text="Linked to A only",
            question_type="open_ended",
            difficulty="medium",
            topic="A",
            language="de",
            review_status=ReviewStatus.APPROVED.value,
            institution_id=aqdf_institution.id,
            created_by=aqdf_user.id,
        )
        q_b = QuestionReview(
            question_text="Linked to B only",
            question_type="open_ended",
            difficulty="medium",
            topic="B",
            language="de",
            review_status=ReviewStatus.APPROVED.value,
            institution_id=aqdf_institution.id,
            created_by=aqdf_user.id,
        )
        q_neither = QuestionReview(
            question_text="Linked to no document",
            question_type="open_ended",
            difficulty="easy",
            topic="None",
            language="de",
            review_status=ReviewStatus.APPROVED.value,
            institution_id=aqdf_institution.id,
            created_by=aqdf_user.id,
        )
        aqdf_db.add_all([q_a, q_b, q_neither])
        aqdf_db.flush()
        aqdf_db.add_all(
            [
                QuestionSourceDocument(question_id=q_a.id, document_id=doc_a.id),
                QuestionSourceDocument(question_id=q_b.id, document_id=doc_b.id),
            ]
        )
        aqdf_db.commit()

        response = aqdf_client.get(
            f"/api/v1/exams/approved-questions?document_ids={doc_a.id},{doc_b.id}"
        )
        assert response.status_code == 200
        returned_ids = {q["id"] for q in response.json()["questions"]}
        assert q_a.id in returned_ids
        assert q_b.id in returned_ids
        assert q_neither.id not in returned_ids


# ---------------------------------------------------------------------------
# TF-406: Fachfilter-Facetten + Sortierung auf GET /approved-questions
# ---------------------------------------------------------------------------


class TestApprovedQuestionsFacetsAndSort:
    """TF-406: ln_level / competency_id / quality_tier / unused facets and the
    most_used / newest / difficulty sort on GET /approved-questions.

    Rows are scoped by a per-run unique ``topic`` marker so assertions stay
    deterministic against the shared, non-teardown test DB (see the
    ``aqdf`` fixtures above for the same pattern).
    """

    @pytest.fixture
    def aqfs_db(self, test_engine):
        from sqlalchemy.orm import sessionmaker

        TestSession = sessionmaker(bind=test_engine)
        session = TestSession()
        yield session
        session.close()

    @pytest.fixture
    def aqfs_institution(self, aqfs_db):
        existing = aqfs_db.query(Institution).filter_by(slug="aqfs-test-inst").first()
        if existing:
            return existing
        inst = Institution(
            name="AQFS Test University",
            slug="aqfs-test-inst",
            subscription_tier="professional",
            max_users=-1,
            max_documents=-1,
            max_questions_per_month=-1,
        )
        aqfs_db.add(inst)
        aqfs_db.commit()
        aqfs_db.refresh(inst)
        return inst

    @pytest.fixture
    def aqfs_user(self, aqfs_db, aqfs_institution):
        existing = aqfs_db.query(User).filter_by(email="aqfs@test.com").first()
        if existing:
            return existing
        user = User(
            email="aqfs@test.com",
            first_name="AQFS",
            last_name="User",
            password_hash="dummy_hash",  # pragma: allowlist secret
            institution_id=aqfs_institution.id,
            status=UserStatus.ACTIVE.value,
        )
        aqfs_db.add(user)
        aqfs_db.commit()
        aqfs_db.refresh(user)
        return user

    @pytest.fixture
    def aqfs_client(self, aqfs_db, aqfs_institution, aqfs_user):
        from utils.auth_utils import get_current_user
        from database import get_db
        import api.exams as exams_module

        app.include_router(exams_module.router)
        mock_user = _make_mock_user(
            institution_id=aqfs_institution.id, user_id=aqfs_user.id
        )
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: aqfs_db
        client = TestClient(app, raise_server_exceptions=True)
        yield client
        app.dependency_overrides.clear()

    def _make_question(self, db, institution, user, topic, **overrides):
        q = QuestionReview(
            question_text=overrides.pop("question_text", "Frage?"),
            question_type=overrides.pop("question_type", "open_ended"),
            difficulty=overrides.pop("difficulty", "medium"),
            topic=topic,
            language="de",
            review_status=ReviewStatus.APPROVED.value,
            institution_id=institution.id,
            created_by=user.id,
            **overrides,
        )
        db.add(q)
        db.flush()
        return q

    def _use_question(self, db, institution, user, question):
        """Attach the question to an exam once (bumps usage_count)."""
        exam = Exam(
            title=f"Exam for {question.id}",
            institution_id=institution.id,
            created_by=user.id,
        )
        db.add(exam)
        db.flush()
        db.add(
            ExamQuestion(
                exam_id=exam.id, question_id=question.id, position=1, points=1.0
            )
        )
        db.flush()

    def test_filter_by_ln_level(
        self, aqfs_client, aqfs_db, aqfs_institution, aqfs_user
    ):
        import uuid

        topic = f"ln-{uuid.uuid4().hex}"
        q2 = self._make_question(
            aqfs_db, aqfs_institution, aqfs_user, topic, ln_level=2
        )
        q4 = self._make_question(
            aqfs_db, aqfs_institution, aqfs_user, topic, ln_level=4
        )
        aqfs_db.commit()

        resp = aqfs_client.get(
            f"/api/v1/exams/approved-questions?topic={topic}&ln_level=2"
        )
        assert resp.status_code == 200
        ids = {q["id"] for q in resp.json()["questions"]}
        assert ids == {q2.id}
        assert q4.id not in ids

    def test_filter_by_quality_tier(
        self, aqfs_client, aqfs_db, aqfs_institution, aqfs_user
    ):
        import uuid

        topic = f"qt-{uuid.uuid4().hex}"
        q_a = self._make_question(
            aqfs_db, aqfs_institution, aqfs_user, topic, quality_tier="A"
        )
        q_b = self._make_question(
            aqfs_db, aqfs_institution, aqfs_user, topic, quality_tier="B"
        )
        aqfs_db.commit()

        resp = aqfs_client.get(
            f"/api/v1/exams/approved-questions?topic={topic}&quality_tier=A"
        )
        assert resp.status_code == 200
        ids = {q["id"] for q in resp.json()["questions"]}
        assert ids == {q_a.id}
        assert q_b.id not in ids

    def test_filter_by_competency_id(
        self, aqfs_client, aqfs_db, aqfs_institution, aqfs_user
    ):
        import uuid

        from models.competency import CompetencyFramework, Competency

        topic = f"comp-{uuid.uuid4().hex}"
        fw = CompetencyFramework(
            name=f"Modul {topic}",
            rendered_text="HKB Text",
            institution_id=aqfs_institution.id,
            created_by=aqfs_user.id,
        )
        aqfs_db.add(fw)
        aqfs_db.flush()
        comp = Competency(framework_id=fw.id, code="B3", title="Handlungskompetenz B3")
        aqfs_db.add(comp)
        aqfs_db.flush()

        q_with = self._make_question(
            aqfs_db, aqfs_institution, aqfs_user, topic, competency_id=comp.id
        )
        q_without = self._make_question(aqfs_db, aqfs_institution, aqfs_user, topic)
        aqfs_db.commit()

        resp = aqfs_client.get(
            f"/api/v1/exams/approved-questions?topic={topic}&competency_id={comp.id}"
        )
        assert resp.status_code == 200
        ids = {q["id"] for q in resp.json()["questions"]}
        assert ids == {q_with.id}
        assert q_without.id not in ids

    def test_filter_unused_returns_only_zero_usage(
        self, aqfs_client, aqfs_db, aqfs_institution, aqfs_user
    ):
        import uuid

        topic = f"unused-{uuid.uuid4().hex}"
        q_used = self._make_question(aqfs_db, aqfs_institution, aqfs_user, topic)
        q_unused = self._make_question(aqfs_db, aqfs_institution, aqfs_user, topic)
        self._use_question(aqfs_db, aqfs_institution, aqfs_user, q_used)
        aqfs_db.commit()

        resp = aqfs_client.get(
            f"/api/v1/exams/approved-questions?topic={topic}&unused=true"
        )
        assert resp.status_code == 200
        questions = resp.json()["questions"]
        ids = {q["id"] for q in questions}
        assert ids == {q_unused.id}
        assert q_used.id not in ids
        # Every returned question is genuinely unused.
        assert all(q["usage_count"] == 0 for q in questions)

    def test_combined_facets_are_anded(
        self, aqfs_client, aqfs_db, aqfs_institution, aqfs_user
    ):
        import uuid

        topic = f"and-{uuid.uuid4().hex}"
        q_both = self._make_question(
            aqfs_db, aqfs_institution, aqfs_user, topic, ln_level=3, quality_tier="B"
        )
        q_ln_only = self._make_question(
            aqfs_db, aqfs_institution, aqfs_user, topic, ln_level=3, quality_tier="A"
        )
        q_tier_only = self._make_question(
            aqfs_db, aqfs_institution, aqfs_user, topic, ln_level=1, quality_tier="B"
        )
        aqfs_db.commit()

        resp = aqfs_client.get(
            f"/api/v1/exams/approved-questions?topic={topic}&ln_level=3&quality_tier=B"
        )
        assert resp.status_code == 200
        ids = {q["id"] for q in resp.json()["questions"]}
        assert ids == {q_both.id}
        assert q_ln_only.id not in ids
        assert q_tier_only.id not in ids

    def test_sort_most_used_orders_by_usage_desc(
        self, aqfs_client, aqfs_db, aqfs_institution, aqfs_user
    ):
        import uuid

        topic = f"mostused-{uuid.uuid4().hex}"
        q_high = self._make_question(aqfs_db, aqfs_institution, aqfs_user, topic)
        q_low = self._make_question(aqfs_db, aqfs_institution, aqfs_user, topic)
        q_zero = self._make_question(aqfs_db, aqfs_institution, aqfs_user, topic)
        self._use_question(aqfs_db, aqfs_institution, aqfs_user, q_high)
        self._use_question(aqfs_db, aqfs_institution, aqfs_user, q_high)
        self._use_question(aqfs_db, aqfs_institution, aqfs_user, q_low)
        aqfs_db.commit()

        resp = aqfs_client.get(
            f"/api/v1/exams/approved-questions?topic={topic}&sort=most_used"
        )
        assert resp.status_code == 200
        ordered_ids = [q["id"] for q in resp.json()["questions"]]
        assert ordered_ids == [q_high.id, q_low.id, q_zero.id]

    def test_sort_most_used_tiebreak_is_newest_first(
        self, aqfs_client, aqfs_db, aqfs_institution, aqfs_user
    ):
        """Equal usage falls back to created_at DESC (newest first).

        created_at must be set explicitly: PostgreSQL ``now()`` returns the
        transaction-start timestamp, so rows committed together would share an
        identical created_at and leave the tie-break order undefined.
        """
        import uuid
        from datetime import datetime

        topic = f"mostused-tie-{uuid.uuid4().hex}"
        q_older = self._make_question(
            aqfs_db,
            aqfs_institution,
            aqfs_user,
            topic,
            created_at=datetime(2024, 1, 1, 12, 0, 0),
        )
        q_newer = self._make_question(
            aqfs_db,
            aqfs_institution,
            aqfs_user,
            topic,
            created_at=datetime(2024, 6, 1, 12, 0, 0),
        )
        # Identical usage count (1 each) so only the created_at tie-break decides.
        self._use_question(aqfs_db, aqfs_institution, aqfs_user, q_older)
        self._use_question(aqfs_db, aqfs_institution, aqfs_user, q_newer)
        aqfs_db.commit()

        resp = aqfs_client.get(
            f"/api/v1/exams/approved-questions?topic={topic}&sort=most_used"
        )
        assert resp.status_code == 200
        ordered_ids = [q["id"] for q in resp.json()["questions"]]
        assert ordered_ids == [q_newer.id, q_older.id]

    def test_unused_combined_with_most_used_sort(
        self, aqfs_client, aqfs_db, aqfs_institution, aqfs_user
    ):
        """unused=true + sort=most_used: only zero-usage rows, newest first.

        Both facets touch ExamQuestion (NOT EXISTS filter vs. grouped usage
        outerjoin); this pins that they compose without dropping or duplicating
        rows. created_at is explicit for a deterministic tie-break (all usages
        are 0, so coalesce(uses, 0) ties and created_at DESC decides).
        """
        import uuid
        from datetime import datetime

        topic = f"unused-mostused-{uuid.uuid4().hex}"
        q_used = self._make_question(aqfs_db, aqfs_institution, aqfs_user, topic)
        q_unused_old = self._make_question(
            aqfs_db,
            aqfs_institution,
            aqfs_user,
            topic,
            created_at=datetime(2024, 1, 1, 12, 0, 0),
        )
        q_unused_new = self._make_question(
            aqfs_db,
            aqfs_institution,
            aqfs_user,
            topic,
            created_at=datetime(2024, 6, 1, 12, 0, 0),
        )
        self._use_question(aqfs_db, aqfs_institution, aqfs_user, q_used)
        aqfs_db.commit()

        resp = aqfs_client.get(
            f"/api/v1/exams/approved-questions?topic={topic}&unused=true&sort=most_used"
        )
        assert resp.status_code == 200
        questions = resp.json()["questions"]
        ordered_ids = [q["id"] for q in questions]
        assert ordered_ids == [q_unused_new.id, q_unused_old.id]
        assert q_used.id not in ordered_ids
        assert all(q["usage_count"] == 0 for q in questions)

    def test_sort_difficulty_orders_easy_to_hard(
        self, aqfs_client, aqfs_db, aqfs_institution, aqfs_user
    ):
        import uuid

        topic = f"diff-{uuid.uuid4().hex}"
        q_hard = self._make_question(
            aqfs_db, aqfs_institution, aqfs_user, topic, difficulty="hard"
        )
        q_easy = self._make_question(
            aqfs_db, aqfs_institution, aqfs_user, topic, difficulty="easy"
        )
        q_medium = self._make_question(
            aqfs_db, aqfs_institution, aqfs_user, topic, difficulty="medium"
        )
        aqfs_db.commit()

        resp = aqfs_client.get(
            f"/api/v1/exams/approved-questions?topic={topic}&sort=difficulty"
        )
        assert resp.status_code == 200
        ordered = [q["difficulty"] for q in resp.json()["questions"]]
        assert ordered == ["easy", "medium", "hard"]
        ids = [q["id"] for q in resp.json()["questions"]]
        assert ids == [q_easy.id, q_medium.id, q_hard.id]

    def test_default_sort_accepts_no_sort_param(
        self, aqfs_client, aqfs_db, aqfs_institution, aqfs_user
    ):
        import uuid

        topic = f"default-{uuid.uuid4().hex}"
        self._make_question(aqfs_db, aqfs_institution, aqfs_user, topic)
        aqfs_db.commit()

        resp = aqfs_client.get(f"/api/v1/exams/approved-questions?topic={topic}")
        assert resp.status_code == 200
        assert len(resp.json()["questions"]) == 1

    def test_invalid_sort_returns_422(self, aqfs_client):
        resp = aqfs_client.get("/api/v1/exams/approved-questions?sort=bogus")
        assert resp.status_code == 422

    def test_invalid_quality_tier_returns_422(self, aqfs_client):
        resp = aqfs_client.get("/api/v1/exams/approved-questions?quality_tier=Z")
        assert resp.status_code == 422

    def test_invalid_ln_level_returns_422(self, aqfs_client):
        resp = aqfs_client.get("/api/v1/exams/approved-questions?ln_level=5")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Task 8: document_ids filter on POST /{exam_id}/auto-fill
# ---------------------------------------------------------------------------


class TestAutoFillDocumentFilter:
    """Tests that auto-fill respects document_ids filter."""

    @pytest.fixture
    def afdf_db(self, test_engine):
        from sqlalchemy.orm import sessionmaker

        TestSession = sessionmaker(bind=test_engine)
        session = TestSession()
        yield session
        session.close()

    @pytest.fixture
    def afdf_institution(self, afdf_db):
        existing = afdf_db.query(Institution).filter_by(slug="afdf-test-inst").first()
        if existing:
            return existing
        inst = Institution(
            name="AFDF Test University",
            slug="afdf-test-inst",
            subscription_tier="professional",
            max_users=-1,
            max_documents=-1,
            max_questions_per_month=-1,
        )
        afdf_db.add(inst)
        afdf_db.commit()
        afdf_db.refresh(inst)
        return inst

    @pytest.fixture
    def afdf_user(self, afdf_db, afdf_institution):
        existing = afdf_db.query(User).filter_by(email="afdf@test.com").first()
        if existing:
            return existing
        user = User(
            email="afdf@test.com",
            first_name="AFDF",
            last_name="User",
            password_hash="dummy_hash",  # pragma: allowlist secret
            institution_id=afdf_institution.id,
            status=UserStatus.ACTIVE.value,
        )
        afdf_db.add(user)
        afdf_db.commit()
        afdf_db.refresh(user)
        return user

    @pytest.fixture
    def afdf_client(self, afdf_db, afdf_institution, afdf_user):
        from utils.auth_utils import get_current_user
        from database import get_db
        import api.exams as exams_module

        app.include_router(exams_module.router)
        mock_user = _make_mock_user(
            institution_id=afdf_institution.id, user_id=afdf_user.id
        )
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: afdf_db
        client = TestClient(app, raise_server_exceptions=True)
        yield client
        app.dependency_overrides.clear()

    def test_auto_fill_respects_document_ids(
        self, afdf_client, afdf_db, afdf_institution, afdf_user
    ):
        from models.document import Document
        from models.question_review import QuestionSourceDocument

        doc = Document(
            filename="os.pdf",
            original_filename="os.pdf",
            file_path="/tmp/os.pdf",
            file_size=1000,
            mime_type="application/pdf",
            institution_id=afdf_institution.id,
            user_id=afdf_user.id,
        )
        afdf_db.add(doc)
        afdf_db.flush()

        exam = Exam(
            title="OS Exam",
            institution_id=afdf_institution.id,
            created_by=afdf_user.id,
        )
        afdf_db.add(exam)
        afdf_db.flush()

        q_linked = QuestionReview(
            question_text="What is a process?",
            question_type="open_ended",
            difficulty="medium",
            topic="OS",
            language="de",
            review_status=ReviewStatus.APPROVED.value,
            institution_id=afdf_institution.id,
            created_by=afdf_user.id,
            estimated_time_minutes=5,
        )
        q_other = QuestionReview(
            question_text="What is a binary tree?",
            question_type="open_ended",
            difficulty="medium",
            topic="Data Structures",
            language="de",
            review_status=ReviewStatus.APPROVED.value,
            institution_id=afdf_institution.id,
            created_by=afdf_user.id,
            estimated_time_minutes=5,
        )
        afdf_db.add_all([q_linked, q_other])
        afdf_db.flush()
        afdf_db.add(QuestionSourceDocument(question_id=q_linked.id, document_id=doc.id))
        afdf_db.commit()

        response = afdf_client.post(
            f"/api/v1/exams/{exam.id}/auto-fill",
            json={"count": 10, "document_ids": [doc.id]},
        )
        assert response.status_code == 200
        added_ids = [eq["question_id"] for eq in response.json()["questions"]]
        assert q_linked.id in added_ids
        assert q_other.id not in added_ids


# ---------------------------------------------------------------------------
# TF-405: GET /approved-questions/{id} — read-only detail for the preview
# ---------------------------------------------------------------------------


class TestApprovedQuestionDetail(
    _make_exam_test_class_fixtures("tf405-aqdetail-uni", "tf405-aqdetail@test.com")
):
    """Detail endpoint: marks the correct solution, exposes explanation/source/LN,
    is tenant-scoped, and never leaks foreign institutions."""

    def _make_question(self, db, institution_id, user_id, **overrides):
        fields = dict(
            question_text="Welcher Sortieralgorithmus ist O(n log n)?",
            question_type="single_choice",
            difficulty="medium",
            topic="Sortieren",
            language="de",
            review_status=ReviewStatus.APPROVED.value,
            options=["Bubblesort", "Heapsort", "Selectionsort", "Insertionsort"],
            correct_answer="Heapsort",
            explanation="Heapsort garantiert O(n log n) im Worst Case.",
            bloom_level=2,
            ln_level=3,
            estimated_time_minutes=4,
            institution_id=institution_id,
            created_by=user_id,
        )
        fields.update(overrides)
        q = QuestionReview(**fields)
        db.add(q)
        db.commit()
        db.refresh(q)
        return q

    def test_detail_marks_correct_option_and_exposes_explanation(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """Happy path: full text, correct option flagged, explanation + LN/Bloom."""
        q = self._make_question(exam_db, exam_institution.id, exam_user.id)

        response = exam_client.get(f"/api/v1/exams/approved-questions/{q.id}")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == q.id
        assert data["question_text"] == q.question_text
        assert data["correct_answer"] == "Heapsort"
        assert data["explanation"] == "Heapsort garantiert O(n log n) im Worst Case."
        assert data["bloom_level"] == 2
        assert data["ln_level"] == 3
        assert data["estimated_time_minutes"] == 4

        # Exactly the correct option is flagged.
        correct = [o for o in data["options"] if o["is_correct"]]
        assert len(correct) == 1
        assert correct[0]["text"] == "Heapsort"
        assert {o["text"] for o in data["options"]} == set(q.options)
        assert all(
            o["is_correct"] == (o["text"] == "Heapsort") for o in data["options"]
        )

    def test_detail_open_ended_returns_musterloesung_without_options(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """Open questions carry the model solution in correct_answer, no options."""
        q = self._make_question(
            exam_db,
            exam_institution.id,
            exam_user.id,
            question_type="open_ended",
            options=None,
            correct_answer="Eine Musterlösung in Prosa.",
        )

        response = exam_client.get(f"/api/v1/exams/approved-questions/{q.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["options"] == []
        assert data["correct_answer"] == "Eine Musterlösung in Prosa."

    def test_detail_includes_source_documents(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """Linked source documents are surfaced via the join table."""
        from models.document import Document
        from models.question_review import QuestionSourceDocument

        q = self._make_question(exam_db, exam_institution.id, exam_user.id)
        doc = Document(
            filename="algorithmen.pdf",
            original_filename="algorithmen.pdf",
            file_path="/tmp/algorithmen.pdf",
            file_size=2048,
            mime_type="application/pdf",
            institution_id=exam_institution.id,
            user_id=exam_user.id,
        )
        exam_db.add(doc)
        exam_db.flush()
        exam_db.add(QuestionSourceDocument(question_id=q.id, document_id=doc.id))
        exam_db.commit()

        response = exam_client.get(f"/api/v1/exams/approved-questions/{q.id}")
        assert response.status_code == 200
        docs = response.json()["source_documents"]
        assert any(d["id"] == doc.id for d in docs)

    def test_detail_404_for_missing(self, exam_client):
        """Unknown id → 404."""
        response = exam_client.get("/api/v1/exams/approved-questions/999999")
        assert response.status_code == 404

    def test_detail_previews_non_approved_question(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """A non-approved question in the tenant is previewable — a question that
        is part of an exam can later transition to ``edited``/``pending`` and
        must still remain previewable (the approval gating only applies to
        the list)."""
        q = self._make_question(
            exam_db,
            exam_institution.id,
            exam_user.id,
            review_status=ReviewStatus.PENDING.value,
        )
        response = exam_client.get(f"/api/v1/exams/approved-questions/{q.id}")
        assert response.status_code == 200
        assert response.json()["id"] == q.id

    def test_detail_previews_archived_question(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """An archived question already in an exam stays previewable (read-only)."""
        from datetime import datetime, timezone

        q = self._make_question(
            exam_db,
            exam_institution.id,
            exam_user.id,
            archived_at=datetime.now(timezone.utc),
        )
        response = exam_client.get(f"/api/v1/exams/approved-questions/{q.id}")
        assert response.status_code == 200
        assert response.json()["id"] == q.id

    def test_detail_tenant_isolation_returns_404(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """A question of a foreign institution is indistinguishable from a missing
        one (404, not 403) — no existence leak across tenants."""
        from utils.auth_utils import get_current_user

        q = self._make_question(exam_db, exam_institution.id, exam_user.id)

        # Non-superuser in a different institution must not see the question.
        foreign_user = _make_mock_user(
            institution_id=exam_institution.id + 99999, user_id=exam_user.id + 99999
        )
        foreign_user.is_superuser = False
        app.dependency_overrides[get_current_user] = lambda: foreign_user

        response = exam_client.get(f"/api/v1/exams/approved-questions/{q.id}")
        assert response.status_code == 404

    def test_list_endpoint_stays_slim(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """TF-405 contract: the 50-row list must NOT carry the heavy detail fields."""
        self._make_question(exam_db, exam_institution.id, exam_user.id)

        response = exam_client.get("/api/v1/exams/approved-questions")
        assert response.status_code == 200
        questions = response.json()["questions"]
        assert questions, "expected at least one approved question"
        for q in questions:
            assert "correct_answer" not in q
            assert "explanation" not in q
            assert "source_documents" not in q
            assert "competency" not in q


class TestExamGradingSchemeEndpoint:
    """PATCH /api/v1/exams/{id}/grading-scheme — the dedicated reassignment
    endpoint the TF-432 frontend wires into the Notenexport panel. Unlike PUT
    it must work on finalized exams (bypasses the draft guard)."""

    @pytest.fixture
    def gs_db(self, test_engine):
        yield from _make_committable_session(
            test_engine, slug="gs-assign-university", email="gsassign@test.com"
        )

    @pytest.fixture
    def gs_institution(self, gs_db):
        from models.auth import Institution

        existing = (
            gs_db.query(Institution).filter_by(slug="gs-assign-university").first()
        )
        if existing:
            return existing
        inst = Institution(
            name="GS Assign University",
            slug="gs-assign-university",
            subscription_tier="professional",
            max_users=-1,
            max_documents=-1,
            max_questions_per_month=-1,
        )
        gs_db.add(inst)
        gs_db.commit()
        gs_db.refresh(inst)
        return inst

    @pytest.fixture
    def gs_user(self, gs_db, gs_institution):
        from models.auth import User, UserStatus

        existing = gs_db.query(User).filter_by(email="gsassign@test.com").first()
        if existing:
            return existing
        user = User(
            email="gsassign@test.com",
            first_name="GS",
            last_name="Assign",
            password_hash="dummy_hash",  # pragma: allowlist secret
            institution_id=gs_institution.id,
            status=UserStatus.ACTIVE.value,
        )
        gs_db.add(user)
        gs_db.commit()
        gs_db.refresh(user)
        return user

    @pytest.fixture
    def swiss_scheme(self, gs_db):
        from models.grading_scheme import GradingScheme

        existing = (
            gs_db.query(GradingScheme)
            .filter_by(institution_id=None, name="Swiss TF432")
            .first()
        )
        if existing:
            return existing
        scheme = GradingScheme(
            institution_id=None,
            name="Swiss TF432",
            display_format="numeric",
            config={
                "type": "linear_segments",
                "round_to": 0.1,
                "segments": [
                    {"from_pct": 0, "to_pct": 50, "from_grade": 1.0, "to_grade": 4.0},
                    {"from_pct": 50, "to_pct": 100, "from_grade": 4.0, "to_grade": 6.0},
                ],
            },
            is_default_for_institution=False,
        )
        gs_db.add(scheme)
        gs_db.commit()
        gs_db.refresh(scheme)
        return scheme

    @pytest.fixture
    def mock_user(self, gs_institution, gs_user):
        return _make_mock_user(institution_id=gs_institution.id, user_id=gs_user.id)

    @pytest.fixture
    def gs_client(self, gs_db, gs_institution, mock_user):
        from utils.auth_utils import get_current_user
        from database import get_db
        import api.exams as exams_module

        app.include_router(exams_module.router)

        def override_get_db():
            yield gs_db

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app, raise_server_exceptions=True)
        yield client
        app.dependency_overrides.clear()

    def _finalized_exam(self, gs_client, gs_db) -> int:
        from models.exam import Exam, ExamStatus

        resp = gs_client.post("/api/v1/exams/", json={"title": "Importierte Prüfung"})
        assert resp.status_code == 201, resp.text
        exam_id = resp.json()["id"]
        # Mark finalized directly — the dedicated PATCH must work post-finalize,
        # which is exactly the imported-exam case the frontend targets.
        exam = gs_db.query(Exam).filter(Exam.id == exam_id).one()
        exam.status = ExamStatus.FINALIZED.value
        gs_db.commit()
        return exam_id

    def _updated_at(self, gs_client, exam_id: int) -> str:
        return gs_client.get(f"/api/v1/exams/{exam_id}").json()["updated_at"]

    def test_assign_system_scheme_to_finalized_exam(
        self, gs_client, gs_db, swiss_scheme
    ):
        exam_id = self._finalized_exam(gs_client, gs_db)
        resp = gs_client.patch(
            f"/api/v1/exams/{exam_id}/grading-scheme",
            json={
                "grading_scheme_id": swiss_scheme.id,
                "updated_at": self._updated_at(gs_client, exam_id),
            },
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["grading_scheme_id"] == swiss_scheme.id
        get_resp = gs_client.get(f"/api/v1/exams/{exam_id}")
        assert get_resp.json()["grading_scheme_id"] == swiss_scheme.id

    def test_clear_scheme_with_null(self, gs_client, gs_db, swiss_scheme):
        exam_id = self._finalized_exam(gs_client, gs_db)
        assigned = gs_client.patch(
            f"/api/v1/exams/{exam_id}/grading-scheme",
            json={
                "grading_scheme_id": swiss_scheme.id,
                "updated_at": self._updated_at(gs_client, exam_id),
            },
        )
        assert assigned.status_code == 200, assigned.text
        resp = gs_client.patch(
            f"/api/v1/exams/{exam_id}/grading-scheme",
            json={
                "grading_scheme_id": None,
                "updated_at": assigned.json()["updated_at"],
            },
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["grading_scheme_id"] is None

    def test_invalid_scheme_rejected_with_422(self, gs_client, gs_db):
        exam_id = self._finalized_exam(gs_client, gs_db)
        resp = gs_client.patch(
            f"/api/v1/exams/{exam_id}/grading-scheme",
            json={
                "grading_scheme_id": 999999,
                "updated_at": self._updated_at(gs_client, exam_id),
            },
        )
        assert resp.status_code == 422, resp.text

    def test_stale_updated_at_returns_409(self, gs_client, gs_db, swiss_scheme):
        exam_id = self._finalized_exam(gs_client, gs_db)
        stale = gs_client.get(f"/api/v1/exams/{exam_id}").json()["updated_at"]
        first = gs_client.patch(
            f"/api/v1/exams/{exam_id}/grading-scheme",
            json={"grading_scheme_id": swiss_scheme.id, "updated_at": stale},
        )
        assert first.status_code == 200, first.text
        second = gs_client.patch(
            f"/api/v1/exams/{exam_id}/grading-scheme",
            json={"grading_scheme_id": None, "updated_at": stale},
        )
        assert second.status_code == 409, second.text

    def test_audit_log_entry_written(self, gs_client, gs_db, swiss_scheme):
        import json

        from models.auth import AuditLog

        exam_id = self._finalized_exam(gs_client, gs_db)
        gs_client.patch(
            f"/api/v1/exams/{exam_id}/grading-scheme",
            json={
                "grading_scheme_id": swiss_scheme.id,
                "updated_at": self._updated_at(gs_client, exam_id),
            },
        )
        entry = (
            gs_db.query(AuditLog)
            .filter(
                AuditLog.action == "update_exam_grading_scheme",
                AuditLog.resource_id == str(exam_id),
            )
            .first()
        )
        assert entry is not None
        # The docstring promises the change is "reconstructable" — the payload
        # is the load-bearing part, so assert it carries the before/after ids
        # and the exam status, not just that *some* row exists.
        payload = json.loads(entry.additional_data)
        assert payload["previous_grading_scheme_id"] is None
        assert payload["new_grading_scheme_id"] == swiss_scheme.id
        assert payload["exam_status"] == "finalized"

    def test_cross_institution_scheme_rejected_with_422(
        self, gs_client, gs_db, gs_institution
    ):
        """An institution-scoped scheme owned by *another* institution must be
        rejected with 422 — the actual tenant-isolation guard, distinct from
        the non-existent-id (999999) case. 404 would leak the scheme's
        existence to a caller in an unrelated institution."""
        from models.auth import Institution
        from models.grading_scheme import GradingScheme

        other_inst = Institution(
            name="Other GS Institution",
            slug="gs-assign-other-institution",
            subscription_tier="professional",
            max_users=-1,
            max_documents=-1,
            max_questions_per_month=-1,
        )
        gs_db.add(other_inst)
        gs_db.commit()
        gs_db.refresh(other_inst)
        foreign_scheme = GradingScheme(
            institution_id=other_inst.id,
            name="Foreign Scheme TF432",
            display_format="numeric",
            config={
                "type": "linear",
                "min_pct": 0,
                "max_pct": 100,
                "min_grade": 1.0,
                "max_grade": 6.0,
            },
            is_default_for_institution=False,
        )
        gs_db.add(foreign_scheme)
        gs_db.commit()
        gs_db.refresh(foreign_scheme)

        exam_id = self._finalized_exam(gs_client, gs_db)
        resp = gs_client.patch(
            f"/api/v1/exams/{exam_id}/grading-scheme",
            json={
                "grading_scheme_id": foreign_scheme.id,
                "updated_at": self._updated_at(gs_client, exam_id),
            },
        )
        assert resp.status_code == 422, resp.text

    def test_missing_updated_at_rejected_with_422(self, gs_client, gs_db, swiss_scheme):
        """``updated_at`` is required (optimistic-lock contract); omitting it is
        a 422 from Pydantic, not a silent skip of the lock."""
        exam_id = self._finalized_exam(gs_client, gs_db)
        resp = gs_client.patch(
            f"/api/v1/exams/{exam_id}/grading-scheme",
            json={"grading_scheme_id": swiss_scheme.id},
        )
        assert resp.status_code == 422, resp.text
