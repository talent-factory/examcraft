"""
Tests for Exam Composer Models: Exam, ExamQuestion, ExamStatus
TDD: These tests are written before the model implementation.
"""

from sqlalchemy.orm import Session

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
