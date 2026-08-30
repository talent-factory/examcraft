"""Tests für tasks.gdpr_tasks (TF-745 DSGVO-Löschautomatik).

Siehe docs/superpowers/specs/2026-08-27-tf745-gdpr-scheduled-deletion-design.md.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.exc import TimeoutError as SATimeoutError

from models.auth import AuditLog, Institution, User, UserStatus


def _make_institution(db, slug: str) -> Institution:
    institution = Institution(
        name=f"Inst-{slug}",
        slug=slug,
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(institution)
    db.flush()
    return institution


def _make_user(
    db,
    institution: Institution,
    email: str,
    *,
    deletion_requested_at=None,
    scheduled_deletion_date=None,
) -> User:
    user = User(
        email=email,
        password_hash="dummy",  # pragma: allowlist secret
        first_name="Test",
        last_name="User",
        institution_id=institution.id,
        status=UserStatus.ACTIVE.value,
        deletion_requested_at=deletion_requested_at,
        scheduled_deletion_date=scheduled_deletion_date,
    )
    db.add(user)
    db.flush()
    return user


def test_gdpr_tasks_importable():
    from tasks.gdpr_tasks import execute_gdpr_deletion, process_scheduled_deletions

    assert (
        process_scheduled_deletions.name
        == "tasks.gdpr_tasks.process_scheduled_deletions"
    )
    assert execute_gdpr_deletion.name == "tasks.gdpr_tasks.execute_gdpr_deletion"


def test_process_scheduled_deletions_dispatches_only_due_users(test_db):
    institution = _make_institution(test_db, "gdpr-tasks-sweep")
    now = datetime.now(timezone.utc)

    due = _make_user(
        test_db,
        institution,
        "due@gdpr-tasks-sweep.ch",
        deletion_requested_at=now - timedelta(days=31),
        scheduled_deletion_date=now - timedelta(days=1),
    )
    _make_user(
        test_db,
        institution,
        "not-due@gdpr-tasks-sweep.ch",
        deletion_requested_at=now - timedelta(days=1),
        scheduled_deletion_date=now + timedelta(days=29),
    )
    _make_user(test_db, institution, "no-request@gdpr-tasks-sweep.ch")
    test_db.commit()

    from tasks.gdpr_tasks import process_scheduled_deletions

    with (
        patch("tasks.gdpr_tasks.SessionLocal", return_value=test_db),
        patch.object(test_db, "close"),
        patch("tasks.gdpr_tasks.execute_gdpr_deletion") as mock_execute,
    ):
        result = process_scheduled_deletions.run()

    assert result == {"dispatched": 1}
    mock_execute.delay.assert_called_once_with(due.id)


def test_process_scheduled_deletions_dispatches_multiple_due_users(test_db):
    """Der Sweep darf nicht nur den ersten fälligen User dispatchen, wenn
    mehrere gleichzeitig fällig sind (z. B. keine versehentliche
    Deduplizierung oder ein `.first()` statt `.all()`-Bug)."""
    institution = _make_institution(test_db, "gdpr-tasks-sweep-multi")
    now = datetime.now(timezone.utc)

    due_1 = _make_user(
        test_db,
        institution,
        "due1@gdpr-tasks-sweep-multi.ch",
        deletion_requested_at=now - timedelta(days=31),
        scheduled_deletion_date=now - timedelta(days=1),
    )
    due_2 = _make_user(
        test_db,
        institution,
        "due2@gdpr-tasks-sweep-multi.ch",
        deletion_requested_at=now - timedelta(days=35),
        scheduled_deletion_date=now - timedelta(days=3),
    )
    test_db.commit()

    from tasks.gdpr_tasks import process_scheduled_deletions

    with (
        patch("tasks.gdpr_tasks.SessionLocal", return_value=test_db),
        patch.object(test_db, "close"),
        patch("tasks.gdpr_tasks.execute_gdpr_deletion") as mock_execute,
    ):
        result = process_scheduled_deletions.run()

    assert result == {"dispatched": 2}
    dispatched_ids = {call.args[0] for call in mock_execute.delay.call_args_list}
    assert dispatched_ids == {due_1.id, due_2.id}


def test_execute_gdpr_deletion_skips_missing_user(test_db):
    from tasks.gdpr_tasks import execute_gdpr_deletion

    with (
        patch("tasks.gdpr_tasks.SessionLocal", return_value=test_db),
        patch.object(test_db, "close"),
    ):
        result = execute_gdpr_deletion.run(user_id=999999)

    assert result == {"status": "skipped", "reason": "user_not_found"}


def test_execute_gdpr_deletion_skips_cancelled(test_db):
    institution = _make_institution(test_db, "gdpr-tasks-cancelled")
    user = _make_user(
        test_db,
        institution,
        "cancelled@gdpr-tasks-cancelled.ch",
        deletion_requested_at=None,
        scheduled_deletion_date=datetime.now(timezone.utc) - timedelta(days=1),
    )
    test_db.commit()

    from tasks.gdpr_tasks import execute_gdpr_deletion

    with (
        patch("tasks.gdpr_tasks.SessionLocal", return_value=test_db),
        patch.object(test_db, "close"),
    ):
        result = execute_gdpr_deletion.run(user_id=user.id)

    assert result == {"status": "skipped", "reason": "cancelled"}
    assert test_db.get(User, user.id) is not None


def test_execute_gdpr_deletion_skips_not_due(test_db):
    institution = _make_institution(test_db, "gdpr-tasks-not-due")
    now = datetime.now(timezone.utc)
    user = _make_user(
        test_db,
        institution,
        "notdue@gdpr-tasks-not-due.ch",
        deletion_requested_at=now - timedelta(days=1),
        scheduled_deletion_date=now + timedelta(days=29),
    )
    test_db.commit()

    from tasks.gdpr_tasks import execute_gdpr_deletion

    with (
        patch("tasks.gdpr_tasks.SessionLocal", return_value=test_db),
        patch.object(test_db, "close"),
    ):
        result = execute_gdpr_deletion.run(user_id=user.id)

    assert result == {"status": "skipped", "reason": "not_due"}
    assert test_db.get(User, user.id) is not None


def test_execute_gdpr_deletion_deletes_due_user(test_db):
    institution = _make_institution(test_db, "gdpr-tasks-due")
    now = datetime.now(timezone.utc)
    user = _make_user(
        test_db,
        institution,
        "due2@gdpr-tasks-due.ch",
        deletion_requested_at=now - timedelta(days=31),
        scheduled_deletion_date=now - timedelta(days=1),
    )
    test_db.commit()
    user_id = user.id

    from tasks.gdpr_tasks import execute_gdpr_deletion

    with (
        patch("tasks.gdpr_tasks.SessionLocal", return_value=test_db),
        patch.object(test_db, "close"),
    ):
        result = execute_gdpr_deletion.run(user_id=user_id)

    assert result["status"] == "deleted"
    assert result["user_id"] == user_id
    assert test_db.get(User, user_id) is None

    log = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == "account_deleted_scheduled")
        .one()
    )
    assert log.user_id is None


def test_execute_gdpr_deletion_writes_audit_log_only_on_final_retry_for_transient_error(
    test_db,
):
    """`self.request.retries` unterhalb `self.max_retries` darf den
    Fehlschlags-Audit-Log noch NICHT schreiben — nur der ausgeschöpfte
    letzte Versuch tut das (Muster wie
    `tasks/import_submissions_task.py::test_transient_error_marks_failed_only_on_retry_exhaustion`).
    Gilt nur für Fehler, die Celery überhaupt automatisch retried
    (`_TRANSIENT_ERRORS`) — siehe die Schwester-Testfunktion unten für den
    nicht-retry-fähigen Fall."""
    institution = _make_institution(test_db, "gdpr-tasks-retry")
    now = datetime.now(timezone.utc)
    user = _make_user(
        test_db,
        institution,
        "retry@gdpr-tasks-retry.ch",
        deletion_requested_at=now - timedelta(days=31),
        scheduled_deletion_date=now - timedelta(days=1),
    )
    test_db.commit()
    user_id = user.id

    from tasks.gdpr_tasks import execute_gdpr_deletion

    # ``run.__wrapped__`` ist an die Task-Instanz gebunden; ``.__func__`` ist
    # der ungebundene Funktionskörper — so lässt sich ``self.request.retries``
    # über ein Fake-``self`` deterministisch steuern.
    raw = execute_gdpr_deletion.run.__wrapped__.__func__

    def _run_with_retries(retries: int) -> None:
        fake_self = SimpleNamespace(
            request=SimpleNamespace(retries=retries), max_retries=3
        )
        with (
            patch("tasks.gdpr_tasks.SessionLocal", return_value=test_db),
            patch.object(test_db, "close"),
            patch(
                "tasks.gdpr_tasks.delete_user_and_gdpr_data",
                side_effect=OperationalError("connection lost", {}, Exception()),
            ),
        ):
            with pytest.raises(OperationalError):
                raw(fake_self, user_id=user_id)

    _run_with_retries(retries=0)
    assert (
        test_db.query(AuditLog)
        .filter(AuditLog.action == "gdpr_scheduled_deletion_failed")
        .count()
        == 0
    )

    _run_with_retries(retries=3)
    failure_log = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == "gdpr_scheduled_deletion_failed")
        .one()
    )
    assert failure_log.status == "error"
    assert failure_log.user_id == user_id


def test_execute_gdpr_deletion_writes_audit_log_immediately_for_non_transient_error(
    test_db,
):
    """Ein nicht-retry-fähiger Fehler (nicht in `_TRANSIENT_ERRORS`, z. B. ein
    echter Programmfehler) wird von Celery gar nicht erst erneut versucht —
    `self.request.retries` bleibt für immer 0. Ohne Sonderfall würde dieser
    Fehler NIE einen Audit-Log-Eintrag bekommen; dieser Test pinnt, dass der
    erste (und einzige) Versuch bereits als „letzter Versuch" zählt."""
    institution = _make_institution(test_db, "gdpr-tasks-retry-permanent")
    now = datetime.now(timezone.utc)
    user = _make_user(
        test_db,
        institution,
        "permanent@gdpr-tasks-retry-permanent.ch",
        deletion_requested_at=now - timedelta(days=31),
        scheduled_deletion_date=now - timedelta(days=1),
    )
    test_db.commit()
    user_id = user.id

    from tasks.gdpr_tasks import execute_gdpr_deletion

    raw = execute_gdpr_deletion.run.__wrapped__.__func__
    fake_self = SimpleNamespace(request=SimpleNamespace(retries=0), max_retries=3)

    with (
        patch("tasks.gdpr_tasks.SessionLocal", return_value=test_db),
        patch.object(test_db, "close"),
        patch(
            "tasks.gdpr_tasks.delete_user_and_gdpr_data",
            side_effect=RuntimeError("boom - permanenter Bug, kein Retry"),
        ),
    ):
        with pytest.raises(RuntimeError):
            raw(fake_self, user_id=user_id)

    failure_log = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == "gdpr_scheduled_deletion_failed")
        .one()
    )
    assert failure_log.status == "error"
    assert failure_log.user_id == user_id


def test_transient_errors_excludes_integrity_error():
    """Sperrt die Klassifikation fest: `sqlalchemy.exc.DatabaseError` ist die
    Oberklasse von `IntegrityError`/`ProgrammingError`/`DataError`/
    `InternalError` — wäre `DatabaseError` (statt nur `OperationalError`) in
    `_TRANSIENT_ERRORS`, würde genau der im Modul-Kommentar zitierte
    Leitfall (eine noch nicht abgedeckte FK-Policy wirft `IntegrityError`)
    weiterhin 3x sinnlos retried, statt sofort final zu werden."""
    from tasks.gdpr_tasks import _TRANSIENT_ERRORS

    assert not issubclass(IntegrityError, _TRANSIENT_ERRORS)


def test_transient_errors_includes_pool_timeout():
    """Positiv-Gegenstück zu `..._excludes_integrity_error`: sperrt fest,
    dass `sqlalchemy.exc.TimeoutError` (Connection-Pool-Checkout-Timeout
    bei Pool-Erschöpfung, z. B. viele parallel dispatchte
    execute_gdpr_deletion-Tasks) in `_TRANSIENT_ERRORS` bleibt — es ist KEIN
    DBAPI-Fehler und wird von `OperationalError` daher NICHT automatisch
    mitabgedeckt (siehe Modul-Kommentar in tasks/gdpr_tasks.py). Würde
    `SATimeoutError` versehentlich aus der Liste fallen, würde ein
    Pool-Timeout sofort final statt retry-fähig behandelt."""
    from tasks.gdpr_tasks import _TRANSIENT_ERRORS

    assert issubclass(SATimeoutError, _TRANSIENT_ERRORS)
    assert issubclass(OperationalError, _TRANSIENT_ERRORS)
    assert issubclass(ConnectionError, _TRANSIENT_ERRORS)


def test_execute_gdpr_deletion_writes_audit_log_immediately_for_integrity_error(
    test_db,
):
    """Wie `..._for_non_transient_error`, aber mit dem im Modul-Kommentar
    konkret genannten Leitfall (FK-Policy-Drift → IntegrityError) statt
    einem generischen RuntimeError — deckt genau den Fehlertyp ab, den ein
    zu breites `_TRANSIENT_ERRORS` (bare `DatabaseError`) fälschlich als
    retry-fähig eingestuft hätte."""
    institution = _make_institution(test_db, "gdpr-tasks-retry-integrity")
    now = datetime.now(timezone.utc)
    user = _make_user(
        test_db,
        institution,
        "integrity@gdpr-tasks-retry-integrity.ch",
        deletion_requested_at=now - timedelta(days=31),
        scheduled_deletion_date=now - timedelta(days=1),
    )
    test_db.commit()
    user_id = user.id

    from tasks.gdpr_tasks import execute_gdpr_deletion

    raw = execute_gdpr_deletion.run.__wrapped__.__func__
    fake_self = SimpleNamespace(request=SimpleNamespace(retries=0), max_retries=3)

    integrity_error = IntegrityError(
        "INSERT INTO ...", {}, Exception("FK constraint violation")
    )
    with (
        patch("tasks.gdpr_tasks.SessionLocal", return_value=test_db),
        patch.object(test_db, "close"),
        patch(
            "tasks.gdpr_tasks.delete_user_and_gdpr_data",
            side_effect=integrity_error,
        ),
    ):
        with pytest.raises(IntegrityError):
            raw(fake_self, user_id=user_id)

    failure_log = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == "gdpr_scheduled_deletion_failed")
        .one()
    )
    assert failure_log.status == "error"
    assert failure_log.user_id == user_id


def test_gdpr_action_strings_are_categorized_as_business():
    from services.audit_service import category_for_action

    assert category_for_action("account_deleted_scheduled") == "business"
    assert category_for_action("gdpr_scheduled_deletion_failed") == "business"
