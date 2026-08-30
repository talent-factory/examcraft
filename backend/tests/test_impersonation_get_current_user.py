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
from fastapi.security import HTTPAuthorizationCredentials

from models.auth import Institution, User, UserStatus
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
        first_name="Test",
        last_name="User",
        institution_id=inst.id,
        status=status,
    )
    db.add(user)
    db.flush()
    return user


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


@pytest.mark.asyncio
async def test_normal_token_leaves_impersonation_context_unset(test_db):
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst, "normal@get-current-user-impersonation.ch")
    test_db.commit()
    tokens = AuthService.create_tokens_for_user(user, test_db)

    result = await get_current_user(_bearer(tokens["access_token"]), test_db)

    assert result.id == user.id
    assert get_impersonation_context() is None


@pytest.mark.asyncio
async def test_impersonation_token_sets_impersonation_context(test_db):
    inst = _make_institution(test_db)
    admin = _make_user(test_db, inst, "admin@get-current-user-impersonation.ch")
    target = _make_user(test_db, inst, "target@get-current-user-impersonation.ch")
    test_db.commit()

    tokens = AuthService.create_impersonation_token(
        target, test_db, impersonator_id=admin.id, impersonation_session_id=7
    )

    result = await get_current_user(_bearer(tokens["access_token"]), test_db)

    assert result.id == target.id
    ctx = get_impersonation_context()
    assert ctx is not None
    assert ctx.impersonator_id == admin.id
    assert ctx.impersonation_session_id == 7


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

    tokens = AuthService.create_impersonation_token(
        target, test_db, impersonator_id=admin.id, impersonation_session_id=8
    )

    result = await get_current_user(_bearer(tokens["access_token"]), test_db)

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
    tokens = AuthService.create_tokens_for_user(user, test_db)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(_bearer(tokens["access_token"]), test_db)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_revoked_impersonation_token_still_rejected(test_db):
    inst = _make_institution(test_db)
    admin = _make_user(test_db, inst, "admin3@get-current-user-impersonation.ch")
    target = _make_user(test_db, inst, "target3@get-current-user-impersonation.ch")
    test_db.commit()

    tokens = AuthService.create_impersonation_token(
        target, test_db, impersonator_id=admin.id, impersonation_session_id=9
    )
    access_payload = AuthService.decode_token(tokens["access_token"])
    AuthService.revoke_token(access_payload["jti"], test_db)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(_bearer(tokens["access_token"]), test_db)

    assert exc_info.value.status_code == 401
