"""Integration tests for ResultsDeletionService (TF-421).

Covers: pre-deletion counts (summary), full cascade (attempts → answers →
grades) plus orphan-submission cleanup, scope correctness (no leak across
exams or institutions), retention of students + import-job history, and that a
clean re-import works after a delete (the idempotency skip no longer triggers).
"""

from __future__ import annotations

from datetime import date

import json

import pytest
from sqlalchemy.orm import Session

from models.auth import Institution
from models.exam import Exam, ExamQuestion
from models.question_review import QuestionReview
from models.student import Student
from models.submission import (
    Attempt,
    AttemptAnswer,
    Grade,
    ImportJob,
    Submission,
)
from services.import_service import ImportService
from services.results_deletion_service import ResultsDeletionService

# ---------------------------------------------------------------------------
# Builders (functions, not fixtures — leak tests need multiple instances)
# ---------------------------------------------------------------------------


def _make_institution(test_db: Session, *, slug: str) -> Institution:
    inst = Institution(
        name=f"TF-421 {slug}",
        slug=slug,
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.flush()
    return inst


def _make_exam_with_questions(test_db: Session, institution: Institution) -> Exam:
    """Exam with 1 MC + 1 true/false + 1 open question (4 + 1 + 5 = 10)."""
    mc_q = QuestionReview(
        question_text="Hauptstadt der Schweiz?",
        question_type="single_choice",
        options=["A) Zürich", "B) Bern", "C) Genf", "D) Basel"],
        correct_answer="Bern",
        difficulty="easy",
        topic="Geografie",
        institution_id=institution.id,
    )
    tf_q = QuestionReview(
        question_text="Bern ist die Hauptstadt der Schweiz.",
        question_type="true_false",
        correct_answer="wahr",
        difficulty="easy",
        topic="Geografie",
        institution_id=institution.id,
    )
    open_q = QuestionReview(
        question_text="Erkläre Föderalismus in 3 Sätzen.",
        question_type="open_ended",
        correct_answer="Drei-Ebenen-System aus Bund, Kantonen, Gemeinden …",
        difficulty="medium",
        topic="Politik",
        institution_id=institution.id,
    )
    test_db.add_all([mc_q, tf_q, open_q])
    test_db.flush()

    exam = Exam(
        title="Allgemeinbildung",
        course="ABU",
        exam_date=date(2026, 5, 15),
        passing_percentage=50.0,
        total_points=10.0,
        status="finalized",
        language="de",
        institution_id=institution.id,
    )
    test_db.add(exam)
    test_db.flush()

    test_db.add_all(
        [
            ExamQuestion(exam_id=exam.id, question_id=mc_q.id, position=1, points=4.0),
            ExamQuestion(exam_id=exam.id, question_id=tf_q.id, position=2, points=1.0),
            ExamQuestion(
                exam_id=exam.id, question_id=open_q.id, position=3, points=5.0
            ),
        ]
    )
    test_db.flush()
    return exam


# Question texts mirror ``_make_exam_with_questions`` so the JSON driver's
# exact-match stage resolves each ``frageN`` to a unique exam question.
_Q1 = "Hauptstadt der Schweiz?"
_Q2 = "Bern ist die Hauptstadt der Schweiz."
_Q3 = "Erkläre Föderalismus in 3 Sätzen."


def _json_two_students(*, domain: str = "example.org") -> bytes:
    """Two students, one attempt each (Anna correct-ish, Bruno wrong)."""

    def _row(vorname, nachname, email, a1, a2, a3, beendet):
        return {
            "vorname": vorname,
            "nachname": nachname,
            "e-mail-adresse": email,
            "begonnen": "2026-05-15 09:00:00",
            "beendet": beendet,
            "frage1": _Q1,
            "antwort1": a1,
            "frage2": _Q2,
            "antwort2": a2,
            "frage3": _Q3,
            "antwort3": a3,
        }

    rows = [
        _row(
            "Anna",
            "Beispiel",
            f"anna@{domain}",
            "Bern",
            "wahr",
            "Antworttext",
            "2026-05-15 09:30:00",
        ),
        _row(
            "Bruno",
            "Muster",
            f"bruno@{domain}",
            "Zürich",
            "falsch",
            "",
            "2026-05-15 09:25:00",
        ),
    ]
    return json.dumps([rows]).encode("utf-8")


def _seed_import(test_db: Session, exam: Exam, *, domain: str = "example.org") -> None:
    """Run the real import pipeline → 2 students, 2 attempts, 6 answers/grades."""
    ImportService(test_db).commit(
        exam=exam,
        driver_name="moodle_json",
        source=_json_two_students(domain=domain),
        triggered_by=None,
        source_metadata={"filename": "klasse.json"},
    )


@pytest.fixture
def institution(test_db: Session) -> Institution:
    inst = _make_institution(test_db, slug="tf421-svc")
    test_db.commit()
    return inst


@pytest.fixture
def exam(test_db: Session, institution: Institution) -> Exam:
    e = _make_exam_with_questions(test_db, institution)
    test_db.commit()
    test_db.refresh(e)
    return e


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def test_summary_counts_pre_deletion(test_db: Session, exam: Exam) -> None:
    _seed_import(test_db, exam)

    summary = ResultsDeletionService(test_db).summary(exam=exam)

    assert summary.exam_id == exam.id
    assert summary.submission_count == 2
    assert summary.attempt_count == 2
    assert summary.student_count == 2
    assert [(s.source, s.attempt_count) for s in summary.by_source] == [
        ("moodle_json", 2)
    ]


def test_summary_zero_for_empty_exam(test_db: Session, exam: Exam) -> None:
    summary = ResultsDeletionService(test_db).summary(exam=exam)

    assert summary.submission_count == 0
    assert summary.attempt_count == 0
    assert summary.student_count == 0
    assert summary.by_source == []


# ---------------------------------------------------------------------------
# Deletion — cascade + orphan cleanup
# ---------------------------------------------------------------------------


def test_delete_removes_attempts_answers_grades_and_submissions(
    test_db: Session, exam: Exam
) -> None:
    _seed_import(test_db, exam)
    assert test_db.query(Attempt).count() == 2
    assert test_db.query(AttemptAnswer).count() == 6
    assert test_db.query(Grade).count() == 6
    assert test_db.query(Submission).count() == 2

    result = ResultsDeletionService(test_db).delete_exam_results(exam=exam)

    assert result.submission_count == 2
    assert result.attempt_count == 2
    assert result.student_count == 2
    # Everything below the submission is gone (DB cascade + orphan cleanup).
    assert test_db.query(Attempt).count() == 0
    assert test_db.query(AttemptAnswer).count() == 0
    assert test_db.query(Grade).count() == 0
    assert test_db.query(Submission).count() == 0


def test_delete_keeps_students_and_import_jobs(test_db: Session, exam: Exam) -> None:
    _seed_import(test_db, exam)
    students_before = test_db.query(Student).count()
    jobs_before = test_db.query(ImportJob).count()
    assert students_before == 2
    assert jobs_before == 1

    ResultsDeletionService(test_db).delete_exam_results(exam=exam)

    # Students (roster) and import-job history survive the delete.
    assert test_db.query(Student).count() == students_before
    assert test_db.query(ImportJob).count() == jobs_before


def test_delete_on_empty_exam_is_noop(test_db: Session, exam: Exam) -> None:
    result = ResultsDeletionService(test_db).delete_exam_results(exam=exam)

    assert result.submission_count == 0
    assert result.attempt_count == 0
    assert test_db.query(Submission).count() == 0


# ---------------------------------------------------------------------------
# Scope — no leak across exams / institutions
# ---------------------------------------------------------------------------


def test_delete_scoped_to_exam_no_cross_exam_leak(
    test_db: Session, institution: Institution
) -> None:
    exam_a = _make_exam_with_questions(test_db, institution)
    exam_b = _make_exam_with_questions(test_db, institution)
    test_db.commit()
    _seed_import(test_db, exam_a, domain="a.example.org")
    _seed_import(test_db, exam_b, domain="b.example.org")
    assert test_db.query(Submission).count() == 4

    ResultsDeletionService(test_db).delete_exam_results(exam=exam_a)

    # Only exam A's results are gone; exam B is untouched.
    assert (
        test_db.query(Submission).filter(Submission.exam_id == exam_a.id).count() == 0
    )
    assert (
        test_db.query(Submission).filter(Submission.exam_id == exam_b.id).count() == 2
    )
    assert (
        test_db.query(Attempt)
        .join(Submission, Attempt.submission_id == Submission.id)
        .filter(Submission.exam_id == exam_b.id)
        .count()
        == 2
    )


def test_delete_no_cross_institution_leak(test_db: Session) -> None:
    inst_a = _make_institution(test_db, slug="tf421-inst-a")
    inst_b = _make_institution(test_db, slug="tf421-inst-b")
    test_db.flush()
    exam_a = _make_exam_with_questions(test_db, inst_a)
    exam_b = _make_exam_with_questions(test_db, inst_b)
    test_db.commit()
    _seed_import(test_db, exam_a, domain="inst-a.example.org")
    _seed_import(test_db, exam_b, domain="inst-b.example.org")

    ResultsDeletionService(test_db).delete_exam_results(exam=exam_a)

    assert (
        test_db.query(Submission).filter(Submission.exam_id == exam_b.id).count() == 2
    )


# ---------------------------------------------------------------------------
# Re-import after delete (the core motivation, TF-419 → TF-421)
# ---------------------------------------------------------------------------


def test_reimport_works_after_delete(test_db: Session, exam: Exam) -> None:
    """After deletion the idempotency keys are gone, so a re-import recreates
    the attempts instead of skipping them."""
    _seed_import(test_db, exam)
    ResultsDeletionService(test_db).delete_exam_results(exam=exam)
    assert test_db.query(Attempt).count() == 0

    # Re-import the same CSV — must NOT be skipped as idempotent.
    _seed_import(test_db, exam)

    assert test_db.query(Attempt).count() == 2
    assert test_db.query(Submission).count() == 2
    assert test_db.query(AttemptAnswer).count() == 6
