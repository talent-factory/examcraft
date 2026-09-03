"""Tests for TF-759's impersonation-started notification email.

Sibling of ``test_impersonation_ended_email.py`` (TF-742). Since TF-764,
``EmailService`` sends via SubscribeFlow templates instead of constructing
HTML in Python -- these tests assert the ``variables`` dict passed to
``EmailService._send``, not HTML string content. Escaping of
``admin_name``/``to_name``/``reason`` is now SubscribeFlow's
autoescaping-Jinja2 responsibility (see ``test_email_service.py``'s
module docstring), not ExamCraft's.
"""

from unittest.mock import AsyncMock, patch

import pytest

from services.email_service import EmailService


@pytest.mark.asyncio
async def test_send_impersonation_started_email_builds_expected_variables():
    with patch.object(EmailService, "_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"id": "email_1", "status": "queued"}

        result = await EmailService.send_impersonation_started_email(
            to_email="target@example.com",
            to_name="Target User",
            admin_name="Admin Person",
            reason="Support-Anfrage TICKET-42",
            started_at="2026-08-31T10:00:00+00:00",
        )

        assert result == {"id": "email_1", "status": "queued"}
        mock_send.assert_called_once_with(
            template_slug="impersonation-started",
            to="target@example.com",
            variables={
                "to_name": "Target User",
                "admin_name": "Admin Person",
                "reason": "Support-Anfrage TICKET-42",
                "started_at": "2026-08-31T10:00:00+00:00",
            },
            idempotency_key="impersonation-started:target@example.com:2026-08-31T10:00:00+00:00",
        )


@pytest.mark.asyncio
async def test_send_impersonation_started_email_handles_missing_started_at():
    """Defensive: must never raise, worst case passes "unknown" through."""
    with patch.object(EmailService, "_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"id": "email_3", "status": "queued"}

        await EmailService.send_impersonation_started_email(
            to_email="target@example.com",
            to_name="Target User",
            admin_name="Admin Person",
            reason="r",
            started_at=None,
        )

        mock_send.assert_called_once()
        assert mock_send.call_args.kwargs["variables"]["started_at"] == "unknown"
        assert (
            mock_send.call_args.kwargs["idempotency_key"]
            == "impersonation-started:target@example.com:unknown"
        )


@pytest.mark.asyncio
async def test_send_impersonation_started_email_prefers_session_id_for_idempotency_key():
    """session_id is unconditionally unique (unlike started_at, which is
    optional) -- when given, it must be the idempotency key, not just
    appended to the old scheme."""
    with patch.object(EmailService, "_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"id": "email_2", "status": "queued"}

        await EmailService.send_impersonation_started_email(
            to_email="target@example.com",
            to_name="Target User",
            admin_name="Admin Person",
            reason="r",
            started_at="2026-08-31T10:00:00+00:00",
            session_id=42,
        )

        assert (
            mock_send.call_args.kwargs["idempotency_key"] == "impersonation-started:42"
        )


@pytest.mark.asyncio
async def test_send_impersonation_started_email_idempotency_key_is_stable_and_distinct():
    """Property, not a hardcoded literal: two calls describing the same
    logical event (a Celery retry) must produce the SAME key, and two
    calls describing different events must produce DIFFERENT keys --
    across both the session_id-based and the legacy fallback scheme."""
    with patch.object(EmailService, "_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"id": "x", "status": "queued"}

        async def _dispatch(*, session_id=None, to_email="target@example.com"):
            await EmailService.send_impersonation_started_email(
                to_email=to_email,
                to_name="Target User",
                admin_name="Admin Person",
                reason="r",
                started_at="2026-08-31T10:00:00+00:00",
                session_id=session_id,
            )
            return mock_send.call_args.kwargs["idempotency_key"]

        # Same session_id, simulating a Celery retry of the same event -> same key.
        key_a1 = await _dispatch(session_id=42)
        key_a2 = await _dispatch(session_id=42)
        assert key_a1 == key_a2

        # Different session_id -> different key.
        key_b = await _dispatch(session_id=43)
        assert key_b != key_a1

        # Without a session_id (legacy fallback): same recipient+started_at
        # retried -> same key; different recipient -> different key.
        key_c1 = await _dispatch(session_id=None, to_email="a@example.com")
        key_c2 = await _dispatch(session_id=None, to_email="a@example.com")
        assert key_c1 == key_c2
        key_d = await _dispatch(session_id=None, to_email="b@example.com")
        assert key_d != key_c1


@pytest.mark.asyncio
async def test_send_impersonation_started_email_passes_raw_unescaped_values():
    """Values reach the SDK raw -- SubscribeFlow's template rendering
    escapes them, ExamCraft must not pre-escape (would double-escape)."""
    with patch.object(EmailService, "_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"id": "email_4", "status": "queued"}

        malicious_reason = '<a href="https://evil.example/reset">click</a>'

        await EmailService.send_impersonation_started_email(
            to_email="target@example.com",
            to_name="Target User",
            admin_name="Admin Person",
            reason=malicious_reason,
            started_at="2026-08-31T10:00:00+00:00",
        )

        assert mock_send.call_args.kwargs["variables"]["reason"] == malicious_reason


def test_impersonation_email_tasks_are_registered_and_routed():
    """Review-fix regression guard (TF-759): both impersonation
    notification tasks were previously unreachable in production --
    ``tasks.notification_tasks`` was missing from ``celery_app``'s
    ``include`` list and neither task had a ``task_routes`` entry."""
    from celery_app import celery_app

    assert "tasks.notification_tasks" in celery_app.conf.include, (
        "tasks.notification_tasks is missing from celery_app.py's "
        "`include` list -- the worker never imports it, so none of its "
        "tasks are registered at all"
    )
    celery_app.loader.import_default_modules()

    consumed_queues = {
        "document_processing",
        "rag_embedding",
        "question_generation",
        "notifications",
        "import_processing",
        "maintenance_processing",
    }

    for name in (
        "tasks.notification_tasks.send_impersonation_started_email",
        "tasks.notification_tasks.send_impersonation_ended_email",
    ):
        assert name in celery_app.tasks, (
            f"{name} isn't registered even after import_default_modules() -- "
            "is the @celery_app.task `name=` wrong?"
        )
        route = celery_app.conf.task_routes.get(name)
        assert route is not None, (
            f"{name} has no task_routes entry -- it would land on the "
            "unconsumed default 'celery' queue and never run"
        )
        assert route["queue"] in consumed_queues, (
            f"{name} is routed to queue {route['queue']!r}, which no "
            "worker command actually consumes"
        )


def test_celery_task_retries_on_retryable_subscribeflow_error():
    """A transient SubscribeFlow failure (network/5xx) must go through the
    normal Celery retry path -- this is the reliability guarantee the
    idempotency key exists for, and was previously entirely untested."""
    from subscribeflow.exceptions import SubscribeFlowError
    from tasks.notification_tasks import send_impersonation_started_email

    exc = SubscribeFlowError("upstream down", status=503)
    with (
        patch.object(
            EmailService,
            "send_impersonation_started_email",
            new_callable=AsyncMock,
            side_effect=exc,
        ),
        patch.object(
            send_impersonation_started_email, "retry", side_effect=exc
        ) as mock_retry,
    ):
        with pytest.raises(SubscribeFlowError):
            send_impersonation_started_email.run(
                to_email="target@example.com",
                to_name="Target User",
                admin_name="Admin Person",
                reason="r",
                started_at="2026-08-31T10:00:00+00:00",
                session_id=42,
            )

    mock_retry.assert_called_once()
    assert mock_retry.call_args.kwargs["exc"] is exc


def test_celery_task_does_not_retry_on_non_retryable_subscribeflow_error():
    """A permanent client error (e.g. 404 for a renamed template slug) must
    NOT be retried -- retrying 5x would only delay and mask a config bug."""
    from subscribeflow.exceptions import NotFoundError
    from tasks.notification_tasks import send_impersonation_started_email

    exc = NotFoundError("template not found", status=404)
    with (
        patch.object(
            EmailService,
            "send_impersonation_started_email",
            new_callable=AsyncMock,
            side_effect=exc,
        ),
        patch.object(send_impersonation_started_email, "retry") as mock_retry,
    ):
        with pytest.raises(NotFoundError):
            send_impersonation_started_email.run(
                to_email="target@example.com",
                to_name="Target User",
                admin_name="Admin Person",
                reason="r",
                started_at="2026-08-31T10:00:00+00:00",
            )

    mock_retry.assert_not_called()


def test_celery_task_retries_on_transient_httpx_error():
    """A raw transport-level failure (not wrapped in a SubscribeFlowError,
    since the SDK only wraps non-2xx HTTP responses) must still go through
    the normal Celery retry path."""
    import httpx
    from tasks.notification_tasks import send_impersonation_started_email

    exc = httpx.ReadTimeout("read timed out")
    with (
        patch.object(
            EmailService,
            "send_impersonation_started_email",
            new_callable=AsyncMock,
            side_effect=exc,
        ),
        patch.object(
            send_impersonation_started_email, "retry", side_effect=exc
        ) as mock_retry,
    ):
        with pytest.raises(httpx.ReadTimeout):
            send_impersonation_started_email.run(
                to_email="target@example.com",
                to_name="Target User",
                admin_name="Admin Person",
                reason="r",
                started_at="2026-08-31T10:00:00+00:00",
                session_id=42,
            )

    mock_retry.assert_called_once()
    assert mock_retry.call_args.kwargs["exc"] is exc


def test_celery_task_does_not_retry_on_unexpected_bug():
    """A bug unrelated to network/API errors must propagate immediately,
    not be treated like a flaky network blip and retried 5x (~310s) --
    narrowing `except Exception` to `except httpx.TransportError` is what
    this test locks in."""
    from tasks.notification_tasks import send_impersonation_started_email

    exc = AttributeError("'NoneType' object has no attribute 'id'")
    with (
        patch.object(
            EmailService,
            "send_impersonation_started_email",
            new_callable=AsyncMock,
            side_effect=exc,
        ),
        patch.object(send_impersonation_started_email, "retry") as mock_retry,
    ):
        with pytest.raises(AttributeError):
            send_impersonation_started_email.run(
                to_email="target@example.com",
                to_name="Target User",
                admin_name="Admin Person",
                reason="r",
                started_at="2026-08-31T10:00:00+00:00",
            )

    mock_retry.assert_not_called()


def test_celery_task_does_not_retry_on_limit_exceeded_error():
    """A plan-quota error (402) is the same class of 'retrying can never
    fix this within the retry window' problem as a 404/422 config bug."""
    from subscribeflow.exceptions import LimitExceededError
    from tasks.notification_tasks import send_impersonation_started_email

    exc = LimitExceededError("plan email quota exceeded", status=402)
    with (
        patch.object(
            EmailService,
            "send_impersonation_started_email",
            new_callable=AsyncMock,
            side_effect=exc,
        ),
        patch.object(send_impersonation_started_email, "retry") as mock_retry,
    ):
        with pytest.raises(LimitExceededError):
            send_impersonation_started_email.run(
                to_email="target@example.com",
                to_name="Target User",
                admin_name="Admin Person",
                reason="r",
                started_at="2026-08-31T10:00:00+00:00",
            )

    mock_retry.assert_not_called()


def test_celery_task_logs_warning_and_does_not_raise_when_email_skipped():
    """EmailService._send returns {"status": "skipped"} (no exception) when
    SUBSCRIBEFLOW_EMAILS_API_KEY isn't configured -- the task must log this
    loudly instead of logging the same "sent" line it would for a real
    send.

    Patches the module logger directly rather than using caplog: caplog
    relies on propagation from the named logger to the root logger, which
    is unreliable across the full backend test suite (some other test/
    module disables propagation depending on run order) -- see
    project_caplog_propagation_full_suite. Patching the logger call is
    immune to that.
    """
    from tasks.notification_tasks import send_impersonation_started_email

    with (
        patch.object(
            EmailService,
            "send_impersonation_started_email",
            new_callable=AsyncMock,
            return_value={"id": "test-email-id", "status": "skipped"},
        ),
        patch("tasks.notification_tasks.logger") as mock_logger,
    ):
        result = send_impersonation_started_email.run(
            to_email="target@example.com",
            to_name="Target User",
            admin_name="Admin Person",
            reason="r",
            started_at="2026-08-31T10:00:00+00:00",
        )

    assert result == {"id": "test-email-id", "status": "skipped"}
    warning_text = "\n".join(
        str(arg) for call in mock_logger.warning.call_args_list for arg in call.args
    )
    assert "NOT sent" in warning_text, (
        "a skipped send must be logged as a warning, not as a misleading 'sent' info line"
    )
    info_text = "\n".join(
        str(arg) for call in mock_logger.info.call_args_list for arg in call.args
    )
    assert "Impersonation-started email sent" not in info_text


def test_celery_task_delegates_to_email_service():
    from tasks.notification_tasks import send_impersonation_started_email

    with patch.object(
        EmailService, "send_impersonation_started_email", new_callable=AsyncMock
    ) as mock_send:
        mock_send.return_value = {"id": "email_5", "status": "queued"}

        result = send_impersonation_started_email.run(
            to_email="target@example.com",
            to_name="Target User",
            admin_name="Admin Person",
            reason="r",
            started_at="2026-08-31T10:00:00+00:00",
            session_id=42,
        )

        assert result == {"id": "email_5", "status": "queued"}
        mock_send.assert_called_once_with(
            to_email="target@example.com",
            to_name="Target User",
            admin_name="Admin Person",
            reason="r",
            started_at="2026-08-31T10:00:00+00:00",
            session_id=42,
        )
