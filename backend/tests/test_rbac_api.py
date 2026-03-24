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


def test_create_role(api_client):
    """Test POST /api/v1/rbac/roles"""
    token = get_auth_token(api_client)

    response = api_client.post(
        "/api/v1/rbac/roles",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "new_test_role",
            "display_name": "New Test Role",
            "description": "A new test role",
            "feature_ids": ["feat_api_test_1", "feat_api_test_2"],
        },
    )

    assert response.status_code == 201
    role = response.json()
    assert role["name"] == "new_test_role"
    assert len(role["features"]) == 2


def test_update_role_features(api_client):
    """Test PUT /api/v1/rbac/roles/{role_id}/features"""
    token = get_auth_token(api_client)

    response = api_client.put(
        "/api/v1/rbac/roles/role_api_test/features",
        headers={"Authorization": f"Bearer {token}"},
        json={"feature_ids": ["feat_api_test_1", "feat_api_test_2"]},
    )

    assert response.status_code == 200
    role = response.json()
    assert len(role["features"]) == 2


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
    assert "quota_limit" in result
    assert "current_usage" in result
    assert "remaining" in result
