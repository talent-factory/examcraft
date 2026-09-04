"""
Tests for RBAC Service
Tests for RBACService: Permission Checks, Quota Management, Role Management

These tests run against a database that may already carry the RBAC seed data
written by the app startup (``scripts/seed_rbac_data``) — in CI it always does.
The fixture therefore owns its subscription tiers under ids the seed never
uses (``tier_rbactest_*``), and the assertions check the rows the fixture
created rather than counting everything in the table. See TF-660: these four
tests used to carry a ``pytest.mark.skipif`` on the CI environment variable and
never ran in CI, which left the combined role+tier feature check and the whole
quota enforcement unverified there.
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

# Tier ids/names owned by this test module. `RBACService` resolves a tier as
# f"tier_{institution.subscription_tier}", so the name is what the institution
# carries and the id is what quotas and tier-features hang off. Deliberately
# distinct from the seeded tiers (free/starter/professional/enterprise) so the
# fixture's quota values are the ones under test, seeded DB or not.
FREE_TIER_NAME = "rbactest_free"
FREE_TIER_ID = f"tier_{FREE_TIER_NAME}"
PRO_TIER_NAME = "rbactest_pro"
PRO_TIER_ID = f"tier_{PRO_TIER_NAME}"

FREE_DOCUMENT_QUOTA = 5
FREE_QUESTION_QUOTA = 20
PRO_QUESTION_QUOTA = 1000

# RBACRole ids created by the fixture below. RBACService maps an old-style
# Role to an RBAC role as f"role_{role.name}", so these two are shared with the
# seed — the features hanging off them are what makes them distinct.
FIXTURE_SYSTEM_ROLE_IDS = {"role_admin", "role_user"}
CUSTOM_ROLE_ID = "role_rbactest_custom"


def _test_institution(db):
    """The institution this module's fixture owns.

    Queried by slug rather than ``.first()`` — on a seeded or shared database
    the first institution in the table is not necessarily ours.
    """
    return db.query(Institution).filter_by(slug="test-university").one()


@pytest.fixture(scope="function")
def rbac_db(test_db):
    """Setup RBAC test data"""
    # Get or create institution
    institution = test_db.query(Institution).filter_by(slug="test-university").first()
    if not institution:
        institution = Institution(
            name="Test University",
            slug="test-university",
            domain="test.edu",
            max_users=10,
            max_documents=100,
            max_questions_per_month=500,
        )
        test_db.add(institution)
    # Set unconditionally: an institution left over from another fixture would
    # otherwise point at a seeded tier and silently change the quota under test.
    institution.subscription_tier = FREE_TIER_NAME
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
        test_db.merge(feature)

    # Create RBAC roles (merge to handle pre-seeded roles)
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
        # A non-system role. The RBAC seed creates system roles only, so
        # without one of these the include_system_roles=False path has
        # nothing it could ever return and passes no matter what it does.
        RBACRole(
            id=CUSTOM_ROLE_ID,
            name="rbactest_custom",
            display_name="Custom (rbac test)",
            description="Custom, non-system role",
            is_system_role=False,
            is_active=True,
        ),
    ]
    for role in rbac_roles:
        test_db.merge(role)
    test_db.flush()

    # Assign features to roles (skip if already assigned)
    role_feature_specs = [
        ("role_admin", [f.id for f in features]),
        ("role_user", ["feat_test_gen", "feat_test_mgmt"]),
    ]
    for role_id, feature_ids in role_feature_specs:
        for fid in feature_ids:
            existing = (
                test_db.query(RoleFeature)
                .filter_by(role_id=role_id, feature_id=fid)
                .first()
            )
            if not existing:
                test_db.add(RoleFeature(role_id=role_id, feature_id=fid))

    # Subscription tiers owned by this module. Unlike the roles/features above
    # these must NOT reuse a seeded row: the seeded "professional" tier has id
    # "tier_professional", so quotas attached to it would never be found for an
    # institution on subscription_tier="pro" — the unlimited test then read a
    # `no_quota_defined` result and died on a missing key instead of checking
    # the unlimited path (TF-660).
    tier_free = test_db.merge(
        SubscriptionTier(
            id=FREE_TIER_ID,
            name=FREE_TIER_NAME,
            display_name="Free (rbac test)",
            description="Free tier",
            price_monthly=0.0,
            price_yearly=0.0,
            is_active=True,
            sort_order=1,
        )
    )
    tier_pro = test_db.merge(
        SubscriptionTier(
            id=PRO_TIER_ID,
            name=PRO_TIER_NAME,
            display_name="Professional (rbac test)",
            description="Pro tier",
            price_monthly=49.0,
            price_yearly=490.0,
            is_active=True,
            sort_order=2,
        )
    )
    test_db.flush()

    # Get or create tier quotas (may exist from seed data)
    quota_specs = [
        (tier_free.id, "documents", FREE_DOCUMENT_QUOTA),
        (tier_free.id, "questions_per_month", FREE_QUESTION_QUOTA),
        (tier_pro.id, "documents", -1),
        (tier_pro.id, "questions_per_month", PRO_QUESTION_QUOTA),
    ]
    for tier_id, resource_type, limit in quota_specs:
        existing = (
            test_db.query(TierQuota)
            .filter_by(tier_id=tier_id, resource_type=resource_type)
            .first()
        )
        if existing:
            # Overwrite rather than keep: the quota values are what the tests
            # assert on, so they have to come from this fixture, not from
            # whatever happens to be in the database already.
            existing.quota_limit = limit
        else:
            test_db.add(
                TierQuota(
                    tier_id=tier_id,
                    resource_type=resource_type,
                    quota_limit=limit,
                )
            )

    # Assign features to tiers (skip if already assigned)
    tier_feature_specs = [
        (tier_free.id, "feat_test_gen"),
        (tier_pro.id, "feat_test_gen"),
        (tier_pro.id, "feat_test_mgmt"),
    ]
    for tid, fid in tier_feature_specs:
        existing = (
            test_db.query(TierFeature).filter_by(tier_id=tid, feature_id=fid).first()
        )
        if not existing:
            test_db.add(TierFeature(tier_id=tid, feature_id=fid))

    # Get or create old-style roles for user mapping (may exist from seed)
    for role_data in [
        {
            "name": "admin",
            "display_name": "Admin",
            "description": "Admin role",
            "permissions": ["*"],
        },
        {
            "name": "user",
            "display_name": "User",
            "description": "User role",
            "permissions": ["view"],
        },
    ]:
        existing = test_db.query(Role).filter_by(name=role_data["name"]).first()
        if not existing:
            test_db.add(Role(**role_data, is_system_role=True))

    test_db.flush()
    yield test_db


# ============================================
# PERMISSION CHECK TESTS
# ============================================


def test_user_has_feature_access_with_role_and_tier(rbac_db):
    """Test permission check with both role and tier requirements"""
    # Create user with admin role and free tier
    institution = _test_institution(rbac_db)
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
    institution = _test_institution(rbac_db)
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
    institution = _test_institution(rbac_db)
    service = RBACService(rbac_db)

    # Fixture free tier allows FREE_DOCUMENT_QUOTA documents, no usage yet
    result = service.check_resource_quota(institution.id, "documents", 1)

    assert result["allowed"] is True
    assert result["quota_limit"] == FREE_DOCUMENT_QUOTA
    assert result["current_usage"] == 0
    assert result["remaining"] == FREE_DOCUMENT_QUOTA


def test_check_resource_quota_unlimited(rbac_db):
    """Test quota check for unlimited resource"""
    # Switch the institution to the fixture's pro tier. RBACService resolves
    # the tier as f"tier_{subscription_tier}" (by id, NOT by SubscriptionTier
    # .name), so the name stored here has to be the id minus the "tier_"
    # prefix.
    institution = _test_institution(rbac_db)
    institution.subscription_tier = PRO_TIER_NAME
    rbac_db.commit()

    service = RBACService(rbac_db)

    # Pro tier has unlimited documents (-1) -> ALLOWED
    result = service.check_resource_quota(institution.id, "documents", 1000)

    # Guard against passing for the wrong reason: a missing TierQuota row also
    # yields allowed=True, but with reason="no_quota_defined" and no limit —
    # that is exactly how this test silently stopped testing the unlimited
    # path on a seeded database (TF-660).
    assert result.get("reason") != "no_quota_defined"
    assert result["allowed"] is True
    assert result["quota_limit"] == -1
    assert result["remaining"] == -1


def test_increment_resource_usage(rbac_db):
    """Test incrementing resource usage"""
    institution = _test_institution(rbac_db)

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


def test_list_roles(rbac_db):
    """Test listing roles"""
    service = RBACService(rbac_db)

    # Deactivate one of the fixture's roles so the include_inactive=False
    # filter has something of ours to exclude — a count over the whole table
    # would only measure how much the RBAC seed happens to contain.
    inactive_role = rbac_db.query(RBACRole).filter_by(id="role_user").one()
    inactive_role.is_active = False
    rbac_db.flush()

    all_roles = service.list_roles(include_system_roles=True, include_inactive=False)
    listed_ids = {role.id for role in all_roles}

    assert "role_admin" in listed_ids
    assert "role_user" not in listed_ids  # deactivated above

    all_roles = service.list_roles(include_system_roles=True, include_inactive=True)
    listed_ids = {role.id for role in all_roles}
    assert FIXTURE_SYSTEM_ROLE_IDS <= listed_ids
    assert CUSTOM_ROLE_ID in listed_ids


def test_list_roles_excluding_system_roles_returns_the_custom_ones(rbac_db):
    """include_system_roles=False must drop system roles and keep the rest.

    This asserts the presence of the custom role, not just the absence of the
    system ones: the filter used to be `not RBACRole.is_system_role`, which
    Python evaluates to a literal False, so the query returned nothing at all
    and an absence-only check passed while the endpoint was broken (found in
    TF-660, fixed alongside it).
    """
    service = RBACService(rbac_db)

    custom_roles = service.list_roles(include_system_roles=False, include_inactive=True)
    custom_ids = {role.id for role in custom_roles}

    assert CUSTOM_ROLE_ID in custom_ids
    assert not FIXTURE_SYSTEM_ROLE_IDS & custom_ids
    assert all(role.is_system_role is False for role in custom_roles)
