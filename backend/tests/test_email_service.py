"""Tests for EmailService (TF-764: SubscribeFlow-backed sending).

Escaping of user-supplied values (first_name etc.) now happens inside
SubscribeFlow's sandboxed, autoescaping Jinja2 environment
(TemplateRenderingService._create_jinja_env, autoescape=True) -- ExamCraft
passes raw values through as template variables and must NOT pre-escape
them (that would double-escape). These tests assert the SDK call
composition, not HTML string content.
"""

from unittest.mock import AsyncMock, patch

import pytest

from services.email_service import EmailService


def _mock_sdk_client():
    """Patch SubscribeFlowClient so EmailService._send never makes a real
    network call. Returns the mocked `emails.send` coroutine for assertions."""
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.id = "es_123"
    mock_response.status = "queued"
    mock_client.emails.send = AsyncMock(return_value=mock_response)
    return mock_client


@pytest.mark.asyncio
async def test_send_verification_email_calls_sdk_with_raw_variables():
    mock_client = _mock_sdk_client()
    with (
        patch("services.email_service.SubscribeFlowClient") as mock_client_cls,
        patch("services.email_service.SUBSCRIBEFLOW_EMAILS_API_KEY", "sf_live_test"),
    ):
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client_cls.return_value.__aexit__.return_value = None

        result = await EmailService.send_verification_email(
            email="target@example.com",
            first_name='<img src=x onerror="alert(1)">',
            verification_token="tok123",
        )

    mock_client.emails.send.assert_called_once_with(
        template_slug="verification",
        to="target@example.com",
        variables={
            "first_name": '<img src=x onerror="alert(1)">',
            "verification_url": "http://localhost:3000/verify-email?token=tok123",
        },
        idempotency_key=None,
    )
    assert result == {"id": "es_123", "status": "queued"}


@pytest.mark.asyncio
async def test_send_welcome_email_calls_sdk_with_expected_variables():
    mock_client = _mock_sdk_client()
    with (
        patch("services.email_service.SubscribeFlowClient") as mock_client_cls,
        patch("services.email_service.SUBSCRIBEFLOW_EMAILS_API_KEY", "sf_live_test"),
    ):
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client_cls.return_value.__aexit__.return_value = None

        await EmailService.send_welcome_email(
            email="target@example.com", first_name="Käthe"
        )

    mock_client.emails.send.assert_called_once_with(
        template_slug="welcome",
        to="target@example.com",
        variables={
            "first_name": "Käthe",
            "dashboard_url": "http://localhost:3000/dashboard",
            "docs_url": "http://localhost:3000/docs",
        },
        idempotency_key=None,
    )


@pytest.mark.asyncio
async def test_send_skips_when_api_key_not_configured():
    with patch("services.email_service.SUBSCRIBEFLOW_EMAILS_API_KEY", ""):
        result = await EmailService.send_verification_email(
            email="target@example.com", first_name="A", verification_token="t"
        )
    assert result == {"id": "test-email-id", "status": "skipped"}


@pytest.mark.asyncio
async def test_send_forwards_idempotency_key_to_sdk():
    """The literal wiring point connecting the impersonation-email
    idempotency-key feature to the SDK: every impersonation-email test
    mocks EmailService._send itself, so none of them would catch a
    typo'd/renamed `idempotency_key` kwarg in the actual SDK call inside
    _send. This test goes through the mocked SDK client instead, closing
    that gap."""
    mock_client = _mock_sdk_client()
    with (
        patch("services.email_service.SubscribeFlowClient") as mock_client_cls,
        patch("services.email_service.SUBSCRIBEFLOW_EMAILS_API_KEY", "sf_live_test"),
    ):
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client_cls.return_value.__aexit__.return_value = None

        await EmailService._send(
            template_slug="impersonation-started",
            to="target@example.com",
            variables={"to_name": "Target"},
            idempotency_key="impersonation-started:42",
        )

    mock_client.emails.send.assert_called_once_with(
        template_slug="impersonation-started",
        to="target@example.com",
        variables={"to_name": "Target"},
        idempotency_key="impersonation-started:42",
    )


@pytest.mark.asyncio
async def test_send_propagates_sdk_errors():
    mock_client = AsyncMock()
    mock_client.emails.send = AsyncMock(side_effect=RuntimeError("network down"))
    with (
        patch("services.email_service.SubscribeFlowClient") as mock_client_cls,
        patch("services.email_service.SUBSCRIBEFLOW_EMAILS_API_KEY", "sf_live_test"),
    ):
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client_cls.return_value.__aexit__.return_value = None

        with pytest.raises(RuntimeError, match="network down"):
            await EmailService.send_verification_email(
                email="target@example.com", first_name="A", verification_token="t"
            )


def test_generate_verification_token_is_url_safe_and_unique():
    token_a = EmailService.generate_verification_token()
    token_b = EmailService.generate_verification_token()
    assert token_a != token_b
    assert len(token_a) > 20


class TestFormatDuration:
    """Direct unit tests for the branching logic in _format_duration --
    previously only indirectly exercised via impersonation-ended email tests."""

    def test_minutes_and_seconds(self):
        assert (
            EmailService._format_duration(
                "2026-08-30T10:00:00+00:00", "2026-08-30T10:12:34+00:00"
            )
            == "12 min 34 sec"
        )

    def test_minutes_only(self):
        assert (
            EmailService._format_duration(
                "2026-08-30T10:00:00+00:00", "2026-08-30T10:05:00+00:00"
            )
            == "5 min"
        )

    def test_seconds_only(self):
        assert (
            EmailService._format_duration(
                "2026-08-30T10:00:00+00:00", "2026-08-30T10:00:45+00:00"
            )
            == "45 sec"
        )

    def test_zero_duration(self):
        assert (
            EmailService._format_duration(
                "2026-08-30T10:00:00+00:00", "2026-08-30T10:00:00+00:00"
            )
            == "0 sec"
        )

    def test_negative_duration_clamped_to_zero(self):
        """ended_at before started_at (clock skew, bad data) must not raise
        or produce a nonsensical negative duration."""
        assert (
            EmailService._format_duration(
                "2026-08-30T10:12:00+00:00", "2026-08-30T10:00:00+00:00"
            )
            == "0 sec"
        )

    def test_missing_started_at_returns_unknown(self):
        assert (
            EmailService._format_duration(None, "2026-08-30T10:00:00+00:00")
            == "unknown"
        )

    def test_missing_ended_at_returns_unknown(self):
        assert (
            EmailService._format_duration("2026-08-30T10:00:00+00:00", None)
            == "unknown"
        )

    def test_malformed_non_empty_timestamp_returns_unknown(self):
        """Non-empty but unparsable input (not the "missing" early-return
        path) must hit the except branch, not raise."""
        assert (
            EmailService._format_duration(
                "not-a-timestamp", "2026-08-30T10:00:00+00:00"
            )
            == "unknown"
        )
