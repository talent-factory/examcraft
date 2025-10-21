"""
Feature Gate Middleware für ExamCraft AI
Ermöglicht Feature-basierte Zugriffskontrolle auf Basis des Subscription Tiers
"""

from functools import wraps
from typing import Callable, Optional
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

from backend.config.features import Feature, SubscriptionTier, has_feature, get_quota, is_unlimited
from backend.models.auth import User, Institution


class FeatureGateException(HTTPException):
    """Exception für Feature-Gate-Verletzungen"""

    def __init__(
        self,
        feature: Feature,
        user_tier: SubscriptionTier,
        required_tier: Optional[SubscriptionTier] = None
    ):
        detail = (
            f"Feature '{feature.value}' ist nicht in Ihrem aktuellen Plan "
            f"({user_tier.value}) verfügbar. "
        )

        if required_tier:
            detail += f"Bitte upgraden Sie auf '{required_tier.value}' oder höher."
        else:
            detail += "Bitte upgraden Sie Ihren Plan."

        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class QuotaExceededException(HTTPException):
    """Exception für Quota-Überschreitungen"""

    def __init__(
        self,
        quota_name: str,
        current_usage: int,
        limit: int,
        user_tier: SubscriptionTier
    ):
        detail = (
            f"Quota '{quota_name}' überschritten: "
            f"{current_usage}/{limit} verwendet. "
            f"Ihr aktueller Plan: {user_tier.value}. "
            f"Bitte upgraden Sie Ihren Plan für höhere Limits."
        )

        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail
        )


def get_user_tier(user: User) -> SubscriptionTier:
    """
    Ermittelt den Subscription Tier eines Users über seine Institution

    Args:
        user: User-Objekt

    Returns:
        SubscriptionTier
    """
    if not user.institution:
        return SubscriptionTier.FREE

    tier_value = user.institution.subscription_tier
    try:
        return SubscriptionTier(tier_value)
    except ValueError:
        # Fallback zu FREE bei ungültigen Werten
        return SubscriptionTier.FREE


def check_feature_access(user: User, feature: Feature) -> bool:
    """
    Prüft ob ein User Zugriff auf ein Feature hat

    Args:
        user: User-Objekt
        feature: Zu prüfendes Feature

    Returns:
        True wenn Zugriff erlaubt
    """
    tier = get_user_tier(user)
    return has_feature(tier, feature)


def require_feature(feature: Feature):
    """
    Decorator für FastAPI Endpoints - Feature-Zugriff erforderlich

    Usage:
        @router.post("/chatbot/query")
        @require_feature(Feature.DOCUMENT_CHATBOT)
        async def chatbot_query(
            user: User = Depends(get_current_user)
        ):
            ...

    Args:
        feature: Erforderliches Feature

    Raises:
        FeatureGateException: Wenn Feature nicht verfügbar
    """

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extrahiere User aus kwargs
            user = kwargs.get('user') or kwargs.get('current_user')

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            # Prüfe Feature-Zugriff
            if not check_feature_access(user, feature):
                tier = get_user_tier(user)
                raise FeatureGateException(feature, tier)

            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Extrahiere User aus kwargs
            user = kwargs.get('user') or kwargs.get('current_user')

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            # Prüfe Feature-Zugriff
            if not check_feature_access(user, feature):
                tier = get_user_tier(user)
                raise FeatureGateException(feature, tier)

            return func(*args, **kwargs)

        # Return async oder sync wrapper basierend auf Funktion
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def check_quota(
    user: User,
    quota_name: str,
    current_usage: int,
    increment: int = 1
) -> bool:
    """
    Prüft ob ein Quota-Limit überschritten würde

    Args:
        user: User-Objekt
        quota_name: Name des Quotas (z.B. "max_documents")
        current_usage: Aktuelle Nutzung
        increment: Geplante Erhöhung (default: 1)

    Returns:
        True wenn Quota erlaubt

    Raises:
        QuotaExceededException: Wenn Quota überschritten
    """
    tier = get_user_tier(user)

    # Prüfe ob unlimited
    if is_unlimited(tier, quota_name):
        return True

    limit = get_quota(tier, quota_name)
    new_usage = current_usage + increment

    if new_usage > limit:
        raise QuotaExceededException(quota_name, current_usage, limit, tier)

    return True


def require_quota(quota_name: str, increment: int = 1):
    """
    Decorator für FastAPI Endpoints - Quota-Check erforderlich

    Usage:
        @router.post("/documents/upload")
        @require_quota("max_documents")
        async def upload_document(
            user: User = Depends(get_current_user),
            db: Session = Depends(get_db)
        ):
            # current_usage wird automatisch ermittelt
            ...

    Args:
        quota_name: Name des Quotas
        increment: Geplante Erhöhung (default: 1)

    Raises:
        QuotaExceededException: Wenn Quota überschritten
    """

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            user = kwargs.get('user') or kwargs.get('current_user')
            db = kwargs.get('db')

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            # Ermittle current_usage basierend auf quota_name
            current_usage = get_current_usage(db, user, quota_name)

            # Prüfe Quota
            check_quota(user, quota_name, current_usage, increment)

            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            user = kwargs.get('user') or kwargs.get('current_user')
            db = kwargs.get('db')

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            # Ermittle current_usage basierend auf quota_name
            current_usage = get_current_usage(db, user, quota_name)

            # Prüfe Quota
            check_quota(user, quota_name, current_usage, increment)

            return func(*args, **kwargs)

        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def get_current_usage(db: Session, user: User, quota_name: str) -> int:
    """
    Ermittelt die aktuelle Nutzung für ein Quota

    Args:
        db: Database Session
        user: User-Objekt
        quota_name: Name des Quotas

    Returns:
        Aktuelle Nutzung (int)
    """
    # TODO: Implementierung basierend auf quota_name
    # Beispiel für max_documents:
    if quota_name == "max_documents":
        from backend.models.document import Document
        return db.query(Document).filter(
            Document.institution_id == user.institution_id
        ).count()

    elif quota_name == "max_users":
        return db.query(User).filter(
            User.institution_id == user.institution_id
        ).count()

    # Fallback
    return 0
