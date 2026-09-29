"""
TF-736: panel window for under-filled generations and server-side dismissal.

Against the real test database — the window lives in the SQL filter of
``/active-tasks``, which the mock-based tests in ``test_active_tasks.py``
cannot see.

Verifies:
1. An own SUCCESS with context_limited stays listed past the 30-minute window
   (up to CONTEXT_LIMITED_TASK_MAX_AGE); a normal SUCCESS of the same age does
   not.
2. The longer window covers only the caller's own jobs — a superuser listing
   does not collect every user's under-filled runs.
3. ``POST /tasks/{task_id}/dismiss`` records the owner's dismissal, and the
   job stays out of ``/active-tasks`` on the next call (= after a reload).
4. Foreign and unfinished jobs are not marked.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from api.rag_exams import (
    COMPLETED_TASK_MAX_AGE,
    CONTEXT_LIMITED_TASK_MAX_AGE,
    dismiss_task,
    get_active_tasks,
)
from models.auth import Institution, User, UserStatus
from models.question_generation_job import QuestionGenerationJob


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def _ago(delta: timedelta) -> datetime:
    return datetime.now(timezone.utc) - delta


# Past the 30-minute window, well inside the 8-hour one.
PAST_COMPLETED_WINDOW = COMPLETED_TASK_MAX_AGE + timedelta(minutes=15)


@pytest.fixture
def stage(test_db):
    # Unique per test run: the CI database is shared, and email, slug and
    # task_id are unique columns.
    sfx = uuid4().hex[:8]
    inst = Institution(
        name=f"Tf736Window-{sfx}",
        slug=f"tf736-window-{sfx}",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.flush()

    def user(email: str, superuser: bool = False) -> User:
        u = User(
            email=email,
            first_name="T",
            last_name="F",
            password_hash="x",
            institution_id=inst.id,
            status=UserStatus.ACTIVE.value,
            is_superuser=superuser,
        )
        test_db.add(u)
        return u

    owner = user(f"tf736-owner-{sfx}@window.ch")
    other = user(f"tf736-other-{sfx}@window.ch")
    admin = user(f"tf736-admin-{sfx}@window.ch", superuser=True)
    test_db.flush()
    return SimpleNamespace(
        owner=owner,
        other=other,
        admin=admin,
        tid=lambda name: f"{name}-{sfx}",
    )


def _job(test_db, task_id: str, user: User, age: timedelta, **fields):
    job = QuestionGenerationJob(
        task_id=task_id,
        user_id=user.id,
        topic="Fenster",
        question_count=15,
        request_data={"question_count": 15},
        **fields,
    )
    job.created_at = _ago(age)
    test_db.add(job)
    test_db.commit()
    return job


def _listed_ids(test_db, user: User) -> set:
    response = _run(get_active_tasks(http_request=None, current_user=user, db=test_db))
    return {task.task_id for task in response.tasks}


class TestContextLimitedWindow:
    def test_under_filled_job_is_still_listed_after_30_minutes(self, stage, test_db):
        _job(
            test_db,
            stage.tid("tf736-limited"),
            stage.owner,
            PAST_COMPLETED_WINDOW,
            status="SUCCESS",
            context_limited=True,
            generated_question_count=6,
        )
        _job(
            test_db,
            stage.tid("tf736-normal"),
            stage.owner,
            PAST_COMPLETED_WINDOW,
            status="SUCCESS",
            generated_question_count=15,
        )

        listed = _listed_ids(test_db, stage.owner)

        assert stage.tid("tf736-limited") in listed
        # Negative control: the same age without the flag has left the panel.
        assert stage.tid("tf736-normal") not in listed

    def test_window_is_eight_hours(self):
        # Product decision (TF-736): a working day, gone by the next morning.
        assert CONTEXT_LIMITED_TASK_MAX_AGE == timedelta(hours=8)

    def test_under_filled_job_is_listed_just_inside_the_long_window(
        self, stage, test_db
    ):
        _job(
            test_db,
            stage.tid("tf736-limited-late"),
            stage.owner,
            CONTEXT_LIMITED_TASK_MAX_AGE - timedelta(minutes=5),
            status="SUCCESS",
            context_limited=True,
        )

        assert stage.tid("tf736-limited-late") in _listed_ids(test_db, stage.owner)

    def test_under_filled_job_leaves_after_the_long_window(self, stage, test_db):
        _job(
            test_db,
            stage.tid("tf736-limited-old"),
            stage.owner,
            CONTEXT_LIMITED_TASK_MAX_AGE + timedelta(minutes=5),
            status="SUCCESS",
            context_limited=True,
        )

        assert stage.tid("tf736-limited-old") not in _listed_ids(test_db, stage.owner)

    def test_failed_job_does_not_get_the_long_window(self, stage, test_db):
        # context_limited is only ever set on SUCCESS; the filter must not
        # rely on that.
        _job(
            test_db,
            stage.tid("tf736-failed"),
            stage.owner,
            PAST_COMPLETED_WINDOW,
            status="FAILURE",
            context_limited=True,
        )

        assert stage.tid("tf736-failed") not in _listed_ids(test_db, stage.owner)

    def test_superuser_gets_the_long_window_only_for_own_jobs(self, stage, test_db):
        _job(
            test_db,
            stage.tid("tf736-foreign-limited"),
            stage.other,
            PAST_COMPLETED_WINDOW,
            status="SUCCESS",
            context_limited=True,
        )
        _job(
            test_db,
            stage.tid("tf736-admin-limited"),
            stage.admin,
            PAST_COMPLETED_WINDOW,
            status="SUCCESS",
            context_limited=True,
        )

        listed = _listed_ids(test_db, stage.admin)

        assert stage.tid("tf736-admin-limited") in listed
        assert stage.tid("tf736-foreign-limited") not in listed


class TestDismiss:
    def test_dismissed_entry_stays_away_after_reload(self, stage, test_db):
        job = _job(
            test_db,
            stage.tid("tf736-dismiss"),
            stage.owner,
            PAST_COMPLETED_WINDOW,
            status="SUCCESS",
            context_limited=True,
        )
        assert stage.tid("tf736-dismiss") in _listed_ids(test_db, stage.owner)

        _run(
            dismiss_task(
                task_id=job.task_id,
                http_request=None,
                current_user=stage.owner,
                db=test_db,
            )
        )

        test_db.refresh(job)
        assert job.dismissed_at is not None
        # A reload is nothing but the next /active-tasks call.
        assert stage.tid("tf736-dismiss") not in _listed_ids(test_db, stage.owner)

    def test_dismissal_also_applies_inside_the_30_minute_window(self, stage, test_db):
        job = _job(
            test_db,
            stage.tid("tf736-dismiss-fresh"),
            stage.owner,
            timedelta(minutes=2),
            status="FAILURE",
        )
        _run(
            dismiss_task(
                task_id=job.task_id,
                http_request=None,
                current_user=stage.owner,
                db=test_db,
            )
        )

        assert stage.tid("tf736-dismiss-fresh") not in _listed_ids(test_db, stage.owner)

    def test_dismiss_is_idempotent(self, stage, test_db):
        job = _job(
            test_db,
            stage.tid("tf736-dismiss-twice"),
            stage.owner,
            timedelta(minutes=2),
            status="SUCCESS",
        )
        for _ in range(2):
            _run(
                dismiss_task(
                    task_id=job.task_id,
                    http_request=None,
                    current_user=stage.owner,
                    db=test_db,
                )
            )
        test_db.refresh(job)
        assert job.dismissed_at is not None

    def test_foreign_job_is_404_for_normal_user(self, stage, test_db):
        job = _job(
            test_db,
            stage.tid("tf736-foreign"),
            stage.other,
            timedelta(minutes=2),
            status="SUCCESS",
        )
        with pytest.raises(HTTPException) as exc:
            _run(
                dismiss_task(
                    task_id=job.task_id,
                    http_request=None,
                    current_user=stage.owner,
                    db=test_db,
                )
            )
        assert exc.value.status_code == 404
        test_db.refresh(job)
        assert job.dismissed_at is None

    def test_unknown_job_is_404(self, stage, test_db):
        with pytest.raises(HTTPException) as exc:
            _run(
                dismiss_task(
                    task_id=stage.tid("tf736-does-not-exist"),
                    http_request=None,
                    current_user=stage.owner,
                    db=test_db,
                )
            )
        assert exc.value.status_code == 404

    def test_superuser_does_not_hide_a_foreign_notice(self, stage, test_db):
        job = _job(
            test_db,
            stage.tid("tf736-foreign-by-admin"),
            stage.other,
            PAST_COMPLETED_WINDOW,
            status="SUCCESS",
            context_limited=True,
        )
        _run(
            dismiss_task(
                task_id=job.task_id,
                http_request=None,
                current_user=stage.admin,
                db=test_db,
            )
        )

        test_db.refresh(job)
        assert job.dismissed_at is None
        assert stage.tid("tf736-foreign-by-admin") in _listed_ids(test_db, stage.other)

    def test_unfinished_job_is_not_hidden(self, stage, test_db):
        # The panel also offers "close" when it lost the connection (UNKNOWN);
        # the job may still be running and must come back once it finishes.
        job = _job(
            test_db,
            stage.tid("tf736-running"),
            stage.owner,
            timedelta(minutes=2),
            status="PENDING",
        )
        _run(
            dismiss_task(
                task_id=job.task_id,
                http_request=None,
                current_user=stage.owner,
                db=test_db,
            )
        )

        test_db.refresh(job)
        assert job.dismissed_at is None
        with patch("celery.result.AsyncResult") as async_result:
            async_result.return_value = Mock(state="PROGRESS", info={})
            assert stage.tid("tf736-running") in _listed_ids(test_db, stage.owner)
