"""Tests for pricing seed data values and upsert behavior."""

from scripts.seed_rbac_data import seed_subscription_tiers, seed_tier_quotas


def test_starter_tier_price_is_9(test_db):
    """Starter tier must be CHF 9/month after seeding."""
    from models.rbac import SubscriptionTier

    seed_subscription_tiers(test_db)
    starter = test_db.query(SubscriptionTier).filter_by(id="tier_starter").first()
    assert starter is not None
    assert float(starter.price_monthly) == 9.00


def test_starter_tier_quotas_reduced(test_db):
    """Starter tier quotas: 20 docs, 100 questions, 1 user, 500 MB."""
    from models.rbac import SubscriptionTier, TierQuota

    seed_subscription_tiers(test_db)
    seed_tier_quotas(test_db)

    quotas = {
        q.resource_type: q.quota_limit
        for q in test_db.query(TierQuota).filter_by(tier_id="tier_starter").all()
    }
    assert quotas["documents"] == 20
    assert quotas["questions_per_month"] == 100
    assert quotas["users"] == 1
    assert quotas["storage_mb"] == 500


def test_seed_upserts_existing_tier(test_db):
    """Running seed twice updates existing tiers instead of skipping."""
    from models.rbac import SubscriptionTier

    seed_subscription_tiers(test_db)
    starter = test_db.query(SubscriptionTier).filter_by(id="tier_starter").first()
    assert float(starter.price_monthly) == 9.00

    starter.price_monthly = 99.00
    test_db.commit()

    seed_subscription_tiers(test_db)
    test_db.refresh(starter)
    assert float(starter.price_monthly) == 9.00


def test_seed_upserts_existing_quotas(test_db):
    """Running seed twice updates existing quotas instead of skipping."""
    from models.rbac import TierQuota

    seed_subscription_tiers(test_db)
    seed_tier_quotas(test_db)

    q = test_db.query(TierQuota).filter_by(
        tier_id="tier_starter", resource_type="documents"
    ).first()
    q.quota_limit = 999
    test_db.commit()

    seed_tier_quotas(test_db)
    test_db.refresh(q)
    assert q.quota_limit == 20


def test_enterprise_tier_price_unchanged(test_db):
    """Enterprise tier remains at CHF 149/month."""
    from models.rbac import SubscriptionTier

    seed_subscription_tiers(test_db)
    enterprise = test_db.query(SubscriptionTier).filter_by(id="tier_enterprise").first()
    assert float(enterprise.price_monthly) == 149.00


def test_professional_tier_unchanged(test_db):
    """Professional tier remains at CHF 49/month with same quotas."""
    from models.rbac import SubscriptionTier, TierQuota

    seed_subscription_tiers(test_db)
    seed_tier_quotas(test_db)

    pro = test_db.query(SubscriptionTier).filter_by(id="tier_professional").first()
    assert float(pro.price_monthly) == 49.00

    quotas = {
        q.resource_type: q.quota_limit
        for q in test_db.query(TierQuota).filter_by(tier_id="tier_professional").all()
    }
    assert quotas["documents"] == -1
    assert quotas["questions_per_month"] == 1000
    assert quotas["users"] == 10
    assert quotas["storage_mb"] == 10000
