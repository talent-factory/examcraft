"""Tests for get_current_user's impersonation-claim handling (TF-741).

Two behavior changes over the normal auth path:
1. When the token carries impersonator_id/impersonation_session_id
   claims, get_current_user populates the request-scoped
   ImpersonationContext (utils/impersonation_context.py).
2. The target user's account-status check (normally 403 on anything
   but ACTIVE) is skipped for impersonation tokens — the support
   use case explicitly requires being able to act as a suspended/
   inactive/pending user, not just start the session against one.
"""

import pytest
from fastapi import HTTPException

from models.auth import ImpersonationSession, Institution, User, UserStatus
from services import session_service
from services.auth_service import AuthService
from utils.auth_utils import get_current_user
from utils.impersonation_context import (
    get_impersonation_context,
    set_impersonation_context,
)


@pytest.fixture(autouse=True)
def _reset_impersonation_context():
    set_impersonation_context(None)
    yield
    set_impersonation_context(None)


def _make_institution(db, slug="get-current-user-impersonation"):
    inst = Institution(
        name=f"Inst-{slug}",
        slug=slug,
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.flush()
    return inst


def _make_user(db, inst, email, status=UserStatus.ACTIVE.value):
    user = User(
        email=email,
        password_hash="dummy",
        # the impersonating admin must still hold users:impersonate
        is_superuser=email.startswith("admin"),
        first_name="Test",
        last_name="User",
        institution_id=inst.id,
        status=status,
    )
    db.add(user)
    db.flush()
    return user


def _login(db, user) -> str:
    token, _row = session_service.create_session(db, user.id)
    return token


def _impersonation_session_id(db, admin, target) -> int:
    """A real ImpersonationSession row (auth_sessions has an FK to it)."""
    row = ImpersonationSession(
        admin_user_id=admin.id, target_user_id=target.id, reason="test"
    )
    db.add(row)
    db.commit()
    return row.id


async def _current(db, session_token, impersonation_token=None):
    return await get_current_user(
        request=None,
        session_token=session_token,
        impersonation_token=impersonation_token,
        db=db,
    )


@pytest.mark.asyncio
async def test_normal_token_leaves_impersonation_context_unset(test_db):
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst, "normal@get-current-user-impersonation.ch")
    test_db.commit()
    token = _login(test_db, user)

    result = await _current(test_db, token)

    assert result.id == user.id
    assert get_impersonation_context() is None


@pytest.mark.asyncio
async def test_impersonation_token_sets_impersonation_context(test_db):
    inst = _make_institution(test_db)
    admin = _make_user(test_db, inst, "admin@get-current-user-impersonation.ch")
    target = _make_user(test_db, inst, "target@get-current-user-impersonation.ch")
    test_db.commit()

    admin_token = _login(test_db, admin)
    imp_id = _impersonation_session_id(test_db, admin, target)
    imp_token, _row = AuthService.create_impersonation_session(
        target, test_db, impersonator_id=admin.id, impersonation_session_id=imp_id
    )

    result = await _current(test_db, admin_token, imp_token)

    assert result.id == target.id
    ctx = get_impersonation_context()
    assert ctx is not None
    assert ctx.impersonator_id == admin.id
    assert ctx.impersonation_session_id == imp_id


@pytest.mark.asyncio
async def test_impersonation_token_bypasses_target_status_check(test_db):
    """The support use case requires acting as a suspended user for the
    lifetime of the session, not just starting it."""
    inst = _make_institution(test_db)
    admin = _make_user(test_db, inst, "admin2@get-current-user-impersonation.ch")
    target = _make_user(
        test_db,
        inst,
        "suspended@get-current-user-impersonation.ch",
        status=UserStatus.SUSPENDED.value,
    )
    test_db.commit()

    admin_token = _login(test_db, admin)
    imp_id = _impersonation_session_id(test_db, admin, target)
    imp_token, _row = AuthService.create_impersonation_session(
        target, test_db, impersonator_id=admin.id, impersonation_session_id=imp_id
    )

    result = await _current(test_db, admin_token, imp_token)

    assert result.id == target.id


@pytest.mark.asyncio
async def test_normal_token_for_suspended_user_still_rejected(test_db):
    """Regression: the bypass must be scoped to impersonation tokens only."""
    inst = _make_institution(test_db)
    user = _make_user(
        test_db,
        inst,
        "suspended-normal@get-current-user-impersonation.ch",
        status=UserStatus.SUSPENDED.value,
    )
    test_db.commit()
    token = _login(test_db, user)

    with pytest.raises(HTTPException) as exc_info:
        await _current(test_db, token)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_ended_impersonation_session_falls_back_to_admin(test_db):
    inst = _make_institution(test_db)
    admin = _make_user(test_db, inst, "admin3@get-current-user-impersonation.ch")
    target = _make_user(test_db, inst, "target3@get-current-user-impersonation.ch")
    test_db.commit()

    admin_token = _login(test_db, admin)
    imp_id = _impersonation_session_id(test_db, admin, target)
    imp_token, _row = AuthService.create_impersonation_session(
        target, test_db, impersonator_id=admin.id, impersonation_session_id=imp_id
    )
    session_service.delete_impersonation_sessions(test_db, imp_id)
    test_db.commit()

    result = await _current(test_db, admin_token, imp_token)

    assert result.id == admin.id
    assert get_impersonation_context() is None


@pytest.mark.asyncio
async def test_impersonation_cookie_without_login_session_rejected(test_db):
    inst = _make_institution(test_db)
    admin = _make_user(test_db, inst, "admin4@get-current-user-impersonation.ch")
    target = _make_user(test_db, inst, "target4@get-current-user-impersonation.ch")
    test_db.commit()

    imp_id = _impersonation_session_id(test_db, admin, target)
    imp_token, _row = AuthService.create_impersonation_session(
        target, test_db, impersonator_id=admin.id, impersonation_session_id=imp_id
    )

    with pytest.raises(HTTPException) as exc_info:
        await _current(test_db, None, imp_token)

    assert exc_info.value.status_code == 401
