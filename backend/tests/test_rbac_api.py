"""
Integration Tests for RBAC API Endpoints
Tests for /api/v1/rbac/* endpoints
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from database import get_db
from models.rbac import (
    Feature,
    RBACRole,
    RoleFeature,
    SubscriptionTier,
    TierQuota,
    TierFeature,
)
from models.auth import User, Role, Institution, UserStatus
from services.auth_service import AuthService


@pytest.fixture(scope="function")
def rbac_api_db(test_db):
    """Setup RBAC test data for API tests"""
    # Create institution
    institution = Institution(
        name="Test University",
        slug="test-university",
        domain="test.edu",
        subscription_tier="free",
        max_users=10,
        max_documents=100,
        max_questions_per_month=500,
    )
    test_db.add(institution)
    test_db.flush()

    # Create features
    features = [
        Feature(
            id="feat_api_test_1",
            name="api_test_feature_1",
            display_name="API Test Feature 1",
            description="Test feature 1",
            category="generation",
            is_active=True,
        ),
        Feature(
            id="feat_api_test_2",
            name="api_test_feature_2",
            display_name="API Test Feature 2",
            description="Test feature 2",
            category="management",
            is_active=True,
        ),
    ]
    for feature in features:
        test_db.add(feature)

    # Create RBAC role
    rbac_role = RBACRole(
        id="role_api_test",
        name="api_test_role",
        display_name="API Test Role",
        description="Test role",
        is_system_role=False,
        is_active=True,
    )
    test_db.add(rbac_role)
    test_db.flush()

    # Assign feature to role
    test_db.add(RoleFeature(role_id="role_api_test", feature_id="feat_api_test_1"))

    # Create subscription tier
    tier = SubscriptionTier(
        id="tier_api_test",
        name="api_test_tier",
        display_name="API Test Tier",
        description="Test tier",
        price_monthly=0.0,
        price_yearly=0.0,
        is_active=True,
        sort_order=1,
    )
    test_db.add(tier)
    test_db.flush()

    # Create tier quota
    quota = TierQuota(
        tier_id="tier_api_test", resource_type="documents", quota_limit=10
    )
    test_db.add(quota)

    # Assign feature to tier
    test_db.add(TierFeature(tier_id="tier_api_test", feature_id="feat_api_test_1"))

    # Get or create old-style role for user
    old_role = test_db.query(Role).filter(Role.name == "api_test_user").first()
    if not old_role:
        old_role = Role(
            name="api_test_user",
            display_name="API Test User",
            description="Test user role",
            permissions=["view"],
            is_system_role=False,
        )
        test_db.add(old_role)
        test_db.flush()

    # Create test user
    user = User(
        email="apitest@test.com",
        password_hash=AuthService.get_password_hash("testpassword123"),
        first_name="API",
        last_name="Test",
        institution_id=institution.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    test_db.add(user)
    test_db.flush()
    user.roles.append(old_role)

    test_db.commit()
    yield test_db


@pytest.fixture(scope="function")
def api_client(rbac_api_db):
    """Create test client with database override"""

    def override_get_db():
        try:
            yield rbac_api_db
        finally:
            pass

    # main.py registers routers inside the FastAPI lifespan, which a plain
    # TestClient(app) (no `with`) never triggers — include them explicitly
    # so this file passes when run standalone, not just as a lucky
    # beneficiary of another test file's side effect on the shared `app`.
    from api import auth
    from api.v1 import rbac as rbac_api

    # Idempotent: avoid appending duplicate routes on every call.
    if not any(getattr(r, "path", None) == "/api/auth/login" for r in app.routes):
        app.include_router(auth.router)
    if not any(
        getattr(r, "path", None) == "/api/v1/rbac/tiers/current" for r in app.routes
    ):
        app.include_router(rbac_api.router)
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def get_auth_token(client, email: str = "apitest@test.com"):
    """Helper to get auth token"""
    response = client.post(
        "/api/auth/login", json={"email": email, "password": "testpassword123"}
    )
    return response.json()["access_token"]


# ============================================
# FEATURE ENDPOINTS
# ============================================


def test_list_features(api_client):
    """Test GET /api/v1/rbac/features"""
    token = get_auth_token(api_client)

    response = api_client.get(
        "/api/v1/rbac/features", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    features = response.json()
    assert len(features) >= 2
    assert any(f["name"] == "api_test_feature_1" for f in features)


def test_list_features_by_category(api_client):
    """Test GET /api/v1/rbac/features?category=generation"""
    token = get_auth_token(api_client)

    response = api_client.get(
        "/api/v1/rbac/features?category=generation",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    features = response.json()
    assert all(f["category"] == "generation" for f in features)


def test_get_feature_by_id(api_client):
    """Test GET /api/v1/rbac/features/{feature_id}"""
    token = get_auth_token(api_client)

    response = api_client.get(
        "/api/v1/rbac/features/feat_api_test_1",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    feature = response.json()
    assert feature["id"] == "feat_api_test_1"
    assert feature["name"] == "api_test_feature_1"


# ============================================
# ROLE ENDPOINTS
# ============================================


def test_list_roles(api_client):
    """Test GET /api/v1/rbac/roles"""
    token = get_auth_token(api_client)

    response = api_client.get(
        "/api/v1/rbac/roles", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    roles = response.json()
    assert len(roles) >= 1
    assert any(r["name"] == "api_test_role" for r in roles)


def test_get_role_by_id(api_client):
    """Test GET /api/v1/rbac/roles/{role_id}"""
    token = get_auth_token(api_client)

    response = api_client.get(
        "/api/v1/rbac/roles/role_api_test", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    role = response.json()
    assert role["id"] == "role_api_test"
    assert role["name"] == "api_test_role"
    assert len(role["features"]) == 1


# ============================================
# SUBSCRIPTION TIER ENDPOINTS (PUBLIC)
# ============================================


def test_list_subscription_tiers_public(api_client):
    """Test GET /api/v1/rbac/tiers (public endpoint)"""
    # No authentication required
    response = api_client.get("/api/v1/rbac/tiers")

    assert response.status_code == 200
    tiers = response.json()
    assert len(tiers) >= 1
    assert any(t["name"] == "api_test_tier" for t in tiers)


def test_get_tier_quotas_public(api_client):
    """Test GET /api/v1/rbac/tiers/{tier_id}/quotas (public endpoint)"""
    # No authentication required
    response = api_client.get("/api/v1/rbac/tiers/tier_api_test/quotas")

    assert response.status_code == 200
    quotas = response.json()
    assert len(quotas) >= 1
    assert any(q["resource_type"] == "documents" for q in quotas)


# ============================================
# PERMISSION CHECK ENDPOINTS
# ============================================


def test_check_permission(api_client):
    """Test GET /api/v1/rbac/check-permission/{feature_name}"""
    token = get_auth_token(api_client)

    response = api_client.get(
        "/api/v1/rbac/check-permission/api_test_feature_1",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    result = response.json()
    assert "has_access" in result
    assert "feature" in result


def test_check_quota(api_client):
    """Test GET /api/v1/rbac/check-quota/{resource_type}"""
    token = get_auth_token(api_client)

    response = api_client.get(
        "/api/v1/rbac/check-quota/documents?requested_amount=5",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    result = response.json()
    assert "allowed" in result


# ============================================
# NOT-FOUND / EDGE-CASE BRANCHES (TF-389 — bisher ungetestet)
# ============================================


def test_get_feature_by_id_returns_404_for_unknown_id(api_client):
    token = get_auth_token(api_client)

    response = api_client.get(
        "/api/v1/rbac/features/does-not-exist",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "rbac_feature_not_found"


def test_get_role_by_id_returns_404_for_unknown_id(api_client):
    token = get_auth_token(api_client)

    response = api_client.get(
        "/api/v1/rbac/roles/does-not-exist",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "rbac_role_not_found"


@pytest.fixture
def free_tier(rbac_api_db):
    """The default `free` SubscriptionTier — `rbac_api_db` only seeds
    `api_test_tier`, so tests exercising the default-tier fallback need
    this added explicitly. A non-isolated fixture elsewhere in the suite
    may already have leaked a real `free` row into the shared test DB
    outside any savepoint (our session still sees already-committed rows
    underneath its own savepoint) — look it up first to avoid colliding
    with `ix_subscription_tiers_name`, same pattern as the `admin_role`
    lookup in test_documents_superuser_access.py."""
    existing = rbac_api_db.query(SubscriptionTier).filter_by(name="free").first()
    if existing:
        return existing
    tier = SubscriptionTier(
        id="tier_free_default",
        name="free",
        display_name="Free",
        description="Default tier",
        price_monthly=0.0,
        price_yearly=0.0,
        is_active=True,
        sort_order=0,
    )
    rbac_api_db.add(tier)
    rbac_api_db.commit()
    return tier


def test_get_current_tier_returns_404_when_default_tier_missing(
    api_client, monkeypatch, rbac_api_db
):
    """`rbac_api_db` only seeds `api_test_tier`, not `free` — with
    `DEFAULT_SUBSCRIPTION_TIER` explicitly unset, both the configured
    default and its fallback miss."""
    monkeypatch.delenv("DEFAULT_SUBSCRIPTION_TIER", raising=False)
    # Guard against a `free` tier leaked into the shared test DB by an
    # unrelated, non-isolated fixture elsewhere in the suite (see
    # `free_tier` above) — this test's premise is "no `free` tier exists",
    # enforced only within our own savepoint-isolated session.
    rbac_api_db.query(SubscriptionTier).filter_by(name="free").delete()
    rbac_api_db.commit()

    response = api_client.get("/api/v1/rbac/tiers/current")

    assert response.status_code == 404
    assert response.json()["error_code"] == "rbac_tier_not_found"


def test_get_current_tier_returns_default_free_tier(api_client, free_tier):
    response = api_client.get("/api/v1/rbac/tiers/current")

    assert response.status_code == 200
    assert response.json()["name"] == "free"


def test_get_my_tier_returns_users_institution_tier(api_client, free_tier):
    """The seeded test user's institution has `subscription_tier="free"`
    (see `rbac_api_db` above) — `free_tier` adds that tier so `/tiers/my`
    resolves it."""
    token = get_auth_token(api_client)

    response = api_client.get(
        "/api/v1/rbac/tiers/my", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["name"] == "free"


def test_check_quota_without_institution_returns_400(api_client):
    """`institution_id` is NOT NULL at the DB level, so a real user without
    one can't be persisted — override `get_current_user` directly with an
    in-memory user instead of round-tripping through the database."""
    from utils.auth_utils import get_current_user

    fake_user = User(
        id=999999,
        email="no-institution@test.com",
        institution_id=None,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    app.dependency_overrides[get_current_user] = lambda: fake_user

    response = api_client.get("/api/v1/rbac/check-quota/documents")

    assert response.status_code == 400
    assert response.json()["error_code"] == "rbac_no_institution"
