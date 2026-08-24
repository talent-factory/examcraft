"""
Tests for superuser bypass in SubscriptionLimits.
Covers all 4 quota methods: User, Document, Storage, Question.
"""

import json

import pytest
from fastapi import HTTPException

from models.auth import AuditLog, User, UserStatus
from models.document import Document, DocumentStatus
from utils.tenant_utils import SubscriptionLimits


def _persist_user(db, user_id, email, is_superuser, institution_id):
    u = User(
        id=user_id,
        email=email,
        first_name="T",
        last_name="U",
        password_hash="x",
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
        is_superuser=is_superuser,
    )
    db.add(u)
    db.commit()
    return u


# Hardcoded primary keys in a high range that the auto-increment sequence never
# reaches within a test run. Other suites can leak committed user rows into the
# shared test DB (e.g. integration tests whose TestClient uses the real get_db),
# and Postgres sequences are not transactional, so a low fixed id like 100 can
# collide with such a leaked auto-id user (TF-400 surfaced this by shifting the
# sequence). Explicit high ids consume no nextval, so they neither shift the
# sequence nor collide. See follow-up: the underlying leak should be removed by
# giving the base `client` fixture a rolled-back get_db override.
_BASE_ID = 9_000_000


@pytest.fixture
def super_user(test_db, test_institution):
    return _persist_user(
        test_db, _BASE_ID + 99, "admin@test.ch", True, test_institution.id
    )


@pytest.fixture
def normal_user(test_db, test_institution):
    return _persist_user(
        test_db, _BASE_ID + 100, "user@test.ch", False, test_institution.id
    )


def _create_users(test_db, institution, count, start_id=_BASE_ID + 200):
    for i in range(count):
        test_db.add(
            User(
                id=start_id + i,
                email=f"u{i}@t.ch",
                first_name="U",
                last_name=f"{i}",
                password_hash="x",
                institution_id=institution.id,
                status=UserStatus.ACTIVE.value,
            )
        )
    test_db.commit()


def test_user_limit_normal_user_blocked(test_db, test_institution, normal_user):
    test_institution.max_users = 3
    test_db.commit()
    # 2 fixture users (super_user/normal_user only normal here) + create 2 more = 3
    _create_users(test_db, test_institution, 2)

    with pytest.raises(HTTPException) as exc:
        SubscriptionLimits.check_user_limit(test_institution, test_db, user=normal_user)
    assert exc.value.status_code == 403


def test_user_limit_superuser_bypass_logs_audit(test_db, test_institution, super_user):
    """Superuser bypass is always logged when a quota is configured."""
    test_institution.max_users = 5
    test_db.commit()

    SubscriptionLimits.check_user_limit(test_institution, test_db, user=super_user)

    logs = test_db.query(AuditLog).filter(AuditLog.action == "superuser_bypass").all()
    assert len(logs) == 1
    assert logs[0].resource_type == "quota"
    extra = json.loads(logs[0].additional_data)
    assert extra["bypassed_action"] == "override_user_limit"
    assert extra["superuser_email"] == "admin@test.ch"


def test_user_limit_superuser_no_log_when_unlimited(
    test_db, test_institution, super_user
):
    """Superuser with -1 (unlimited) → no bypass log (nothing to bypass)."""
    test_institution.max_users = -1
    test_db.commit()

    SubscriptionLimits.check_user_limit(test_institution, test_db, user=super_user)
    assert (
        test_db.query(AuditLog).filter(AuditLog.action == "superuser_bypass").count()
        == 0
    )


def test_user_limit_backwards_compat_no_user_kwarg(test_db, test_institution):
    """Calling without the user param keeps working (backwards compat)."""
    test_institution.max_users = 100
    test_db.commit()
    SubscriptionLimits.check_user_limit(test_institution, test_db)  # no exception


def _create_documents(test_db, institution, count, start_id=400):
    for i in range(count):
        test_db.add(
            Document(
                id=start_id + i,
                filename=f"f{i}.pdf",
                original_filename=f"f{i}.pdf",
                file_path=f"/tmp/f{i}.pdf",
                file_size=1,
                mime_type="application/pdf",
                status=DocumentStatus.PROCESSED,
                institution_id=institution.id,
            )
        )
    test_db.commit()


def test_document_limit_normal_user_blocked(test_db, test_institution, normal_user):
    test_institution.max_documents = 3
    test_db.commit()
    _create_documents(test_db, test_institution, 3)

    with pytest.raises(HTTPException) as exc:
        SubscriptionLimits.check_document_limit(
            test_institution, test_db, user=normal_user
        )
    assert exc.value.status_code == 403


def test_document_limit_superuser_bypass_logs_audit(
    test_db, test_institution, super_user
):
    """Bypass is always logged when a limit is configured."""
    test_institution.max_documents = 100
    test_db.commit()

    SubscriptionLimits.check_document_limit(test_institution, test_db, user=super_user)

    logs = test_db.query(AuditLog).filter(AuditLog.action == "superuser_bypass").all()
    assert len(logs) == 1
    assert logs[0].resource_type == "quota"
    extra = json.loads(logs[0].additional_data)
    assert extra["bypassed_action"] == "override_document_limit"


def test_document_limit_superuser_no_log_when_unlimited(
    test_db, test_institution, super_user
):
    test_institution.max_documents = -1
    test_db.commit()
    SubscriptionLimits.check_document_limit(test_institution, test_db, user=super_user)
    assert (
        test_db.query(AuditLog).filter(AuditLog.action == "superuser_bypass").count()
        == 0
    )


def test_document_limit_backwards_compat(test_db, test_institution):
    test_institution.max_documents = 100
    test_db.commit()
    SubscriptionLimits.check_document_limit(test_institution, test_db)  # no exception


def _create_questions(test_db, institution, count, start_id=600):
    from models.question_review import QuestionReview, ReviewStatus

    for i in range(count):
        test_db.add(
            QuestionReview(
                id=start_id + i,
                question_text=f"Q{i}",
                question_type="single_choice",
                options=["a", "b"],
                correct_answer="a",
                explanation="x",
                difficulty="medium",
                topic="t",
                institution_id=institution.id,
                review_status=ReviewStatus.PENDING.value,
            )
        )
    test_db.commit()


def test_question_limit_normal_user_blocked(test_db, test_institution, normal_user):
    test_institution.max_questions_per_month = 3
    test_db.commit()
    _create_questions(test_db, test_institution, 3)

    with pytest.raises(HTTPException) as exc:
        SubscriptionLimits.check_question_limit(
            test_institution, test_db, additional_count=1, user=normal_user
        )
    assert exc.value.status_code == 403


def test_question_limit_superuser_bypass_logs_audit(
    test_db, test_institution, super_user
):
    """Bypass is always logged when a limit is configured."""
    test_institution.max_questions_per_month = 100
    test_db.commit()

    SubscriptionLimits.check_question_limit(
        test_institution, test_db, additional_count=1, user=super_user
    )

    logs = test_db.query(AuditLog).filter(AuditLog.action == "superuser_bypass").all()
    assert len(logs) == 1
    extra = json.loads(logs[0].additional_data)
    assert extra["bypassed_action"] == "override_question_limit"


def test_question_limit_superuser_no_log_when_unlimited(
    test_db, test_institution, super_user
):
    test_institution.max_questions_per_month = -1
    test_db.commit()
    SubscriptionLimits.check_question_limit(
        test_institution, test_db, additional_count=1, user=super_user
    )
    assert (
        test_db.query(AuditLog).filter(AuditLog.action == "superuser_bypass").count()
        == 0
    )


def test_question_limit_backwards_compat(test_db, test_institution):
    test_institution.max_questions_per_month = 100
    test_db.commit()
    SubscriptionLimits.check_question_limit(
        test_institution, test_db, additional_count=1
    )


def _seed_storage_quota(test_db, institution, quota_mb: int):
    from models.rbac import SubscriptionTier, TierQuota

    tier_id = f"tier_{institution.subscription_tier}"
    test_db.merge(
        SubscriptionTier(
            id=tier_id,
            name=institution.subscription_tier,
            display_name=institution.subscription_tier.capitalize(),
        )
    )
    # Real upsert: TierQuota has (tier_id, resource_type) as a unique index,
    # but id as the primary key — merge() without an id would always INSERT
    # and collide with idx_tier_quota_unique if a previous test leaked the
    # row via commit (test_seed_pricing, test_quota_enforcement_integration).
    existing = (
        test_db.query(TierQuota)
        .filter_by(tier_id=tier_id, resource_type="storage_mb")
        .first()
    )
    if existing:
        existing.quota_limit = quota_mb
    else:
        test_db.add(
            TierQuota(
                tier_id=tier_id,
                resource_type="storage_mb",
                quota_limit=quota_mb,
            )
        )
    test_db.commit()


def test_storage_limit_normal_user_blocked(test_db, test_institution, normal_user):
    _seed_storage_quota(test_db, test_institution, quota_mb=1)
    _create_documents(test_db, test_institution, 1, start_id=900)
    # With only a 1MB quota, a 10MB upload would exceed it:
    with pytest.raises(HTTPException) as exc:
        SubscriptionLimits.check_storage_limit(
            test_institution,
            test_db,
            file_size_bytes=10 * 1024 * 1024,
            user=normal_user,
        )
    assert exc.value.status_code == 403


def test_storage_limit_superuser_bypass_logs_audit(
    test_db, test_institution, super_user
):
    """Bypass is always logged when a limit is configured (even when under the limit)."""
    _seed_storage_quota(test_db, test_institution, quota_mb=1000)
    SubscriptionLimits.check_storage_limit(
        test_institution,
        test_db,
        file_size_bytes=1,
        user=super_user,
    )
    logs = test_db.query(AuditLog).filter(AuditLog.action == "superuser_bypass").all()
    assert len(logs) == 1
    extra = json.loads(logs[0].additional_data)
    assert extra["bypassed_action"] == "override_storage_limit"


def test_storage_limit_backwards_compat(test_db, test_institution):
    _seed_storage_quota(test_db, test_institution, quota_mb=1000)
    SubscriptionLimits.check_storage_limit(test_institution, test_db, file_size_bytes=1)
