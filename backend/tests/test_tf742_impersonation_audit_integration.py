"""Tests for TF-742: impersonation audit-integration & email notification.

Covers the ticket's acceptance criteria:
  - every audit row written during an impersonated request carries
    ``impersonator_user_id``, regardless of the emitting call site (the
    central auto-fill in ``AuditService.log_action``, not touching the
    ~90 existing ``log_action``/``log_event_best_effort`` call sites);
  - new ``impersonation.start``/``impersonation.end`` actions, category
    ``admin``;
  - the target user is notified by email after every session end (manual,
    lost-token fallback, logout-during-impersonation, and reaper timeout);
  - the audit API surfaces an ``impersonator`` field, and institution-admins
    see SuperAdmin impersonations of their own institution's users.

Builds on the TF-741 test harness in ``test_impersonation_api.py`` (real
HTTP requests + real JWTs, since the mechanism under test is inseparable
from the token/claims flow).
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from database import get_db
from main import app
from models.auth import AuditLog, Institution, Role, User, UserStatus
from services.audit_service import AuditService
from services.auth_service import AuthService
from utils.impersonation_context import ImpersonationContext, set_impersonation_context


# ---------------------------------------------------------------------------
# Fixtures / helpers (mirrors test_impersonation_api.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def test_client(test_db):
    def override_get_db():
        yield test_db

    from api import admin, audit, auth, gdpr
    from api.v1 import billing

    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(audit.router)
    app.include_router(gdpr.router)
    app.include_router(billing.router, prefix="/api/v1/billing", tags=["billing"])

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _reset_impersonation_context():
    """Guard against context leaking between tests that call
    ``set_impersonation_context`` directly (unit tests below) instead of
    going through the real per-request middleware."""
    yield
    set_impersonation_context(None)


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


def _make_role(db, name, permissions_json):
    role = Role(
        name=name,
        display_name=name,
        description="test role",
        permissions=permissions_json,
        is_system_role=False,
        is_active=True,
    )
    db.add(role)
    db.flush()
    return role


def _grant_impersonate_permission(db, user):
    role = _make_role(db, f"impersonator-{user.id}", '["users:impersonate"]')
    user.roles.append(role)
    db.flush()


def _make_admin_role_user(db, inst, email):
    user = _make_user(db, inst, email)
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if admin_role is None:
        admin_role = _make_role(db, "admin", "[]")
    user.roles.append(admin_role)
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
    return client.post(
        f"/api/admin/users/{target_id}/impersonate",
        json={"reason": reason, "admin_password": admin_password},
        headers=_auth(admin_token),
    )


# ---------------------------------------------------------------------------
# AuditService.log_action: central impersonator_user_id auto-fill
# ---------------------------------------------------------------------------


def test_log_action_autofills_impersonator_user_id_from_context(test_db):
    """The ~90 existing call sites never pass ``impersonator_user_id``
    explicitly. During an impersonated request, ``log_action`` must fill it
    in from the request-scoped ``ImpersonationContext`` on its own."""
    inst = _make_institution(test_db, "tf742-unit-autofill")
    admin = _make_user(test_db, inst, "admin@tf742-unit-autofill.ch")
    target = _make_user(test_db, inst, "target@tf742-unit-autofill.ch")
    test_db.commit()

    set_impersonation_context(ImpersonationContext(admin.id, 1, "jti-1"))

    log = AuditService.log_action(
        db=test_db,
        action="some_unrelated_action",
        user_id=target.id,
    )

    assert log is not None
    assert log.impersonator_user_id == admin.id
    assert log.user_id == target.id


def test_log_action_impersonator_user_id_stays_none_without_context(test_db):
    """Outside of an impersonated request (the overwhelming majority of
    calls), the new column must stay ``NULL`` -- unchanged behaviour."""
    inst = _make_institution(test_db, "tf742-unit-no-context")
    target = _make_user(test_db, inst, "target@tf742-unit-no-context.ch")
    test_db.commit()

    assert set_impersonation_context(None) is None

    log = AuditService.log_action(
        db=test_db,
        action="some_unrelated_action",
        user_id=target.id,
    )

    assert log is not None
    assert log.impersonator_user_id is None


def test_log_action_explicit_impersonator_user_id_overrides_context(test_db):
    """Test-quality review fix: this used to only check (via
    ``inspect.signature``) that ``log_action`` *has* an
    ``impersonator_user_id`` parameter defaulting to ``None`` -- it never
    called ``log_action`` at all, so the actual "explicit value wins over
    context" behaviour the name promises (and that
    ``record_impersonation_started``/``record_impersonation_ended`` rely
    on -- ``start_impersonation`` runs on the admin's own, not-yet-
    impersonated request, so there is no context to read from, and the
    reaper's Celery worker process has no request-scoped context at all)
    went unverified."""
    inst = _make_institution(test_db, "tf742-unit-explicit-override")
    context_admin = _make_user(test_db, inst, "context-admin@tf742-explicit.ch")
    explicit_admin = _make_user(test_db, inst, "explicit-admin@tf742-explicit.ch")
    target = _make_user(test_db, inst, "target@tf742-explicit.ch")
    test_db.commit()

    set_impersonation_context(ImpersonationContext(context_admin.id, 1, "jti-explicit"))

    log = AuditService.log_action(
        db=test_db,
        action="some_unrelated_action",
        user_id=target.id,
        impersonator_user_id=explicit_admin.id,
    )

    assert log is not None
    assert log.impersonator_user_id == explicit_admin.id
    assert log.impersonator_user_id != context_admin.id


def test_log_event_best_effort_forwards_impersonator_user_id(test_db):
    inst = _make_institution(test_db, "tf742-unit-best-effort")
    admin = _make_user(test_db, inst, "admin@tf742-unit-best-effort.ch")
    target = _make_user(test_db, inst, "target@tf742-unit-best-effort.ch")
    test_db.commit()

    set_impersonation_context(ImpersonationContext(admin.id, 1, "jti-2"))

    AuditService.log_event_best_effort(
        test_db,
        action="some_unrelated_action",
        user_id=target.id,
    )

    row = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == "some_unrelated_action")
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert row.impersonator_user_id == admin.id


def test_impersonation_actions_are_categorized_as_admin():
    from services.audit_service import ACTIONS_BY_CATEGORY

    assert AuditService.ACTION_IMPERSONATION_START in ACTIONS_BY_CATEGORY["admin"]
    assert AuditService.ACTION_IMPERSONATION_END in ACTIONS_BY_CATEGORY["admin"]
    assert AuditService.ACTION_IMPERSONATION_START == "impersonation.start"
    assert AuditService.ACTION_IMPERSONATION_END == "impersonation.end"


# ---------------------------------------------------------------------------
# start_impersonation: impersonation.start audit event
# ---------------------------------------------------------------------------


def test_start_impersonation_writes_audit_event(test_client, test_db):
    inst = _make_institution(test_db, "tf742-start")
    superadmin = _make_user(test_db, inst, "super@tf742-start.ch", is_superuser=True)
    target = _make_user(test_db, inst, "target@tf742-start.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    response = _impersonate(
        test_client, admin_token, target.id, reason="Kundenanfrage TICKET-42"
    )
    assert response.status_code == 200
    session_id = response.json()["impersonation_session_id"]

    row = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == AuditService.ACTION_IMPERSONATION_START)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert row is not None
    assert row.user_id == target.id
    assert row.impersonator_user_id == superadmin.id
    import json

    data = json.loads(row.additional_data)
    assert data["reason"] == "Kundenanfrage TICKET-42"
    assert data["impersonation_session_id"] == session_id


# ---------------------------------------------------------------------------
# end_impersonation (all three code paths) + reaper: impersonation.end +
# email notification
# ---------------------------------------------------------------------------


def test_end_impersonation_writes_audit_event_and_queues_email(test_client, test_db):
    inst = _make_institution(test_db, "tf742-end")
    superadmin = _make_user(test_db, inst, "super@tf742-end.ch", is_superuser=True)
    target = _make_user(test_db, inst, "target@tf742-end.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    start = _impersonate(test_client, admin_token, target.id, reason="Ticket-7")
    impersonation_token = start.json()["access_token"]
    session_id = start.json()["impersonation_session_id"]

    with patch("tasks.notification_tasks.send_impersonation_ended_email") as mock_task:
        end_response = test_client.post(
            "/api/admin/impersonate/end", headers=_auth(impersonation_token)
        )
    assert end_response.status_code == 204

    row = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == AuditService.ACTION_IMPERSONATION_END)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert row is not None
    assert row.user_id == target.id
    assert row.impersonator_user_id == superadmin.id
    import json

    data = json.loads(row.additional_data)
    assert data["impersonation_session_id"] == session_id
    assert data["end_reason"] == "manual"
    assert data["reason"] == "Ticket-7"

    mock_task.delay.assert_called_once()
    kwargs = mock_task.delay.call_args.kwargs
    assert kwargs["to_email"] == target.email
    assert kwargs["admin_name"] == superadmin.full_name
    assert kwargs["end_reason"] == "manual"
    assert kwargs["reason"] == "Ticket-7"
    assert kwargs["session_id"] == int(session_id)


def test_end_impersonation_via_lost_token_fallback_writes_audit_and_email(
    test_client, test_db
):
    inst = _make_institution(test_db, "tf742-end-fallback")
    superadmin = _make_user(
        test_db, inst, "super@tf742-end-fallback.ch", is_superuser=True
    )
    target = _make_user(test_db, inst, "target@tf742-end-fallback.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    start = _impersonate(test_client, admin_token, target.id, reason="lost-token")
    assert start.status_code == 200

    with patch("tasks.notification_tasks.send_impersonation_ended_email") as mock_task:
        end_response = test_client.post(
            "/api/admin/impersonate/end", headers=_auth(admin_token)
        )
    assert end_response.status_code == 204

    row = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == AuditService.ACTION_IMPERSONATION_END)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert row is not None
    assert row.user_id == target.id
    assert row.impersonator_user_id == superadmin.id
    mock_task.delay.assert_called_once()
    assert mock_task.delay.call_args.kwargs["to_email"] == target.email


def test_logout_during_impersonation_writes_audit_and_email(test_client, test_db):
    inst = _make_institution(test_db, "tf742-logout")
    superadmin = _make_user(test_db, inst, "super@tf742-logout.ch", is_superuser=True)
    target = _make_user(test_db, inst, "target@tf742-logout.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    start = _impersonate(test_client, admin_token, target.id, reason="via-logout")
    impersonation_token = start.json()["access_token"]

    with patch("tasks.notification_tasks.send_impersonation_ended_email") as mock_task:
        logout_response = test_client.post(
            "/api/auth/logout", headers=_auth(impersonation_token)
        )
    assert logout_response.status_code == 204

    row = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == AuditService.ACTION_IMPERSONATION_END)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert row is not None
    assert row.impersonator_user_id == superadmin.id
    mock_task.delay.assert_called_once()


def test_end_impersonation_email_dispatch_failure_does_not_break_endpoint(
    test_client, test_db
):
    """A broker outage while queuing the notification must not turn a
    successful session-end into a 5xx (mirrors the pattern already used for
    the reindex-on-transfer dispatch in test_admin_users_transfer.py)."""
    from unittest.mock import MagicMock

    inst = _make_institution(test_db, "tf742-email-fail")
    superadmin = _make_user(
        test_db, inst, "super@tf742-email-fail.ch", is_superuser=True
    )
    target = _make_user(test_db, inst, "target@tf742-email-fail.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    start = _impersonate(test_client, admin_token, target.id)
    impersonation_token = start.json()["access_token"]

    mock_task = MagicMock()
    mock_task.delay.side_effect = RuntimeError("broker unreachable")
    with patch("tasks.notification_tasks.send_impersonation_ended_email", mock_task):
        end_response = test_client.post(
            "/api/admin/impersonate/end", headers=_auth(impersonation_token)
        )

    assert end_response.status_code == 204
    row = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == AuditService.ACTION_IMPERSONATION_END)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert row is not None


def test_record_impersonation_ended_swallows_db_lookup_failure(test_db):
    """TF-742 review fix: ``record_impersonation_ended``'s docstring
    promises it never raises once the session-closing UPDATE has already
    committed. Before the fix, the ``db.get(User, ...)`` lookups used to
    build the notification email sat *outside* any try/except -- a
    DB-level error there (e.g. a dropped connection, exactly the class of
    failure the docstring already claims is handled for the Celery broker)
    would have propagated straight out of this "never raises" function
    into whichever endpoint called it (``POST /admin/impersonate/end``,
    the lost-token fallback, or ``POST /auth/logout`` while impersonating
    -- none of which wrap the call in their own try/except), turning an
    already-successful session-close into a spurious 500."""
    inst = _make_institution(test_db, "tf742-dbget-fail")
    admin = _make_user(test_db, inst, "admin@tf742-dbget-fail.ch")
    target = _make_user(test_db, inst, "target@tf742-dbget-fail.ch")
    test_db.commit()

    with patch.object(test_db, "get", side_effect=RuntimeError("connection dropped")):
        # Must not raise.
        AuthService.record_impersonation_ended(
            test_db,
            admin_user_id=admin.id,
            target_user_id=target.id,
            session_id=1,
            reason="r",
            started_at=None,
            ended_at=datetime.now(timezone.utc),
            end_reason="manual",
        )

    # The audit write happens before the guarded db.get() lookups, so it
    # must still have gone through even though the notification couldn't.
    row = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == AuditService.ACTION_IMPERSONATION_END)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert row is not None
    assert row.impersonator_user_id == admin.id


def test_record_impersonation_ended_writes_audit_but_skips_email_for_erased_users(
    test_db,
):
    """Test-coverage review fix: ``ImpersonationSession.admin_user_id`` /
    ``target_user_id`` are ``ondelete="SET NULL"`` (TF-745's GDPR sweep can
    erase either row before the reaper -- or a lost-token fallback --
    processes an already-orphaned session). The audit write must still go
    through (best-effort, tolerant of a null ``user_id``); only the
    notification is skipped, since there's no one left to email."""
    with patch("tasks.notification_tasks.send_impersonation_ended_email") as mock_task:
        AuthService.record_impersonation_ended(
            test_db,
            admin_user_id=None,
            target_user_id=None,
            session_id=999,
            reason="orphaned-by-gdpr-erasure",
            started_at=None,
            ended_at=datetime.now(timezone.utc),
            end_reason="timeout",
        )

    mock_task.delay.assert_not_called()
    row = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == AuditService.ACTION_IMPERSONATION_END)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert row is not None
    assert row.user_id is None
    assert row.impersonator_user_id is None


# ---------------------------------------------------------------------------
# End-to-end proof: an existing, untouched call site (list_audit_logs's
# "audit-the-auditor" log_action call) auto-fills impersonator_user_id
# through a real impersonated HTTP request.
# ---------------------------------------------------------------------------


def test_existing_call_site_gets_impersonator_autofilled_under_impersonation(
    test_client, test_db
):
    inst = _make_institution(test_db, "tf742-autofill-e2e")
    superadmin = _make_user(
        test_db, inst, "super@tf742-autofill-e2e.ch", is_superuser=True
    )
    target_admin = _make_admin_role_user(
        test_db, inst, "target-admin@tf742-autofill-e2e.ch"
    )
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    start = _impersonate(test_client, admin_token, target_admin.id)
    assert start.status_code == 200
    impersonation_token = start.json()["access_token"]

    # GET /api/v1/audit calls AuditService.log_action(action=ACTION_VIEW_AUDIT_LOG,
    # user_id=current_user.id, ...) directly, with no impersonator_user_id
    # argument at all -- exactly one of the ~90 untouched call sites.
    response = test_client.get("/api/v1/audit", headers=_auth(impersonation_token))
    assert response.status_code == 200

    row = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == AuditService.ACTION_VIEW_AUDIT_LOG)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert row is not None
    assert row.user_id == target_admin.id
    assert row.impersonator_user_id == superadmin.id


# ---------------------------------------------------------------------------
# Audit API: impersonator field + institution-admin visibility
# ---------------------------------------------------------------------------


def test_audit_log_out_includes_impersonator_field(test_client, test_db):
    inst = _make_institution(test_db, "tf742-out-field")
    superadmin = _make_user(
        test_db, inst, "super@tf742-out-field.ch", is_superuser=True
    )
    target = _make_user(test_db, inst, "target@tf742-out-field.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    _impersonate(test_client, admin_token, target.id)

    response = test_client.get(
        "/api/v1/audit",
        params={"action": AuditService.ACTION_IMPERSONATION_START},
        headers=_auth(admin_token),
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["impersonator"] == superadmin.full_name


def test_institution_admin_sees_superadmin_impersonation_of_own_institution_user(
    test_client, test_db
):
    """AC: institution-admins see both their own impersonation activity and
    SuperAdmin impersonations of users belonging to their institution."""
    inst = _make_institution(test_db, "tf742-inst-visibility")
    superadmin = _make_user(
        test_db, inst, "super@tf742-inst-visibility.ch", is_superuser=True
    )
    inst_admin = _make_admin_role_user(
        test_db, inst, "inst-admin@tf742-inst-visibility.ch"
    )
    target = _make_user(test_db, inst, "target@tf742-inst-visibility.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]
    inst_admin_token = _tokens(test_db, inst_admin)["access_token"]

    start = _impersonate(test_client, admin_token, target.id)
    assert start.status_code == 200
    impersonation_token = start.json()["access_token"]
    with patch("tasks.notification_tasks.send_impersonation_ended_email"):
        end_response = test_client.post(
            "/api/admin/impersonate/end", headers=_auth(impersonation_token)
        )
    assert end_response.status_code == 204

    response = test_client.get(
        "/api/v1/audit",
        params={"category": "admin", "user_id": target.id},
        headers=_auth(inst_admin_token),
    )
    assert response.status_code == 200
    actions = {item["action"] for item in response.json()["items"]}
    assert AuditService.ACTION_IMPERSONATION_START in actions
    assert AuditService.ACTION_IMPERSONATION_END in actions
    for item in response.json()["items"]:
        if item["action"] in (
            AuditService.ACTION_IMPERSONATION_START,
            AuditService.ACTION_IMPERSONATION_END,
        ):
            assert item["impersonator"] == superadmin.full_name


def test_institution_admin_does_not_see_impersonation_of_other_institutions_user(
    test_client, test_db
):
    """Test-coverage review fix: the sibling test above only ever proves
    the positive case (same-institution visibility) -- this pins down the
    negative case the ``audit_query_service.py`` comment claims ("scoping
    is already enforced via the target"): an institution-admin from a
    *different* institution must not see a SuperAdmin's impersonation of
    another institution's user, and in particular must never learn the
    impersonator's name for a row outside their own institution's scope."""
    inst_a = _make_institution(test_db, "tf742-inst-visibility-a")
    inst_b = _make_institution(test_db, "tf742-inst-visibility-b")
    superadmin = _make_user(
        test_db, inst_a, "super@tf742-inst-visibility-a.ch", is_superuser=True
    )
    inst_b_admin = _make_admin_role_user(
        test_db, inst_b, "inst-b-admin@tf742-inst-visibility-b.ch"
    )
    target_a = _make_user(test_db, inst_a, "target@tf742-inst-visibility-a.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]
    inst_b_admin_token = _tokens(test_db, inst_b_admin)["access_token"]

    start = _impersonate(test_client, admin_token, target_a.id)
    assert start.status_code == 200
    impersonation_token = start.json()["access_token"]
    with patch("tasks.notification_tasks.send_impersonation_ended_email"):
        end_response = test_client.post(
            "/api/admin/impersonate/end", headers=_auth(impersonation_token)
        )
    assert end_response.status_code == 204

    response = test_client.get(
        "/api/v1/audit",
        params={"category": "admin"},
        headers=_auth(inst_b_admin_token),
    )
    assert response.status_code == 200
    items = response.json()["items"]
    actions = {item["action"] for item in items}
    assert AuditService.ACTION_IMPERSONATION_START not in actions
    assert AuditService.ACTION_IMPERSONATION_END not in actions
    assert not any(item.get("impersonator") == superadmin.full_name for item in items)
