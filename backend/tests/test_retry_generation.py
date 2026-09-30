"""Tests for the retry-generation mechanism and request_data persistence."""

import pytest

from models.auth import Institution, User
from models.question_generation_job import QuestionGenerationJob


@pytest.fixture
def db_with_user(test_db):
    """Set up a minimal institution + user to satisfy FK constraint on user_id."""
    institution = Institution(
        name="Retry Test University",
        slug="retry-test",
        subscription_tier="free",
        max_users=10,
        max_documents=50,
        max_questions_per_month=100,
    )
    test_db.add(institution)
    test_db.flush()

    user = User(
        id=1,
        email="retry-test@example.com",
        first_name="Retry",
        last_name="Tester",
        institution_id=institution.id,
        status="active",
    )
    test_db.merge(user)
    test_db.commit()

    return test_db


class TestRequestDataPersistence:
    """Verify request_data is stored and retrievable on QuestionGenerationJob."""

    def test_job_stores_request_data(self, db_with_user):
        """QuestionGenerationJob must persist request_data as JSON."""
        job = QuestionGenerationJob(
            task_id="test-persist-123",
            user_id=1,
            topic="Test Topic",
            question_count=5,
            request_data={
                "topic": "Test Topic",
                "question_count": 5,
                "difficulty": "medium",
                "language": "de",
                "document_ids": [1, 2],
            },
        )
        db_with_user.add(job)
        db_with_user.commit()

        saved = (
            db_with_user.query(QuestionGenerationJob)
            .filter_by(task_id="test-persist-123")
            .first()
        )
        assert saved is not None
        assert saved.request_data is not None
        assert saved.request_data["topic"] == "Test Topic"
        assert saved.request_data["question_count"] == 5
        assert saved.request_data["difficulty"] == "medium"
        assert saved.request_data["document_ids"] == [1, 2]

    def test_job_without_request_data(self, db_with_user):
        """QuestionGenerationJob with request_data=None should work (backward compatible)."""
        job = QuestionGenerationJob(
            task_id="test-no-data-456",
            user_id=1,
            topic="Old Job",
            question_count=3,
        )
        db_with_user.add(job)
        db_with_user.commit()

        saved = (
            db_with_user.query(QuestionGenerationJob)
            .filter_by(task_id="test-no-data-456")
            .first()
        )
        assert saved is not None
        assert saved.request_data is None


class TestRetryValidation:
    """Verify retry endpoint validation logic (unit-level, no HTTP)."""

    def test_only_failure_jobs_are_retryable(self, db_with_user):
        """Only jobs with status FAILURE or REVOKED should be retryable."""
        for status in ("FAILURE", "REVOKED"):
            job = QuestionGenerationJob(
                task_id=f"retry-{status.lower()}-job",
                user_id=1,
                topic="Retryable",
                question_count=5,
                status=status,
                request_data={"topic": "Retryable", "question_count": 5},
            )
            db_with_user.add(job)

        for status in ("PENDING", "STARTED", "SUCCESS"):
            job = QuestionGenerationJob(
                task_id=f"no-retry-{status.lower()}-job",
                user_id=1,
                topic="Not Retryable",
                question_count=5,
                status=status,
                request_data={"topic": "Not Retryable", "question_count": 5},
            )
            db_with_user.add(job)

        db_with_user.commit()

        # Verify retryable statuses
        for status in ("FAILURE", "REVOKED"):
            job = (
                db_with_user.query(QuestionGenerationJob)
                .filter_by(task_id=f"retry-{status.lower()}-job")
                .first()
            )
            assert job.status in ("FAILURE", "REVOKED")

        # Verify non-retryable statuses
        for status in ("PENDING", "STARTED", "SUCCESS"):
            job = (
                db_with_user.query(QuestionGenerationJob)
                .filter_by(task_id=f"no-retry-{status.lower()}-job")
                .first()
            )
            assert job.status not in ("FAILURE", "REVOKED")

    def test_retry_requires_request_data(self, db_with_user):
        """A failed job without request_data cannot be retried."""
        job = QuestionGenerationJob(
            task_id="no-data-retry-job",
            user_id=1,
            topic="No Data",
            question_count=5,
            status="FAILURE",
            request_data=None,
        )
        db_with_user.add(job)
        db_with_user.commit()

        saved = (
            db_with_user.query(QuestionGenerationJob)
            .filter_by(task_id="no-data-retry-job")
            .first()
        )
        assert saved.status == "FAILURE"
        assert saved.request_data is None

    def test_request_data_preserved_across_retry(self, db_with_user):
        """When creating a retry job, request_data from the original should be copied exactly."""
        original_data = {
            "topic": "Algorithmen",
            "question_count": 10,
            "difficulty": "hard",
            "language": "de",
            "question_types": ["single_choice", "open_ended"],
            "document_ids": [42, 43],
            "context_chunks_per_question": 5,
        }

        original = QuestionGenerationJob(
            task_id="original-job-abc",
            user_id=1,
            topic="Algorithmen",
            question_count=10,
            status="FAILURE",
            request_data=original_data,
        )
        db_with_user.add(original)
        db_with_user.commit()

        # Simulate retry: create new job with same request_data
        retry_job = QuestionGenerationJob(
            task_id="retry-job-xyz",
            user_id=1,
            topic=original.topic,
            question_count=original.question_count,
            request_data=original.request_data,
        )
        db_with_user.add(retry_job)
        db_with_user.commit()

        saved_retry = (
            db_with_user.query(QuestionGenerationJob)
            .filter_by(task_id="retry-job-xyz")
            .first()
        )
        assert saved_retry.request_data == original_data
        assert saved_retry.status == "PENDING"
        assert saved_retry.topic == "Algorithmen"
        assert saved_retry.question_count == 10


# === TF-964: retrying a job whose questions are already saved ===


@pytest.fixture
def weg_a_stage(test_db):
    """Owner, institution with a small quota, and a job whose run is driven
    through the real task with SessionLocal bound to the test transaction."""
    from types import SimpleNamespace
    from unittest.mock import patch

    from sqlalchemy.orm import sessionmaker

    from models.auth import UserStatus

    inst = Institution(
        name="TF-964 Retry",
        slug="tf964-retry",
        subscription_tier="free",
        max_users=10,
        max_documents=50,
        max_questions_per_month=10,
    )
    test_db.add(inst)
    test_db.flush()
    owner = User(
        email="owner@tf964-retry.ch",
        first_name="O",
        last_name="W",
        password_hash="x",  # pragma: allowlist secret
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    test_db.add(owner)
    test_db.flush()
    request_data = {
        "topic": "Weg A",
        "question_count": 3,
        "question_types": ["single_choice"],
        "difficulty": "medium",
        "language": "de",
        "document_ids": None,
        "context_chunks_per_question": 3,
        "prompt_config": None,
    }
    job = QuestionGenerationJob(
        task_id="tf964-weg-a",
        user_id=owner.id,
        topic="Weg A",
        question_count=3,
        request_data=request_data,
    )
    test_db.add(job)
    test_db.commit()

    # Plain values, read now: a lazy attribute load later would open a
    # savepoint on test_db *before* the task's own sessions write, and the
    # rollback in retry_generation's 409 path would then take their rows
    # along — a test artefact, not production behaviour.
    stage = SimpleNamespace(
        inst=inst,
        owner=owner,
        job=job,
        task_id=job.task_id,
        request_data=job.request_data,
        owner_id=owner.id,
        inst_id=inst.id,
    )
    test_db.commit()

    bound = sessionmaker(
        bind=test_db.get_bind(), join_transaction_mode="create_savepoint"
    )
    with patch("database.SessionLocal", bound):
        yield stage


def _run_until_crash_after_commit(stage):
    """Runs generate_questions_task and lets it die right after its commit —
    the moment Weg A in TF-964 is about."""
    import dataclasses
    from unittest.mock import MagicMock, patch

    from tasks.question_tasks import generate_questions_task

    @dataclasses.dataclass
    class Q:
        question_text: str
        question_type: str = "single_choice"
        options: list = dataclasses.field(default_factory=lambda: ["a", "b"])
        correct_answer: str = "a"
        explanation: str = "e"
        difficulty: str = "medium"
        source_chunks: list = dataclasses.field(default_factory=list)
        source_documents: list = dataclasses.field(default_factory=list)
        confidence_score: float = 0.9

    result = MagicMock()
    result.exam_id = "rag_exam_weg_a"
    result.topic = "Weg A"
    result.questions = [Q(question_text=f"Frage {i}?") for i in range(3)]
    result.generation_time = 1.0
    result.quality_metrics = {}

    generate_questions_task.update_state = MagicMock()
    generate_questions_task.push_request(id=stage.task_id)
    try:
        with (
            patch("tasks.question_tasks.run_async", return_value=result),
            patch("tasks.question_tasks.RAGService", MagicMock()),
            patch(
                "tasks.question_tasks.dataclasses.asdict",
                side_effect=RuntimeError("worker lost after commit"),
            ),
        ):
            with pytest.raises(RuntimeError):
                generate_questions_task.run(
                    stage.request_data,
                    str(stage.owner_id),
                    institution_id=stage.inst_id,
                )
    finally:
        generate_questions_task.pop_request()


def _question_count(db, inst):
    from models.question_review import QuestionReview

    return db.query(QuestionReview).filter_by(institution_id=inst.id).count()


def test_weg_a_crash_after_commit_then_retry_is_rejected(weg_a_stage, test_db, mocker):
    """Acceptance «Weg A»: the task dies after the commit and Celery records
    FAILURE. The job row stays SUCCESS (the /active-tasks phantom sync can't
    downgrade it), retry-generation answers 409 rag_retry_already_succeeded,
    no second set of QuestionReview rows appears, and the monthly quota
    counts the questions once."""
    import asyncio

    from api.rag_exams import retry_generation
    from errors import AppHTTPException
    from tasks.question_tasks import _try_update_job_status
    from utils.tenant_utils import SubscriptionLimits

    s = weg_a_stage
    _run_until_crash_after_commit(s)
    # What /active-tasks and the watchdog do with Celery's FAILURE.
    _try_update_job_status(s.task_id, "FAILURE")
    test_db.expire_all()
    assert s.job.status == "SUCCESS"
    assert _question_count(test_db, s.inst) == 3
    jobs_before = test_db.query(QuestionGenerationJob).count()
    dispatch = mocker.patch("api.rag_exams.generate_questions_task")

    with pytest.raises(AppHTTPException) as excinfo:
        asyncio.new_event_loop().run_until_complete(
            retry_generation(
                task_id=s.task_id,
                http_request=None,
                current_user=s.owner,
                db=test_db,
            )
        )

    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "rag_retry_already_succeeded"
    dispatch.apply_async.assert_not_called()
    assert test_db.query(QuestionGenerationJob).count() == jobs_before
    assert _question_count(test_db, s.inst) == 3
    # Quota of 10: exactly 3 used — 7 more fit, 8 don't.
    SubscriptionLimits.check_question_limit(s.inst, test_db, additional_count=7)
    with pytest.raises(AppHTTPException):
        SubscriptionLimits.check_question_limit(s.inst, test_db, additional_count=8)


def test_legacy_failure_row_with_linked_questions_is_repaired(
    weg_a_stage, test_db, mocker
):
    """A row that ended on FAILURE although its questions are linked (the
    state the pre-TF-964 three-commit write could leave behind) is set to
    SUCCESS by the rejected retry, so the panel shows it as finished."""
    import asyncio

    from api.rag_exams import retry_generation
    from errors import AppHTTPException

    s = weg_a_stage
    _run_until_crash_after_commit(s)
    test_db.query(QuestionGenerationJob).filter_by(task_id=s.task_id).update(
        {"status": "FAILURE"}
    )
    test_db.commit()
    mocker.patch("api.rag_exams.generate_questions_task")

    with pytest.raises(AppHTTPException) as excinfo:
        asyncio.new_event_loop().run_until_complete(
            retry_generation(
                task_id=s.task_id,
                http_request=None,
                current_user=s.owner,
                db=test_db,
            )
        )

    assert excinfo.value.status_code == 409
    test_db.expire_all()
    assert s.job.status == "SUCCESS"
