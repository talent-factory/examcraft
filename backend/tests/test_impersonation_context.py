"""Tests for the request-scoped impersonation ContextVar (TF-741).

This is the foundation for the audit follow-up ticket mentioned in TF-741:
``get_current_user`` sets this per-request value from JWT impersonation
claims; downstream code (account-security guard, later TF-742 audit
wiring) reads it without needing the claims threaded through every
function signature.
"""

import pytest

from utils.impersonation_context import (
    ImpersonationContext,
    get_impersonation_context,
    set_impersonation_context,
)


@pytest.fixture(autouse=True)
def _reset_impersonation_context():
    """ContextVars are not test-isolated by pytest itself (no fresh
    contextvars.Context per test function) — reset explicitly around
    every test in this file so ordering never matters.
    """
    set_impersonation_context(None)
    yield
    set_impersonation_context(None)


def test_get_impersonation_context_defaults_to_none():
    assert get_impersonation_context() is None


def test_set_and_get_impersonation_context_roundtrip():
    ctx = ImpersonationContext(
        impersonator_id=1, impersonation_session_id=2, token_jti="abc"
    )
    set_impersonation_context(ctx)
    assert get_impersonation_context() == ctx


def test_set_none_clears_context():
    set_impersonation_context(
        ImpersonationContext(
            impersonator_id=1, impersonation_session_id=2, token_jti="x"
        )
    )
    set_impersonation_context(None)
    assert get_impersonation_context() is None
