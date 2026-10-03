"""
TF-972: ``/active-tasks`` delivers ``created_at`` with a UTC offset.

The column used to be ``timestamp without time zone``. Postgres handed the
UTC wall-clock time back naive, Pydantic serialized it without an offset, and
the browser's ``new Date(...)`` read "19:21" as local time — two hours early
in Swiss summer time.

Against the real test database: the mock-based tests in
``test_active_tasks.py`` set an aware ``created_at`` on a Mock and never see
what the column actually returns.

Verifies:
1. The value read back from the database is timezone-aware and unchanged.
2. The serialized ``ActiveTaskInfo`` converts to Europe/Zurich local time —
   once in summer (UTC+2) and once in winter (UTC+1), so the fix is not tied
   to a fixed two-hour shift.
3. ``/active-tasks`` itself delivers the offset, for finished and running
   jobs, and its age cutoffs still apply against the aware column.
4. The migration converts existing naive rows as UTC, independent of the
   session time zone, and the downgrade reverses it exactly.
"""

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text

from api.rag_exams import COMPLETED_TASK_MAX_AGE, get_active_tasks
from models.auth import Institution, User, UserStatus
from models.question_generation_job import QuestionGenerationJob
from schemas.active_tasks import ActiveTaskInfo

ZURICH = ZoneInfo("Europe/Zurich")

# 19:21 UTC, the time of the bug report — once in summer, once in winter.
SUMMER_UTC = datetime(2026, 9, 29, 19, 21, tzinfo=timezone.utc)
WINTER_UTC = datetime(2026, 1, 15, 19, 21, tzinfo=timezone.utc)

_MIGRATION_PATH = (
    Path(__file__).resolve().parent.parent
    / "alembic"
    / "versions"
    / "2026_10_02_tf972_job_created_at_timestamptz.py"
)


@pytest.fixture
def owner(test_db):
    # Unique per run: the CI database is shared, email and slug are unique.
    sfx = uuid4().hex[:8]
    inst = Institution(
        name=f"Tf972Tz-{sfx}",
        slug=f"tf972-tz-{sfx}",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.flush()
    user = User(
        email=f"tf972-owner-{sfx}@tz.ch",
        first_name="Tz",
        last_name="Owner",
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
    )
    test_db.add(user)
    test_db.flush()
    return user


def _stored_job(
    test_db, user: User, created_at: datetime, status: str = "SUCCESS"
) -> QuestionGenerationJob:
    job = QuestionGenerationJob(
        task_id=f"tf972-{uuid4().hex[:8]}",
        user_id=user.id,
        topic="Heapsort",
        question_count=3,
        status=status,
    )
    job.created_at = created_at
    test_db.add(job)
    test_db.commit()
    test_db.expire_all()
    return test_db.get(QuestionGenerationJob, job.id)


def _local_wall_clock(serialized: str) -> str:
    parsed = datetime.fromisoformat(serialized)
    # Without an offset the browser guesses local time — the bug.
    assert parsed.tzinfo is not None, f"created_at without offset: {serialized!r}"
    return parsed.astimezone(ZURICH).strftime("%H:%M")


async def _listed_tasks(owner, test_db) -> dict:
    response = await get_active_tasks(http_request=None, current_user=owner, db=test_db)
    payload = json.loads(response.model_dump_json())
    return {t["task_id"]: t for t in payload["tasks"]}


def test_model_column_is_timezone_aware():
    """Cheap guard without a database: the column type itself."""
    assert QuestionGenerationJob.__table__.c.created_at.type.timezone is True


class TestCreatedAtRoundTrip:
    def test_value_comes_back_timezone_aware(self, owner, test_db):
        job = _stored_job(test_db, owner, SUMMER_UTC)

        assert job.created_at.tzinfo is not None
        assert job.created_at == SUMMER_UTC

    @pytest.mark.parametrize(
        ("created_at", "expected_local"),
        [(SUMMER_UTC, "21:21"), (WINTER_UTC, "20:21")],
        ids=["summer-utc+2", "winter-utc+1"],
    )
    def test_serialized_value_shows_local_time_in_zurich(
        self, owner, test_db, created_at, expected_local
    ):
        job = _stored_job(test_db, owner, created_at)

        info = ActiveTaskInfo(
            task_id=job.task_id, status=job.status, created_at=job.created_at
        )
        serialized = json.loads(info.model_dump_json())["created_at"]

        assert _local_wall_clock(serialized) == expected_local


@pytest.mark.asyncio
class TestActiveTasksEndpoint:
    async def test_listed_finished_task_carries_offset(self, owner, test_db):
        # Inside the 30-minute window for finished jobs, so the row is listed.
        created_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).replace(
            microsecond=0
        )
        job = _stored_job(test_db, owner, created_at)

        listed = (await _listed_tasks(owner, test_db))[job.task_id]

        parsed = datetime.fromisoformat(listed["created_at"])
        assert parsed.tzinfo is not None, listed["created_at"]
        assert parsed == created_at

    async def test_listed_running_task_carries_offset(self, owner, test_db):
        created_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).replace(
            microsecond=0
        )
        job = _stored_job(test_db, owner, created_at, status="PENDING")

        with patch("celery.result.AsyncResult") as async_result:
            async_result.return_value = Mock(state="PENDING", info=None)
            listed = (await _listed_tasks(owner, test_db))[job.task_id]

        parsed = datetime.fromisoformat(listed["created_at"])
        assert parsed.tzinfo is not None, listed["created_at"]
        assert parsed == created_at

    async def test_finished_task_outside_window_is_not_listed(self, owner, test_db):
        """The SQL cutoff compares aware with aware against the real column."""
        too_old = (
            datetime.now(timezone.utc) - COMPLETED_TASK_MAX_AGE - timedelta(minutes=1)
        )
        job = _stored_job(test_db, owner, too_old)

        assert job.task_id not in await _listed_tasks(owner, test_db)


class TestMigrationConvertsExistingRows:
    """Runs the real ``upgrade()``/``downgrade()`` inside the test transaction.

    The session time zone is set to Europe/Zurich on purpose: a cast without
    ``AT TIME ZONE 'UTC'`` would read the naive values as Zurich time and
    shift every existing row by one or two hours in production.
    """

    @staticmethod
    def _migration():
        spec = importlib.util.spec_from_file_location(
            "tf972_migration", _MIGRATION_PATH
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def _run(test_db, step) -> None:
        context = MigrationContext.configure(test_db.connection())
        with Operations.context(context):
            step()

    def _created_at(self, test_db, job_id: int):
        return test_db.execute(
            text("SELECT created_at FROM question_generation_jobs WHERE id = :id"),
            {"id": job_id},
        ).scalar_one()

    @pytest.mark.parametrize(
        "created_at", [SUMMER_UTC, WINTER_UTC], ids=["summer", "winter"]
    )
    def test_upgrade_reads_naive_values_as_utc_and_downgrade_reverses(
        self, owner, test_db, created_at
    ):
        migration = self._migration()
        job = _stored_job(test_db, owner, created_at)
        test_db.execute(text("SET LOCAL TIME ZONE 'Europe/Zurich'"))

        # Back to the pre-TF-972 schema: the row holds the naive UTC wall clock.
        self._run(test_db, migration.downgrade)
        naive = created_at.replace(tzinfo=None)
        assert self._created_at(test_db, job.id) == naive

        self._run(test_db, migration.upgrade)
        assert self._created_at(test_db, job.id) == created_at

        self._run(test_db, migration.downgrade)
        assert self._created_at(test_db, job.id) == naive
