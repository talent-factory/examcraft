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

import base64
import binascii
import json
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
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
        question_type="single_choice",
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


_JSON = json.dumps(
    [
        [
            {
                "vorname": "Anna",
                "nachname": "Beispiel",
                "e-mail-adresse": "anna@example.org",
                "begonnen": "2026-05-15 09:00:00",
                "beendet": "2026-05-15 09:30:00",
                "frage1": "Hauptstadt der Schweiz?",
                "antwort1": "Bern",
            }
        ]
    ]
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


# Tasks receive base64 of the raw upload bytes (Celery args are JSON-serialised).
_JSON_B64 = base64.b64encode(_JSON.encode("utf-8")).decode("ascii")


def _create_pending_job(db: Session, *, institution_id: int, exam_id: int) -> int:
    """Pre-create an ImportJob in queued state and return its id.

    Mirrors the API caller's responsibility: the task no longer creates
    rows on its own — every retry reuses the row id passed in.
    """
    from enums import ImportJobStatus

    job = ImportJob(
        institution_id=institution_id,
        exam_id=exam_id,
        driver_name="moodle_json",
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
            driver_name="moodle_json",
            source_b64=_JSON_B64,
            import_job_id=job_id,
            triggered_by=None,
            source_metadata={"filename": "klasse.json"},
        )

    assert result["import_job_id"] == job_id
    assert result["status"] == "succeeded"
    assert result["rows_processed"] == 1
    assert result["rows_failed"] == 0


def test_import_task_module_is_in_celery_include() -> None:
    """The worker only loads task modules listed in ``celery_app``'s
    ``include``. If this module is missing, ``apply_async`` would enqueue
    imports that no worker ever executes — they'd sit in ``queued`` forever.
    """
    from celery_app import celery_app

    assert "tasks.import_submissions_task" in (celery_app.conf.include or [])


def test_import_task_is_routed_to_a_consumed_queue() -> None:
    """The task must be routed to ``import_processing``. Without a route it
    lands on the default ``celery`` queue, which the queue-pinned workers
    (docker-compose --queues, and the Fly worker via task_queues) never
    consume — every import would sit ``queued`` forever (TF-412)."""
    from celery_app import celery_app

    route = (celery_app.conf.task_routes or {}).get(
        "tasks.import_submissions_task.import_submissions"
    )
    assert route is not None, "import_submissions has no task route"
    assert route["queue"] == "import_processing"

    declared = {q.name for q in (celery_app.conf.task_queues or ())}
    assert "import_processing" in declared, (
        "routed queue must also be declared in task_queues so the no-`-Q` "
        "Fly worker consumes it"
    )


def test_import_job_status_terminal_partition() -> None:
    """The terminal/transient partition is hand-mirrored in the frontend
    (``TERMINAL_STATUSES`` in ImportDialog.tsx). A new ImportJobStatus added
    on the backend without updating that set would make the poll loop hang
    (treats the new status as transient) or exit early. Lock the partition so
    such a change trips this test first and points the author at the frontend."""
    from enums import ImportJobStatus

    all_statuses = {s.value for s in ImportJobStatus}
    non_terminal = {ImportJobStatus.QUEUED.value, ImportJobStatus.RUNNING.value}
    terminal = {
        ImportJobStatus.SUCCEEDED.value,
        ImportJobStatus.PARTIAL.value,
        ImportJobStatus.FAILED.value,
    }
    assert non_terminal.isdisjoint(terminal)
    assert all_statuses == non_terminal | terminal, (
        "ImportJobStatus changed — update TERMINAL_STATUSES in "
        "core/frontend/src/components/auswertungen/ImportDialog.tsx to match"
    )


def test_task_decodes_base64_source_to_raw_bytes(
    test_db: Session, institution: Institution, exam_simple: Exam
) -> None:
    """Contract: the caller passes base64 of the raw upload bytes; the task
    decodes it back to ``bytes`` and hands the driver the exact original
    bytes. This keeps grading identical to the synchronous path and lets the
    driver's own encoding detection run (utf-8-sig/cp1252/latin-1) — a plain
    decoded ``str`` would bypass it and crash byte-expecting drivers."""
    job_id = _create_pending_job(
        test_db, institution_id=institution.id, exam_id=exam_simple.id
    )
    raw_bytes = _JSON.encode("utf-8")
    captured: dict[str, object] = {}
    fake_job = MagicMock(id=job_id, status="succeeded", rows_processed=1, rows_failed=0)

    def _capture(**kwargs: object) -> MagicMock:
        captured["source"] = kwargs["source"]
        return fake_job

    with (
        patch("tasks.import_submissions_task.SessionLocal", return_value=test_db),
        patch.object(test_db, "close"),
        patch("tasks.import_submissions_task.ImportService") as service_cls,
    ):
        service_cls.return_value.commit.side_effect = _capture
        import_submissions.run(
            exam_id=exam_simple.id,
            driver_name="moodle_json",
            source_b64=base64.b64encode(raw_bytes).decode("ascii"),
            import_job_id=job_id,
            triggered_by=None,
        )

    assert isinstance(captured["source"], bytes)
    assert captured["source"] == raw_bytes


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
            driver_name="moodle_json",
            source_b64=_JSON_B64,
            import_job_id=job_id,
            triggered_by=None,
        )
        # Simulate a Celery retry — same job_id, same payload.
        import_submissions.run(
            exam_id=exam_simple.id,
            driver_name="moodle_json",
            source_b64=_JSON_B64,
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
                driver_name="moodle_json",
                source_b64=_JSON_B64,
                import_job_id=job_id,
                triggered_by=None,
            )

    test_db.expire_all()
    job = test_db.get(ImportJob, job_id)
    assert job is not None
    assert job.status == "failed"
    # The polling client renders error_log to the user, so a failed job must
    # carry a diagnostic entry tagged with the step that failed. (The re-raised
    # ValueError is also caught by the generic handler, which appends a second
    # ``step="task"`` entry — both describe the same failure; we only assert the
    # specific ``lookup`` diagnostic is present rather than its exact position.)
    assert job.error_log, "missing-exam failure must populate error_log"
    assert any((e or {}).get("step") == "lookup" for e in job.error_log)


def test_decode_failure_marks_job_failed_without_retry(
    test_db: Session, institution: Institution, exam_simple: Exam
) -> None:
    """A malformed ``source_b64`` is a permanent error: the task marks the
    pre-created job terminal-FAILED (step='decode') and re-raises WITHOUT
    constructing ImportService — so it never retries and never grades. This
    is the path that runs before the exam lookup; if it regressed, a corrupt
    payload would leave the job stuck ``queued`` forever."""
    job_id = _create_pending_job(
        test_db, institution_id=institution.id, exam_id=exam_simple.id
    )

    with (
        patch("tasks.import_submissions_task.SessionLocal", return_value=test_db),
        patch.object(test_db, "close"),
        patch("tasks.import_submissions_task.ImportService") as service_cls,
    ):
        with pytest.raises((binascii.Error, ValueError)):
            import_submissions.run(
                exam_id=exam_simple.id,
                driver_name="moodle_json",
                source_b64="!!! not valid base64 !!!",
                import_job_id=job_id,
                triggered_by=None,
            )
        # Permanent error: grading must never start.
        service_cls.assert_not_called()

    test_db.expire_all()
    job = test_db.get(ImportJob, job_id)
    assert job is not None
    assert job.status == "failed"
    assert job.error_log
    assert job.error_log[-1]["step"] == "decode"


def test_transient_error_marks_failed_only_on_retry_exhaustion(
    test_db: Session, institution: Institution, exam_simple: Exam
) -> None:
    """The transient-error branch records a *terminal* failure only once
    retries are exhausted (``retries >= max_retries``); below that it leaves
    the row for Celery to retry. Invoked via ``run.__wrapped__`` with a fake
    ``self`` so we drive ``request.retries`` directly and bypass autoretry's
    broker re-dispatch."""
    # ``run.__wrapped__`` is bound to the task instance; ``.__func__`` is the
    # unbound body, so we can drive ``self.request.retries`` via a fake self.
    raw = import_submissions.run.__wrapped__.__func__
    transient = OperationalError("SELECT 1", {}, Exception("db gone"))

    def _run_with_retries(job_id: int, retries: int) -> None:
        fake_self = SimpleNamespace(
            request=SimpleNamespace(retries=retries),
            max_retries=2,
        )
        with (
            patch("tasks.import_submissions_task.SessionLocal", return_value=test_db),
            patch.object(test_db, "close"),
            patch("tasks.import_submissions_task.ImportService") as service_cls,
        ):
            service_cls.return_value.commit.side_effect = transient
            with pytest.raises(OperationalError):
                raw(
                    fake_self,
                    exam_id=exam_simple.id,
                    driver_name="moodle_json",
                    source_b64=_JSON_B64,
                    import_job_id=job_id,
                    triggered_by=None,
                )

    # Not yet exhausted: row left non-terminal, no celery_retry entry.
    job_id_a = _create_pending_job(
        test_db, institution_id=institution.id, exam_id=exam_simple.id
    )
    _run_with_retries(job_id_a, retries=0)
    test_db.expire_all()
    job_a = test_db.get(ImportJob, job_id_a)
    assert job_a is not None
    assert job_a.status == "queued"  # untouched — commit was mocked out
    assert not any(
        (e or {}).get("step") == "celery_retry" for e in (job_a.error_log or [])
    )

    # Exhausted: terminal failure recorded with step='celery_retry'.
    job_id_b = _create_pending_job(
        test_db, institution_id=institution.id, exam_id=exam_simple.id
    )
    _run_with_retries(job_id_b, retries=2)
    test_db.expire_all()
    job_b = test_db.get(ImportJob, job_id_b)
    assert job_b is not None
    assert job_b.status == "failed"
    assert job_b.error_log
    assert job_b.error_log[-1]["step"] == "celery_retry"


def test_reaper_age_fails_stuck_jobs_only(
    test_db: Session, institution: Institution, exam_simple: Exam
) -> None:
    """``reap_stuck_import_jobs`` (TF-412 watchdog) age-fails rows stuck in
    queued/running past the threshold, so the polling client always converges
    on a terminal status even if the task message was lost. It must NOT touch
    recent rows or already-terminal rows."""
    from enums import ImportJobStatus
    from tasks.maintenance_tasks import (
        _IMPORT_STUCK_THRESHOLD,
        reap_stuck_import_jobs,
    )

    now = datetime.now(timezone.utc)
    old = now - _IMPORT_STUCK_THRESHOLD - timedelta(minutes=10)

    def _job(status: str, created_at: datetime) -> int:
        job = ImportJob(
            institution_id=institution.id,
            exam_id=exam_simple.id,
            driver_name="moodle_json",
            status=status,
            rows_processed=0,
            rows_failed=0,
            error_log=[],
            source_metadata={},
            created_at=created_at,
        )
        test_db.add(job)
        test_db.commit()
        test_db.refresh(job)
        return job.id

    stuck_queued = _job(ImportJobStatus.QUEUED.value, old)
    stuck_running = _job(ImportJobStatus.RUNNING.value, old)
    fresh_queued = _job(ImportJobStatus.QUEUED.value, now)
    old_succeeded = _job(ImportJobStatus.SUCCEEDED.value, old)

    with (
        patch("tasks.maintenance_tasks.SessionLocal", return_value=test_db),
        patch.object(test_db, "close"),
    ):
        result = reap_stuck_import_jobs.run()

    assert result["reaped"] == 2
    test_db.expire_all()
    assert test_db.get(ImportJob, stuck_queued).status == "failed"
    assert test_db.get(ImportJob, stuck_running).status == "failed"
    # Recent queued + already-terminal rows are untouched.
    assert test_db.get(ImportJob, fresh_queued).status == "queued"
    assert test_db.get(ImportJob, old_succeeded).status == "succeeded"
    # Reaped row carries a diagnostic entry the UI can render.
    reaped = test_db.get(ImportJob, stuck_queued)
    assert reaped.error_log
    assert reaped.error_log[-1]["step"] == "reaper"


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
                driver_name="moodle_json",
                source_b64=_JSON_B64,
                import_job_id=job_id,
                triggered_by=None,
            )

    fake_session.close.assert_called_once()
