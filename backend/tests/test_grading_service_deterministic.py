"""Tests for DeterministicGrader. Pure unit tests, no DB."""

from __future__ import annotations

import pytest

from services.grading.deterministic_grader import DeterministicGrader, GradeOutcome


@pytest.fixture
def grader() -> DeterministicGrader:
    return DeterministicGrader()


# ---------------------------------------------------------------------------
# Multiple Choice
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "given,correct,is_correct",
    [
        ("A", "A", True),
        ("a", "A", True),  # case-insensitive
        ("Berlin", "berlin", True),
        ("  Berlin  ", "Berlin", True),  # trim
        ("A", "B", False),
        ("Wien", "Berlin", False),
    ],
)
def test_multiple_choice_basic(
    grader: DeterministicGrader, given: str, correct: str, is_correct: bool
) -> None:
    outcome = grader.grade(
        question_type="multiple_choice",
        given_answer=given,
        correct_answer=correct,
        points_max=4.0,
    )
    assert outcome.is_correct is is_correct
    assert outcome.points_awarded == (4.0 if is_correct else 0.0)
    assert outcome.points_max == 4.0
    assert outcome.status == "proposed"


def test_multiple_choice_empty_given_answer_is_wrong(
    grader: DeterministicGrader,
) -> None:
    outcome = grader.grade(
        question_type="multiple_choice",
        given_answer=None,
        correct_answer="A",
        points_max=2.0,
    )
    assert outcome.is_correct is False
    assert outcome.points_awarded == 0.0


def test_multiple_choice_missing_correct_answer_is_wrong(
    grader: DeterministicGrader,
) -> None:
    outcome = grader.grade(
        question_type="multiple_choice",
        given_answer="A",
        correct_answer=None,
        points_max=2.0,
    )
    assert outcome.is_correct is False


@pytest.mark.parametrize(
    "given,correct",
    [
        # Real Moodle exports emit option as "letter) text", question
        # bank stores the canonical text. The most common production
        # failure mode pre-fix was every MC silently scored 0.
        ("B) Bern", "Bern"),
        ("Bern", "B) Bern"),
        ("a. Zürich", "Zürich"),
        ("(C) Genf", "Genf"),
        ("[D] Basel", "Basel"),
        ("A: Zürich", "Zürich"),
        # Stripping is symmetric
        ("B) Bern", "b) Bern"),
    ],
)
def test_multiple_choice_letter_prefix_tolerance(
    grader: DeterministicGrader, given: str, correct: str
) -> None:
    outcome = grader.grade(
        question_type="multiple_choice",
        given_answer=given,
        correct_answer=correct,
        points_max=4.0,
    )
    assert outcome.is_correct is True
    assert outcome.points_awarded == 4.0


def test_multiple_choice_letter_prefix_does_not_match_unrelated(
    grader: DeterministicGrader,
) -> None:
    """``B) Bern`` must not match ``A) Bern`` once stripped — different
    options that happen to have the same canonical text are still the
    same answer; but ``B) Bern`` must NOT match ``A) Zürich``."""
    outcome = grader.grade(
        question_type="multiple_choice",
        given_answer="B) Bern",
        correct_answer="A) Zürich",
        points_max=4.0,
    )
    assert outcome.is_correct is False


# ---------------------------------------------------------------------------
# True / False
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "given,correct,is_correct",
    [
        # Cross-language synonyms
        ("wahr", "true", True),
        ("Richtig", "WAHR", True),
        ("Ja", "yes", True),
        ("falsch", "false", True),
        ("Nein", "no", True),
        ("True", "False", False),
        ("Falsch", "Wahr", False),
        ("ja", "nein", False),
        # Less-common synonyms must still normalise
        ("stimmt", "wahr", True),
        ("korrekt", "true", True),
        ("unzutreffend", "false", True),
        ("t", "wahr", True),
        ("f", "false", True),
        ("1", "wahr", True),
        ("0", "false", True),
        # Cross-synonym pairings
        ("stimmt", "korrekt", True),
        ("unzutreffend", "nein", True),
    ],
)
def test_true_false_normalisation(
    grader: DeterministicGrader, given: str, correct: str, is_correct: bool
) -> None:
    outcome = grader.grade(
        question_type="true_false",
        given_answer=given,
        correct_answer=correct,
        points_max=1.0,
    )
    assert outcome.is_correct is is_correct


def test_true_false_unrecognised_token_is_wrong(
    grader: DeterministicGrader,
) -> None:
    """Spec 6.2: nicht-erkennbare Antworten werten als falsch."""
    outcome = grader.grade(
        question_type="true_false",
        given_answer="vielleicht",
        correct_answer="wahr",
        points_max=1.0,
    )
    assert outcome.is_correct is False
    assert outcome.points_awarded == 0.0


def test_true_false_empty_is_wrong(grader: DeterministicGrader) -> None:
    outcome = grader.grade(
        question_type="true_false",
        given_answer="",
        correct_answer="wahr",
        points_max=1.0,
    )
    assert outcome.is_correct is False


# ---------------------------------------------------------------------------
# Unbekannter Typ
# ---------------------------------------------------------------------------


def test_unknown_question_type_raises(grader: DeterministicGrader) -> None:
    with pytest.raises(ValueError, match="question_type"):
        grader.grade(
            question_type="numeric",
            given_answer="42",
            correct_answer="42",
            points_max=1.0,
        )


# ---------------------------------------------------------------------------
# Stub für offene Fragen (Phase-1-Verhalten)
# ---------------------------------------------------------------------------


def test_open_ended_stub_returns_zero_points() -> None:
    outcome = DeterministicGrader.stub_for_open_ended(points_max=5.0)
    assert outcome.points_awarded == 0.0
    assert outcome.points_max == 5.0
    assert outcome.is_correct is None
    assert outcome.status == "proposed"


def test_grade_outcome_is_immutable() -> None:
    from dataclasses import FrozenInstanceError

    outcome = GradeOutcome(
        points_awarded=2.0, points_max=4.0, is_correct=True, status="proposed"
    )
    with pytest.raises(FrozenInstanceError):
        outcome.points_awarded = 0.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Multi-Select-MC: dokumentiert das Strict-Equality-Verhalten
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "given,correct,is_correct",
    [
        # Same canonical multi-select string ⇒ correct
        ("A,C", "A,C", True),
        ("A, C", "A, C", True),
        # Different order ⇒ wrong (no permutation tolerance by design)
        ("C,A", "A,C", False),
        # Spacing/whitespace differences ⇒ wrong (only outer trim)
        ("A,C ", "A,C", True),  # trim only
        ("A , C", "A,C", False),
    ],
)
def test_multi_select_mc_uses_strict_canonical_equality(
    grader: DeterministicGrader, given: str, correct: str, is_correct: bool
) -> None:
    """Multi-correct MC must agree on a canonical form on both sides.

    This locks in current behaviour so a future refactor that adds
    permutation tolerance is an explicit choice (and updates this test),
    not an accidental side-effect.
    """
    outcome = grader.grade(
        question_type="multiple_choice",
        given_answer=given,
        correct_answer=correct,
        points_max=2.0,
    )
    assert outcome.is_correct is is_correct


def test_true_false_warns_when_correct_answer_is_unrecognised(
    grader: DeterministicGrader, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Question-bank bug — log loud so the author notices.

    Patches ``logger.warning`` directly instead of relying on
    ``caplog``: pytest-cov's import-time hooking + the project's root
    logging config produced inconsistent caplog capture across local
    and CI runs. A direct mock of the module-level logger is
    deterministic everywhere.
    """
    from services.grading import deterministic_grader as dg_module

    captured: list[tuple[str, tuple]] = []
    monkeypatch.setattr(
        dg_module.logger,
        "warning",
        lambda fmt, *args, **kwargs: captured.append((fmt, args)),
    )

    outcome = grader.grade(
        question_type="true_false",
        given_answer="wahr",
        correct_answer="vielleicht",
        points_max=1.0,
    )
    assert outcome.is_correct is False
    # One warning; format string mentions correct_answer + arg is the bad value.
    assert any(
        "correct_answer" in fmt and "vielleicht" in repr(args) for fmt, args in captured
    )


# ---------------------------------------------------------------------------
# GradingService: SubmissionNotFoundError + empty-attempts reset
# ---------------------------------------------------------------------------


def test_grade_submission_raises_when_id_missing(test_db) -> None:
    """grade_submission must raise SubmissionNotFoundError instead of
    returning None — silent None previously masked typos in caller code."""
    from services.grading_service import GradingService, SubmissionNotFoundError

    service = GradingService(test_db)
    with pytest.raises(SubmissionNotFoundError, match="9999999"):
        service.grade_submission(9999999)


def test_grade_submission_resets_aggregates_when_no_attempts(test_db) -> None:
    """Submission with stale aggregates but zero attempts (e.g. all
    deleted before re-import) must have its aggregates reset rather
    than retain stale point totals from a previous import."""
    from datetime import date

    from models.auth import Institution
    from models.exam import Exam
    from models.student import Student
    from models.submission import Submission
    from services.grading_service import GradingService

    inst = Institution(
        name="Empty-Attempts Inst",
        slug="empty-attempts-test",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.flush()

    exam = Exam(
        title="Empty-Attempts Exam",
        course="X",
        exam_date=date(2026, 5, 15),
        passing_percentage=50.0,
        total_points=10.0,
        status="finalized",
        language="de",
        institution_id=inst.id,
    )
    student = Student(
        institution_id=inst.id, external_id="student@example.org", display_name="X"
    )
    test_db.add_all([exam, student])
    test_db.flush()

    submission = Submission(
        exam_id=exam.id,
        student_id=student.id,
        scoring_strategy="latest",
        grade_status="fully_reviewed",
        total_points_awarded=8.0,
        total_points_max=10.0,
        percentage=80.0,
    )
    test_db.add(submission)
    test_db.commit()

    result = GradingService(test_db).grade_submission(submission.id)
    assert result is submission
    assert submission.total_points_awarded == 0.0
    assert submission.percentage == 0.0
    assert submission.grade_status == "pending_review"
    assert submission.graded_attempt_id is None


def test_grade_submission_handles_unknown_question_type_as_stub(
    test_db, monkeypatch
) -> None:
    """An unrecognised question_type must NOT roll back the import.
    The branch logs an error and falls back to needs-review-stub."""
    from datetime import date

    from models.auth import Institution
    from models.exam import Exam, ExamQuestion
    from models.question_review import QuestionReview
    from models.student import Student
    from models.submission import Attempt, AttemptAnswer, Submission
    from services.grading_service import GradingService

    inst = Institution(
        name="Unknown-QT Inst",
        slug="unknown-qt-test",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.flush()

    weird_q = QuestionReview(
        question_text="Berechne die Wahrscheinlichkeit.",
        question_type="numeric",  # not handled by DeterministicGrader
        correct_answer="0.5",
        difficulty="medium",
        topic="Mathe",
        institution_id=inst.id,
    )
    test_db.add(weird_q)
    test_db.flush()

    exam = Exam(
        title="X",
        course="Y",
        exam_date=date(2026, 5, 15),
        passing_percentage=50.0,
        total_points=4.0,
        status="finalized",
        language="de",
        institution_id=inst.id,
    )
    student = Student(institution_id=inst.id, external_id="s@example.org")
    test_db.add_all([exam, student])
    test_db.flush()
    eq = ExamQuestion(exam_id=exam.id, question_id=weird_q.id, position=1, points=4.0)
    test_db.add(eq)
    test_db.flush()

    submission = Submission(
        exam_id=exam.id, student_id=student.id, scoring_strategy="latest"
    )
    test_db.add(submission)
    test_db.flush()

    attempt = Attempt(
        submission_id=submission.id,
        institution_id=inst.id,
        attempt_number=1,
        source="moodle_csv",
        source_attempt_id="s|2026-05-15|1",
    )
    test_db.add(attempt)
    test_db.flush()

    answer = AttemptAnswer(
        attempt_id=attempt.id,
        exam_question_id=eq.id,
        given_answer="0.5",
    )
    test_db.add(answer)
    test_db.commit()

    # Must not raise — falls through to needs-review-stub
    result = GradingService(test_db).grade_submission(submission.id)
    assert result is submission
    test_db.refresh(answer)
    assert answer.grade is not None
    # Stub: 0 points + is_correct=None (needs review)
    assert answer.grade.points_awarded == 0.0
    assert answer.grade.is_correct is None
    # Submission stays pending_review because is_correct=None gates it
    assert submission.grade_status == "pending_review"
