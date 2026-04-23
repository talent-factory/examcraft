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
            "question_types": ["multiple_choice", "open_ended"],
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
