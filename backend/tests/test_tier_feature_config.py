"""
Tests for Tier-Feature configuration.

Ensures that RAG generation is available for ALL tiers (including Free),
and that tier feature sets are consistent (each higher tier includes
all features of the lower tiers).
"""

import pytest
from config.features import (
    Feature,
    SubscriptionTier,
    has_feature,
    get_tier_features,
)


class TestRAGAvailableForAllTiers:
    """RAG must be a core feature available to every tier."""

    @pytest.mark.parametrize(
        "tier",
        [
            SubscriptionTier.FREE,
            SubscriptionTier.STARTER,
            SubscriptionTier.PROFESSIONAL,
            SubscriptionTier.ENTERPRISE,
        ],
    )
    def test_rag_generation_available(self, tier):
        assert has_feature(tier, Feature.RAG_GENERATION), (
            f"RAG_GENERATION must be available for {tier.value} tier"
        )


class TestTierFeatureHierarchy:
    """Each higher tier must include all features of the tier below it."""

    TIER_ORDER = [
        SubscriptionTier.FREE,
        SubscriptionTier.STARTER,
        SubscriptionTier.PROFESSIONAL,
        SubscriptionTier.ENTERPRISE,
    ]

    def test_starter_includes_all_free_features(self):
        free = set(get_tier_features(SubscriptionTier.FREE))
        starter = set(get_tier_features(SubscriptionTier.STARTER))
        missing = free - starter
        assert not missing, (
            f"Starter tier is missing Free features: {missing}"
        )

    def test_professional_includes_all_starter_features(self):
        starter = set(get_tier_features(SubscriptionTier.STARTER))
        professional = set(get_tier_features(SubscriptionTier.PROFESSIONAL))
        missing = starter - professional
        assert not missing, (
            f"Professional tier is missing Starter features: {missing}"
        )

    def test_enterprise_includes_all_professional_features(self):
        professional = set(get_tier_features(SubscriptionTier.PROFESSIONAL))
        enterprise = set(get_tier_features(SubscriptionTier.ENTERPRISE))
        missing = professional - enterprise
        assert not missing, (
            f"Enterprise tier is missing Professional features: {missing}"
        )


class TestCoreFeatures:
    """Core features must be present in the Free tier."""

    @pytest.mark.parametrize(
        "feature",
        [
            Feature.DOCUMENT_UPLOAD,
            Feature.BASIC_QUESTION_GENERATION,
            Feature.DOCUMENT_LIBRARY,
            Feature.RAG_GENERATION,
        ],
    )
    def test_core_feature_in_free_tier(self, feature):
        assert has_feature(SubscriptionTier.FREE, feature), (
            f"{feature.value} must be a core feature (available in Free tier)"
        )
