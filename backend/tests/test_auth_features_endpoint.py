"""TF-1055: ``GET /api/auth/features`` ships the evaluation tier limits.

The frontend disables tier-gated evaluation actions up front from
``evaluation_limits``; the expected values are taken from
``auswertung_quotas.get_limits`` rather than hard-coded, so a change to
``_TIER_LIMITS`` cannot leave the response and this test silently diverging.

No database needed: the user and institution are transient model objects and
both dependencies are overridden (``conftest.py`` resets the overrides).

One client for the whole module: every lifespan start re-registers the
routers, and FastAPI nests the lifespans on each ``include_router``, so a
``with TestClient(app)`` per request pushed later tests over the recursion
limit (``test_task_result.py`` in the full run).
"""

import dataclasses

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

import api.auth as auth_module
from config.features import TIER_QUOTAS, SubscriptionTier
from database import get_db
from main import app
from models.auth import Institution, User
from services.auswertung_quotas import (
    UnknownTierError,
    get_limits,
    get_limits_for_user,
)
from utils.auth_utils import get_current_active_user


def _expected_limits(tier: str) -> dict:
    limits = dataclasses.asdict(get_limits(tier))
    limits["drivers"] = list(limits["drivers"])
    return limits


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def get_features(client):
    def _get(user: User):
        app.dependency_overrides[get_current_active_user] = lambda: user
        app.dependency_overrides[get_db] = lambda: None
        return client.get("/api/auth/features")

    return _get


def _user_with_tier(tier: str) -> User:
    institution = Institution(
        id=1055,
        name="TF-1055",
        slug="tf-1055",
        subscription_tier=tier,
        max_users=7,
        max_documents=11,
        max_questions_per_month=13,
    )
    return User(id=1055, email="tf1055@example.org", institution=institution)


@pytest.mark.parametrize("tier", [t.value for t in SubscriptionTier])
def test_evaluation_limits_match_get_limits_for_every_tier(tier, get_features):
    response = get_features(_user_with_tier(tier))

    assert response.status_code == 200
    body = response.json()
    assert body["subscription_tier"] == tier
    assert body["evaluation_limits"] == _expected_limits(tier)
    # The institution's own quota columns still win over the tier defaults.
    assert body["quotas"] == {
        "max_documents": 11,
        "max_questions_per_month": 13,
        "max_users": 7,
    }


def test_tiers_differ_in_the_gated_flags(get_features):
    """Guards the parametrised test above against a vacuous pass: if every
    tier had the same limits, a response ignoring the tier would match too."""
    responses = {
        t.value: get_features(_user_with_tier(t.value)).json()["evaluation_limits"]
        for t in SubscriptionTier
    }
    assert responses["free"] != responses["enterprise"]
    assert not responses["starter"]["review_bulk"]
    assert responses["professional"]["review_bulk"]
    assert not responses["professional"]["custom_grading_schemes"]


def test_user_without_institution_gets_free_and_200(get_features):
    user = User(id=1056, email="no-inst@example.org", institution=None)

    response = get_features(user)

    assert response.status_code == 200
    body = response.json()
    assert body["subscription_tier"] == "free"
    assert body["evaluation_limits"] == _expected_limits("free")
    free_quotas = TIER_QUOTAS[SubscriptionTier.FREE]
    assert body["quotas"] == {
        key: free_quotas[key]
        for key in ("max_documents", "max_questions_per_month", "max_users")
    }


def test_unknown_tier_falls_back_to_free_outside_production(monkeypatch, get_features):
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    response = get_features(_user_with_tier("platinum"))

    assert response.status_code == 200
    body = response.json()
    assert body["subscription_tier"] == "free"
    assert body["evaluation_limits"] == _expected_limits("free")


def test_unknown_tier_in_production_falls_back_to_free_and_logs_error(
    monkeypatch, get_features
):
    # Read-only endpoint: a misconfigured row must not 500 every feature gate.
    monkeypatch.setenv("ENVIRONMENT", "production")
    logger_mock = Mock()
    monkeypatch.setattr(auth_module, "logger", logger_mock)

    response = get_features(_user_with_tier("platinum"))

    assert response.status_code == 200
    body = response.json()
    assert body["subscription_tier"] == "free"
    assert body["evaluation_limits"] == _expected_limits("free")
    logger_mock.error.assert_called_once()


def test_unknown_tier_in_production_still_blocks_quota_gates(monkeypatch):
    # Write-path gates stay strict: a misconfigured tier must not pass.
    monkeypatch.setenv("ENVIRONMENT", "production")

    with pytest.raises(UnknownTierError):
        get_limits_for_user(_user_with_tier("platinum"))
