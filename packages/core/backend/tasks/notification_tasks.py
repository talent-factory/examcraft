"""
Celery Tasks for Notifications & External Services
Handles async operations like newsletter subscriptions that may involve cold-starting services.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="tasks.notification_tasks.subscribe_to_newsletter",
    max_retries=5,
    default_retry_delay=10,
)
def subscribe_to_newsletter(
    email: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    user_id: Optional[str] = None,
    source: str = "email_verification",
) -> Dict[str, Any]:
    """
    Subscribe a user to the SubscribeFlow newsletter.

    Runs as a Celery task with retries to handle cold-starting services.
    Uses exponential backoff: 10s, 20s, 40s, 80s, 160s.

    Args:
        email: User's email address
        first_name: Optional first name
        last_name: Optional last name
        user_id: Optional ExamCraft user ID
        source: Subscription source for analytics

    Returns:
        Dict with subscription result
    """
    from services.subscribeflow_service import subscribeflow_service

    if not subscribeflow_service.is_available():
        logger.warning("SubscribeFlow not configured, skipping")
        return {"status": "skipped", "reason": "not_configured"}

    try:
        result = asyncio.run(
            subscribeflow_service.subscribe_user(
                email=email,
                first_name=first_name,
                last_name=last_name,
                user_id=user_id,
                source=source,
            )
        )
        logger.info(f"SubscribeFlow subscription for {email}: {result}")
        return result

    except Exception as exc:
        logger.warning(
            f"SubscribeFlow subscription attempt failed for {email}: {exc} "
            f"(retry {subscribe_to_newsletter.request.retries}/{subscribe_to_newsletter.max_retries})"
        )
        raise subscribe_to_newsletter.retry(exc=exc, countdown=10 * (2 ** subscribe_to_newsletter.request.retries))
