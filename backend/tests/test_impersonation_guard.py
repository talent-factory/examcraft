"""Tests for the block_during_impersonation dependency (TF-741).

Direct unit test of the guard function itself, independent of any one
protected endpoint (those get end-to-end coverage in
tests/test_impersonation_api.py once wired up).
"""

import pytest
from fastapi import HTTPException

from models.auth import Institution, User, UserStatus
from utils.auth_utils import block_during_impersonation
from utils.impersonation_context import (
    ImpersonationContext,
    set_impersonation_context,
)


@pytest.fixture(autouse=True)
def _reset_impersonation_context():
    set_impersonation_context(None)
    yield
    set_impersonation_context(None)


def _make_user(db):
    inst = Institution(
        name="Guard-Test",
        slug="impersonation-guard-test",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.flush()
    user = User(
        email="guarded@impersonation-guard-test.ch",
        password_hash="dummy",
        first_name="Test",
        last_name="User",
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
    )
    db.add(user)
    db.commit()
    return user


def test_allows_request_when_not_impersonating(test_db):
    user = _make_user(test_db)
    # Should not raise.
    block_during_impersonation(request=None, current_user=user)


def test_blocks_request_when_impersonating(test_db):
    user = _make_user(test_db)
    set_impersonation_context(
        ImpersonationContext(
            impersonator_id=1, impersonation_session_id=2, token_jti="jti"
        )
    )

    with pytest.raises(HTTPException) as exc_info:
        block_during_impersonation(request=None, current_user=user)

    assert exc_info.value.status_code == 403
