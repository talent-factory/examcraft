"""Tests for TF-742's impersonation-ended notification email.

``EmailService.send_impersonation_ended_email`` (``services/email_service.py``
-- the flat, actually-wired module used by ``api/auth.py``, not the parallel
``services/email/`` package) and the Celery task that wraps it
(``tasks.notification_tasks.send_impersonation_ended_email``).
"""

from unittest.mock import patch

from services.email_service import EmailService


def test_send_impersonation_ended_email_builds_expected_content():
    with patch.object(EmailService, "_send_email") as mock_send:
        mock_send.return_value = {"id": "email_1"}

        result = EmailService.send_impersonation_ended_email(
            to_email="target@example.com",
            to_name="Target User",
            admin_name="Admin Person",
            reason="Support-Anfrage TICKET-42",
            started_at="2026-08-30T10:00:00+00:00",
            ended_at="2026-08-30T10:12:00+00:00",
            end_reason="manual",
        )

        assert result == {"id": "email_1"}
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        assert call_kwargs["to"] == "target@example.com"
        assert "Admin Person" in call_kwargs["html"]
        assert "Support-Anfrage TICKET-42" in call_kwargs["html"]
        assert "Target User" in call_kwargs["html"]
        assert "Admin Person" in call_kwargs["text"]
        assert call_kwargs["tags"] == {"type": "impersonation_ended"}


def test_send_impersonation_ended_email_mentions_timeout_reason():
    with patch.object(EmailService, "_send_email") as mock_send:
        mock_send.return_value = {"id": "email_2"}

        EmailService.send_impersonation_ended_email(
            to_email="target@example.com",
            to_name="Target User",
            admin_name="Admin Person",
            reason="stuck session",
            started_at="2026-08-30T10:00:00+00:00",
            ended_at="2026-08-30T10:30:00+00:00",
            end_reason="timeout",
        )

        html = mock_send.call_args.kwargs["html"]
        assert "30" in html or "automatically" in html.lower()


def test_send_impersonation_ended_email_handles_missing_timestamps():
    """The reaper / fallback paths may not always have a clean ISO string
    (defensive: this must never raise, worst case shows "unknown")."""
    with patch.object(EmailService, "_send_email") as mock_send:
        mock_send.return_value = {"id": "email_3"}

        EmailService.send_impersonation_ended_email(
            to_email="target@example.com",
            to_name="Target User",
            admin_name="Admin Person",
            reason="r",
            started_at=None,
            ended_at=None,
            end_reason="manual",
        )

        mock_send.assert_called_once()


def test_send_impersonation_ended_email_escapes_html_in_admin_supplied_reason():
    """TF-742 review fix: ``reason`` is free text (3-500 chars, no
    character restriction -- see ``ImpersonateRequest`` in ``api/admin.py``)
    typed by the *impersonating admin* and delivered inside a trusted-
    looking ExamCraft security notice to a *different* user (the
    impersonation target). Without escaping, an admin could embed markup
    or a link into that notice. ``to_name``/``admin_name`` carry the same
    risk. The plain-text body can't render markup and is intentionally
    left unescaped."""
    with patch.object(EmailService, "_send_email") as mock_send:
        mock_send.return_value = {"id": "email_5"}

        malicious_reason = '<a href="https://evil.example/reset">click</a>'

        EmailService.send_impersonation_ended_email(
            to_email="target@example.com",
            to_name="Target User",
            admin_name="Admin Person",
            reason=malicious_reason,
            started_at="2026-08-30T10:00:00+00:00",
            ended_at="2026-08-30T10:12:00+00:00",
            end_reason="manual",
        )

        html = mock_send.call_args.kwargs["html"]
        assert "<a href=" not in html
        assert "&lt;a href=" in html
        assert "&lt;/a&gt;" in html
        # The plain-text alternative needs no escaping -- it can't render
        # markup -- so the raw reason is expected there.
        text = mock_send.call_args.kwargs["text"]
        assert malicious_reason in text


def test_celery_task_delegates_to_email_service():
    from tasks.notification_tasks import send_impersonation_ended_email

    with patch.object(EmailService, "send_impersonation_ended_email") as mock_send:
        mock_send.return_value = {"id": "email_4"}

        result = send_impersonation_ended_email.run(
            to_email="target@example.com",
            to_name="Target User",
            admin_name="Admin Person",
            reason="r",
            started_at="2026-08-30T10:00:00+00:00",
            ended_at="2026-08-30T10:12:00+00:00",
            end_reason="manual",
        )

        assert result == {"id": "email_4"}
        mock_send.assert_called_once_with(
            to_email="target@example.com",
            to_name="Target User",
            admin_name="Admin Person",
            reason="r",
            started_at="2026-08-30T10:00:00+00:00",
            ended_at="2026-08-30T10:12:00+00:00",
            end_reason="manual",
        )
