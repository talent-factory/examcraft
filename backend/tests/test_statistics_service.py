"""Tests for ``services.statistics_service``.

Mix of pure unit tests for the math helpers (no DB) and a small
integration test for the service against ``test_db``. The math helpers
are the high-risk surface (Pearson correlation, histogram bucketing,
learning-effect averaging); the service is mostly query stitching.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from models.auth import Institution, User, UserStatus
from models.exam import Exam, ExamQuestion
from models.question_review import QuestionReview
from models.student import Student
from models.submission import Attempt, AttemptAnswer, Grade, Submission
from services.statistics_service import (
    HistogramBucket,
    StatisticsService,
    _discrimination,
    _empty_histogram,
    _histogram,
    _learning_effect,
    _safe_mean,
    _safe_median,
    _success_and_difficulty,
    _top_wrong_answers,
)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([], None),
        ([42.0], 42.0),
        ([1.0, 2.0, 3.0], 2.0),
        ([10.0, 20.0, 30.0, 40.0], 25.0),
    ],
)
def test_safe_mean(values: list[float], expected: float | None) -> None:
    assert _safe_mean(values) == expected


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([], None),
        ([5.0], 5.0),
        ([1.0, 2.0, 3.0], 2.0),
        ([1.0, 2.0, 3.0, 4.0], 2.5),
    ],
)
def test_safe_median(values: list[float], expected: float | None) -> None:
    assert _safe_median(values) == expected


def test_empty_histogram_has_ten_buckets() -> None:
    buckets = _empty_histogram()
    assert len(buckets) == 10
    assert buckets[0] == HistogramBucket(from_pct=0, to_pct=10, count=0)
    assert buckets[-1] == HistogramBucket(from_pct=90, to_pct=100, count=0)


def test_histogram_buckets_correctly() -> None:
    # Boundary at exactly 50 % goes into [50, 60); 100 % goes into the
    # last bucket [90, 100] thanks to the "last bucket owns its right
    # edge" rule.
    buckets = _histogram([0.0, 9.999, 10.0, 50.0, 100.0])
    counts = {b.from_pct: b.count for b in buckets}
    assert counts[0] == 2  # 0 and 9.999
    assert counts[10] == 1  # 10.0
    assert counts[50] == 1  # 50.0
    assert counts[90] == 1  # 100 → last bucket


def test_histogram_clamps_out_of_range() -> None:
    buckets = _histogram([-50.0, 200.0])
    counts = {b.from_pct: b.count for b in buckets}
    assert counts[0] == 1
    assert counts[90] == 1


def _row(
    points_awarded: float,
    points_max: float,
    percentage: float,
    *,
    given: str = "X",
    correct: bool | None = None,
):
    """Build a duck-typed row that mirrors the SQLAlchemy result."""

    class Row:
        pass

    r = Row()
    r.points_awarded = points_awarded
    r.points_max = points_max
    r.percentage = percentage
    r.given_answer = given
    r.is_correct = correct
    return r


def test_success_and_difficulty_returns_none_for_empty() -> None:
    assert _success_and_difficulty([], 4.0) == (None, None)


def test_success_and_difficulty_distinguishes_full_vs_partial() -> None:
    rows = [
        _row(4.0, 4.0, 80.0),  # fully correct
        _row(2.0, 4.0, 50.0),  # partial — counts for success_rate but not difficulty
        _row(0.0, 4.0, 10.0),
    ]
    success, difficulty = _success_and_difficulty(rows, 4.0)
    # success_rate is mean of fractions: (1.0 + 0.5 + 0.0) / 3
    assert success == pytest.approx(0.5)
    # difficulty is share of fully_correct: 1/3
    assert difficulty == pytest.approx(1 / 3)


def test_discrimination_perfect_positive_correlation() -> None:
    # Each row's item-success rises in lockstep with the submission's
    # overall percentage. Pearson should clock in at +1.0.
    rows = [
        _row(0.0, 4.0, 0.0),
        _row(2.0, 4.0, 50.0),
        _row(4.0, 4.0, 100.0),
    ]
    assert _discrimination(rows) == pytest.approx(1.0)


def test_discrimination_perfect_negative_correlation() -> None:
    rows = [
        _row(4.0, 4.0, 0.0),
        _row(2.0, 4.0, 50.0),
        _row(0.0, 4.0, 100.0),
    ]
    assert _discrimination(rows) == pytest.approx(-1.0)


def test_discrimination_constant_series_returns_none() -> None:
    # Every row has the same item-success → can't correlate.
    rows = [
        _row(2.0, 4.0, 30.0),
        _row(2.0, 4.0, 60.0),
        _row(2.0, 4.0, 90.0),
    ]
    assert _discrimination(rows) is None


def test_discrimination_too_few_rows_returns_none() -> None:
    assert _discrimination([_row(2.0, 4.0, 50.0)]) is None
    assert _discrimination([]) is None


def test_top_wrong_answers_excludes_correct_and_empty() -> None:
    rows = [
        _row(0.0, 1.0, 50.0, given="Zürich", correct=False),
        _row(0.0, 1.0, 50.0, given="Zürich", correct=False),
        _row(1.0, 1.0, 50.0, given="Bern", correct=True),
        _row(0.0, 1.0, 50.0, given="Genf", correct=False),
        _row(0.0, 1.0, 50.0, given="", correct=False),  # excluded
    ]
    top = _top_wrong_answers(rows)
    assert top == [("Zürich", 2), ("Genf", 1)]


def test_learning_effect_returns_none_for_single_attempt() -> None:
    # Empty dict: no students at all.
    assert _learning_effect({}) is None
    # Single student with a single attempt: nothing to pair.
    assert _learning_effect({101: {1: True}}) is None
    # Many students, all single-attempt — still no pair.
    assert _learning_effect({101: {1: True}, 102: {1: False}}) is None


def test_learning_effect_positive_when_student_improves_on_retry() -> None:
    # Student 101 went False → True on attempts 1 → 2 (delta +1.0).
    # Student 102 stayed True → True (delta 0.0).
    # Mean of paired deltas: 0.5.
    effect = _learning_effect(
        {
            101: {1: False, 2: True},
            102: {1: True, 2: True},
        }
    )
    assert effect == pytest.approx(0.5)


def test_learning_effect_negative_when_students_regress() -> None:
    effect = _learning_effect(
        {
            101: {1: True, 2: False},
            102: {1: True, 2: True},
        }
    )
    assert effect == pytest.approx(-0.5)


def test_learning_effect_ignores_non_retriers() -> None:
    """A student who only took attempt 1 must not pollute the cohort.

    The bug we previously had would average attempt-1 over *all* students
    including this one, then average attempt-2 over only the retrier —
    artificially inflating the apparent gain.
    """
    effect = _learning_effect(
        {
            # Retrier with no improvement.
            101: {1: True, 2: True},
            # Non-retrier — would have inflated attempt-1 mean before.
            102: {1: False},
            # Non-retrier — same.
            103: {1: False},
        }
    )
    assert effect == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Service integration test (real DB)
# ---------------------------------------------------------------------------


def _make_inst(db: Session) -> Institution:
    inst = Institution(
        name="Stat-Inst",
        slug="stat-inst",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.flush()
    return inst


def _make_user(db: Session, inst_id: int) -> User:
    user = User(
        email="lp@stat.ch",
        first_name="Test",
        last_name="LP",
        password_hash="x",  # pragma: allowlist secret
        institution_id=inst_id,
        status=UserStatus.ACTIVE.value,
        is_superuser=True,
    )
    db.add(user)
    db.flush()
    return user


def _make_exam_with_one_mc_question(
    db: Session, inst_id: int
) -> tuple[Exam, ExamQuestion]:
    qr = QuestionReview(
        question_text="Hauptstadt der Schweiz?",
        question_type="single_choice",
        options=["Bern", "Zürich", "Genf"],
        correct_answer="Bern",
        difficulty="easy",
        topic="Geo",
        bloom_level=1,
        institution_id=inst_id,
    )
    db.add(qr)
    db.flush()

    exam = Exam(
        title="Stats Smoke",
        passing_percentage=50.0,
        total_points=4.0,
        status="finalized",
        language="de",
        institution_id=inst_id,
    )
    db.add(exam)
    db.flush()
    eq = ExamQuestion(exam_id=exam.id, question_id=qr.id, position=1, points=4.0)
    db.add(eq)
    db.flush()
    return exam, eq


def _make_submission(
    db: Session,
    *,
    exam: Exam,
    inst_id: int,
    student_external_id: str,
    eq_id: int,
    awarded: float,
    points_max: float,
    percentage: float,
    grade_status: str = "fully_reviewed",
    given_answer: str = "Bern",
    is_correct: bool | None = True,
) -> Submission:
    student = Student(
        institution_id=inst_id,
        external_id=student_external_id,
    )
    db.add(student)
    db.flush()

    submission = Submission(
        exam_id=exam.id,
        student_id=student.id,
        total_points_awarded=awarded,
        total_points_max=points_max,
        percentage=percentage,
        grade_status=grade_status,
    )
    db.add(submission)
    db.flush()

    started = datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc)
    attempt = Attempt(
        submission_id=submission.id,
        institution_id=inst_id,
        attempt_number=1,
        started_at=started,
        submitted_at=started + timedelta(minutes=20),
        source="moodle_csv",
        source_attempt_id=f"src-{student_external_id}-1",
    )
    db.add(attempt)
    db.flush()

    submission.graded_attempt_id = attempt.id
    db.flush()

    answer = AttemptAnswer(
        attempt_id=attempt.id,
        exam_question_id=eq_id,
        given_answer=given_answer,
    )
    db.add(answer)
    db.flush()

    grade = Grade(
        attempt_answer_id=answer.id,
        points_awarded=awarded,
        points_max=points_max,
        status="approved",
        is_correct=is_correct,
    )
    db.add(grade)
    db.flush()
    return submission


def test_overview_aggregates_correctly(test_db: Session) -> None:
    inst = _make_inst(test_db)
    _make_user(test_db, inst.id)
    exam, eq = _make_exam_with_one_mc_question(test_db, inst.id)

    _make_submission(
        test_db,
        exam=exam,
        inst_id=inst.id,
        student_external_id="anna",
        eq_id=eq.id,
        awarded=4.0,
        points_max=4.0,
        percentage=100.0,
    )
    _make_submission(
        test_db,
        exam=exam,
        inst_id=inst.id,
        student_external_id="bruno",
        eq_id=eq.id,
        awarded=2.0,
        points_max=4.0,
        percentage=50.0,
    )
    _make_submission(
        test_db,
        exam=exam,
        inst_id=inst.id,
        student_external_id="clara",
        eq_id=eq.id,
        awarded=0.0,
        points_max=4.0,
        percentage=20.0,
        grade_status="pending_review",
        given_answer="Zürich",
        is_correct=False,
    )
    test_db.commit()

    stats = StatisticsService(test_db).overview(exam_id=exam.id)
    assert stats.submission_count == 3
    assert stats.fully_reviewed_count == 2
    assert stats.avg_percentage == pytest.approx((100 + 50 + 20) / 3)
    assert stats.median_percentage == 50.0
    assert stats.min_percentage == 20.0
    assert stats.max_percentage == 100.0
    # passing 50 → 2 of 3 pass = 0.666…
    assert stats.pass_rate == pytest.approx(2 / 3)
    # avg_duration ~ 20 minutes for each: 1200 s
    assert stats.avg_duration_seconds == pytest.approx(1200.0)
    # Histogram: 100→[90,100), 50→[50,60), 20→[20,30)
    counts = {b.from_pct: b.count for b in stats.histogram}
    assert counts[20] == 1
    assert counts[50] == 1
    assert counts[90] == 1


def test_overview_empty_exam(test_db: Session) -> None:
    inst = _make_inst(test_db)
    _make_user(test_db, inst.id)
    exam, _ = _make_exam_with_one_mc_question(test_db, inst.id)
    test_db.commit()

    stats = StatisticsService(test_db).overview(exam_id=exam.id)
    assert stats.submission_count == 0
    assert stats.avg_percentage is None
    assert all(b.count == 0 for b in stats.histogram)


def test_per_question_correlates_item_with_total(test_db: Session) -> None:
    inst = _make_inst(test_db)
    _make_user(test_db, inst.id)
    exam, eq = _make_exam_with_one_mc_question(test_db, inst.id)

    # Three submissions where the single question's award fraction
    # matches the overall percentage exactly → discrimination = 1.
    _make_submission(
        test_db,
        exam=exam,
        inst_id=inst.id,
        student_external_id="a",
        eq_id=eq.id,
        awarded=4.0,
        points_max=4.0,
        percentage=100.0,
    )
    _make_submission(
        test_db,
        exam=exam,
        inst_id=inst.id,
        student_external_id="b",
        eq_id=eq.id,
        awarded=2.0,
        points_max=4.0,
        percentage=50.0,
    )
    _make_submission(
        test_db,
        exam=exam,
        inst_id=inst.id,
        student_external_id="c",
        eq_id=eq.id,
        awarded=0.0,
        points_max=4.0,
        percentage=0.0,
        is_correct=False,
        given_answer="Zürich",
    )
    test_db.commit()

    items = StatisticsService(test_db).per_question(exam_id=exam.id)
    assert len(items) == 1
    item = items[0]
    assert item.position == 1
    assert item.answered_count == 3
    assert item.success_rate == pytest.approx(0.5)
    # 1 of 3 fully correct → difficulty 1/3
    assert item.difficulty == pytest.approx(1 / 3)
    assert item.discrimination == pytest.approx(1.0)
    # MC question with one wrong answer → top_wrong_answers populated
    assert ("Zürich", 1) in item.top_wrong_answers


def test_per_submission_breaks_down_by_topic_and_bloom(test_db: Session) -> None:
    inst = _make_inst(test_db)
    _make_user(test_db, inst.id)
    exam, eq = _make_exam_with_one_mc_question(test_db, inst.id)

    submission = _make_submission(
        test_db,
        exam=exam,
        inst_id=inst.id,
        student_external_id="anna",
        eq_id=eq.id,
        awarded=2.0,
        points_max=4.0,
        percentage=50.0,
    )
    test_db.commit()

    stats = StatisticsService(test_db).per_submission(submission_id=submission.id)
    assert stats is not None
    assert stats.percentage == 50.0
    assert stats.bloom_mix == {1: 1}
    # One topic "Geo" with 2/4 awarded → 50 %
    geo = stats.topic_heatmap["Geo"]
    assert geo["points_awarded"] == 2.0
    assert geo["points_max"] == 4.0
    assert geo["percentage"] == 50.0


def test_per_submission_returns_none_for_unknown_id(test_db: Session) -> None:
    assert StatisticsService(test_db).per_submission(submission_id=999_999) is None
