"""API tests for /api/v1/admin/moodle-connections/* (TF-336 Subarea C).

Covers CRUD, Token-Verschlüsselung, Test-Endpoint-Mocking, multi-tenancy.
"""

from __future__ import annotations

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import get_db
from main import app
from models.auth import Institution, User, UserStatus
from models.submission import MoodleConnection
from utils.auth_utils import get_current_user, get_current_active_user
from utils.secret_encryption import decrypt_secret, reset_cache_for_tests


@pytest.fixture(autouse=True)
def _crypto_env(monkeypatch):
    monkeypatch.delenv("MOODLE_TOKEN_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("SECRET_KEY", "dev-secret-key-for-tests")
    reset_cache_for_tests()
    yield
    reset_cache_for_tests()


def _make_institution(db: Session, slug: str) -> Institution:
    inst = Institution(
        name=f"Inst-{slug}",
        slug=slug,
        subscription_tier="enterprise",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.flush()
    return inst


def _make_user(db: Session, institution_id: int) -> User:
    user = User(
        email=f"admin-{institution_id}@test.ch",
        first_name="Admin",
        last_name="X",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
        is_superuser=True,
    )
    db.add(user)
    db.flush()
    return user


def _client(test_db: Session, user: User) -> TestClient:
    import api.moodle_connections as module

    if module.router not in app.router.routes:
        app.include_router(module.router)

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def test_create_persists_encrypted_token(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="tf336-mc-create")
    user = _make_user(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    resp = client.post(
        "/api/v1/admin/moodle-connections",
        json={
            "base_url": "https://moodle.example.org/",
            "token": "supersecretmoodletoken1234",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["base_url"] == "https://moodle.example.org"
    # Token wird maskiert ausgespielt.
    assert body["token_masked"].startswith("****")
    assert body["token_masked"].endswith("1234")

    row = (
        test_db.query(MoodleConnection)
        .filter(MoodleConnection.institution_id == inst.id)
        .one()
    )
    # In der DB ist der Token verschlüsselt — Rohwert ist nicht enthalten.
    assert "supersecretmoodletoken1234" not in row.token_encrypted
    assert decrypt_secret(row.token_encrypted) == "supersecretmoodletoken1234"


def test_create_rejects_duplicate_for_institution(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="tf336-mc-dup")
    user = _make_user(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    body = {
        "base_url": "https://moodle.example.org",
        "token": "supersecrettokenA1234",
    }
    first = client.post("/api/v1/admin/moodle-connections", json=body)
    assert first.status_code == 201
    dup = client.post("/api/v1/admin/moodle-connections", json=body)
    assert dup.status_code == 409


def test_update_changes_token_in_place(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="tf336-mc-update")
    user = _make_user(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    created = client.post(
        "/api/v1/admin/moodle-connections",
        json={
            "base_url": "https://moodle.example.org",
            "token": "originaltokenXYZA",
        },
    )
    cid = created.json()["id"]

    resp = client.patch(
        f"/api/v1/admin/moodle-connections/{cid}",
        json={"token": "rotatedtokenABCDE"},
    )
    assert resp.status_code == 200
    assert resp.json()["token_masked"].endswith("BCDE")

    row = test_db.query(MoodleConnection).filter(MoodleConnection.id == cid).one()
    assert decrypt_secret(row.token_encrypted) == "rotatedtokenABCDE"


def test_delete_removes_connection(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="tf336-mc-delete")
    user = _make_user(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    created = client.post(
        "/api/v1/admin/moodle-connections",
        json={"base_url": "https://moodle.example.org", "token": "tokABCDEFGH"},
    )
    cid = created.json()["id"]

    resp = client.delete(f"/api/v1/admin/moodle-connections/{cid}")
    assert resp.status_code == 204
    assert (
        test_db.query(MoodleConnection).filter(MoodleConnection.id == cid).one_or_none()
        is None
    )


def test_get_returns_404_for_other_institution(test_db: Session) -> None:
    inst_a = _make_institution(test_db, slug="tf336-mc-a")
    inst_b = _make_institution(test_db, slug="tf336-mc-b")
    user_b = _make_user(test_db, inst_b.id)
    foreign = MoodleConnection(
        institution_id=inst_a.id,
        base_url="https://other.moodle.example",
        token_encrypted="dummy",
    )
    test_db.add(foreign)
    test_db.commit()

    client = _client(test_db, user_b)
    resp = client.get(f"/api/v1/admin/moodle-connections/{foreign.id}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Verbindungstest
# ---------------------------------------------------------------------------


def test_test_endpoint_success(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="tf336-mc-test-ok")
    user = _make_user(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    created = client.post(
        "/api/v1/admin/moodle-connections",
        json={"base_url": "https://moodle.example.org", "token": "validtokenOK1"},
    )
    cid = created.json()["id"]

    with respx.mock(assert_all_called=True) as mock:
        mock.post("https://moodle.example.org/webservice/rest/server.php").mock(
            return_value=httpx.Response(
                200,
                json={
                    "sitename": "Test Moodle",
                    "siteurl": "https://moodle.example.org",
                    "fullname": "API User",
                },
            )
        )
        resp = client.post(f"/api/v1/admin/moodle-connections/{cid}/test")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["site_name"] == "Test Moodle"


def test_test_endpoint_invalid_token(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="tf336-mc-test-bad")
    user = _make_user(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    created = client.post(
        "/api/v1/admin/moodle-connections",
        json={"base_url": "https://moodle.example.org", "token": "notarealtoken1"},
    )
    cid = created.json()["id"]

    with respx.mock(assert_all_called=True) as mock:
        mock.post("https://moodle.example.org/webservice/rest/server.php").mock(
            return_value=httpx.Response(
                200,
                json={
                    "exception": "moodle_exception",
                    "errorcode": "invalidtoken",
                    "message": "Invalid token",
                },
            )
        )
        resp = client.post(f"/api/v1/admin/moodle-connections/{cid}/test")

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert "Invalid token" in (body["error"] or "")


def test_test_endpoint_network_error(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="tf336-mc-test-net")
    user = _make_user(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    created = client.post(
        "/api/v1/admin/moodle-connections",
        json={"base_url": "https://offline.example.org", "token": "tokenOFFLINE1"},
    )
    cid = created.json()["id"]

    with respx.mock() as mock:
        mock.post("https://offline.example.org/webservice/rest/server.php").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        resp = client.post(f"/api/v1/admin/moodle-connections/{cid}/test")
    assert resp.status_code == 200
    assert resp.json()["ok"] is False
