"""
Tests for Exam Composer Models: Exam, ExamQuestion, ExamStatus
TDD: These tests are written before the model implementation.
"""

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
        """Fresh DB session that supports commit/rollback (no wrapping transaction).

        test_db uses a connection-level transaction which prevents commit()
        inside the API endpoints. This fixture creates a plain session instead.
        """
        from sqlalchemy.orm import sessionmaker

        TestSession = sessionmaker(bind=test_engine)
        session = TestSession()
        yield session
        session.close()

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

    def test_delete_draft_exam(self, exam_client):
        """DELETE /api/v1/exams/{id} deletes a draft exam (status 204)."""
        create_resp = exam_client.post("/api/v1/exams/", json={"title": "To Delete"})
        exam_id = create_resp.json()["id"]

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


# ---------------------------------------------------------------------------
# Task 3: Question Management API Tests
# ---------------------------------------------------------------------------


class TestExamQuestionApi:
    """Tests for exam question management endpoints — add, update, remove, reorder."""

    @pytest.fixture
    def exam_db(self, test_engine):
        """Fresh DB session that supports commit/rollback (no wrapping transaction)."""
        from sqlalchemy.orm import sessionmaker

        TestSession = sessionmaker(bind=test_engine)
        session = TestSession()
        yield session
        session.close()

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
        question_type="multiple_choice",
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

        # Create approved question (multiple_choice + medium => 4 pts)
        q = self._create_approved_question(
            exam_db,
            exam_institution.id,
            exam_user.id,
            question_type="multiple_choice",
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
        """Fresh DB session that supports commit/rollback (no wrapping transaction)."""
        from sqlalchemy.orm import sessionmaker

        TestSession = sessionmaker(bind=test_engine)
        session = TestSession()
        yield session
        session.close()

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
        question_type="multiple_choice",
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
            options=["A", "B", "C", "D"]
            if question_type == "multiple_choice"
            else None,
            correct_answer="A" if question_type == "multiple_choice" else None,
            explanation="A is correct." if question_type == "multiple_choice" else None,
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
        assert "empty" in response.json()["detail"].lower()

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
            from sqlalchemy.orm import sessionmaker

            TestSession = sessionmaker(bind=test_engine)
            session = TestSession()
            yield session
            session.close()

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
            question_type="multiple_choice",
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
                if question_type == "multiple_choice"
                else None,
                correct_answer="A" if question_type == "multiple_choice" else None,
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
        assert "draft" in response.json()["detail"].lower()

    def test_delete_exam_404(self, exam_client):
        """DELETE /api/v1/exams/{id} returns 404 for non-existent exam."""
        response = exam_client.delete("/api/v1/exams/999999")
        assert response.status_code == 404

    def test_delete_non_draft_exam_returns_400(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """DELETE /api/v1/exams/{id} returns 400 when exam is finalized."""
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
        assert response.status_code == 400

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
        assert "999999" in response.json()["detail"]

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
            question_type="multiple_choice",
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
        assert "No matching questions" in response.json()["detail"]

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
        assert str(q.id) in detail or "no longer approved" in detail.lower()

    def test_unfinalize_already_draft_returns_400(self, exam_client):
        """POST /{exam_id}/unfinalize returns 400 if exam is already a draft."""
        create_resp = exam_client.post(
            "/api/v1/exams/", json={"title": "Draft Unfinalize"}
        )
        exam_id = create_resp.json()["id"]

        response = exam_client.post(f"/api/v1/exams/{exam_id}/unfinalize")
        assert response.status_code == 400
        assert "already a draft" in response.json()["detail"].lower()

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
        """Helper: create exam + finalize with one approved MC question."""
        create_resp = client.post("/api/v1/exams/", json={"title": title})
        assert create_resp.status_code == 201
        exam_id = create_resp.json()["id"]

        q = self._create_approved_question(db, institution_id, user_id)
        client.post(
            f"/api/v1/exams/{exam_id}/questions",
            json={"question_ids": [q.id]},
        )
        return exam_id

    def test_export_empty_exam_returns_400(self, exam_client):
        """GET /export/md returns 400 for an exam with no questions."""
        create_resp = exam_client.post("/api/v1/exams/", json={"title": "Empty Export"})
        exam_id = create_resp.json()["id"]

        response = exam_client.get(f"/api/v1/exams/{exam_id}/export/md")
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_export_unsupported_format_returns_400(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """GET /export/pdf (unsupported) returns 400."""
        exam_id = self._create_exam_with_question(
            exam_client, exam_db, exam_institution.id, exam_user.id
        )
        response = exam_client.get(f"/api/v1/exams/{exam_id}/export/pdf")
        assert response.status_code == 400
        assert "pdf" in response.json()["detail"].lower()

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
        assert "_solutions.md" in response.headers["content-disposition"]
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
        exam_id = self._create_exam_with_question(
            exam_client,
            exam_db,
            exam_institution.id,
            exam_user.id,
            title="Status Export",
        )
        # Finalize first
        fin_resp = exam_client.post(f"/api/v1/exams/{exam_id}/finalize")
        assert fin_resp.status_code == 200
        assert fin_resp.json()["status"] == "finalized"

        # Export
        export_resp = exam_client.get(f"/api/v1/exams/{exam_id}/export/md")
        assert export_resp.status_code == 200

        # Status should now be 'exported'
        detail = exam_client.get(f"/api/v1/exams/{exam_id}").json()
        assert detail["status"] == "exported"

    def test_export_draft_exam_does_not_change_status(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """Exporting a draft exam does not change its status (still draft)."""
        exam_id = self._create_exam_with_question(
            exam_client,
            exam_db,
            exam_institution.id,
            exam_user.id,
            title="Draft Export Status",
        )
        # Export without finalizing
        exam_client.get(f"/api/v1/exams/{exam_id}/export/json")

        detail = exam_client.get(f"/api/v1/exams/{exam_id}").json()
        # Status stays 'draft' since it was never finalized
        assert detail["status"] == "draft"

    def test_export_404_non_existent_exam(self, exam_client):
        """GET /export/md returns 404 for a non-existent exam."""
        response = exam_client.get("/api/v1/exams/999999/export/md")
        assert response.status_code == 404
