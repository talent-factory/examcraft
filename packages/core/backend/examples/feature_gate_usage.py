"""
Beispiele für Feature-Gate-Nutzung in ExamCraft AI
Zeigt verschiedene Patterns für Feature-Gating und Quota-Checks

HINWEIS: Diese Datei ist nur ein Beispiel und wird nicht im Production-Code verwendet.
Die Imports get_current_user und get_db sind absichtlich nicht definiert (# noqa: F821).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.models.auth import User
from backend.config.features import Feature
from backend.middleware.feature_gate import (
    require_feature,
    require_quota,
    check_feature_access,
    get_user_tier,
)

# Beispiel Router
router = APIRouter(prefix="/api/v1/examples", tags=["examples"])


# BEISPIEL 1: Feature-Gate via Decorator
@router.post("/chatbot/query")
@require_feature(Feature.DOCUMENT_CHATBOT)
async def chatbot_query(
    query: str,
    user: User = Depends(get_current_user),  # type: ignore  # noqa: F821
):
    """
    ChatBot-Endpoint - nur für Professional+ Tier

    Raises:
        FeatureGateException: Wenn User nicht Professional+ ist
    """
    # Feature-Check ist bereits via Decorator erfolgt
    # Implementierung...
    return {"response": "ChatBot response", "tier": get_user_tier(user).value}


# BEISPIEL 2: Feature-Gate manuell prüfen
@router.get("/analytics/dashboard")
async def analytics_dashboard(
    user: User = Depends(get_current_user),  # type: ignore  # noqa: F821
):
    """
    Analytics Dashboard - zeigt unterschiedliche Daten je nach Tier
    """
    tier = get_user_tier(user)

    # Basic Analytics für alle
    basic_data = {"documents_count": 10, "questions_generated": 50}

    # Advanced Analytics nur für Professional+
    if check_feature_access(user, Feature.ANALYTICS_DASHBOARD):
        advanced_data = {
            **basic_data,
            "conversion_rate": 0.85,
            "user_engagement": 0.72,
            "trending_topics": ["AI", "Python", "FastAPI"],
        }
        return {"tier": tier.value, "data": advanced_data}

    return {"tier": tier.value, "data": basic_data}


# BEISPIEL 3: Quota-Check via Decorator
@router.post("/documents/upload")
@require_quota("max_documents")
async def upload_document(
    file: bytes,
    user: User = Depends(get_current_user),  # type: ignore  # noqa: F821
    db: Session = Depends(get_db),  # type: ignore  # noqa: F821
):
    """
    Document Upload - mit automatischem Quota-Check

    Raises:
        QuotaExceededException: Wenn max_documents überschritten
    """
    # Quota-Check ist bereits via Decorator erfolgt
    # Implementierung...
    return {"message": "Document uploaded", "tier": get_user_tier(user).value}


# BEISPIEL 4: Feature-basiertes Routing
@router.get("/features/available")
async def get_available_features(
    user: User = Depends(get_current_user),  # type: ignore  # noqa: F821
):
    """
    Zeigt alle verfügbaren Features für den aktuellen User
    """
    from backend.config.features import get_tier_features, TIER_QUOTAS

    tier = get_user_tier(user)
    features = get_tier_features(tier)
    quotas = TIER_QUOTAS[tier]

    return {
        "tier": tier.value,
        "features": [f.value for f in features],
        "quotas": quotas,
    }


# BEISPIEL 5: Upgrade-Prompt bei Feature-Gate
@router.post("/premium-feature")
async def premium_feature(
    user: User = Depends(get_current_user),  # type: ignore  # noqa: F821
):
    """
    Zeigt Upgrade-Prompt wenn Feature nicht verfügbar
    """
    required_feature = Feature.ADVANCED_PROMPT_MANAGEMENT

    if not check_feature_access(user, required_feature):
        tier = get_user_tier(user)

        # Empfehle passenden Tier
        recommended_tier = "professional"
        if tier == "free":
            recommended_tier = "starter"

        raise HTTPException(
            status_code=403,
            detail={
                "error": "feature_not_available",
                "feature": required_feature.value,
                "current_tier": tier.value,
                "recommended_tier": recommended_tier,
                "upgrade_url": f"/pricing?upgrade_to={recommended_tier}",
                "message": f"Upgrade auf '{recommended_tier}' um dieses Feature freizuschalten",
            },
        )

    # Feature ist verfügbar - Implementierung
    return {"message": "Premium feature executed"}


# BEISPIEL 6: Kombination Feature-Gate + Quota-Check
@router.post("/batch-generation")
@require_feature(Feature.BATCH_PROCESSING)
async def batch_generation(
    count: int,
    user: User = Depends(get_current_user),  # type: ignore  # noqa: F821
    db: Session = Depends(get_db),  # type: ignore  # noqa: F821
):
    """
    Batch-Generierung - Feature-Gate + manueller Quota-Check
    """
    from backend.middleware.feature_gate import check_quota, get_current_usage

    # Manuelle Quota-Prüfung für mehrere Items
    current_usage = get_current_usage(db, user, "max_questions_per_month")
    check_quota(user, "max_questions_per_month", current_usage, increment=count)

    # Implementierung...
    return {
        "message": f"{count} questions generated",
        "tier": get_user_tier(user).value,
    }


# Dummy-Dependencies für Beispiele
async def get_current_user():
    """Dummy für Beispiel - nutze echte Auth in Production"""
    pass


async def get_db():
    """Dummy für Beispiel - nutze echte DB in Production"""
    pass
