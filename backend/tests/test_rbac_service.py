"""
Tests for RBAC Service
Tests for RBACService: Permission Checks, Quota Management, Role Management
"""

import pytest

from services.rbac_service import RBACService
from models.rbac import (
    Feature,
    RBACRole,
    RoleFeature,
    SubscriptionTier,
    TierQuota,
    TierFeature,
)
from models.auth import User, Role, Institution, UserStatus


@pytest.fixture(scope="function")
def rbac_db(test_db):
    """Setup RBAC test data"""
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
            id="feat_test_gen",
            name="test_generation",
            display_name="Test Generation",
            description="Generate tests",
            category="generation",
            is_active=True,
        ),
        Feature(
            id="feat_test_mgmt",
            name="test_management",
            display_name="Test Management",
            description="Manage tests",
            category="management",
            is_active=True,
        ),
        Feature(
            id="feat_admin",
            name="admin_panel",
            display_name="Admin Panel",
            description="Admin access",
            category="administration",
            is_active=True,
        ),
    ]
    for feature in features:
        test_db.add(feature)

    # Create RBAC roles
    rbac_roles = [
        RBACRole(
            id="role_admin",
            name="admin",
            display_name="Administrator",
            description="Full access",
            is_system_role=True,
            is_active=True,
        ),
        RBACRole(
            id="role_user",
            name="user",
            display_name="User",
            description="Basic access",
            is_system_role=True,
            is_active=True,
        ),
    ]
    for role in rbac_roles:
        test_db.add(role)
    test_db.flush()

    # Assign features to roles
    # Admin: all features
    for feature in features:
        test_db.add(RoleFeature(role_id="role_admin", feature_id=feature.id))

    # User: only generation and management
    test_db.add(RoleFeature(role_id="role_user", feature_id="feat_test_gen"))
    test_db.add(RoleFeature(role_id="role_user", feature_id="feat_test_mgmt"))

    # Create subscription tiers
    tiers = [
        SubscriptionTier(
            id="tier_free",
            name="free",
            display_name="Free",
            description="Free tier",
            price_monthly=0.0,
            price_yearly=0.0,
            is_active=True,
            sort_order=1,
        ),
        SubscriptionTier(
            id="tier_pro",
            name="professional",
            display_name="Professional",
            description="Pro tier",
            price_monthly=49.0,
            price_yearly=490.0,
            is_active=True,
            sort_order=2,
        ),
    ]
    for tier in tiers:
        test_db.add(tier)
    test_db.flush()

    # Create tier quotas
    quotas = [
        TierQuota(tier_id="tier_free", resource_type="documents", quota_limit=5),
        TierQuota(
            tier_id="tier_free", resource_type="questions_per_month", quota_limit=20
        ),
        TierQuota(
            tier_id="tier_pro", resource_type="documents", quota_limit=-1
        ),  # Unlimited
        TierQuota(
            tier_id="tier_pro", resource_type="questions_per_month", quota_limit=1000
        ),
    ]
    for quota in quotas:
        test_db.add(quota)

    # Assign features to tiers
    # Free: only generation
    test_db.add(TierFeature(tier_id="tier_free", feature_id="feat_test_gen"))
    # Pro: generation + management
    test_db.add(TierFeature(tier_id="tier_pro", feature_id="feat_test_gen"))
    test_db.add(TierFeature(tier_id="tier_pro", feature_id="feat_test_mgmt"))

    # Create old-style roles for user mapping
    old_roles = [
        Role(
            name="admin",
            display_name="Admin",
            description="Admin role",
            permissions=["*"],
            is_system_role=True,
        ),
        Role(
            name="user",
            display_name="User",
            description="User role",
            permissions=["view"],
            is_system_role=True,
        ),
    ]
    for role in old_roles:
        test_db.add(role)

    test_db.flush()
    yield test_db


# ============================================
# PERMISSION CHECK TESTS
# ============================================


def test_user_has_feature_access_with_role_and_tier(rbac_db):
    """Test permission check with both role and tier requirements"""
    # Create user with admin role and free tier
    institution = rbac_db.query(Institution).first()
    admin_role = rbac_db.query(Role).filter(Role.name == "admin").first()

    user = User(
        email="admin@test.com",
        password_hash="hash",
        first_name="Admin",
        last_name="User",
        institution_id=institution.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    rbac_db.add(user)
    rbac_db.flush()
    user.roles.append(admin_role)
    rbac_db.commit()
    rbac_db.refresh(user)

    service = RBACService(rbac_db)

    # Admin role has test_generation, free tier has test_generation -> ALLOWED
    assert service.user_has_feature_access(user.id, "test_generation", log_access=False)

    # Admin role has test_management, but free tier does NOT -> DENIED
    assert not service.user_has_feature_access(
        user.id, "test_management", log_access=False
    )


def test_user_without_role_permission_denied(rbac_db):
    """Test permission denied when user role doesn't have feature"""
    institution = rbac_db.query(Institution).first()
    user_role = rbac_db.query(Role).filter(Role.name == "user").first()

    user = User(
        email="user@test.com",
        password_hash="hash",
        first_name="Test",
        last_name="User",
        institution_id=institution.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    rbac_db.add(user)
    rbac_db.flush()
    user.roles.append(user_role)
    rbac_db.commit()
    rbac_db.refresh(user)

    service = RBACService(rbac_db)

    # User role does NOT have admin_panel feature -> DENIED
    assert not service.user_has_feature_access(user.id, "admin_panel", log_access=False)


# ============================================
# QUOTA MANAGEMENT TESTS
# ============================================


def test_check_resource_quota_within_limit(rbac_db):
    """Test quota check when within limit"""
    institution = rbac_db.query(Institution).first()
    service = RBACService(rbac_db)

    # Free tier has 5 documents limit, no usage yet -> ALLOWED
    result = service.check_resource_quota(institution.id, "documents", 1)

    assert result["allowed"] is True
    assert result["quota_limit"] == 5
    assert result["current_usage"] == 0
    assert result["remaining"] == 5


def test_check_resource_quota_unlimited(rbac_db):
    """Test quota check for unlimited resource"""
    # Change institution to pro tier
    institution = rbac_db.query(Institution).first()
    institution.subscription_tier = "pro"  # Must match tier_id without "tier_" prefix
    rbac_db.commit()

    service = RBACService(rbac_db)

    # Pro tier has unlimited documents (-1) -> ALLOWED
    result = service.check_resource_quota(institution.id, "documents", 1000)

    assert result["allowed"] is True
    assert result["quota_limit"] == -1
    assert result["remaining"] == -1


def test_increment_resource_usage(rbac_db):
    """Test incrementing resource usage"""
    institution = rbac_db.query(Institution).first()

    service = RBACService(rbac_db)

    # Increment usage
    usage = service.increment_resource_usage(institution.id, "documents", 3)

    assert usage.usage_count == 3
    assert usage.resource_type == "documents"

    # Increment again
    usage = service.increment_resource_usage(institution.id, "documents", 2)
    assert usage.usage_count == 5


# ============================================
# ROLE MANAGEMENT TESTS
# ============================================


def test_create_custom_role(rbac_db):
    """Test creating a custom role"""
    service = RBACService(rbac_db)

    role = service.create_custom_role(
        name="custom_reviewer",
        display_name="Custom Reviewer",
        description="Custom role for reviewers",
        feature_ids=["feat_test_gen", "feat_test_mgmt"],
        created_by=1,
    )

    assert role.name == "custom_reviewer"
    assert role.display_name == "Custom Reviewer"
    assert role.is_system_role is False
    assert role.is_active is True


def test_update_role_features(rbac_db):
    """Test updating role features"""
    service = RBACService(rbac_db)

    # Create custom role
    role = service.create_custom_role(
        name="test_role",
        display_name="Test Role",
        description="Test",
        feature_ids=["feat_test_gen"],
        created_by=1,
    )

    # Update features
    updated_role = service.update_role_features(
        role.id, ["feat_test_gen", "feat_test_mgmt", "feat_admin"]
    )

    features = service.get_role_features(updated_role.id)
    assert len(features) == 3


def test_cannot_update_system_role_features(rbac_db):
    """Test that system roles cannot be modified"""
    service = RBACService(rbac_db)

    with pytest.raises(ValueError, match="Cannot modify features of system roles"):
        service.update_role_features("role_admin", ["feat_test_gen"])


def test_list_roles(rbac_db):
    """Test listing roles"""
    service = RBACService(rbac_db)

    # List all roles
    all_roles = service.list_roles(include_system_roles=True, include_inactive=False)
    assert len(all_roles) == 2  # admin + user

    # List only custom roles
    custom_roles = service.list_roles(
        include_system_roles=False, include_inactive=False
    )
    assert len(custom_roles) == 0  # No custom roles yet
