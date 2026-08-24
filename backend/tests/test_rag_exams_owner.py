"""
Owner-check tests for rag_exams.retry_generation.

Verifies: enforce_resource_access is called correctly, so that a
QuestionGenerationJob owned by another user returns 403 for a non-superuser
and is waved through for a superuser (with an audit log entry).
"""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from api.rag_exams import retry_generation
from models.auth import Institution, User, UserStatus
from models.question_generation_job import QuestionGenerationJob


@pytest.fixture
def stage(test_db):
    # No hardcoded PK IDs: the shared CI test DB accumulates rows from
    # non-isolated fixtures of other modules; a fixed ``id=320`` would then
    # collide with a leaked institution (UniqueViolation institutions_pkey).
    # Autoincrement + referencing via ``.id`` avoids collisions.
    inst = Institution(
        name="RagOwner",
        slug="ragowner",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.flush()
    owner = User(
        email="owner@r.ch",
        first_name="O",
        last_name="W",
        password_hash="x",
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    other = User(
        email="other@r.ch",
        first_name="X",
        last_name="Y",
        password_hash="x",
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    admin = User(
        email="admin@r.ch",
        first_name="A",
        last_name="D",
        password_hash="x",
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=True,
    )
    test_db.add_all([owner, other, admin])
    test_db.flush()
    job = QuestionGenerationJob(
        task_id="rag-task-foreign",
        user_id=owner.id,
        topic="Test",
        question_count=5,
        status="FAILURE",
        request_data={"question_count": 5},
    )
    test_db.add(job)
    test_db.commit()
    return SimpleNamespace(owner=owner, other=other, admin=admin, job=job)


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def test_retry_foreign_failed_job_as_other_user_403(stage, test_db):
    s = stage
    with pytest.raises(HTTPException) as exc:
        _run(
            retry_generation(
                task_id=s.job.task_id,
                http_request=None,
                current_user=s.other,
                db=test_db,
            )
        )
    assert exc.value.status_code == 403


def test_retry_unknown_task_returns_404(stage, test_db):
    s = stage
    with pytest.raises(HTTPException) as exc:
        _run(
            retry_generation(
                task_id="does-not-exist",
                http_request=None,
                current_user=s.owner,
                db=test_db,
            )
        )
    assert exc.value.status_code == 404


def test_retry_own_failed_job_as_owner_succeeds(stage, test_db, mocker):
    """Owner may retry their own FAILURE job → 200 + new task_id, no
    bypass audit entry (owner is not a superuser)."""
    from models.auth import AuditLog

    s = stage
    # Mock the Celery broker — the test checks endpoint logic, not the worker.
    mocker.patch("api.rag_exams.generate_questions_task")

    response = _run(
        retry_generation(
            task_id=s.job.task_id,
            http_request=None,
            current_user=s.owner,
            db=test_db,
        )
    )
    assert response.task_id != s.job.task_id  # A new task was created.
    bypass_logs = (
        test_db.query(AuditLog).filter(AuditLog.action == "superuser_bypass").all()
    )
    assert bypass_logs == []  # Owner is not a superuser → no bypass.


def test_retry_foreign_failed_job_as_superuser_logs_bypass(stage, test_db, mocker):
    """Superuser may retry another user's FAILURE job + a bypass audit entry
    is created with resource_type=question_generation_job, action=retry, owner=320."""
    import json
    from models.auth import AuditLog

    s = stage
    mocker.patch("api.rag_exams.generate_questions_task")

    response = _run(
        retry_generation(
            task_id=s.job.task_id,
            http_request=None,
            current_user=s.admin,
            db=test_db,
        )
    )
    assert response.task_id != s.job.task_id

    bypass_logs = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == "superuser_bypass")
        .filter(AuditLog.resource_type == "question_generation_job")
        .all()
    )
    assert len(bypass_logs) == 1
    log = bypass_logs[0]
    assert log.user_id == s.admin.id
    assert log.resource_id == str(s.job.id)
    extra = json.loads(log.additional_data)
    assert extra["bypassed_action"] == "retry"
    assert extra["owner_user_id"] == s.owner.id


def test_retry_foreign_job_as_superuser_aborts_when_audit_fails(stage, test_db, mocker):
    """GDPR: If the bypass audit log cannot be persisted, an HTTPException 500
    MUST be raised — no retry without an audit trail."""
    s = stage
    mocker.patch("api.rag_exams.generate_questions_task")
    mocker.patch("services.audit_service.AuditService.log_action", return_value=None)

    with pytest.raises(HTTPException) as exc:
        _run(
            retry_generation(
                task_id=s.job.task_id,
                http_request=None,
                current_user=s.admin,
                db=test_db,
            )
        )
    assert exc.value.status_code == 500
