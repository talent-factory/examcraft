"""Tests for the Celery wrapper around ImportService.commit.

Covers:
* Happy path: returns the persisted ImportJob's diagnostic summary.
* Missing exam: surfaces ValueError loud enough for Celery to mark FAILURE.
* Permanent (non-transient) errors: must not retry — otherwise every retry
  creates a new ImportJob row.
* Transient (DB drop / connection) errors: are listed in autoretry_for so
  Celery's retry machinery picks them up.
* finally db.close: the SessionLocal is always closed even when commit raises.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from models.auth import Institution
from models.exam import Exam, ExamQuestion
from models.question_review import QuestionReview
from models.submission import ImportJob
from tasks.import_submissions_task import (
    _TRANSIENT_ERRORS,
    import_submissions,
)


@pytest.fixture
def institution(test_db: Session) -> Institution:
    inst = Institution(
        name="Celery-Task Test Inst",
        slug="celery-task-test",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.commit()
    test_db.refresh(inst)
    return inst


@pytest.fixture
def exam_simple(test_db: Session, institution: Institution) -> Exam:
    """Minimal one-MC-question exam so the import has something to grade."""
    mc_q = QuestionReview(
        question_text="Hauptstadt der Schweiz?",
        question_type="multiple_choice",
        correct_answer="Bern",
        difficulty="easy",
        topic="Geo",
        institution_id=institution.id,
    )
    test_db.add(mc_q)
    test_db.flush()

    exam = Exam(
        title="Mini",
        course="ABU",
        exam_date=date(2026, 5, 15),
        passing_percentage=50.0,
        total_points=4.0,
        status="finalized",
        language="de",
        institution_id=institution.id,
    )
    test_db.add(exam)
    test_db.flush()
    test_db.add(
        ExamQuestion(exam_id=exam.id, question_id=mc_q.id, position=1, points=4.0)
    )
    test_db.commit()
    test_db.refresh(exam)
    return exam


_CSV = (
    "Vorname;Nachname;E-Mail-Adresse;Begonnen am;Beendet;Antwort 1\n"
    "Anna;Beispiel;anna@example.org;2026-05-15 09:00:00;"
    "2026-05-15 09:30:00;Bern\n"
)


def test_transient_errors_are_in_autoretry_set() -> None:
    """Regression guard for the duplicate-ImportJob bug.

    Adding IntegrityError or ValidationError to _TRANSIENT_ERRORS would
    cause Celery to retry permanent failures, and every retry creates a
    new ImportJob row. The set must stay narrowly scoped to truly
    transient classes.
    """
    assert OperationalError in _TRANSIENT_ERRORS
    assert ConnectionError in _TRANSIENT_ERRORS

    from sqlalchemy.exc import IntegrityError, DataError

    # Permanent classes must NOT be in the retry set.
    assert IntegrityError not in _TRANSIENT_ERRORS
    assert DataError not in _TRANSIENT_ERRORS
    assert ValueError not in _TRANSIENT_ERRORS


def _create_pending_job(db: Session, *, institution_id: int, exam_id: int) -> int:
    """Pre-create an ImportJob in queued state and return its id.

    Mirrors the API caller's responsibility: the task no longer creates
    rows on its own — every retry reuses the row id passed in.
    """
    from enums import ImportJobStatus

    job = ImportJob(
        institution_id=institution_id,
        exam_id=exam_id,
        driver_name="moodle_csv",
        status=ImportJobStatus.QUEUED.value,
        rows_processed=0,
        rows_failed=0,
        error_log=[],
        source_metadata={},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job.id


def test_task_returns_job_summary_on_happy_path(
    test_db: Session, institution: Institution, exam_simple: Exam
) -> None:
    """End-to-end: task returns persisted job's id + status."""
    job_id = _create_pending_job(
        test_db, institution_id=institution.id, exam_id=exam_simple.id
    )
    with (
        patch("tasks.import_submissions_task.SessionLocal", return_value=test_db),
        patch.object(test_db, "close"),
    ):  # don't let the task close our shared session
        result = import_submissions.run(
            exam_id=exam_simple.id,
            driver_name="moodle_csv",
            source_text=_CSV,
            import_job_id=job_id,
            triggered_by=None,
            source_metadata={"filename": "klasse.csv"},
        )

    assert result["import_job_id"] == job_id
    assert result["status"] == "succeeded"
    assert result["rows_processed"] == 1
    assert result["rows_failed"] == 0


def test_retry_reuses_same_job_row_no_duplicate(
    test_db: Session, institution: Institution, exam_simple: Exam
) -> None:
    """Regression for the duplicate-ImportJob bug.

    Pre-create one ImportJob, then run the task twice as if Celery
    retried after a transient error. The second run must not create a
    second row — it must reset the existing row and re-run the
    pipeline against it.
    """
    job_id = _create_pending_job(
        test_db, institution_id=institution.id, exam_id=exam_simple.id
    )

    with (
        patch("tasks.import_submissions_task.SessionLocal", return_value=test_db),
        patch.object(test_db, "close"),
    ):
        import_submissions.run(
            exam_id=exam_simple.id,
            driver_name="moodle_csv",
            source_text=_CSV,
            import_job_id=job_id,
            triggered_by=None,
        )
        # Simulate a Celery retry — same job_id, same payload.
        import_submissions.run(
            exam_id=exam_simple.id,
            driver_name="moodle_csv",
            source_text=_CSV,
            import_job_id=job_id,
            triggered_by=None,
        )

    rows = test_db.query(ImportJob).filter(ImportJob.exam_id == exam_simple.id).all()
    assert len(rows) == 1, (
        "Retry must not create a second ImportJob row — the first one is reused"
    )
    assert rows[0].id == job_id


def test_missing_exam_marks_job_failed(
    test_db: Session, institution: Institution, exam_simple: Exam
) -> None:
    """Unknown exam_id must raise AND mark the pre-created job FAILED."""
    job_id = _create_pending_job(
        test_db, institution_id=institution.id, exam_id=exam_simple.id
    )

    with (
        patch("tasks.import_submissions_task.SessionLocal", return_value=test_db),
        patch.object(test_db, "close"),
    ):
        with pytest.raises(ValueError, match="nicht gefunden"):
            import_submissions.run(
                exam_id=9_999_999,
                driver_name="moodle_csv",
                source_text=_CSV,
                import_job_id=job_id,
                triggered_by=None,
            )

    test_db.expire_all()
    job = test_db.get(ImportJob, job_id)
    assert job is not None
    assert job.status == "failed"


def test_session_is_closed_even_when_commit_raises(
    test_db: Session, institution: Institution, exam_simple: Exam
) -> None:
    """The finally clause must close the SessionLocal so a worker thread
    doesn't leak a connection on a permanent failure."""
    job_id = _create_pending_job(
        test_db, institution_id=institution.id, exam_id=exam_simple.id
    )
    fake_session = MagicMock(wraps=test_db)

    # Make ImportService.commit blow up once we get past the exam lookup.
    with (
        patch("tasks.import_submissions_task.SessionLocal", return_value=fake_session),
        patch("tasks.import_submissions_task.ImportService") as service_cls,
    ):
        service_cls.return_value.commit.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            import_submissions.run(
                exam_id=exam_simple.id,
                driver_name="moodle_csv",
                source_text=_CSV,
                import_job_id=job_id,
                triggered_by=None,
            )

    fake_session.close.assert_called_once()
