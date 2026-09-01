"""Tests for TF-759: real-time notification of the impersonation target
while the session is still running.

TF-742 already notifies the target *after* a session ends. This ticket
adds the symmetric notification *at start*, dispatched from
``AuthService.record_impersonation_started`` right alongside the existing
``impersonation.start`` audit event -- mirrors ``record_impersonation_ended``'s
"audit + notify" pattern so the target learns about an ongoing session
without having to wait for it to close.

Builds on the TF-742 test harness in ``test_tf742_impersonation_audit_integration.py``.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from database import get_db
from main import app
from models.auth import AuditLog, ImpersonationSession, Institution, User, UserStatus
from services.audit_service import AuditService
from services.auth_service import AuthService


# ---------------------------------------------------------------------------
# Fixtures / helpers (mirrors test_tf742_impersonation_audit_integration.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def test_client(test_db):
    def override_get_db():
        yield test_db

    from api import admin, audit, auth

    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(audit.router)

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def _make_institution(db, slug):
    inst = Institution(
        name=f"Inst-{slug}",
        slug=slug,
        subscription_tier="professional",
        max_users=50,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.flush()
    return inst


def _make_user(db, inst, email, status=UserStatus.ACTIVE.value, is_superuser=False):
    user = User(
        email=email,
        password_hash=AuthService.get_password_hash("Test1234!"),
        first_name="Test",
        last_name="User",
        institution_id=inst.id,
        status=status,
        is_superuser=is_superuser,
    )
    db.add(user)
    db.flush()
    return user


def _tokens(db, user):
    return AuthService.create_tokens_for_user(user, db)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _impersonate(
    client,
    admin_token,
    target_id,
    reason="Support-Anfrage TICKET-1",
    admin_password="Test1234!",
):
    # TF-758 (merged after this file was written) added a required
    # `admin_password` step-up field to `ImpersonateRequest` — matches
    # the password `_make_user()` hashes below, and the same default
    # already used by `test_impersonation_api.py::_impersonate`.
    return client.post(
        f"/api/admin/users/{target_id}/impersonate",
        json={"reason": reason, "admin_password": admin_password},
        headers=_auth(admin_token),
    )


# ---------------------------------------------------------------------------
# start_impersonation: dispatches the started-email notification
# ---------------------------------------------------------------------------


def test_start_impersonation_dispatches_started_email(test_client, test_db):
    inst = _make_institution(test_db, "tf759-start")
    superadmin = _make_user(test_db, inst, "super@tf759-start.ch", is_superuser=True)
    target = _make_user(test_db, inst, "target@tf759-start.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    with patch(
        "tasks.notification_tasks.send_impersonation_started_email"
    ) as mock_task:
        response = _impersonate(
            test_client, admin_token, target.id, reason="Kundenanfrage TICKET-42"
        )
    assert response.status_code == 200

    mock_task.delay.assert_called_once()
    kwargs = mock_task.delay.call_args.kwargs
    assert kwargs["to_email"] == target.email
    assert kwargs["to_name"] == target.first_name
    assert kwargs["admin_name"] == superadmin.full_name
    assert kwargs["reason"] == "Kundenanfrage TICKET-42"

    # Test-coverage review fix: `started_at` is the one genuinely new field
    # this ticket threads through -- checking only "is not None" would still
    # pass if the wrong timestamp (e.g. a freshly-computed `datetime.now()`
    # instead of the persisted `session.started_at`) were passed. Compare
    # against the actual persisted session row instead.
    session_row = (
        test_db.query(ImpersonationSession)
        .filter(ImpersonationSession.target_user_id == target.id)
        .order_by(ImpersonationSession.id.desc())
        .first()
    )
    assert session_row is not None
    assert session_row.started_at is not None
    assert kwargs["started_at"] == session_row.started_at.isoformat()


def test_start_impersonation_email_dispatch_failure_does_not_break_endpoint(
    test_client, test_db
):
    """Mirrors TF-742's
    ``test_end_impersonation_email_dispatch_failure_does_not_break_endpoint``:
    a broker outage while queuing the notification must not turn an
    already-successful session start into a 5xx."""
    inst = _make_institution(test_db, "tf759-email-fail")
    superadmin = _make_user(
        test_db, inst, "super@tf759-email-fail.ch", is_superuser=True
    )
    target = _make_user(test_db, inst, "target@tf759-email-fail.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    mock_task = MagicMock()
    mock_task.delay.side_effect = RuntimeError("broker unreachable")
    with patch("tasks.notification_tasks.send_impersonation_started_email", mock_task):
        response = _impersonate(test_client, admin_token, target.id)

    assert response.status_code == 200

    row = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == AuditService.ACTION_IMPERSONATION_START)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert row is not None
    assert row.impersonator_user_id == superadmin.id


# ---------------------------------------------------------------------------
# record_impersonation_started: unit-level "never raises" guarantee
# ---------------------------------------------------------------------------


def test_record_impersonation_started_swallows_db_lookup_failure(test_db):
    """A DB-level error while looking up the admin/target rows for the
    notification (e.g. a dropped connection) must not propagate out of
    ``record_impersonation_started`` and turn an already-created
    impersonation session into a 500 for the caller -- same contract as
    ``record_impersonation_ended``."""
    inst = _make_institution(test_db, "tf759-dbget-fail")
    admin = _make_user(test_db, inst, "admin@tf759-dbget-fail.ch")
    target = _make_user(test_db, inst, "target@tf759-dbget-fail.ch")
    test_db.commit()

    with patch.object(test_db, "get", side_effect=RuntimeError("connection dropped")):
        # Must not raise.
        AuthService.record_impersonation_started(
            test_db,
            admin_user_id=admin.id,
            target_user_id=target.id,
            session_id=1,
            reason="r",
            started_at=datetime.now(timezone.utc),
        )

    # The audit write happens before the guarded db.get() lookups, so it
    # must still have gone through even though the notification couldn't.
    row = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == AuditService.ACTION_IMPERSONATION_START)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert row is not None
    assert row.impersonator_user_id == admin.id


def test_record_impersonation_started_skips_email_when_lookup_returns_none(test_db):
    """Test-coverage review fix: unlike ``record_impersonation_ended``
    (whose ``admin_user_id``/``target_user_id`` are ``Optional[int]`` and
    can already be ``None`` at the call site due to GDPR SET-NULL erasure),
    ``record_impersonation_started`` takes required, non-Optional ids --
    but its ``db.get()`` calls can still come back empty (e.g. a row
    hard-deleted between session creation and this call). That must still
    skip the notification without raising, while the audit write still
    goes through -- mirrors
    ``test_record_impersonation_ended_writes_audit_but_skips_email_for_erased_users``
    in ``test_tf742_impersonation_audit_integration.py``, adapted for the
    ``db.get()``-returns-``None`` path instead of a null FK."""
    inst = _make_institution(test_db, "tf759-none-lookup")
    admin = _make_user(test_db, inst, "admin@tf759-none-lookup.ch")
    target = _make_user(test_db, inst, "target@tf759-none-lookup.ch")
    test_db.commit()

    with (
        patch.object(test_db, "get", return_value=None) as mock_get,
        patch("tasks.notification_tasks.send_impersonation_started_email") as mock_task,
    ):
        AuthService.record_impersonation_started(
            test_db,
            admin_user_id=admin.id,
            target_user_id=target.id,
            session_id=2,
            reason="r",
            started_at=datetime.now(timezone.utc),
        )

    mock_get.assert_called()
    mock_task.delay.assert_not_called()

    row = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == AuditService.ACTION_IMPERSONATION_START)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert row is not None
    assert row.impersonator_user_id == admin.id
