"""OIDC login flow against a mocked Zitadel (EXAMCRAFT-125).

Callback: known sub, JIT, blocked user, bad state, IdP failure. Session
cookie lifecycle: me, expiry, status check per request, logout,
impersonation. Test-login endpoint: absent by default, startup refusal in
production.
"""

import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jose import jwk, jwt

from database import get_db
from main import app
from models.auth import AuthSession, Institution, Role, User, UserRole, UserStatus
from services import oidc_client, session_service

ISSUER = "https://tessera.example"
CLIENT_ID = "examcraft-web"


@pytest.fixture(autouse=True)
def oidc_env(monkeypatch):
    monkeypatch.setenv("OIDC_ISSUER", ISSUER)
    monkeypatch.setenv("OIDC_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "s3cret")  # pragma: allowlist secret
    monkeypatch.setenv("OIDC_REDIRECT_URI", "http://testserver/api/v1/auth/callback")
    monkeypatch.setenv("FRONTEND_URL", "http://frontend.example")
    monkeypatch.setenv("ZITADEL_ORG_ID", "org-123")
    oidc_client.clear_caches()
    yield
    oidc_client.clear_caches()


@pytest.fixture(scope="module")
def signing_key():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    from cryptography.hazmat.primitives import serialization

    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public = jwk.construct(key.public_key(), "RS256").to_dict()
    public.update({"kid": "k1", "use": "sig", "alg": "RS256"})
    return pem.decode(), public


@pytest.fixture
def db(test_db):
    inst = Institution(
        name="Schule",
        slug="schule-oidc",
        domain="schule.example",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=100,
    )
    test_db.add(inst)
    for name in (UserRole.ADMIN.value, UserRole.DOZENT.value, UserRole.VIEWER.value):
        if not test_db.query(Role).filter(Role.name == name).first():
            test_db.add(
                Role(
                    name=name,
                    display_name=name,
                    description=name,
                    permissions=[],
                    is_system_role=True,
                )
            )
    test_db.commit()
    return test_db


@pytest.fixture
def client(db):
    from api import auth, auth_oidc, admin

    app.include_router(auth.router)
    app.include_router(auth_oidc.router)
    app.include_router(admin.router)
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app, follow_redirects=False)
    app.dependency_overrides.clear()


def _mock_idp(signing_key, sub, email, nonce, *, extra=None):
    pem, public = signing_key
    claims = {
        "iss": ISSUER,
        "aud": CLIENT_ID,
        "sub": sub,
        "exp": int(time.time()) + 300,
        "iat": int(time.time()),
        "nonce": nonce,
        "email": email,
        "email_verified": True,
        **(extra or {}),
    }
    id_token = jwt.encode(claims, pem, algorithm="RS256", headers={"kid": "k1"})
    respx.get(f"{ISSUER}/.well-known/openid-configuration").mock(
        return_value=httpx.Response(
            200,
            json={
                "authorization_endpoint": f"{ISSUER}/oauth/v2/authorize",
                "token_endpoint": f"{ISSUER}/oauth/v2/token",
                "jwks_uri": f"{ISSUER}/oauth/v2/keys",
                "userinfo_endpoint": f"{ISSUER}/oidc/v1/userinfo",
            },
        )
    )
    respx.get(f"{ISSUER}/oauth/v2/keys").mock(
        return_value=httpx.Response(200, json={"keys": [public]})
    )
    respx.post(f"{ISSUER}/oauth/v2/token").mock(
        return_value=httpx.Response(
            200, json={"id_token": id_token, "access_token": "at"}
        )
    )
    respx.get(f"{ISSUER}/oidc/v1/userinfo").mock(
        return_value=httpx.Response(200, json={"sub": sub, "email": email})
    )


def _start(client):
    """GET /login, return (state, nonce) and leave the flow cookies on the client."""
    resp = client.get("/api/v1/auth/login")
    assert resp.status_code == 307
    query = parse_qs(urlparse(resp.headers["location"]).query)
    return query["state"][0], client.cookies.get("oidc_nonce"), query


class TestLogin:
    @respx.mock
    def test_login_redirects_with_pkce_state_nonce_and_org_scope(
        self, client, signing_key
    ):
        _mock_idp(signing_key, "s", "a@schule.example", "n")
        _state, _nonce, q = _start(client)
        assert q["client_id"] == [CLIENT_ID] or q["client_id"] == CLIENT_ID
        assert q["code_challenge_method"] == ["S256"]
        assert "urn:zitadel:iam:org:id:org-123" in q["scope"][0]
        assert "prompt" not in q

    @respx.mock
    def test_reauth_forces_prompt_login(self, client, signing_key):
        _mock_idp(signing_key, "s", "a@schule.example", "n")
        resp = client.get("/api/v1/auth/login?reauth=true")
        assert parse_qs(urlparse(resp.headers["location"]).query)["prompt"] == ["login"]

    @respx.mock
    def test_idp_down_redirects_to_login_error(self, client):
        respx.get(f"{ISSUER}/.well-known/openid-configuration").mock(
            return_value=httpx.Response(503)
        )
        resp = client.get("/api/v1/auth/login")
        assert resp.headers["location"].endswith("/login?error=idp_unavailable")


class TestCallback:
    @respx.mock
    def test_new_user_is_provisioned_and_session_cookie_set(
        self, client, db, signing_key
    ):
        state, nonce, _ = _start_unmocked(client)
        _mock_idp(signing_key, "sub-new", "new@schule.example", nonce)
        resp = client.get(f"/api/v1/auth/callback?state={state}&code=abc")
        assert resp.status_code == 307
        assert resp.headers["location"] == "http://frontend.example/"
        user = db.query(User).filter(User.zitadel_sub == "sub-new").one()
        assert user.last_login_at is not None  # record_login ran
        assert db.query(AuthSession).filter_by(user_id=user.id).count() == 1
        set_cookie = resp.headers.get_list("set-cookie")
        session_cookie = next(c for c in set_cookie if c.startswith("session_id="))
        assert "HttpOnly" in session_cookie and "samesite=lax" in session_cookie.lower()

    @respx.mock
    def test_known_sub_logs_in_without_creating(self, client, db, signing_key):
        inst = db.query(Institution).filter_by(slug="schule-oidc").one()
        db.add(
            User(
                email="old@schule.example",
                zitadel_sub="sub-old",
                first_name="O",
                last_name="L",
                institution_id=inst.id,
                status=UserStatus.ACTIVE.value,
            )
        )
        db.commit()
        before = db.query(User).count()
        state, nonce, _ = _start_unmocked(client)
        _mock_idp(signing_key, "sub-old", "old@schule.example", nonce)
        resp = client.get(f"/api/v1/auth/callback?state={state}&code=abc")
        assert resp.status_code == 307 and "error" not in resp.headers["location"]
        assert db.query(User).count() == before

    @respx.mock
    def test_record_login_once_per_session(self, client, db, signing_key):
        state, nonce, _ = _start_unmocked(client)
        _mock_idp(signing_key, "sub-r", "r@schule.example", nonce)
        client.get(f"/api/v1/auth/callback?state={state}&code=abc")
        user = db.query(User).filter_by(zitadel_sub="sub-r").one()
        assert user.previous_login_at is None
        first = user.last_login_at
        # /auth/me (a request in the session) must not stamp another login
        client.get("/api/auth/me")
        db.refresh(user)
        assert user.last_login_at == first

    @pytest.mark.parametrize("status", ["suspended", "inactive", "pending"])
    @respx.mock
    def test_non_active_user_is_rejected(self, client, db, signing_key, status):
        inst = db.query(Institution).filter_by(slug="schule-oidc").one()
        db.add(
            User(
                email="b@schule.example",
                zitadel_sub="sub-b",
                first_name="B",
                last_name="B",
                institution_id=inst.id,
                status=status,
            )
        )
        db.commit()
        state, nonce, _ = _start_unmocked(client)
        _mock_idp(signing_key, "sub-b", "b@schule.example", nonce)
        resp = client.get(f"/api/v1/auth/callback?state={state}&code=abc")
        assert resp.headers["location"].endswith("/login?error=account_inactive")
        assert db.query(AuthSession).count() == 0

    @respx.mock
    def test_state_mismatch_redirects_and_exchanges_no_code(self, client, signing_key):
        _start_unmocked(client)
        resp = client.get("/api/v1/auth/callback?state=forged&code=abc")
        assert resp.status_code == 307
        assert resp.headers["location"].endswith("/login?error=login_expired")
        assert not any(c.url.path.endswith("/token") for c, _ in respx.calls)

    def test_missing_flow_cookies_redirect(self, client):
        resp = client.get("/api/v1/auth/callback?state=x&code=abc")
        assert resp.headers["location"].endswith("/login?error=login_expired")

    def test_missing_state_param_redirects(self, client):
        resp = client.get("/api/v1/auth/callback?code=abc")
        assert resp.headers["location"].endswith("/login?error=login_expired")

    @respx.mock
    def test_missing_nonce_cookie_is_rejected(self, client, signing_key):
        state, _nonce, _ = _start_unmocked(client)
        client.cookies.delete("oidc_nonce")
        resp = client.get(f"/api/v1/auth/callback?state={state}&code=abc")
        assert resp.headers["location"].endswith("/login?error=login_expired")

    @respx.mock
    def test_wrong_nonce_is_login_failed(self, client, signing_key):
        state, _nonce, _ = _start_unmocked(client)
        _mock_idp(signing_key, "s", "x@schule.example", "other-nonce")
        resp = client.get(f"/api/v1/auth/callback?state={state}&code=abc")
        assert resp.headers["location"].endswith("/login?error=login_failed")

    @respx.mock
    def test_denied_consent_redirects(self, client):
        state, _n, _ = _start_unmocked(client)
        resp = client.get(f"/api/v1/auth/callback?state={state}&error=access_denied")
        assert resp.headers["location"].endswith("/login?error=login_cancelled")

    @respx.mock
    def test_email_conflict_redirects(self, client, db, signing_key):
        inst = db.query(Institution).filter_by(slug="schule-oidc").one()
        db.add(
            User(
                email="dup@schule.example",
                first_name="D",
                last_name="D",
                institution_id=inst.id,
                status=UserStatus.ACTIVE.value,
            )
        )
        db.commit()
        state, nonce, _ = _start_unmocked(client)
        _mock_idp(signing_key, "sub-dup", "dup@schule.example", nonce)
        resp = client.get(f"/api/v1/auth/callback?state={state}&code=abc")
        assert resp.headers["location"].endswith("/login?error=email_conflict")

    @respx.mock
    def test_token_endpoint_failure_redirects(self, client, signing_key):
        state, nonce, _ = _start_unmocked(client)
        _mock_idp(signing_key, "s", "x@schule.example", nonce)
        respx.post(f"{ISSUER}/oauth/v2/token").mock(return_value=httpx.Response(500))
        resp = client.get(f"/api/v1/auth/callback?state={state}&code=abc")
        assert resp.headers["location"].endswith("/login?error=login_failed")


def _start_unmocked(client):
    respx.get(f"{ISSUER}/.well-known/openid-configuration").mock(
        return_value=httpx.Response(
            200,
            json={
                "authorization_endpoint": f"{ISSUER}/oauth/v2/authorize",
                "token_endpoint": f"{ISSUER}/oauth/v2/token",
                "jwks_uri": f"{ISSUER}/oauth/v2/keys",
            },
        )
    )
    return _start(client)


def _login_as(client, db, email="u@schule.example", **user_kwargs):
    inst = db.query(Institution).filter_by(slug="schule-oidc").one()
    dozent = db.query(Role).filter_by(name=UserRole.DOZENT.value).one()
    user = User(
        email=email,
        zitadel_sub=f"sub-{email}",
        first_name="U",
        last_name="U",
        institution_id=inst.id,
        status=user_kwargs.pop("status", UserStatus.ACTIVE.value),
        **user_kwargs,
    )
    user.roles.append(dozent)
    db.add(user)
    db.commit()
    token, row = session_service.create_session(
        db, user.id, authenticated_at=datetime.now(timezone.utc)
    )
    client.cookies.set(session_service.SESSION_COOKIE_NAME, token)
    return user, row


class TestSessionOnRequests:
    def test_me_with_session(self, client, db):
        user, _ = _login_as(client, db)
        resp = client.get("/api/auth/me")
        assert resp.status_code == 200 and resp.json()["email"] == user.email

    def test_no_cookie_is_401(self, client):
        assert client.get("/api/auth/me").status_code == 401

    def test_bearer_token_is_no_longer_accepted(self, client, db):
        from services.auth_service import AuthService

        user, _ = _login_as(client, db)
        client.cookies.clear()
        token = AuthService.create_access_token({"sub": str(user.id)})
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_expired_session_is_401(self, client, db):
        _user, row = _login_as(client, db)
        from datetime import datetime, timezone

        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
        assert client.get("/api/auth/me").status_code == 401

    @pytest.mark.parametrize("status", ["suspended", "inactive", "pending"])
    def test_status_is_checked_on_every_request(self, client, db, status):
        user, _ = _login_as(client, db)
        assert client.get("/api/auth/me").status_code == 200
        user.status = status
        db.commit()
        assert client.get("/api/auth/me").status_code == 403

    def test_deleted_user_session_is_gone(self, client, db):
        user, _ = _login_as(client, db)
        db.delete(user)
        db.commit()
        assert client.get("/api/auth/me").status_code == 401


class TestLogout:
    def test_logout_ends_local_session_and_is_idempotent(self, client, db):
        _login_as(client, db)
        assert client.post("/api/v1/auth/logout").status_code == 204
        assert db.query(AuthSession).count() == 0
        assert client.get("/api/auth/me").status_code == 401
        assert client.post("/api/v1/auth/logout").status_code == 204

    def test_logout_without_session_is_noop(self, client):
        assert client.post("/api/v1/auth/logout").status_code == 204


class TestImpersonationSession:
    def _admin_and_target(self, client, db):
        admin, row = _login_as(client, db, "adm@schule.example", is_superuser=True)
        target_inst = db.query(Institution).filter_by(slug="schule-oidc").one()
        target = User(
            email="tgt@schule.example",
            zitadel_sub="sub-tgt",
            first_name="T",
            last_name="T",
            institution_id=target_inst.id,
            status=UserStatus.ACTIVE.value,
        )
        db.add(target)
        db.commit()
        return admin, target, row

    def test_requires_recent_login(self, client, db):
        from datetime import datetime, timezone

        admin, target, row = self._admin_and_target(client, db)
        row.authenticated_at = datetime.now(timezone.utc) - timedelta(hours=2)
        db.commit()
        resp = client.post(
            f"/api/admin/users/{target.id}/impersonate", json={"reason": "support"}
        )
        assert resp.status_code == 403
        assert (
            db.query(AuthSession)
            .filter(AuthSession.impersonator_id.isnot(None))
            .count()
            == 0
        )

    def test_start_acts_as_target_and_end_returns_to_admin(self, client, db):
        admin, target, _row = self._admin_and_target(client, db)
        resp = client.post(
            f"/api/admin/users/{target.id}/impersonate", json={"reason": "support"}
        )
        assert resp.status_code == 200, resp.text
        assert "access_token" not in resp.json()
        assert client.cookies.get(session_service.IMPERSONATION_COOKIE_NAME)
        assert client.get("/api/auth/me").json()["email"] == target.email

        assert client.post("/api/admin/impersonate/end").status_code == 204
        assert client.get("/api/auth/me").json()["email"] == admin.email

    def test_logout_while_impersonating_keeps_admin_logged_in(self, client, db):
        admin, target, _row = self._admin_and_target(client, db)
        client.post(
            f"/api/admin/users/{target.id}/impersonate", json={"reason": "support"}
        )
        assert client.post("/api/v1/auth/logout").status_code == 204
        assert client.get("/api/auth/me").json()["email"] == admin.email

    def test_impersonation_session_expires_after_30_minutes_at_most(self, client, db):
        admin, target, _row = self._admin_and_target(client, db)
        client.post(
            f"/api/admin/users/{target.id}/impersonate", json={"reason": "support"}
        )
        imp = (
            db.query(AuthSession).filter(AuthSession.impersonator_id == admin.id).one()
        )
        from datetime import datetime, timezone

        assert imp.expires_at - datetime.now(timezone.utc) <= timedelta(minutes=30)
        imp.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
        # expired impersonation falls back to the admin's own identity
        assert client.get("/api/auth/me").json()["email"] == admin.email


class TestTestLogin:
    def test_route_absent_by_default(self, client):
        assert client.post(
            "/api/v1/auth/test-login", json={"email": "a@b.example"}
        ).status_code in (404, 405)

    def test_production_refuses_to_start_with_flag(self, monkeypatch):
        from api import auth_oidc

        monkeypatch.setenv("E2E_TEST_LOGIN", "true")
        monkeypatch.setenv("ENVIRONMENT", "production")
        with pytest.raises(RuntimeError, match="E2E_TEST_LOGIN"):
            auth_oidc.assert_test_login_safe()

    def test_flag_outside_production_is_allowed(self, monkeypatch):
        from api import auth_oidc

        monkeypatch.setenv("E2E_TEST_LOGIN", "true")
        monkeypatch.setenv("ENVIRONMENT", "development")
        auth_oidc.assert_test_login_safe()

    def test_production_without_flag_is_fine(self, monkeypatch):
        from api import auth_oidc

        monkeypatch.delenv("E2E_TEST_LOGIN", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "production")
        auth_oidc.assert_test_login_safe()


class TestReauth:
    def _flow(self, client, signing_key, auth_time, reauth=True):
        _mock_idp(signing_key, "sub-re", "re@schule.example", "n")
        url = "/api/v1/auth/login?reauth=true" if reauth else "/api/v1/auth/login"
        resp = client.get(url)
        q = parse_qs(urlparse(resp.headers["location"]).query)
        state, nonce = q["state"][0], client.cookies.get("oidc_nonce")
        extra = {} if auth_time is None else {"auth_time": auth_time}
        _mock_idp(signing_key, "sub-re", "re@schule.example", nonce, extra=extra)
        return q, client.get(f"/api/v1/auth/callback?state={state}&code=abc")

    @respx.mock
    def test_reauth_asks_max_age_zero(self, client, signing_key):
        q, _ = self._flow(client, signing_key, int(time.time()))
        assert q["max_age"] == ["0"] and q["prompt"] == ["login"]

    @respx.mock
    def test_fresh_auth_time_is_recorded(self, client, db, signing_key):
        _q, resp = self._flow(client, signing_key, int(time.time()))
        assert resp.headers["location"] == "http://frontend.example/"
        row = db.query(AuthSession).one()
        assert session_service.is_recent_login(row)

    @respx.mock
    def test_reauth_with_old_auth_time_is_rejected(self, client, db, signing_key):
        _q, resp = self._flow(client, signing_key, int(time.time()) - 3600)
        assert resp.headers["location"].endswith("/login?error=reauth_failed")
        assert db.query(AuthSession).count() == 0

    @respx.mock
    def test_reauth_without_auth_time_is_rejected(self, client, signing_key):
        _q, resp = self._flow(client, signing_key, None)
        assert resp.headers["location"].endswith("/login?error=reauth_failed")

    @respx.mock
    def test_silent_sso_login_does_not_count_as_step_up(self, client, db, signing_key):
        _q, _resp = self._flow(
            client, signing_key, int(time.time()) - 3600, reauth=False
        )
        row = db.query(AuthSession).one()
        assert not session_service.is_recent_login(row)


class TestRetention:
    @respx.mock
    def test_login_purges_expired_sessions(self, client, db, signing_key):
        user, _row = _login_as(client, db, "old@schule.example")
        _tok, expired_row = session_service.create_session(
            db, user.id, max_age=timedelta(seconds=-5)
        )
        expired_id = expired_row.id
        client.cookies.clear()
        state, nonce, _ = _start_unmocked(client)
        _mock_idp(signing_key, "sub-ret", "ret@schule.example", nonce)
        client.get(f"/api/v1/auth/callback?state={state}&code=abc")
        assert db.query(AuthSession).filter(AuthSession.id == expired_id).count() == 0


class TestHardening:
    @respx.mock
    def test_normal_login_clears_a_leftover_reauth_marker(self, client, signing_key):
        _mock_idp(signing_key, "s", "a@schule.example", "n")
        client.cookies.set("oidc_reauth", "1")
        resp = client.get("/api/v1/auth/login")
        cleared = [
            c
            for c in resp.headers.get_list("set-cookie")
            if c.startswith("oidc_reauth=")
        ]
        assert cleared and "Max-Age=0" in cleared[0]

    def test_impersonation_cookie_is_no_login_session(self, client, db):
        admin, _row = _login_as(client, db, "adm3@schule.example", is_superuser=True)
        target = User(
            email="t3@schule.example",
            zitadel_sub="t3",
            first_name="T",
            last_name="T",
            institution_id=admin.institution_id,
            status=UserStatus.ACTIVE.value,
        )
        db.add(target)
        db.commit()
        client.post(
            f"/api/admin/users/{target.id}/impersonate", json={"reason": "support"}
        )
        imp_token = client.cookies.get(session_service.IMPERSONATION_COOKIE_NAME)
        client.cookies.clear()
        # the impersonation token, smuggled in as the login cookie, is worthless
        client.cookies.set(session_service.SESSION_COOKIE_NAME, imp_token)
        assert client.get("/api/auth/me").status_code == 401

    @respx.mock
    def test_user_limit_redirects_from_callback(self, client, db, signing_key):
        inst = db.query(Institution).filter_by(slug="schule-oidc").one()
        inst.max_users = 1
        db.add(
            User(
                email="first@schule.example",
                zitadel_sub="sub-first",
                first_name="F",
                last_name="F",
                institution_id=inst.id,
                status=UserStatus.ACTIVE.value,
            )
        )
        db.commit()
        state, nonce, _ = _start_unmocked(client)
        _mock_idp(signing_key, "sub-two", "two@schule.example", nonce)
        resp = client.get(f"/api/v1/auth/callback?state={state}&code=abc")
        assert resp.headers["location"].endswith("/login?error=user_limit")

    @respx.mock
    def test_unseeded_roles_fail_the_login_without_a_half_user(
        self, client, db, signing_key
    ):
        db.query(Role).delete()
        db.commit()
        state, nonce, _ = _start_unmocked(client)
        _mock_idp(signing_key, "sub-nr", "nr@schule.example", nonce)
        resp = client.get(f"/api/v1/auth/callback?state={state}&code=abc")
        assert resp.headers["location"].endswith("/login?error=login_failed")
        assert db.query(User).filter_by(zitadel_sub="sub-nr").count() == 0

    @respx.mock
    def test_missing_email_claim_is_reported(self, client, db, signing_key):
        state, nonce, _ = _start_unmocked(client)
        _mock_idp(signing_key, "sub-ne", "x@schule.example", nonce)
        # id token without email and userinfo down
        respx.get(f"{ISSUER}/oidc/v1/userinfo").mock(return_value=httpx.Response(503))
        pem, _public = signing_key
        claims = {
            "iss": ISSUER,
            "aud": CLIENT_ID,
            "sub": "sub-ne",
            "nonce": nonce,
            "exp": int(time.time()) + 300,
            "iat": int(time.time()),
        }
        id_token = jwt.encode(claims, pem, algorithm="RS256", headers={"kid": "k1"})
        respx.post(f"{ISSUER}/oauth/v2/token").mock(
            return_value=httpx.Response(
                200, json={"id_token": id_token, "access_token": "at"}
            )
        )
        resp = client.get(f"/api/v1/auth/callback?state={state}&code=abc")
        assert resp.headers["location"].endswith("/login?error=claims_missing")

    @respx.mock
    def test_audit_entries_for_login_rejection_and_logout(
        self, client, db, signing_key
    ):
        from models.auth import AuditLog

        inst = db.query(Institution).filter_by(slug="schule-oidc").one()
        db.add(
            User(
                email="blocked@schule.example",
                zitadel_sub="sub-blocked",
                first_name="B",
                last_name="B",
                institution_id=inst.id,
                status=UserStatus.SUSPENDED.value,
            )
        )
        db.commit()
        state, nonce, _ = _start_unmocked(client)
        _mock_idp(signing_key, "sub-blocked", "blocked@schule.example", nonce)
        client.get(f"/api/v1/auth/callback?state={state}&code=abc")
        failures = db.query(AuditLog).filter(
            AuditLog.action == "login", AuditLog.status == "failure"
        )
        assert failures.count() == 1
        assert "suspended" in failures.one().error_message

        client.cookies.clear()
        state, nonce, _ = _start_unmocked(client)
        _mock_idp(signing_key, "sub-ok", "ok@schule.example", nonce)
        client.get(f"/api/v1/auth/callback?state={state}&code=abc")
        ok = db.query(AuditLog).filter(
            AuditLog.action == "login", AuditLog.status == "success"
        )
        assert ok.count() == 1
        assert "zitadel" in str(ok.one().additional_data)
        client.post("/api/v1/auth/logout")
        assert db.query(AuditLog).filter(AuditLog.action == "logout").count() == 1


class TestIdTokenValidation:
    """validate_id_token is the trust anchor of the login."""

    def _token(self, signing_key, **over):
        pem, _ = signing_key
        claims = {
            "iss": ISSUER,
            "aud": CLIENT_ID,
            "sub": "s",
            "nonce": "n",
            "exp": int(time.time()) + 300,
            "iat": int(time.time()),
        }
        claims.update(over)
        return jwt.encode(claims, pem, algorithm="RS256", headers={"kid": "k1"})

    @pytest.fixture(autouse=True)
    def _idp(self, signing_key):
        with respx.mock:
            _mock_idp(signing_key, "s", "a@b.example", "n")
            yield

    def test_valid(self, signing_key):
        assert (
            oidc_client.validate_id_token(self._token(signing_key), "n")["sub"] == "s"
        )

    @pytest.mark.parametrize(
        "over",
        [{"aud": "other"}, {"iss": "https://evil.example"}, {"exp": 1}, {"nonce": "x"}],
    )
    def test_wrong_claims_are_rejected(self, signing_key, over):
        from jose.exceptions import JWTError

        with pytest.raises(JWTError):
            oidc_client.validate_id_token(self._token(signing_key, **over), "n")

    def test_missing_nonce_argument_is_rejected(self, signing_key):
        from jose.exceptions import JWTError

        with pytest.raises(JWTError):
            oidc_client.validate_id_token(self._token(signing_key), "")

    def test_hs256_token_is_rejected(self, signing_key):
        from jose.exceptions import JWTError

        forged = jwt.encode(
            {
                "iss": ISSUER,
                "aud": CLIENT_ID,
                "sub": "s",
                "nonce": "n",
                "exp": int(time.time()) + 300,
            },
            "shared-secret",
            algorithm="HS256",
            headers={"kid": "k1"},
        )
        with pytest.raises(JWTError):
            oidc_client.validate_id_token(forged, "n")

    def test_token_signed_with_a_foreign_key_is_rejected(self, signing_key):
        from cryptography.hazmat.primitives import serialization
        from jose.exceptions import JWTError

        other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = other.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode()
        forged = jwt.encode(
            {
                "iss": ISSUER,
                "aud": CLIENT_ID,
                "sub": "s",
                "nonce": "n",
                "exp": int(time.time()) + 300,
            },
            pem,
            algorithm="RS256",
            headers={"kid": "k1"},
        )
        with pytest.raises(JWTError):
            oidc_client.validate_id_token(forged, "n")

    def test_unknown_kid_refetches_once_then_fails(self, signing_key):
        pem, _ = signing_key
        token = jwt.encode(
            {
                "iss": ISSUER,
                "aud": CLIENT_ID,
                "sub": "s",
                "nonce": "n",
                "exp": int(time.time()) + 300,
            },
            pem,
            algorithm="RS256",
            headers={"kid": "rotated"},
        )
        with pytest.raises(oidc_client.UnknownSigningKeyError):
            oidc_client.validate_id_token(token, "n")
        keys_calls = [c for c, _ in respx.calls if c.url.path.endswith("/keys")]
        assert len(keys_calls) == 2  # first fetch + exactly one refetch

    def test_key_rotation_is_picked_up(self, signing_key):
        pem, public = signing_key
        token = jwt.encode(
            {
                "iss": ISSUER,
                "aud": CLIENT_ID,
                "sub": "s",
                "nonce": "n",
                "exp": int(time.time()) + 300,
            },
            pem,
            algorithm="RS256",
            headers={"kid": "k2"},
        )
        rotated = {**public, "kid": "k2"}
        oidc_client.validate_id_token(self._token(signing_key), "n")  # cache old JWKS
        respx.get(f"{ISSUER}/oauth/v2/keys").mock(
            return_value=httpx.Response(200, json={"keys": [public, rotated]})
        )
        assert oidc_client.validate_id_token(token, "n")["sub"] == "s"


class TestUserinfoMerge:
    @pytest.fixture(autouse=True)
    def _disco(self, signing_key):
        with respx.mock:
            _mock_idp(signing_key, "s", "a@b.example", "n")
            yield

    def test_profile_claims_are_merged(self):
        respx.get(f"{ISSUER}/oidc/v1/userinfo").mock(
            return_value=httpx.Response(
                200, json={"sub": "s", "email": "x@y.example", "given_name": "Ann"}
            )
        )
        merged = oidc_client.merge_userinfo_claims({"sub": "s"}, "at")
        assert merged["email"] == "x@y.example" and merged["given_name"] == "Ann"

    def test_identity_claims_cannot_be_overwritten(self):
        respx.get(f"{ISSUER}/oidc/v1/userinfo").mock(
            return_value=httpx.Response(
                200,
                json={
                    "sub": "s",
                    "auth_time": 1,
                    "nonce": "evil",
                    "iss": "evil",
                    "exp": 1,
                },
            )
        )
        base = {"sub": "s", "auth_time": 999, "nonce": "n", "iss": ISSUER, "exp": 5}
        assert oidc_client.merge_userinfo_claims(base, "at") == base

    def test_userinfo_of_another_sub_is_ignored(self):
        respx.get(f"{ISSUER}/oidc/v1/userinfo").mock(
            return_value=httpx.Response(
                200, json={"sub": "other", "email": "evil@x.example"}
            )
        )
        assert "email" not in oidc_client.merge_userinfo_claims({"sub": "s"}, "at")

    @pytest.mark.parametrize(
        "response", [httpx.Response(503), httpx.Response(200, text="no json")]
    )
    def test_userinfo_failure_falls_back_to_id_token(self, response):
        respx.get(f"{ISSUER}/oidc/v1/userinfo").mock(return_value=response)
        assert oidc_client.merge_userinfo_claims(
            {"sub": "s", "email": "a@b.c"}, "at"
        ) == {
            "sub": "s",
            "email": "a@b.c",
        }

    def test_without_access_token_nothing_is_fetched(self):
        assert oidc_client.merge_userinfo_claims({"sub": "s"}, None) == {"sub": "s"}


class TestTestLoginEndpoint:
    """The route is created at import; reload the module under the flag."""

    @pytest.fixture
    def flagged_client(self, db, monkeypatch):
        import importlib

        from fastapi import FastAPI

        from api import auth_oidc

        monkeypatch.setenv("E2E_TEST_LOGIN", "true")
        monkeypatch.setenv("ENVIRONMENT", "e2e")
        module = importlib.reload(auth_oidc)
        mini = FastAPI()
        mini.include_router(module.router)
        mini.dependency_overrides[get_db] = lambda: db
        yield TestClient(mini)
        monkeypatch.delenv("E2E_TEST_LOGIN")
        importlib.reload(auth_oidc)

    def test_logs_in_an_active_user(self, flagged_client, db):
        user, _row = _login_as(flagged_client, db, "e2e@schule.example")
        flagged_client.cookies.clear()
        resp = flagged_client.post(
            "/api/v1/auth/test-login", json={"email": "E2E@schule.example"}
        )
        assert resp.status_code == 204
        cookie = resp.headers["set-cookie"]
        assert "session_id=" in cookie and "HttpOnly" in cookie
        newest = db.query(AuthSession).order_by(AuthSession.id.desc()).first()
        assert newest.user_id == user.id and newest.authenticated_at is not None

    @pytest.mark.parametrize("status", ["suspended", "pending"])
    def test_refuses_non_active_users(self, flagged_client, db, status):
        _login_as(flagged_client, db, "blocked@schule.example", status=status)
        flagged_client.cookies.clear()
        resp = flagged_client.post(
            "/api/v1/auth/test-login", json={"email": "blocked@schule.example"}
        )
        assert resp.status_code == 404

    def test_unknown_email_is_404(self, flagged_client):
        assert (
            flagged_client.post(
                "/api/v1/auth/test-login", json={"email": "nobody@schule.example"}
            ).status_code
            == 404
        )

    @pytest.mark.parametrize("env", ["production", "prod", "staging", "Production"])
    def test_import_refuses_to_start_outside_dev(self, monkeypatch, env):
        import importlib

        from api import auth_oidc

        monkeypatch.setenv("E2E_TEST_LOGIN", "1")
        monkeypatch.setenv("ENVIRONMENT", env)
        with pytest.raises(RuntimeError, match="E2E_TEST_LOGIN"):
            importlib.reload(auth_oidc)
        monkeypatch.delenv("E2E_TEST_LOGIN")
        importlib.reload(auth_oidc)


def test_callback_path_matches_the_zitadel_client_contract():
    """tessera registers ``https://examcraft.ch/api/v1/auth/callback`` as the
    redirect URI of examcraft-web (examcraft_web_redirect_uris); the route must
    live exactly there or Zitadel rejects every login."""
    from api import auth_oidc

    paths = {route.path for route in auth_oidc.router.routes}
    assert "/api/v1/auth/callback" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/logout" in paths


class TestNoFrontendUrlInProduction:
    """A redirect helper that raises would turn every error path into a 500."""

    @pytest.fixture(autouse=True)
    def _prod_without_frontend_url(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("FRONTEND_URL", raising=False)

    def test_frontend_base_url_default_only_in_dev(self, monkeypatch):
        with pytest.raises(oidc_client.OidcNotConfiguredError):
            oidc_client.frontend_base_url()
        monkeypatch.setenv("ENVIRONMENT", "development")
        assert oidc_client.frontend_base_url() == "http://localhost:3000"

    def test_error_redirect_falls_back_to_a_relative_url(self, client):
        resp = client.get("/api/v1/auth/callback?state=x&code=abc")
        assert resp.status_code == 307
        assert resp.headers["location"] == "/login?error=login_expired"

    @respx.mock
    def test_successful_login_still_sets_the_session_cookie(
        self, client, db, signing_key
    ):
        client.base_url = "https://testserver"  # Secure cookies need https
        state, nonce, _ = _start_unmocked(client)
        _mock_idp(signing_key, "sub-nf", "nf@schule.example", nonce)
        resp = client.get(f"/api/v1/auth/callback?state={state}&code=abc")
        assert resp.status_code == 307 and resp.headers["location"] == "/"
        assert any(
            c.startswith("session_id=") for c in resp.headers.get_list("set-cookie")
        )
        assert db.query(AuthSession).count() == 1


class TestSecureCookies:
    @respx.mock
    def test_session_cookie_is_secure_in_production(
        self, client, db, signing_key, monkeypatch
    ):
        monkeypatch.setenv("ENVIRONMENT", "production")
        client.base_url = "https://testserver"  # Secure cookies need https
        state, nonce, _ = _start_unmocked(client)
        _mock_idp(signing_key, "sub-sec", "sec@schule.example", nonce)
        resp = client.get(f"/api/v1/auth/callback?state={state}&code=abc")
        session_cookie = next(
            c
            for c in resp.headers.get_list("set-cookie")
            if c.startswith("session_id=")
        )
        assert "Secure" in session_cookie and "HttpOnly" in session_cookie

    @respx.mock
    def test_flow_cookies_are_deleted_after_the_callback(self, client, db, signing_key):
        state, nonce, _ = _start_unmocked(client)
        _mock_idp(signing_key, "sub-fc", "fc@schule.example", nonce)
        resp = client.get(f"/api/v1/auth/callback?state={state}&code=abc")
        deleted = {
            c.split("=")[0]
            for c in resp.headers.get_list("set-cookie")
            if "Max-Age=0" in c
        }
        assert {"oidc_state", "oidc_verifier", "oidc_nonce", "oidc_reauth"} <= deleted
        # replaying the callback with the (now cleared) cookie jar is expired
        replay = client.get(f"/api/v1/auth/callback?state={state}&code=abc")
        assert replay.headers["location"].endswith("/login?error=login_expired")


class TestLogoutIsBestEffort:
    def test_failing_impersonation_end_still_removes_session_and_cookies(
        self, client, db, monkeypatch
    ):
        from services.auth_service import AuthService

        _login_as(client, db, "bye@schule.example")

        def boom(*args, **kwargs):
            raise RuntimeError("db hiccup")

        monkeypatch.setattr(AuthService, "end_own_impersonation_session", boom)
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 204
        assert db.query(AuthSession).count() == 0
        deleted = {
            c.split("=")[0]
            for c in resp.headers.get_list("set-cookie")
            if "Max-Age=0" in c
        }
        assert {"session_id", "impersonation_id"} <= deleted

    def test_unknown_token_still_clears_the_cookies(self, client):
        client.cookies.set("session_id", "unknown")
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 204
        assert any(
            "session_id=" in c and "Max-Age=0" in c
            for c in resp.headers.get_list("set-cookie")
        )
