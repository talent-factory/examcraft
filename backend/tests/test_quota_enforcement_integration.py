"""
Integration tests for quota enforcement at API level.

Tests that:
1. Registration rejects when user limit is reached
2. Document upload rejects when document/storage limit is exceeded
3. tier_quotas → Institution.max_* sync works at login and tier change
4. storage_mb enforcement works end-to-end
"""

import pytest
from fastapi import HTTPException

from models.auth import Institution, User, Role, UserStatus
from models.document import Document, DocumentStatus
from models.rbac import TierQuota, SubscriptionTier
from services.auth_service import AuthService
from utils.tenant_utils import SubscriptionLimits, sync_institution_quotas


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def db_with_quotas(test_db):
    """Set up institution, roles, and tier_quotas for integration tests."""
    # Subscription tiers (required FK for tier_quotas)
    for tier_name in ["free", "starter", "professional", "enterprise"]:
        existing = (
            test_db.query(SubscriptionTier)
            .filter(SubscriptionTier.id == f"tier_{tier_name}")
            .first()
        )
        if not existing:
            test_db.add(
                SubscriptionTier(
                    id=f"tier_{tier_name}",
                    name=tier_name,
                    display_name=tier_name.capitalize(),
                    description=f"{tier_name} tier",
                    is_active=True,
                    sort_order=["free", "starter", "professional", "enterprise"].index(
                        tier_name
                    )
                    + 1,
                )
            )
    test_db.flush()

    # Institution with tight limits for testing
    institution = Institution(
        name="Quota Test University",
        slug="quota-test",
        domain="quotatest.edu",
        subscription_tier="free",
        max_users=2,
        max_documents=3,
        max_questions_per_month=5,
    )
    test_db.add(institution)
    test_db.flush()

    # Roles
    for role_def in [
        {
            "name": "dozent",
            "display_name": "Dozent",
            "description": "Teaching role",
            "permissions": '["create_questions","create_documents","documents:read"]',
            "is_system_role": True,
        },
        {
            "name": "viewer",
            "display_name": "Viewer",
            "description": "View only",
            "permissions": '["view_questions","documents:read"]',
            "is_system_role": True,
        },
    ]:
        existing = test_db.query(Role).filter(Role.name == role_def["name"]).first()
        if not existing:
            test_db.add(Role(**role_def))

    # Tier quotas (free tier)
    for resource_type, limit in [
        ("documents", 3),
        ("questions_per_month", 5),
        ("users", 2),
        ("storage_mb", 1),  # 1 MB — tight for testing
    ]:
        existing = (
            test_db.query(TierQuota)
            .filter(
                TierQuota.tier_id == "tier_free",
                TierQuota.resource_type == resource_type,
            )
            .first()
        )
        if existing:
            existing.quota_limit = limit
        else:
            test_db.add(
                TierQuota(
                    tier_id="tier_free",
                    resource_type=resource_type,
                    quota_limit=limit,
                )
            )

    # Professional tier quotas (for upgrade tests)
    for resource_type, limit in [
        ("documents", -1),
        ("questions_per_month", 1000),
        ("users", 10),
        ("storage_mb", 10000),
    ]:
        existing = (
            test_db.query(TierQuota)
            .filter(
                TierQuota.tier_id == "tier_professional",
                TierQuota.resource_type == resource_type,
            )
            .first()
        )
        if existing:
            existing.quota_limit = limit
        else:
            test_db.add(
                TierQuota(
                    tier_id="tier_professional",
                    resource_type=resource_type,
                    quota_limit=limit,
                )
            )

    test_db.commit()

    yield test_db


@pytest.fixture
def institution(db_with_quotas):
    return db_with_quotas.query(Institution).first()


@pytest.fixture
def active_user(db_with_quotas, institution):
    """Create one active user in the institution."""
    dozent = db_with_quotas.query(Role).filter(Role.name == "dozent").first()
    user = User(
        email="existing@quotatest.edu",
        password_hash=AuthService.get_password_hash("TestPass123!"),
        first_name="Existing",
        last_name="User",
        institution_id=institution.id,
        status=UserStatus.ACTIVE.value,
        is_email_verified=True,
    )
    db_with_quotas.add(user)
    db_with_quotas.flush()
    user.roles.append(dozent)
    db_with_quotas.commit()
    db_with_quotas.refresh(user)
    return user


# ============================================================================
# User Limit at Registration
# ============================================================================


class TestUserLimitEnforcement:
    """User limit must be enforced when registering new users."""

    def test_user_limit_checked_at_registration(self, db_with_quotas, institution):
        """
        check_user_limit() must reject when the institution's active user
        count has reached max_users.
        """
        institution.max_users = 1
        db_with_quotas.commit()

        # Create one active user (at limit)
        user = User(
            email="first@quotatest.edu",
            first_name="First",
            last_name="User",
            password_hash="dummy",
            institution_id=institution.id,
            status=UserStatus.ACTIVE.value,
        )
        db_with_quotas.add(user)
        db_with_quotas.commit()

        # Attempting another user should fail
        with pytest.raises(HTTPException) as exc_info:
            SubscriptionLimits.check_user_limit(institution, db_with_quotas)
        assert exc_info.value.status_code == 403
        assert "User limit" in exc_info.value.detail

    def test_pending_users_dont_count_toward_limit(self, db_with_quotas, institution):
        """
        Pending users (not yet email-verified) must NOT count toward
        the user limit, allowing registration to proceed.
        """
        institution.max_users = 1
        db_with_quotas.commit()

        # Create one PENDING user
        user = User(
            email="pending@quotatest.edu",
            first_name="Pending",
            last_name="User",
            password_hash="dummy",
            institution_id=institution.id,
            status=UserStatus.PENDING.value,
        )
        db_with_quotas.add(user)
        db_with_quotas.commit()

        # Should NOT raise — pending users don't count
        SubscriptionLimits.check_user_limit(institution, db_with_quotas)


# ============================================================================
# Storage Limit at Document Upload
# ============================================================================


class TestStorageLimitEnforcement:
    """Storage limit must be enforced when uploading documents."""

    def test_storage_limit_exceeded(self, db_with_quotas, institution, active_user):
        """
        Upload must be rejected when cumulative file sizes exceed
        the storage_mb quota from tier_quotas table.
        """
        # storage_mb = 1 (from fixture), so limit is 1 MB = 1048576 bytes
        # Add existing document using 900 KB
        doc = Document(
            filename="big.pdf",
            original_filename="big.pdf",
            file_path="/tmp/big.pdf",
            file_size=900 * 1024,  # 900 KB
            mime_type="application/pdf",
            status=DocumentStatus.PROCESSED,
            user_id=active_user.id,
            institution_id=institution.id,
        )
        db_with_quotas.add(doc)
        db_with_quotas.commit()

        # Trying to add 200 KB more (total > 1 MB) should fail
        with pytest.raises(HTTPException) as exc_info:
            SubscriptionLimits.check_storage_limit(
                institution, db_with_quotas, 200 * 1024
            )
        assert exc_info.value.status_code == 403
        assert "Storage limit" in exc_info.value.detail

    def test_storage_limit_not_exceeded(self, db_with_quotas, institution, active_user):
        """Upload should succeed when under storage limit."""
        # Add small existing document (100 KB)
        doc = Document(
            filename="small.pdf",
            original_filename="small.pdf",
            file_path="/tmp/small.pdf",
            file_size=100 * 1024,  # 100 KB
            mime_type="application/pdf",
            status=DocumentStatus.PROCESSED,
            user_id=active_user.id,
            institution_id=institution.id,
        )
        db_with_quotas.add(doc)
        db_with_quotas.commit()

        # Adding 500 KB more (total 600 KB < 1 MB) should succeed
        SubscriptionLimits.check_storage_limit(institution, db_with_quotas, 500 * 1024)

    def test_storage_unlimited_skips_check(self, db_with_quotas, institution):
        """Unlimited storage (-1) should always pass."""
        # Set storage to unlimited
        quota = (
            db_with_quotas.query(TierQuota)
            .filter(
                TierQuota.tier_id == "tier_free",
                TierQuota.resource_type == "storage_mb",
            )
            .first()
        )
        quota.quota_limit = -1
        db_with_quotas.commit()

        # Even a huge file should pass
        SubscriptionLimits.check_storage_limit(
            institution, db_with_quotas, 999 * 1024 * 1024
        )

    def test_storage_check_with_no_tier_quota_row(self, db_with_quotas, institution):
        """If no storage_mb row exists in tier_quotas, skip check."""
        # Delete the storage_mb row
        db_with_quotas.query(TierQuota).filter(
            TierQuota.tier_id == "tier_free",
            TierQuota.resource_type == "storage_mb",
        ).delete()
        db_with_quotas.commit()

        # Should not raise even for large files
        SubscriptionLimits.check_storage_limit(
            institution, db_with_quotas, 999 * 1024 * 1024
        )


# ============================================================================
# Tier Quota Sync
# ============================================================================


class TestTierQuotaSync:
    """tier_quotas DB values must sync to Institution.max_* fields."""

    def test_sync_updates_institution_fields(self, db_with_quotas, institution):
        """
        sync_institution_quotas() must copy tier_quotas values to
        Institution.max_* fields.
        """
        # Institution starts with max_users=2, max_documents=3
        assert institution.max_users == 2
        assert institution.max_documents == 3

        # tier_quotas has: users=2, documents=3 (matches fixture)
        # Change tier_quotas to different values
        for q in (
            db_with_quotas.query(TierQuota)
            .filter(TierQuota.tier_id == "tier_free")
            .all()
        ):
            if q.resource_type == "users":
                q.quota_limit = 5
            elif q.resource_type == "documents":
                q.quota_limit = 50
            elif q.resource_type == "questions_per_month":
                q.quota_limit = 200
        db_with_quotas.commit()

        # Sync
        sync_institution_quotas(institution, db_with_quotas)

        assert institution.max_users == 5
        assert institution.max_documents == 50
        assert institution.max_questions_per_month == 200

    def test_sync_on_tier_upgrade(self, db_with_quotas, institution):
        """
        When subscription_tier changes to professional, sync must
        update Institution fields to professional-tier quotas.
        """
        # Upgrade tier
        institution.subscription_tier = "professional"
        sync_institution_quotas(institution, db_with_quotas)

        assert institution.max_users == 10
        assert institution.max_documents == -1  # unlimited
        assert institution.max_questions_per_month == 1000

    def test_sync_no_rows_leaves_values(self, db_with_quotas, institution):
        """
        If tier_quotas has no rows for the tier, sync should not
        change existing Institution values.
        """
        original_users = institution.max_users
        original_docs = institution.max_documents

        institution.subscription_tier = "nonexistent_tier"
        sync_institution_quotas(institution, db_with_quotas)

        assert institution.max_users == original_users
        assert institution.max_documents == original_docs

    def test_sync_idempotent(self, db_with_quotas, institution):
        """Running sync twice should produce the same result."""
        sync_institution_quotas(institution, db_with_quotas)
        users_after_first = institution.max_users

        sync_institution_quotas(institution, db_with_quotas)
        assert institution.max_users == users_after_first


# ============================================================================
# Document Limit Enforcement (existing, verify integration)
# ============================================================================


class TestDocumentLimitEnforcement:
    """Document count limit must be enforced at upload."""

    def test_document_limit_blocks_upload(
        self, db_with_quotas, institution, active_user
    ):
        """
        When document count reaches max_documents, uploading another
        must return 403.
        """
        institution.max_documents = 2
        db_with_quotas.commit()

        # Create 2 documents (at limit)
        for i in range(2):
            db_with_quotas.add(
                Document(
                    filename=f"doc{i}.pdf",
                    original_filename=f"doc{i}.pdf",
                    file_path=f"/tmp/doc{i}.pdf",
                    file_size=1024,
                    mime_type="application/pdf",
                    status=DocumentStatus.PROCESSED,
                    user_id=active_user.id,
                    institution_id=institution.id,
                )
            )
        db_with_quotas.commit()

        with pytest.raises(HTTPException) as exc_info:
            SubscriptionLimits.check_document_limit(institution, db_with_quotas)
        assert exc_info.value.status_code == 403

    def test_document_unlimited_allows_all(
        self, db_with_quotas, institution, active_user
    ):
        """Unlimited documents (-1) should always pass."""
        institution.max_documents = -1
        db_with_quotas.commit()

        for i in range(50):
            db_with_quotas.add(
                Document(
                    filename=f"doc{i}.pdf",
                    original_filename=f"doc{i}.pdf",
                    file_path=f"/tmp/doc{i}.pdf",
                    file_size=1024,
                    mime_type="application/pdf",
                    status=DocumentStatus.PROCESSED,
                    user_id=active_user.id,
                    institution_id=institution.id,
                )
            )
        db_with_quotas.commit()

        # Should not raise
        SubscriptionLimits.check_document_limit(institution, db_with_quotas)


# ============================================================================
# Question Limit Enforcement (existing, verify integration)
# ============================================================================


class TestQuestionLimitEnforcement:
    """Monthly question limit must be enforced at generation."""

    def test_question_limit_blocks_generation(
        self, db_with_quotas, institution, active_user
    ):
        """
        When monthly question count reaches max_questions_per_month,
        generating more must return 403.
        """
        from models.question_review import QuestionReview, ReviewStatus

        institution.max_questions_per_month = 2
        db_with_quotas.commit()

        # Create 2 questions this month (at limit)
        for i in range(2):
            db_with_quotas.add(
                QuestionReview(
                    question_text=f"Question {i}?",
                    question_type="multiple_choice",
                    difficulty="medium",
                    topic="Test Topic",
                    institution_id=institution.id,
                    review_status=ReviewStatus.PENDING.value,
                )
            )
        db_with_quotas.commit()

        with pytest.raises(HTTPException) as exc_info:
            SubscriptionLimits.check_question_limit(
                institution, db_with_quotas, additional_count=1
            )
        assert exc_info.value.status_code == 403

    def test_question_limit_allows_within_quota(self, db_with_quotas, institution):
        """Under-limit question generation should succeed."""
        institution.max_questions_per_month = 10
        db_with_quotas.commit()

        # No questions yet, requesting 5
        SubscriptionLimits.check_question_limit(
            institution, db_with_quotas, additional_count=5
        )


# ============================================================================
# End-to-End: Quota change in DB propagates to enforcement
# ============================================================================


class TestQuotaChangePropagatesToEnforcement:
    """
    The critical scenario: admin changes a quota in tier_quotas,
    and on next login the new limit takes effect.
    """

    def test_quota_change_enforced_after_sync(
        self, db_with_quotas, institution, active_user
    ):
        """
        Changing tier_quotas.documents from 3 to 1, then syncing,
        must cause check_document_limit to reject at 2 documents.
        """
        # Initially max_documents=3 (from fixture)
        assert institution.max_documents == 3

        # Change tier_quotas
        doc_quota = (
            db_with_quotas.query(TierQuota)
            .filter(
                TierQuota.tier_id == "tier_free",
                TierQuota.resource_type == "documents",
            )
            .first()
        )
        doc_quota.quota_limit = 1
        db_with_quotas.commit()

        # Sync (as would happen at login)
        sync_institution_quotas(institution, db_with_quotas)
        assert institution.max_documents == 1

        # Create 1 document
        db_with_quotas.add(
            Document(
                filename="doc.pdf",
                original_filename="doc.pdf",
                file_path="/tmp/doc.pdf",
                file_size=1024,
                mime_type="application/pdf",
                status=DocumentStatus.PROCESSED,
                user_id=active_user.id,
                institution_id=institution.id,
            )
        )
        db_with_quotas.commit()

        # Now at limit — next upload must fail
        with pytest.raises(HTTPException) as exc_info:
            SubscriptionLimits.check_document_limit(institution, db_with_quotas)
        assert exc_info.value.status_code == 403

    def test_tier_upgrade_unlocks_more_capacity(
        self, db_with_quotas, institution, active_user
    ):
        """
        Upgrading from free to professional via tier_quotas sync
        must unlock higher (or unlimited) quotas.
        """
        # At free tier: max_documents=3
        assert institution.max_documents == 3

        # Fill to limit
        for i in range(3):
            db_with_quotas.add(
                Document(
                    filename=f"doc{i}.pdf",
                    original_filename=f"doc{i}.pdf",
                    file_path=f"/tmp/doc{i}.pdf",
                    file_size=1024,
                    mime_type="application/pdf",
                    status=DocumentStatus.PROCESSED,
                    user_id=active_user.id,
                    institution_id=institution.id,
                )
            )
        db_with_quotas.commit()

        # At limit — should fail
        with pytest.raises(HTTPException):
            SubscriptionLimits.check_document_limit(institution, db_with_quotas)

        # Upgrade to professional
        institution.subscription_tier = "professional"
        sync_institution_quotas(institution, db_with_quotas)

        # Now unlimited — should succeed
        assert institution.max_documents == -1
        SubscriptionLimits.check_document_limit(institution, db_with_quotas)
