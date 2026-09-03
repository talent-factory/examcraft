"""Tests for tasks/notification_tasks.py's subscribe_to_newsletter task.

Sibling coverage to test_impersonation_ended_email.py /
test_impersonation_started_email.py's Celery-retry-classification tests --
subscribe_to_newsletter calls into the same SubscribeFlow SDK (via
SubscribeFlowService.subscribe_user) and so is exposed to the same
NON_RETRYABLE_SUBSCRIBEFLOW_STATUS_CODES split, but (unlike the two
impersonation tasks) previously had no dedicated test coverage at all.
"""

from unittest.mock import AsyncMock, patch

import pytest

from services.subscribeflow_service import SubscribeFlowService


def test_subscribe_to_newsletter_retries_on_retryable_subscribeflow_error():
    """A transient SubscribeFlow failure (network/5xx) must go through the
    normal Celery retry path."""
    from subscribeflow.exceptions import SubscribeFlowError
    from tasks.notification_tasks import subscribe_to_newsletter

    exc = SubscribeFlowError("upstream down", status=503)
    with (
        patch.object(SubscribeFlowService, "is_available", return_value=True),
        patch.object(
            SubscribeFlowService,
            "subscribe_user",
            new_callable=AsyncMock,
            side_effect=exc,
        ),
        patch.object(subscribe_to_newsletter, "retry", side_effect=exc) as mock_retry,
    ):
        with pytest.raises(SubscribeFlowError):
            subscribe_to_newsletter.run(email="user@example.com")

    mock_retry.assert_called_once()
    assert mock_retry.call_args.kwargs["exc"] is exc


def test_subscribe_to_newsletter_does_not_retry_on_non_retryable_subscribeflow_error():
    """A permanent client error (e.g. 404) must NOT be retried -- retrying
    5x would only delay and mask a config bug, exactly the problem
    NON_RETRYABLE_SUBSCRIBEFLOW_STATUS_CODES exists to catch."""
    from subscribeflow.exceptions import NotFoundError
    from tasks.notification_tasks import subscribe_to_newsletter

    exc = NotFoundError("tag not found", status=404)
    with (
        patch.object(SubscribeFlowService, "is_available", return_value=True),
        patch.object(
            SubscribeFlowService,
            "subscribe_user",
            new_callable=AsyncMock,
            side_effect=exc,
        ),
        patch.object(subscribe_to_newsletter, "retry") as mock_retry,
    ):
        with pytest.raises(NotFoundError):
            subscribe_to_newsletter.run(email="user@example.com")

    mock_retry.assert_not_called()


def test_subscribe_to_newsletter_retries_on_transient_httpx_error():
    """A raw transport-level failure (connect/read timeout, connection
    error) -- not wrapped in a SubscribeFlowError, since the SDK only
    wraps non-2xx HTTP responses -- must still go through the normal
    Celery retry path."""
    import httpx
    from tasks.notification_tasks import subscribe_to_newsletter

    exc = httpx.ConnectTimeout("connection timed out")
    with (
        patch.object(SubscribeFlowService, "is_available", return_value=True),
        patch.object(
            SubscribeFlowService,
            "subscribe_user",
            new_callable=AsyncMock,
            side_effect=exc,
        ),
        patch.object(subscribe_to_newsletter, "retry", side_effect=exc) as mock_retry,
    ):
        with pytest.raises(httpx.ConnectTimeout):
            subscribe_to_newsletter.run(email="user@example.com")

    mock_retry.assert_called_once()
    assert mock_retry.call_args.kwargs["exc"] is exc


def test_subscribe_to_newsletter_does_not_retry_on_unexpected_bug():
    """A bug unrelated to network/API errors (e.g. a TypeError from a
    renamed kwarg) must propagate immediately, not be treated like a
    flaky network blip and retried 5x (~310s) before finally failing --
    narrowing `except Exception` to `except httpx.TransportError` is what
    this test locks in."""
    from tasks.notification_tasks import subscribe_to_newsletter

    exc = TypeError("subscribe_user() got an unexpected keyword argument")
    with (
        patch.object(SubscribeFlowService, "is_available", return_value=True),
        patch.object(
            SubscribeFlowService,
            "subscribe_user",
            new_callable=AsyncMock,
            side_effect=exc,
        ),
        patch.object(subscribe_to_newsletter, "retry") as mock_retry,
    ):
        with pytest.raises(TypeError):
            subscribe_to_newsletter.run(email="user@example.com")

    mock_retry.assert_not_called()


def test_subscribe_to_newsletter_does_not_retry_on_limit_exceeded_error():
    """A plan-quota error (402) needs an upgrade, not a retry."""
    from subscribeflow.exceptions import LimitExceededError
    from tasks.notification_tasks import subscribe_to_newsletter

    exc = LimitExceededError("plan subscriber quota exceeded", status=402)
    with (
        patch.object(SubscribeFlowService, "is_available", return_value=True),
        patch.object(
            SubscribeFlowService,
            "subscribe_user",
            new_callable=AsyncMock,
            side_effect=exc,
        ),
        patch.object(subscribe_to_newsletter, "retry") as mock_retry,
    ):
        with pytest.raises(LimitExceededError):
            subscribe_to_newsletter.run(email="user@example.com")

    mock_retry.assert_not_called()
