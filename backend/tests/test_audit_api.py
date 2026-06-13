"""Integration tests for GET /api/v1/audit (TF-415).

Scope matrix, cross-tenant leakage, PII gating, pagination, and the
audit-the-auditor invariant.
"""

import json

import pytest
from fastapi.testclient import TestClient

from main import app
from database import get_db
from models.auth import AuditLog, Institution, Role, User, UserStatus
from utils.auth_utils import get_current_user


# --- builders (no hardcoded PKs; namespaced emails) -----------------------


def make_institution(test_db, name):
    inst = Institution(
        name=name,
        slug=name.lower().replace(" ", "-"),
        domain=f"{name.lower().replace(' ', '')}.ch",
        subscription_tier="free",
        max_users=10,
        max_documents=100,
        max_questions_per_month=500,
    )
    test_db.add(inst)
    test_db.flush()
    return inst


def make_user(test_db, institution_id, email, *, is_superuser=False, admin=False):
    user = User(
        email=email,
        first_name="Test",
        last_name="User",
        password_hash="dummy",
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
        is_superuser=is_superuser,
    )
    if admin:
        role = test_db.query(Role).filter(Role.name == "admin").first()
        if role is None:
            role = Role(name="admin", display_name="Admin", permissions="[]")
            test_db.add(role)
            test_db.flush()
        user.roles.append(role)
    test_db.add(user)
    test_db.flush()
    return user


def make_audit(
    test_db,
    user_id,
    action,
    *,
    status="success",
    resource_type="test",
    resource_id="1",
    ip_address="10.0.0.1",
    user_agent="pytest",
):
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status,
        ip_address=ip_address,
        user_agent=user_agent,
        additional_data=json.dumps({"k": "v"}),
    )
    test_db.add(log)
    test_db.flush()
    return log


def make_client(test_db, user):
    import api.audit as audit_module

    # Idempotent: avoid appending a duplicate /api/v1/audit route on every call.
    if not any(getattr(r, "path", None) == "/api/v1/audit" for r in app.routes):
        app.include_router(audit_module.router)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: test_db
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def world(test_db):
    """Two institutions, an admin in A, a superuser, a plain user, plus events."""
    inst_a = make_institution(test_db, "AuditInstA")
    inst_b = make_institution(test_db, "AuditInstB")
    admin_a = make_user(test_db, inst_a.id, "admin-a@audit.ch", admin=True)
    plain_a = make_user(test_db, inst_a.id, "plain-a@audit.ch")
    user_b = make_user(test_db, inst_b.id, "user-b@audit.ch")
    superuser = make_user(test_db, inst_a.id, "root@audit.ch", is_superuser=True)

    # Institution A events
    make_audit(test_db, plain_a.id, "create_document")  # business
    make_audit(test_db, plain_a.id, "create_user")  # admin
    make_audit(test_db, plain_a.id, "login")  # auth (super only)
    make_audit(test_db, plain_a.id, "permission_denied", status="failure")  # security
    # Institution B event (must never leak to admin A)
    make_audit(test_db, user_b.id, "create_document")
    # Orphan event (user_id NULL) — super only
    make_audit(test_db, None, "create_document")
    test_db.commit()
    return {
        "inst_a": inst_a,
        "inst_b": inst_b,
        "admin_a": admin_a,
        "plain_a": plain_a,
        "user_b": user_b,
        "superuser": superuser,
    }


def _get(test_db, user, **params):
    client = make_client(test_db, user)
    try:
        return client.get("/api/v1/audit", params=params)
    finally:
        app.dependency_overrides.clear()


class TestAuditScopeMatrix:
    def test_plain_user_forbidden(self, test_db, world):
        r = _get(test_db, world["plain_a"])
        assert r.status_code == 403

    def test_admin_sees_only_own_institution_business_and_admin(self, test_db, world):
        r = _get(test_db, world["admin_a"])
        assert r.status_code == 200
        actions = sorted({i["action"] for i in r.json()["items"]})
        # business + admin from inst A only; NO auth/security; NO inst B; NO orphan
        assert actions == ["create_document", "create_user"]

    def test_admin_cannot_see_auth_or_security(self, test_db, world):
        r = _get(test_db, world["admin_a"])
        cats = {i["category"] for i in r.json()["items"]}
        assert "auth" not in cats and "security" not in cats

    def test_admin_requesting_auth_category_is_forbidden(self, test_db, world):
        r = _get(test_db, world["admin_a"], category="auth")
        assert r.status_code == 403

    def test_superuser_sees_all_categories_all_institutions_and_orphan(
        self, test_db, world
    ):
        r = _get(test_db, world["superuser"])
        assert r.status_code == 200
        items = r.json()["items"]
        cats = {i["category"] for i in items}
        assert {"business", "admin", "auth", "security"} <= cats
        # includes the orphan (user_id null) and inst-B row → >= 6 rows total
        assert r.json()["total"] >= 6
        assert any(i["user_id"] is None for i in items)


class TestTenantIsolation:
    def test_admin_cannot_target_foreign_user_id(self, test_db, world):
        r = _get(test_db, world["admin_a"], user_id=world["user_b"].id)
        assert r.status_code == 403


class TestPiiGating:
    def test_admin_does_not_receive_ip_or_user_agent(self, test_db, world):
        r = _get(test_db, world["admin_a"])
        for item in r.json()["items"]:
            assert item["ip_address"] is None
            assert item["user_agent"] is None

    def test_superuser_receives_ip_and_user_agent(self, test_db, world):
        r = _get(test_db, world["superuser"])
        owned = [i for i in r.json()["items"] if i["ip_address"] is not None]
        assert owned, "superuser should see ip_address on owned-actor rows"

    def test_admin_does_not_receive_additional_data(self, test_db, world):
        # additional_data is an unstructured blob that may carry PII; it is
        # gated on the same flag as ip/user_agent → never visible to admins.
        r = _get(test_db, world["admin_a"])
        for item in r.json()["items"]:
            assert item["additional_data"] is None

    def test_superuser_receives_additional_data(self, test_db, world):
        r = _get(test_db, world["superuser"])
        assert any(i["additional_data"] is not None for i in r.json()["items"])


class TestValidation:
    def test_invalid_category_value_is_400(self, test_db, world):
        r = _get(test_db, world["superuser"], category="bogus")
        assert r.status_code == 400

    def test_date_from_after_date_to_is_400(self, test_db, world):
        r = _get(
            test_db,
            world["superuser"],
            date_from="2030-01-02T00:00:00Z",
            date_to="2030-01-01T00:00:00Z",
        )
        assert r.status_code == 400


class TestAuditTheAuditor:
    def test_query_writes_view_audit_log_event(self, test_db, world):
        before = (
            test_db.query(AuditLog).filter(AuditLog.action == "view_audit_log").count()
        )
        _get(test_db, world["superuser"])
        after = (
            test_db.query(AuditLog).filter(AuditLog.action == "view_audit_log").count()
        )
        assert after == before + 1


class TestPagination:
    def test_has_more_true_when_more_rows_exist(self, test_db, world):
        r = _get(test_db, world["superuser"], limit=2, offset=0)
        body = r.json()
        assert r.status_code == 200
        assert body["total"] >= 6
        assert body["has_more"] is True
        assert len(body["items"]) == 2

    def test_has_more_false_on_last_page(self, test_db, world):
        r = _get(test_db, world["superuser"], limit=100, offset=0)
        body = r.json()
        assert body["has_more"] is False


class TestSecurityRegressionGuards:
    def test_admin_explicit_action_outside_allowlist_returns_empty(
        self, test_db, world
    ):
        # Headline case (spec §8): an institution-admin passing ?action=login
        # must NOT leak auth events — the category allow-list runs unconditionally.
        r = _get(test_db, world["admin_a"], action="login")
        assert r.status_code == 200
        assert r.json()["items"] == []

    def test_uncategorized_action_is_superadmin_only(self, test_db, world):
        # An action absent from every category fails closed → SuperAdmin-only.
        make_audit(test_db, world["plain_a"].id, "ws_subscribe")
        test_db.flush()
        admin_actions = {
            i["action"] for i in _get(test_db, world["admin_a"]).json()["items"]
        }
        assert "ws_subscribe" not in admin_actions
        super_actions = {
            i["action"] for i in _get(test_db, world["superuser"]).json()["items"]
        }
        assert "ws_subscribe" in super_actions


class TestAuditTheAuditorPayload:
    def test_view_audit_log_records_filters_in_additional_data(self, test_db, world):
        # audit-the-auditor must persist the applied filters (spec §8).
        _get(test_db, world["superuser"], status="success", limit=5)
        row = (
            test_db.query(AuditLog)
            .filter(AuditLog.action == "view_audit_log")
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert row is not None
        data = json.loads(row.additional_data)
        assert "result_count" in data
        assert "total" in data
        assert data["status"] == "success"
