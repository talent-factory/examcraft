"""WebSocket authentication against real sessions (EXAMCRAFT-125).

``test_websocket.py`` mocks ``session_service``; these tests use real
``AuthSession`` rows, so a renamed cookie or a swapped argument breaks them.
"""

import asyncio
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from api.v1 import websocket as ws
from models.auth import ImpersonationSession, Institution, User, UserStatus
from services import session_service


class _KeepOpen:
    """Hands the test session to the code under test; ``close`` must not end it."""

    def __init__(self, db):
        self._db = db

    def __getattr__(self, name):
        return getattr(self._db, name)

    def close(self):
        pass


@pytest.fixture
def world(test_db):
    inst = Institution(
        name="WS Schule",
        slug="ws-schule",
        subscription_tier="professional",
        max_users=10,
        max_documents=10,
        max_questions_per_month=10,
    )
    test_db.add(inst)
    test_db.flush()

    def make(email, status=UserStatus.ACTIVE.value, superuser=False):
        user = User(
            email=email,
            zitadel_sub=f"ws-{email}",
            first_name="W",
            last_name="S",
            institution_id=inst.id,
            status=status,
            is_superuser=superuser,
        )
        test_db.add(user)
        test_db.flush()
        return user

    return SimpleNamespace(db=test_db, make=make)


def _authenticate(db, cookies, origin=None):
    headers = {"origin": origin} if origin else {}
    fake = SimpleNamespace(cookies=cookies, headers=headers, close=AsyncMock())
    with patch.object(ws, "SessionLocal", lambda: _KeepOpen(db)):
        user = asyncio.run(ws._authenticate_websocket(fake))
    return user, fake


def test_active_user_is_accepted(world):
    user = world.make("a@ws.example")
    token, _ = session_service.create_session(world.db, user.id)
    result, fake = _authenticate(world.db, {"session_id": token})
    assert result.id == user.id
    fake.close.assert_not_called()


@pytest.mark.parametrize("status", ["suspended", "inactive", "pending"])
def test_non_active_user_is_closed(world, status):
    user = world.make("b@ws.example", status=status)
    token, _ = session_service.create_session(world.db, user.id)
    result, fake = _authenticate(world.db, {"session_id": token})
    assert result is None
    fake.close.assert_awaited_once_with(code=1008)


def test_expired_session_is_closed(world):
    user = world.make("c@ws.example")
    token, _ = session_service.create_session(
        world.db, user.id, max_age=timedelta(seconds=-1)
    )
    result, fake = _authenticate(world.db, {"session_id": token})
    assert result is None
    fake.close.assert_awaited_once_with(code=1008)


def test_no_cookie_is_closed(world):
    result, fake = _authenticate(world.db, {})
    assert result is None
    fake.close.assert_awaited_once_with(code=1008)


def _impersonation(world, target_status):
    admin = world.make("admin@ws.example", superuser=True)
    target = world.make("target@ws.example", status=target_status)
    imp = ImpersonationSession(
        admin_user_id=admin.id, target_user_id=target.id, reason="support"
    )
    world.db.add(imp)
    world.db.flush()
    admin_tok, _ = session_service.create_session(world.db, admin.id)
    imp_tok, _ = session_service.create_session(
        world.db,
        target.id,
        max_age=session_service.IMPERSONATION_SESSION_MAX_AGE,
        impersonator_id=admin.id,
        impersonation_session_id=imp.id,
    )
    return admin, target, admin_tok, imp_tok


def test_impersonation_acts_as_the_target_even_if_not_active(world):
    _admin, target, admin_tok, imp_tok = _impersonation(world, "suspended")
    result, _fake = _authenticate(
        world.db, {"session_id": admin_tok, "impersonation_id": imp_tok}
    )
    assert result.id == target.id


def test_impersonation_cookie_alone_is_closed(world):
    _admin, _target, _admin_tok, imp_tok = _impersonation(world, "active")
    result, fake = _authenticate(world.db, {"impersonation_id": imp_tok})
    assert result is None
    fake.close.assert_awaited_once_with(code=1008)


def test_impersonation_token_as_login_cookie_is_closed(world):
    _admin, _target, _admin_tok, imp_tok = _impersonation(world, "active")
    result, _fake = _authenticate(world.db, {"session_id": imp_tok})
    assert result is None


def test_foreign_origin_is_closed_before_the_session_is_read(world):
    user = world.make("d@ws.example")
    token, _ = session_service.create_session(world.db, user.id)
    result, fake = _authenticate(
        world.db, {"session_id": token}, origin="https://evil.example"
    )
    assert result is None
    fake.close.assert_awaited_once_with(code=1008)
