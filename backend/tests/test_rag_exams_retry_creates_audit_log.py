"""TF-337 regression guard: retry_generation writes a create_question AuditLog.

Before TF-337, only the initial trigger in ``generate_rag_exam`` wrote
the AuditLog. Retried generations (``api/rag_exams.py:retry_generation``)
were invisible — they showed up in QuestionGenerationJob but neither in
the dashboard activity widget nor on the new ``/aktivitaeten`` page.
This test pins the new behaviour so the next refactor doesn't quietly
drop the audit row again.
"""

import asyncio
import json
from types import SimpleNamespace

import pytest

from api.rag_exams import retry_generation
from models.auth import AuditLog, Institution, User, UserStatus
from models.question_generation_job import QuestionGenerationJob


@pytest.fixture
def stage(test_db):
    """Owner-style fixture mirroring test_rag_exams_owner.stage."""
    inst = Institution(
        id=420,
        name="RetryAudit",
        slug="retryaudit",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    owner = User(
        id=420,
        email="owner@retry.ch",
        first_name="O",
        last_name="W",
        password_hash="x",  # pragma: allowlist secret
        institution_id=420,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    test_db.add(owner)
    test_db.flush()
    job = QuestionGenerationJob(
        id=650,
        task_id="rag-task-original",
        user_id=owner.id,
        topic="Audit-Coverage",
        question_count=7,
        status="FAILURE",
        request_data={"question_count": 7, "topic": "Audit-Coverage"},
    )
    test_db.add(job)
    test_db.commit()
    return SimpleNamespace(owner=owner, job=job)


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def test_retry_writes_create_question_audit_log(stage, test_db, mocker):
    """After a successful retry an AuditLog with action=create_question
    exists for the new task_id, scoped to the original owner.

    Regression guard for TF-337: without this row, retried generations
    are invisible to the dashboard widget and to /aktivitaeten.
    """
    s = stage
    mocker.patch("api.rag_exams.generate_questions_task")

    # Sanity: no create_question logs exist yet.
    assert (
        test_db.query(AuditLog).filter(AuditLog.action == "create_question").count()
        == 0
    )

    response = _run(
        retry_generation(
            task_id=s.job.task_id,
            http_request=None,
            current_user=s.owner,
            db=test_db,
        )
    )
    new_task_id = response.task_id
    assert new_task_id != s.job.task_id

    logs = test_db.query(AuditLog).filter(AuditLog.action == "create_question").all()
    assert len(logs) == 1
    log = logs[0]
    assert log.user_id == s.owner.id
    assert log.resource_id == new_task_id
    assert log.status == "success"

    # additional_data carries the topic + question_count so the
    # activity-feed title resolution works without an extra DB hop,
    # plus the retry_of_task_id breadcrumb for forensic queries.
    extra = json.loads(log.additional_data)
    assert extra["topic"] == "Audit-Coverage"
    assert extra["question_count"] == 7
    assert extra["retry_of_task_id"] == s.job.task_id


def test_retry_succeeds_when_audit_write_fails(stage, test_db, mocker):
    """Audit failure must NOT 500 the retry — the Celery task is
    already enqueued and a 500 would prompt the user to retry, double-
    charging quota. Pin this so a refactor that lifts the audit call
    out of the narrow try/except surfaces in CI.

    Failure mode caught: a regression that re-raises AuditService
    failures, or moves the audit write before the Celery enqueue.
    """
    s = stage
    mocker.patch("api.rag_exams.generate_questions_task")
    mocker.patch(
        "services.audit_service.AuditService.log_action",
        side_effect=RuntimeError("audit DB down"),
    )

    response = _run(
        retry_generation(
            task_id=s.job.task_id,
            http_request=None,
            current_user=s.owner,
            db=test_db,
        )
    )
    # Retry succeeded — task_id returned, new job row exists.
    assert response.task_id != s.job.task_id
    assert (
        test_db.query(QuestionGenerationJob)
        .filter(QuestionGenerationJob.task_id == response.task_id)
        .count()
        == 1
    )
    # No audit row was written (the patched call raised).
    assert (
        test_db.query(AuditLog).filter(AuditLog.action == "create_question").count()
        == 0
    )
