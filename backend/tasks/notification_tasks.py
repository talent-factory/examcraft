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
        raise subscribe_to_newsletter.retry(
            exc=exc, countdown=10 * (2**subscribe_to_newsletter.request.retries)
        )


@celery_app.task(
    name="tasks.notification_tasks.send_impersonation_ended_email",
    max_retries=5,
    default_retry_delay=10,
)
def send_impersonation_ended_email(
    to_email: str,
    to_name: str,
    admin_name: str,
    reason: str,
    started_at: Optional[str],
    ended_at: Optional[str],
    end_reason: str,
) -> Dict[str, Any]:
    """Notify an impersonation target after their session has ended (TF-742).

    Runs as a Celery task so a slow/unavailable email provider never blocks
    the request that closed the session (manual end, lost-token fallback,
    logout-while-impersonating, or the timeout reaper). Retries with
    exponential backoff, same pattern as ``subscribe_to_newsletter`` above.
    """
    from services.email_service import EmailService

    try:
        result = EmailService.send_impersonation_ended_email(
            to_email=to_email,
            to_name=to_name,
            admin_name=admin_name,
            reason=reason,
            started_at=started_at,
            ended_at=ended_at,
            end_reason=end_reason,
        )
        logger.info(f"Impersonation-ended email sent to {to_email}")
        return result

    except Exception as exc:
        logger.warning(
            f"Impersonation-ended email attempt failed for {to_email}: {exc} "
            f"(retry {send_impersonation_ended_email.request.retries}/"
            f"{send_impersonation_ended_email.max_retries})"
        )
        raise send_impersonation_ended_email.retry(
            exc=exc,
            countdown=10 * (2**send_impersonation_ended_email.request.retries),
        )
