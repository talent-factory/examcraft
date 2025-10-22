"""
Feature Flag Configuration für ExamCraft AI
Definiert Features pro Subscription Tier gemäß TF-116 Monetarisierungsstrategie
"""

from enum import Enum
from typing import Dict, List


class SubscriptionTier(str, Enum):
    """Subscription Tiers für Freemium-Modell"""

    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class Feature(str, Enum):
    """Verfügbare Features in ExamCraft AI"""

    # Core Features (Free Tier)
    DOCUMENT_UPLOAD = "document_upload"
    BASIC_QUESTION_GENERATION = "basic_question_generation"
    DOCUMENT_LIBRARY = "document_library"

    # Starter Tier Features
    RAG_GENERATION = "rag_generation"
    PROMPT_TEMPLATES = "prompt_templates"
    BATCH_PROCESSING = "batch_processing"

    # Professional Tier Features
    DOCUMENT_CHATBOT = "document_chatbot"  # TF-111
    ADVANCED_PROMPT_MANAGEMENT = "advanced_prompt_management"  # TF-122
    ANALYTICS_DASHBOARD = "analytics_dashboard"
    QUESTION_REVIEW_WORKFLOW = "question_review_workflow"  # TF-60
    EXPORT_FORMATS = "export_formats"

    # Enterprise Tier Features
    SSO_INTEGRATION = "sso_integration"
    CUSTOM_BRANDING = "custom_branding"
    API_ACCESS = "api_access"
    ADVANCED_ANALYTICS = "advanced_analytics"
    PRIORITY_SUPPORT = "priority_support"
    LDAP_INTEGRATION = "ldap_integration"
    AUDIT_LOGS = "audit_logs"
    MULTI_ORGANIZATION = "multi_organization"


# Feature-zu-Tier Mapping (aus TF-116)
TIER_FEATURES: Dict[SubscriptionTier, List[Feature]] = {
    SubscriptionTier.FREE: [
        Feature.DOCUMENT_UPLOAD,
        Feature.BASIC_QUESTION_GENERATION,
        Feature.DOCUMENT_LIBRARY,
    ],
    SubscriptionTier.STARTER: [
        # Free Features
        Feature.DOCUMENT_UPLOAD,
        Feature.BASIC_QUESTION_GENERATION,
        Feature.DOCUMENT_LIBRARY,
        # Starter Features
        Feature.RAG_GENERATION,
        Feature.PROMPT_TEMPLATES,
        Feature.BATCH_PROCESSING,
    ],
    SubscriptionTier.PROFESSIONAL: [
        # Free + Starter Features
        Feature.DOCUMENT_UPLOAD,
        Feature.BASIC_QUESTION_GENERATION,
        Feature.DOCUMENT_LIBRARY,
        Feature.RAG_GENERATION,
        Feature.PROMPT_TEMPLATES,
        Feature.BATCH_PROCESSING,
        # Professional Features
        Feature.DOCUMENT_CHATBOT,
        Feature.ADVANCED_PROMPT_MANAGEMENT,
        Feature.ANALYTICS_DASHBOARD,
        Feature.QUESTION_REVIEW_WORKFLOW,
        Feature.EXPORT_FORMATS,
    ],
    SubscriptionTier.ENTERPRISE: [
        # All Features
        Feature.DOCUMENT_UPLOAD,
        Feature.BASIC_QUESTION_GENERATION,
        Feature.DOCUMENT_LIBRARY,
        Feature.RAG_GENERATION,
        Feature.PROMPT_TEMPLATES,
        Feature.BATCH_PROCESSING,
        Feature.DOCUMENT_CHATBOT,
        Feature.ADVANCED_PROMPT_MANAGEMENT,
        Feature.ANALYTICS_DASHBOARD,
        Feature.QUESTION_REVIEW_WORKFLOW,
        Feature.EXPORT_FORMATS,
        # Enterprise Features
        Feature.SSO_INTEGRATION,
        Feature.CUSTOM_BRANDING,
        Feature.API_ACCESS,
        Feature.ADVANCED_ANALYTICS,
        Feature.PRIORITY_SUPPORT,
        Feature.LDAP_INTEGRATION,
        Feature.AUDIT_LOGS,
        Feature.MULTI_ORGANIZATION,
    ],
}


# Ressourcen-Quotas pro Tier (aus TF-116)
TIER_QUOTAS: Dict[SubscriptionTier, Dict[str, int]] = {
    SubscriptionTier.FREE: {
        "max_documents": 5,
        "max_questions_per_month": 20,
        "max_users": 1,
        "max_institutions": 1,
    },
    SubscriptionTier.STARTER: {
        "max_documents": 50,
        "max_questions_per_month": 200,
        "max_users": 3,
        "max_institutions": 1,
    },
    SubscriptionTier.PROFESSIONAL: {
        "max_documents": -1,  # Unlimited
        "max_questions_per_month": 1000,
        "max_users": 10,
        "max_institutions": 3,
    },
    SubscriptionTier.ENTERPRISE: {
        "max_documents": -1,  # Unlimited
        "max_questions_per_month": -1,  # Unlimited
        "max_users": -1,  # Unlimited
        "max_institutions": -1,  # Unlimited
    },
}


def get_tier_features(tier: SubscriptionTier) -> List[Feature]:
    """
    Gibt alle verfügbaren Features für einen Tier zurück

    Args:
        tier: Subscription Tier

    Returns:
        Liste der verfügbaren Features
    """
    return TIER_FEATURES.get(tier, TIER_FEATURES[SubscriptionTier.FREE])


def has_feature(tier: SubscriptionTier, feature: Feature) -> bool:
    """
    Prüft ob ein Feature in einem Tier verfügbar ist

    Args:
        tier: Subscription Tier
        feature: Zu prüfendes Feature

    Returns:
        True wenn Feature verfügbar, sonst False
    """
    return feature in get_tier_features(tier)


def get_quota(tier: SubscriptionTier, quota_name: str) -> int:
    """
    Gibt das Quota-Limit für einen Tier zurück

    Args:
        tier: Subscription Tier
        quota_name: Name des Quotas (z.B. "max_documents")

    Returns:
        Quota-Limit (-1 für unlimited)
    """
    quotas = TIER_QUOTAS.get(tier, TIER_QUOTAS[SubscriptionTier.FREE])
    return quotas.get(quota_name, 0)


def is_unlimited(tier: SubscriptionTier, quota_name: str) -> bool:
    """
    Prüft ob ein Quota unlimited ist

    Args:
        tier: Subscription Tier
        quota_name: Name des Quotas

    Returns:
        True wenn unlimited (-1)
    """
    return get_quota(tier, quota_name) == -1
