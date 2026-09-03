"""
Celery Tasks for Notifications & External Services
Handles async operations like newsletter subscriptions that may involve cold-starting services.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

import httpx

from celery_app import celery_app

logger = logging.getLogger(__name__)

# Client errors from SubscribeFlow that retrying can never fix (bad
# credentials, unknown/renamed template slug, malformed variables, plan
# quota exceeded) -- distinct from network errors, 429, and 5xx, which
# genuinely can resolve on retry. Without this split, a permanent
# config/code bug (e.g. a renamed template slug, which has already
# happened once during TF-764 Phase A -> Phase B propagation) looks
# identical in the logs to a flaky network blip and burns through all 5
# retries before failing, instead of failing fast. 402 (plan limit
# exceeded) is included because a plan upgrade, not a retry, is what
# resolves it -- the ~310s total backoff window is far shorter than an
# operator reacting to a quota alert.
NON_RETRYABLE_SUBSCRIBEFLOW_STATUS_CODES = {400, 401, 402, 403, 404, 422}


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
    from subscribeflow.exceptions import SubscribeFlowError

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

    except SubscribeFlowError as exc:
        if exc.status in NON_RETRYABLE_SUBSCRIBEFLOW_STATUS_CODES:
            logger.error(
                f"SubscribeFlow subscription permanently failed for {email}: "
                f"SubscribeFlow returned {exc.status} ({exc}) -- not retrying, "
                "this looks like a config/code bug rather than a transient "
                "failure"
            )
            raise
        logger.warning(
            f"SubscribeFlow subscription attempt failed for {email}: {exc} "
            f"(retry {subscribe_to_newsletter.request.retries}/{subscribe_to_newsletter.max_retries})"
        )
        raise subscribe_to_newsletter.retry(
            exc=exc, countdown=10 * (2**subscribe_to_newsletter.request.retries)
        )
    except httpx.TransportError as exc:
        # Narrowed from a bare `except Exception`: this now only catches
        # transport-level failures (connect/read/write/pool timeouts,
        # connection errors) -- the genuinely transient class a retry can
        # actually fix. The SDK already converts every non-2xx HTTP
        # response into a SubscribeFlowError (handled above), so anything
        # else reaching here (TypeError, AttributeError, a bug in
        # SubscribeFlowService) is a real code/config problem that
        # retrying 5x would only delay discovering by ~310s, not fix --
        # let it propagate immediately instead.
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
    session_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Notify an impersonation target after their session has ended (TF-742).

    Runs as a Celery task so a slow/unavailable email provider never blocks
    the request that closed the session (manual end, lost-token fallback,
    logout-while-impersonating, or the timeout reaper). Retries with
    exponential backoff, same pattern as ``subscribe_to_newsletter`` above.

    ``session_id`` is forwarded to ``EmailService`` unchanged so its
    idempotency key can key off the impersonation session id rather than
    recipient+``started_at`` -- see its docstring.
    """
    from subscribeflow.exceptions import SubscribeFlowError

    from services.email_service import EmailService

    try:
        result = asyncio.run(
            EmailService.send_impersonation_ended_email(
                to_email=to_email,
                to_name=to_name,
                admin_name=admin_name,
                reason=reason,
                started_at=started_at,
                ended_at=ended_at,
                end_reason=end_reason,
                session_id=session_id,
            )
        )
        if result.get("status") == "skipped":
            logger.warning(
                f"Impersonation-ended email NOT sent to {to_email}: "
                "SUBSCRIBEFLOW_EMAILS_API_KEY not configured"
            )
        else:
            logger.info(f"Impersonation-ended email sent to {to_email}")
        return result

    except SubscribeFlowError as exc:
        if exc.status in NON_RETRYABLE_SUBSCRIBEFLOW_STATUS_CODES:
            logger.error(
                f"Impersonation-ended email permanently failed for {to_email}: "
                f"SubscribeFlow returned {exc.status} ({exc}) -- not retrying, "
                "this looks like a config/template bug rather than a transient "
                "failure"
            )
            raise
        logger.warning(
            f"Impersonation-ended email attempt failed for {to_email}: {exc} "
            f"(retry {send_impersonation_ended_email.request.retries}/"
            f"{send_impersonation_ended_email.max_retries})"
        )
        raise send_impersonation_ended_email.retry(
            exc=exc,
            countdown=10 * (2**send_impersonation_ended_email.request.retries),
        )
    except httpx.TransportError as exc:
        # See subscribe_to_newsletter's comment above: narrowed to
        # transport-level failures only, so a real code/config bug fails
        # fast instead of burning through 5 retries (~310s) first.
        logger.warning(
            f"Impersonation-ended email attempt failed for {to_email}: {exc} "
            f"(retry {send_impersonation_ended_email.request.retries}/"
            f"{send_impersonation_ended_email.max_retries})"
        )
        raise send_impersonation_ended_email.retry(
            exc=exc,
            countdown=10 * (2**send_impersonation_ended_email.request.retries),
        )


@celery_app.task(
    name="tasks.notification_tasks.send_impersonation_started_email",
    max_retries=5,
    default_retry_delay=10,
)
def send_impersonation_started_email(
    to_email: str,
    to_name: str,
    admin_name: str,
    reason: str,
    started_at: Optional[str],
    session_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Notify an impersonation target in real time that their session has
    just started (TF-759).

    Sibling of ``send_impersonation_ended_email`` above -- same Celery
    retry/backoff pattern, dispatched at session start instead of at
    session end so the target doesn't have to wait for the session to
    close to find out about it. ``session_id`` is forwarded unchanged, see
    that method's docstring.
    """
    from subscribeflow.exceptions import SubscribeFlowError

    from services.email_service import EmailService

    try:
        result = asyncio.run(
            EmailService.send_impersonation_started_email(
                to_email=to_email,
                to_name=to_name,
                admin_name=admin_name,
                reason=reason,
                started_at=started_at,
                session_id=session_id,
            )
        )
        if result.get("status") == "skipped":
            logger.warning(
                f"Impersonation-started email NOT sent to {to_email}: "
                "SUBSCRIBEFLOW_EMAILS_API_KEY not configured"
            )
        else:
            logger.info(f"Impersonation-started email sent to {to_email}")
        return result

    except SubscribeFlowError as exc:
        if exc.status in NON_RETRYABLE_SUBSCRIBEFLOW_STATUS_CODES:
            logger.error(
                f"Impersonation-started email permanently failed for {to_email}: "
                f"SubscribeFlow returned {exc.status} ({exc}) -- not retrying, "
                "this looks like a config/template bug rather than a transient "
                "failure"
            )
            raise
        logger.warning(
            f"Impersonation-started email attempt failed for {to_email}: {exc} "
            f"(retry {send_impersonation_started_email.request.retries}/"
            f"{send_impersonation_started_email.max_retries})"
        )
        raise send_impersonation_started_email.retry(
            exc=exc,
            countdown=10 * (2**send_impersonation_started_email.request.retries),
        )
    except httpx.TransportError as exc:
        # See subscribe_to_newsletter's comment above: narrowed to
        # transport-level failures only, so a real code/config bug fails
        # fast instead of burning through 5 retries (~310s) first.
        logger.warning(
            f"Impersonation-started email attempt failed for {to_email}: {exc} "
            f"(retry {send_impersonation_started_email.request.retries}/"
            f"{send_impersonation_started_email.max_retries})"
        )
        raise send_impersonation_started_email.retry(
            exc=exc,
            countdown=10 * (2**send_impersonation_started_email.request.retries),
        )
