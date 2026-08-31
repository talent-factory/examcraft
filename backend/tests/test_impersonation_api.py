"""Integration tests for TF-741: impersonation start/end endpoints,
scope rules, nesting rejection, and the account-security guard.

Covers the ticket's acceptance criteria end-to-end via real HTTP
requests and real JWTs (not dependency overrides for auth), since the
whole point of this ticket is the token/claims mechanism itself.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from database import get_db
from main import app
from models.auth import (
    AuditLog,
    ImpersonationSession,
    Institution,
    Role,
    User,
    UserStatus,
)
from services.auth_service import AuthService


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


class FakeRatelimitRedis:
    """Minimal in-memory stand-in for the Redis ratelimit client -- just
    the INCR/EXPIRE operations ``ImpersonationRateLimiter`` relies on.
    Same shape as the one in test_impersonation_rate_limit.py; duplicated
    rather than shared since it's a handful of lines and this file is
    otherwise self-contained.
    """

    def __init__(self):
        self._counts: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]

    def expire(self, key: str, ttl: int) -> None:
        pass


@pytest.fixture(autouse=True)
def _fake_ratelimit_redis(monkeypatch):
    """Every impersonation start now runs an admin-scoped rate-limit check
    (TF-760), which talks to Redis. Stub it out for every test in this file
    so that check is fast and deterministic and doesn't depend on a
    reachable Redis instance -- tests that actually exercise rate limiting
    configure their own tight limiter instance explicitly (see below).
    """
    client = FakeRatelimitRedis()
    monkeypatch.setattr(
        "middleware.rate_limit.RedisService.get_ratelimit_client",
        lambda: client,
    )
    return client


def _patch_impersonation_rate_limiter(monkeypatch, limiter):
    """Patch ``_impersonation_rate_limiter`` on whatever module actually
    backs the registered impersonation-start route(s) on ``app`` -- not on
    a module reached by name.

    ``main.py`` additionally loads ``admin.py`` a *second* time via
    ``importlib.util.spec_from_file_location("core_api_admin", ...)`` /
    ``exec_module`` to build (one copy of) the router registered on the
    FastAPI app, without ever inserting that module into ``sys.modules``
    (unlike e.g. its ``api.activity`` / ``api.audit`` counterparts a few
    lines above it in main.py, which do). That copy is therefore only
    reachable through the route objects it produced -- there is no module
    name to patch it by. It has its own independent copy of every
    module-level global, including this singleton.

    Which copy ends up serving a given request is then a function of test
    *order*: once any earlier test in the suite triggers the app's
    lifespan (``with TestClient(app) as client:``), that unreachable
    copy's router gets registered into ``app.routes`` and -- since routes
    are matched in registration order and ``app`` is a process-wide
    singleton whose routes are never reset between tests -- keeps winning
    route resolution for the rest of the test session, regardless of what
    this file's own ``test_client`` fixture registers afterwards.

    So instead of guessing a module name (a plain ``monkeypatch.setattr
    (admin_api, ...)``, or even a ``sys.modules`` lookup by every name
    ``admin.py`` might have been loaded under -- which still misses this
    unregistered copy), walk ``app.routes`` for every endpoint function
    whose globals carry this singleton and patch it there directly. That
    finds -- and covers -- every copy actually wired into the app,
    including ones with no importable name, sidestepping the ordering
    question entirely. Same underlying gotcha as TF-745's dual-module
    test bug.
    """
    patched_globals_ids = set()
    for route in app.routes:
        endpoint = getattr(route, "endpoint", None)
        route_globals = getattr(endpoint, "__globals__", None)
        if route_globals is None or "_impersonation_rate_limiter" not in route_globals:
            continue
        if id(route_globals) in patched_globals_ids:
            continue
        patched_globals_ids.add(id(route_globals))
        monkeypatch.setitem(route_globals, "_impersonation_rate_limiter", limiter)
    assert patched_globals_ids, (
        "no registered route exposes _impersonation_rate_limiter -- "
        "has start_impersonation's module path changed?"
    )


@pytest.fixture
def test_client(test_db):
    def override_get_db():
        yield test_db

    # Importing main.app alone does not populate its full router set in
    # this test environment (main.py's registration is deployment-mode
    # dependent) -- explicitly include what this file needs, same
    # pattern as tests/test_auth_api.py.
    from api import admin, auth, gdpr
    from api.v1 import billing

    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(gdpr.router)
    app.include_router(billing.router, prefix="/api/v1/billing", tags=["billing"])

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
    """A non-superuser user holding the "admin" role (institution admin).

    ``Role.name`` is globally unique and ``_is_admin_role`` checks for the
    literal string "admin" -- reuse an existing row if the full suite (or
    another fixture in this session) already seeded one, instead of
    inserting a second one and hitting the unique constraint.
    """
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
# Scope rules
# ---------------------------------------------------------------------------


def test_superadmin_can_impersonate_any_user_including_admin(test_client, test_db):
    inst = _make_institution(test_db, "tf741-super-any")
    other_inst = _make_institution(test_db, "tf741-super-any-other")
    superadmin = _make_user(
        test_db, inst, "super@tf741-super-any.ch", is_superuser=True
    )
    target_admin = _make_admin_role_user(
        test_db, other_inst, "target-admin@tf741-super-any.ch"
    )
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    response = _impersonate(test_client, admin_token, target_admin.id)

    assert response.status_code == 200
    data = response.json()
    assert data["target_user_id"] == target_admin.id
    assert "access_token" in data
    assert data["expires_in"] == 30 * 60


def test_institution_admin_can_impersonate_non_admin_same_institution(
    test_client, test_db
):
    inst = _make_institution(test_db, "tf741-inst-admin-ok")
    admin = _make_user(test_db, inst, "admin@tf741-inst-admin-ok.ch")
    _grant_impersonate_permission(test_db, admin)
    target = _make_user(test_db, inst, "target@tf741-inst-admin-ok.ch")
    test_db.commit()
    admin_token = _tokens(test_db, admin)["access_token"]

    response = _impersonate(test_client, admin_token, target.id)

    assert response.status_code == 200
    assert response.json()["target_user_id"] == target.id


def test_institution_admin_blocked_cross_institution(test_client, test_db):
    inst = _make_institution(test_db, "tf741-cross-inst-a")
    other_inst = _make_institution(test_db, "tf741-cross-inst-b")
    admin = _make_user(test_db, inst, "admin@tf741-cross-inst-a.ch")
    _grant_impersonate_permission(test_db, admin)
    target = _make_user(test_db, other_inst, "target@tf741-cross-inst-b.ch")
    test_db.commit()
    admin_token = _tokens(test_db, admin)["access_token"]

    response = _impersonate(test_client, admin_token, target.id)

    assert response.status_code == 403


def test_institution_admin_blocked_target_is_admin_role(test_client, test_db):
    inst = _make_institution(test_db, "tf741-target-admin")
    admin = _make_user(test_db, inst, "admin@tf741-target-admin.ch")
    _grant_impersonate_permission(test_db, admin)
    target_admin = _make_admin_role_user(
        test_db, inst, "target-admin@tf741-target-admin.ch"
    )
    test_db.commit()
    admin_token = _tokens(test_db, admin)["access_token"]

    response = _impersonate(test_client, admin_token, target_admin.id)

    assert response.status_code == 403


def test_institution_admin_blocked_target_has_admin_permission_via_custom_role(
    test_client, test_db
):
    """TF-741 review fix: the scope check previously only excluded targets
    holding the literal role name "admin" (``_is_admin_role``). ``Role.name``
    is a free-form, admin-assignable string, so a target holding a
    custom-named role with an admin-class permission was impersonable —
    handing the impersonating admin that same power for 30 minutes."""
    inst = _make_institution(test_db, "tf741-target-custom-admin-perm")
    admin = _make_user(test_db, inst, "admin@tf741-target-custom-admin-perm.ch")
    _grant_impersonate_permission(test_db, admin)
    target = _make_user(test_db, inst, "target@tf741-target-custom-admin-perm.ch")
    custom_role = _make_role(test_db, "team-lead", '["manage_users"]')
    target.roles.append(custom_role)
    test_db.flush()
    test_db.commit()
    admin_token = _tokens(test_db, admin)["access_token"]

    response = _impersonate(test_client, admin_token, target.id)

    assert response.status_code == 403


def test_institution_admin_blocked_target_is_superuser(test_client, test_db):
    inst = _make_institution(test_db, "tf741-target-super")
    admin = _make_user(test_db, inst, "admin@tf741-target-super.ch")
    _grant_impersonate_permission(test_db, admin)
    target_super = _make_user(
        test_db, inst, "target-super@tf741-target-super.ch", is_superuser=True
    )
    test_db.commit()
    admin_token = _tokens(test_db, admin)["access_token"]

    response = _impersonate(test_client, admin_token, target_super.id)

    assert response.status_code == 403


def test_user_without_permission_is_blocked(test_client, test_db):
    inst = _make_institution(test_db, "tf741-no-perm")
    plain_user = _make_user(test_db, inst, "plain@tf741-no-perm.ch")
    target = _make_user(test_db, inst, "target@tf741-no-perm.ch")
    test_db.commit()
    token = _tokens(test_db, plain_user)["access_token"]

    response = _impersonate(test_client, token, target.id)

    assert response.status_code == 403


def test_target_user_not_found_returns_404(test_client, test_db):
    inst = _make_institution(test_db, "tf741-404")
    superadmin = _make_user(test_db, inst, "super@tf741-404.ch", is_superuser=True)
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    response = _impersonate(test_client, admin_token, 999_999_999)

    assert response.status_code == 404


def test_self_impersonation_rejected(test_client, test_db):
    inst = _make_institution(test_db, "tf741-self")
    superadmin = _make_user(test_db, inst, "super@tf741-self.ch", is_superuser=True)
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    response = _impersonate(test_client, admin_token, superadmin.id)

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Atomicity: a failed token mint must not leave an orphaned "active" session
# ---------------------------------------------------------------------------


def test_failed_token_mint_leaves_no_orphaned_session(test_client, test_db):
    """TF-741 review fix: the ImpersonationSession row used to be committed
    *before* AuthService.create_impersonation_token ran. If minting failed
    partway (decode failure, DB blip), the row stayed committed as "active"
    with no token ever issued -- locking the admin out of impersonating
    anyone else (via the one-active-session-per-admin check) until the
    reaper aged it out after up to 30 minutes, with no self-service
    recovery. Session creation and token minting are now one transaction:
    a failure rolls both back."""
    inst = _make_institution(test_db, "tf741-atomic-fail")
    superadmin = _make_user(
        test_db, inst, "super@tf741-atomic-fail.ch", is_superuser=True
    )
    target = _make_user(test_db, inst, "target@tf741-atomic-fail.ch")
    other_target = _make_user(test_db, inst, "other-target@tf741-atomic-fail.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    sessions_before = test_db.query(ImpersonationSession).count()

    with patch(
        "api.admin.AuthService.create_impersonation_token",
        side_effect=ValueError("Failed to decode impersonation access token"),
    ):
        failed = _impersonate(test_client, admin_token, target.id)

    assert failed.status_code == 500

    test_db.expire_all()
    assert test_db.query(ImpersonationSession).count() == sessions_before

    # The admin is not locked out by the rolled-back attempt -- a fresh,
    # unmocked impersonation succeeds immediately.
    recovered = _impersonate(test_client, admin_token, other_target.id)
    assert recovered.status_code == 200


# ---------------------------------------------------------------------------
# Nesting
# ---------------------------------------------------------------------------


def test_nested_impersonation_via_admins_own_token_rejected(test_client, test_db):
    inst = _make_institution(test_db, "tf741-nest-a")
    superadmin = _make_user(test_db, inst, "super@tf741-nest-a.ch", is_superuser=True)
    target1 = _make_user(test_db, inst, "target1@tf741-nest-a.ch")
    target2 = _make_user(test_db, inst, "target2@tf741-nest-a.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    first = _impersonate(test_client, admin_token, target1.id)
    assert first.status_code == 200

    second = _impersonate(test_client, admin_token, target2.id)

    assert second.status_code == 409


def test_nested_impersonation_via_impersonation_token_rejected(test_client, test_db):
    inst = _make_institution(test_db, "tf741-nest-b")
    superadmin = _make_user(test_db, inst, "super@tf741-nest-b.ch", is_superuser=True)
    # target1 is itself a superuser: FastAPI resolves Depends() -- including
    # require_permission("users:impersonate") on start_impersonation --
    # before the endpoint body (and its already_nested check) ever runs.
    # A target without impersonation privileges of their own would 403 out
    # of the permission dependency regardless of nesting, which would make
    # this test pass without ever exercising the nesting check it's named
    # for (TF-741 review fix: the previous version of this test did exactly
    # that). Making target1 a superuser clears the permission dependency so
    # the scenario that actually matters -- a privileged impersonation
    # token being used to pivot into a second impersonation -- is what
    # gets tested.
    target1 = _make_user(test_db, inst, "target1@tf741-nest-b.ch", is_superuser=True)
    target2 = _make_user(test_db, inst, "target2@tf741-nest-b.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    first = _impersonate(test_client, admin_token, target1.id)
    assert first.status_code == 200
    impersonation_token = first.json()["access_token"]

    second = _impersonate(test_client, impersonation_token, target2.id)

    assert second.status_code == 409


# ---------------------------------------------------------------------------
# Ending a session
# ---------------------------------------------------------------------------


def test_end_impersonation_ends_session_and_revokes_token(test_client, test_db):
    inst = _make_institution(test_db, "tf741-end")
    superadmin = _make_user(test_db, inst, "super@tf741-end.ch", is_superuser=True)
    target = _make_user(test_db, inst, "target@tf741-end.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    start = _impersonate(test_client, admin_token, target.id)
    impersonation_token = start.json()["access_token"]
    session_id = start.json()["impersonation_session_id"]

    end_response = test_client.post(
        "/api/admin/impersonate/end", headers=_auth(impersonation_token)
    )
    assert end_response.status_code == 204

    session = (
        test_db.query(ImpersonationSession)
        .filter(ImpersonationSession.id == session_id)
        .first()
    )
    assert session.ended_at is not None
    assert session.end_reason == "manual"

    # The revoked token is now unusable.
    me_response = test_client.get("/api/auth/me", headers=_auth(impersonation_token))
    assert me_response.status_code == 401

    # The admin's own token, untouched, still works ("back to my account").
    admin_me = test_client.get("/api/auth/me", headers=_auth(admin_token))
    assert admin_me.status_code == 200


def test_end_without_active_impersonation_rejected(test_client, test_db):
    inst = _make_institution(test_db, "tf741-end-none")
    superadmin = _make_user(test_db, inst, "super@tf741-end-none.ch", is_superuser=True)
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    response = test_client.post(
        "/api/admin/impersonate/end", headers=_auth(admin_token)
    )

    assert response.status_code == 400


def test_end_impersonation_recovers_via_admins_own_token_if_impersonation_token_lost(
    test_client, test_db
):
    """TF-741 review fix: if the impersonation token itself is lost (tab
    closed, storage cleared, browser crash), the admin previously had no
    way to end their own open session -- POST /impersonate/end required
    the (lost) impersonation token, and start_impersonation's own-session
    check would then lock them out of impersonating anyone else until the
    reaper aged the row out after up to ~30 minutes. Calling
    /impersonate/end with the admin's own token now falls back to closing
    their own open session directly."""
    inst = _make_institution(test_db, "tf741-end-recover")
    superadmin = _make_user(
        test_db, inst, "super@tf741-end-recover.ch", is_superuser=True
    )
    target = _make_user(test_db, inst, "target@tf741-end-recover.ch")
    other_target = _make_user(test_db, inst, "other-target@tf741-end-recover.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    start = _impersonate(test_client, admin_token, target.id)
    assert start.status_code == 200
    session_id = start.json()["impersonation_session_id"]
    # The impersonation token itself is deliberately never used here --
    # simulating that it was lost.

    end_response = test_client.post(
        "/api/admin/impersonate/end", headers=_auth(admin_token)
    )
    assert end_response.status_code == 204

    test_db.expire_all()
    session = (
        test_db.query(ImpersonationSession)
        .filter(ImpersonationSession.id == session_id)
        .first()
    )
    assert session.ended_at is not None
    assert session.end_reason == "manual"

    # The admin is no longer locked out -- a fresh impersonation succeeds
    # immediately, no reaper wait needed.
    second_start = _impersonate(test_client, admin_token, other_target.id)
    assert second_start.status_code == 200


def test_logout_during_impersonation_ends_session_not_target_sessions(
    test_client, test_db
):
    """TF-741 review fix: while impersonating, ``current_user`` resolves to
    the target, not the admin. Logging out must not call
    revoke_all_user_sessions on the real target (forcibly killing all of
    their other devices/tabs) -- it should just end the impersonation,
    like POST /admin/impersonate/end."""
    inst = _make_institution(test_db, "tf741-logout-imp")
    superadmin = _make_user(
        test_db, inst, "super@tf741-logout-imp.ch", is_superuser=True
    )
    target = _make_user(test_db, inst, "target@tf741-logout-imp.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    # The target has an independent session of their own that must survive.
    target_own_token = _tokens(test_db, target)["access_token"]

    start = _impersonate(test_client, admin_token, target.id)
    assert start.status_code == 200
    session_id = start.json()["impersonation_session_id"]
    impersonation_token = start.json()["access_token"]

    logout_response = test_client.post(
        "/api/auth/logout", headers=_auth(impersonation_token)
    )
    assert logout_response.status_code == 204

    test_db.expire_all()
    session = (
        test_db.query(ImpersonationSession)
        .filter(ImpersonationSession.id == session_id)
        .first()
    )
    assert session.ended_at is not None
    assert session.end_reason == "manual"

    # The target's own, independent session was not touched.
    target_me = test_client.get("/api/auth/me", headers=_auth(target_own_token))
    assert target_me.status_code == 200

    # The admin's own token is untouched too.
    admin_me = test_client.get("/api/auth/me", headers=_auth(admin_token))
    assert admin_me.status_code == 200


# ---------------------------------------------------------------------------
# Support use case: suspended target
# ---------------------------------------------------------------------------


def test_impersonating_suspended_target_still_allows_requests(test_client, test_db):
    inst = _make_institution(test_db, "tf741-suspended")
    superadmin = _make_user(
        test_db, inst, "super@tf741-suspended.ch", is_superuser=True
    )
    suspended_target = _make_user(
        test_db,
        inst,
        "suspended@tf741-suspended.ch",
        status=UserStatus.SUSPENDED.value,
    )
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    start = _impersonate(test_client, admin_token, suspended_target.id)
    assert start.status_code == 200
    impersonation_token = start.json()["access_token"]

    me_response = test_client.get("/api/auth/me", headers=_auth(impersonation_token))

    assert me_response.status_code == 200
    assert me_response.json()["email"] == suspended_target.email


# ---------------------------------------------------------------------------
# Account-security guard on other endpoints
# ---------------------------------------------------------------------------


def _start_impersonation(test_client, test_db, slug):
    inst = _make_institution(test_db, slug)
    superadmin = _make_user(test_db, inst, f"super@{slug}.ch", is_superuser=True)
    target = _make_user(test_db, inst, f"target@{slug}.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]
    start = _impersonate(test_client, admin_token, target.id)
    assert start.status_code == 200
    return start.json()["access_token"]


def test_change_password_blocked_during_impersonation(test_client, test_db):
    token = _start_impersonation(test_client, test_db, "tf741-guard-pw")

    response = test_client.post(
        "/api/auth/change-password",
        json={"current_password": "irrelevant", "new_password": "NewPass1234!"},
        headers=_auth(token),
    )

    assert response.status_code == 403


def test_request_deletion_blocked_during_impersonation(test_client, test_db):
    token = _start_impersonation(test_client, test_db, "tf741-guard-del-req")

    response = test_client.post("/api/v1/gdpr/request-deletion", headers=_auth(token))

    assert response.status_code == 403


def test_delete_account_now_blocked_during_impersonation(test_client, test_db):
    token = _start_impersonation(test_client, test_db, "tf741-guard-del-now")

    response = test_client.request(
        "DELETE",
        "/api/v1/gdpr/delete-account-now",
        params={"password": "irrelevant"},
        headers=_auth(token),
    )

    assert response.status_code == 403


def test_create_checkout_session_blocked_during_impersonation(test_client, test_db):
    token = _start_impersonation(test_client, test_db, "tf741-guard-checkout")

    response = test_client.post(
        "/api/v1/billing/create-checkout-session",
        json={"price_id": "price_test"},
        headers=_auth(token),
    )

    assert response.status_code == 403


def test_customer_portal_blocked_during_impersonation(test_client, test_db):
    token = _start_impersonation(test_client, test_db, "tf741-guard-portal")

    response = test_client.post("/api/v1/billing/customer-portal", headers=_auth(token))

    assert response.status_code == 403


def test_set_password_blocked_during_impersonation(test_client, test_db):
    """TF-741 review fix: /auth/set-password needs no existing credential,
    so an admin impersonating an OAuth-only target could otherwise give
    that account an admin-chosen password that outlives the 30-minute
    impersonation session entirely -- the guard was missing here even
    though it was applied to /auth/change-password."""
    inst = _make_institution(test_db, "tf741-guard-set-pw")
    superadmin = _make_user(
        test_db, inst, "super@tf741-guard-set-pw.ch", is_superuser=True
    )
    oauth_target = User(
        email="oauth-target@tf741-guard-set-pw.ch",
        password_hash=None,
        first_name="Test",
        last_name="User",
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
        oauth_provider="google",
    )
    test_db.add(oauth_target)
    test_db.flush()
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    start = _impersonate(test_client, admin_token, oauth_target.id)
    assert start.status_code == 200
    token = start.json()["access_token"]

    response = test_client.post(
        "/api/auth/set-password",
        json={"password": "NewPass1234!"},
        headers=_auth(token),
    )

    assert response.status_code == 403


def test_change_password_endpoint_reachable_without_impersonation(test_client, test_db):
    """Regression: the guard must not block the normal, non-impersonated path."""
    inst = _make_institution(test_db, "tf741-guard-regression")
    user = _make_user(test_db, inst, "user@tf741-guard-regression.ch")
    test_db.commit()
    token = _tokens(test_db, user)["access_token"]

    response = test_client.post(
        "/api/auth/change-password",
        json={"current_password": "Test1234!", "new_password": "NewPass1234!"},
        headers=_auth(token),
    )

    assert response.status_code == 204


# ---------------------------------------------------------------------------
# TF-758: admin password re-entry (step-up) before minting the token
# ---------------------------------------------------------------------------


def test_impersonation_wrong_admin_password_rejected(test_client, test_db):
    """Wrong ``admin_password`` blocks the start -- no session is created."""
    inst = _make_institution(test_db, "tf758-wrong-pw")
    superadmin = _make_user(test_db, inst, "super@tf758-wrong-pw.ch", is_superuser=True)
    target = _make_user(test_db, inst, "target@tf758-wrong-pw.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    response = _impersonate(
        test_client, admin_token, target.id, admin_password="WrongPassword!"
    )

    assert response.status_code == 400
    assert (
        test_db.query(ImpersonationSession)
        .filter(ImpersonationSession.admin_user_id == superadmin.id)
        .count()
        == 0
    )


def test_impersonation_wrong_admin_password_is_audited(test_client, test_db):
    """A failed step-up attempt is written to the audit trail (STATUS_FAILURE,
    same ACTION_IMPERSONATION_START action as a successful start)."""
    from services.audit_service import AuditService

    inst = _make_institution(test_db, "tf758-wrong-pw-audit")
    superadmin = _make_user(
        test_db, inst, "super@tf758-wrong-pw-audit.ch", is_superuser=True
    )
    target = _make_user(test_db, inst, "target@tf758-wrong-pw-audit.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    _impersonate(test_client, admin_token, target.id, admin_password="WrongPassword!")

    log_entry = (
        test_db.query(AuditLog)
        .filter(
            AuditLog.action == AuditService.ACTION_IMPERSONATION_START,
            AuditLog.status == AuditService.STATUS_FAILURE,
            AuditLog.user_id == superadmin.id,
        )
        .first()
    )
    assert log_entry is not None
    assert log_entry.resource_id == str(target.id)


def test_impersonation_missing_admin_password_field_rejected(test_client, test_db):
    """``admin_password`` is a required field -- omitting it is a 422, not a
    silent bypass of the step-up."""
    inst = _make_institution(test_db, "tf758-missing-pw")
    superadmin = _make_user(
        test_db, inst, "super@tf758-missing-pw.ch", is_superuser=True
    )
    target = _make_user(test_db, inst, "target@tf758-missing-pw.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    response = test_client.post(
        f"/api/admin/users/{target.id}/impersonate",
        json={"reason": "Support-Anfrage TICKET-1"},
        headers=_auth(admin_token),
    )

    assert response.status_code == 422


def test_impersonation_oauth_only_admin_blocked(test_client, test_db):
    """An admin with no password set (OAuth-only account) cannot use the
    step-up at all -- rejected outright rather than silently skipped."""
    inst = _make_institution(test_db, "tf758-oauth-admin")
    oauth_admin = User(
        email="oauth-admin@tf758-oauth-admin.ch",
        password_hash=None,
        first_name="Test",
        last_name="Admin",
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=True,
        oauth_provider="google",
    )
    test_db.add(oauth_admin)
    test_db.flush()
    target = _make_user(test_db, inst, "target@tf758-oauth-admin.ch")
    test_db.commit()
    admin_token = _tokens(test_db, oauth_admin)["access_token"]

    response = _impersonate(test_client, admin_token, target.id)

    assert response.status_code == 403
    assert (
        test_db.query(ImpersonationSession)
        .filter(ImpersonationSession.admin_user_id == oauth_admin.id)
        .count()
        == 0
    )


def test_impersonation_correct_admin_password_still_succeeds(test_client, test_db):
    """Sanity check: the step-up doesn't break the happy path."""
    inst = _make_institution(test_db, "tf758-correct-pw")
    superadmin = _make_user(
        test_db, inst, "super@tf758-correct-pw.ch", is_superuser=True
    )
    target = _make_user(test_db, inst, "target@tf758-correct-pw.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    response = _impersonate(
        test_client, admin_token, target.id, admin_password="Test1234!"
    )

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# TF-758 review fixes: check-ordering regression coverage, lockout, audit
# symmetry
# ---------------------------------------------------------------------------


def test_impersonation_wrong_password_and_nonexistent_target_returns_400_not_404(
    test_client, test_db
):
    """The step-up's whole point is that a hijacked admin session can't use
    404-vs-400 as an oracle to enumerate target user IDs -- so a wrong
    password against a *nonexistent* target must still be a plain 400, not
    the 404 that ``test_target_user_not_found_returns_404`` gets with the
    correct password. Regression guard for the check ordering described in
    the comment above the step-up in api/admin.py."""
    inst = _make_institution(test_db, "tf758-wrong-pw-404")
    superadmin = _make_user(
        test_db, inst, "super@tf758-wrong-pw-404.ch", is_superuser=True
    )
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    response = _impersonate(
        test_client, admin_token, 999_999_999, admin_password="WrongPassword!"
    )

    assert response.status_code == 400


def test_impersonation_wrong_password_and_cross_institution_target_returns_400_not_403(
    test_client, test_db
):
    """Same regression guard as the 404 case above, but against the
    institution-scope 403 that ``test_institution_admin_blocked_cross_institution``
    gets with the correct password -- a wrong password must pre-empt that
    too, not reveal that the target exists in another institution."""
    inst = _make_institution(test_db, "tf758-wrong-pw-cross-a")
    other_inst = _make_institution(test_db, "tf758-wrong-pw-cross-b")
    admin = _make_user(test_db, inst, "admin@tf758-wrong-pw-cross-a.ch")
    _grant_impersonate_permission(test_db, admin)
    target = _make_user(test_db, other_inst, "target@tf758-wrong-pw-cross-b.ch")
    test_db.commit()
    admin_token = _tokens(test_db, admin)["access_token"]

    response = _impersonate(
        test_client, admin_token, target.id, admin_password="WrongPassword!"
    )

    assert response.status_code == 400


def test_impersonation_empty_admin_password_rejected(test_client, test_db):
    """``min_length=1`` on ``admin_password`` is enforced by Pydantic, not
    just by the frontend's non-empty guard -- an empty string sent directly
    to the API is a 422, same as omitting the field entirely."""
    inst = _make_institution(test_db, "tf758-empty-pw")
    superadmin = _make_user(test_db, inst, "super@tf758-empty-pw.ch", is_superuser=True)
    target = _make_user(test_db, inst, "target@tf758-empty-pw.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    response = _impersonate(test_client, admin_token, target.id, admin_password="")

    assert response.status_code == 422


def test_impersonation_oauth_only_admin_rejection_is_audited(test_client, test_db):
    """Review fix: the "no password set" (403) branch must be audited just
    like the "wrong password" (400) branch -- both are attempts to use the
    step-up on a hijacked/left-open admin session, so both need a trail."""
    from services.audit_service import AuditService

    inst = _make_institution(test_db, "tf758-oauth-audit")
    oauth_admin = User(
        email="oauth-admin@tf758-oauth-audit.ch",
        password_hash=None,
        first_name="Test",
        last_name="Admin",
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=True,
        oauth_provider="google",
    )
    test_db.add(oauth_admin)
    test_db.flush()
    target = _make_user(test_db, inst, "target@tf758-oauth-audit.ch")
    test_db.commit()
    admin_token = _tokens(test_db, oauth_admin)["access_token"]

    response = _impersonate(test_client, admin_token, target.id)
    assert response.status_code == 403

    log_entry = (
        test_db.query(AuditLog)
        .filter(
            AuditLog.action == AuditService.ACTION_IMPERSONATION_START,
            AuditLog.status == AuditService.STATUS_FAILURE,
            AuditLog.user_id == oauth_admin.id,
        )
        .first()
    )
    assert log_entry is not None
    assert log_entry.resource_id == str(target.id)


def test_impersonation_locks_out_after_repeated_wrong_password_attempts(
    test_client, test_db, monkeypatch
):
    """Critical review fix: without a lockout, the step-up would be a free
    password oracle for a hijacked admin token. After
    ``MAX_FAILED_PASSWORD_ATTEMPTS`` wrong guesses, even the *correct*
    password is rejected with 429 -- same account-wide lockout
    POST /auth/login enforces, since both share the same counter.

    Uses a generously loosened TF-760 rate limiter so this test exercises
    the TF-758 lockout specifically and isn't coincidentally gated by the
    (independent, differently-scoped) per-admin rate limit instead --
    which defaults to the same threshold (10/hour) this test's own
    ``MAX_FAILED_PASSWORD_ATTEMPTS`` happens to use."""
    from middleware.rate_limit import ImpersonationRateLimiter

    _patch_impersonation_rate_limiter(
        monkeypatch,
        ImpersonationRateLimiter(requests_per_hour=1000, requests_per_day=1000),
    )

    inst = _make_institution(test_db, "tf758-lockout")
    superadmin = _make_user(test_db, inst, "super@tf758-lockout.ch", is_superuser=True)
    target = _make_user(test_db, inst, "target@tf758-lockout.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    for _ in range(AuthService.MAX_FAILED_PASSWORD_ATTEMPTS):
        response = _impersonate(
            test_client, admin_token, target.id, admin_password="WrongPassword!"
        )
        assert response.status_code == 400

    locked_response = _impersonate(
        test_client, admin_token, target.id, admin_password="Test1234!"
    )

    assert locked_response.status_code == 429
    assert (
        test_db.query(ImpersonationSession)
        .filter(ImpersonationSession.admin_user_id == superadmin.id)
        .count()
        == 0
    )


def test_impersonation_correct_password_resets_failed_attempt_counter(
    test_client, test_db, monkeypatch
):
    """A successful step-up clears the shared failed-attempt counter, same
    as a successful POST /auth/login -- a few wrong guesses followed by the
    right password must not carry a residual count toward a later
    lockout.

    Same TF-760 rate-limiter decoupling as the lockout test above -- 10
    total calls here would otherwise sit right at that limiter's own
    default hourly threshold too."""
    from middleware.rate_limit import ImpersonationRateLimiter

    _patch_impersonation_rate_limiter(
        monkeypatch,
        ImpersonationRateLimiter(requests_per_hour=1000, requests_per_day=1000),
    )

    inst = _make_institution(test_db, "tf758-reset-counter")
    superadmin = _make_user(
        test_db, inst, "super@tf758-reset-counter.ch", is_superuser=True
    )
    target = _make_user(test_db, inst, "target@tf758-reset-counter.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    for _ in range(AuthService.MAX_FAILED_PASSWORD_ATTEMPTS - 1):
        _impersonate(
            test_client, admin_token, target.id, admin_password="WrongPassword!"
        )

    success_response = _impersonate(
        test_client, admin_token, target.id, admin_password="Test1234!"
    )
    assert success_response.status_code == 200

    test_db.refresh(superadmin)
    assert superadmin.failed_login_attempts == 0
    assert superadmin.last_failed_login is None


# ---------------------------------------------------------------------------
# Per-admin rate limiting (TF-760)
# ---------------------------------------------------------------------------


def test_admin_is_rate_limited_after_too_many_impersonation_attempts(
    test_client, test_db, monkeypatch
):
    """The limiter counts every start *attempt*, not just successful
    starts -- so the 2nd call (blocked as 409 "already active" by the
    unrelated nesting guard) still counts toward the admin's budget, and
    the 3rd call is rejected by the limiter itself before it even reaches
    that check."""
    from middleware.rate_limit import ImpersonationRateLimiter

    _patch_impersonation_rate_limiter(
        monkeypatch,
        ImpersonationRateLimiter(requests_per_hour=2, requests_per_day=30),
    )

    inst = _make_institution(test_db, "tf760-hourly")
    superadmin = _make_user(test_db, inst, "super@tf760-hourly.ch", is_superuser=True)
    target = _make_user(test_db, inst, "target@tf760-hourly.ch")
    test_db.commit()
    admin_token = _tokens(test_db, superadmin)["access_token"]

    first = _impersonate(test_client, admin_token, target.id)
    assert first.status_code == 200

    second = _impersonate(test_client, admin_token, target.id)
    assert second.status_code == 409

    third = _impersonate(test_client, admin_token, target.id)

    assert third.status_code == 429
    assert "Retry-After" in third.headers
    assert 0 < int(third.headers["Retry-After"]) <= 3600

    audit_rows = (
        test_db.query(AuditLog)
        .filter(
            AuditLog.user_id == superadmin.id,
            AuditLog.action == "rate_limit_exceeded",
        )
        .all()
    )
    assert len(audit_rows) == 1


def test_impersonation_rate_limit_is_tracked_per_admin(
    test_client, test_db, monkeypatch
):
    """One admin hitting their limit must not affect a different admin."""
    from middleware.rate_limit import ImpersonationRateLimiter

    _patch_impersonation_rate_limiter(
        monkeypatch,
        ImpersonationRateLimiter(requests_per_hour=1, requests_per_day=30),
    )

    inst = _make_institution(test_db, "tf760-per-admin")
    admin_one = _make_user(
        test_db, inst, "admin-one@tf760-per-admin.ch", is_superuser=True
    )
    admin_two = _make_user(
        test_db, inst, "admin-two@tf760-per-admin.ch", is_superuser=True
    )
    target = _make_user(test_db, inst, "target@tf760-per-admin.ch")
    test_db.commit()
    admin_one_token = _tokens(test_db, admin_one)["access_token"]
    admin_two_token = _tokens(test_db, admin_two)["access_token"]

    first = _impersonate(test_client, admin_one_token, target.id)
    assert first.status_code == 200

    blocked = _impersonate(test_client, admin_one_token, target.id)
    assert blocked.status_code == 429

    still_allowed = _impersonate(test_client, admin_two_token, target.id)
    assert still_allowed.status_code == 200
