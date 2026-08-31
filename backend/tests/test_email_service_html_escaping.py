"""Tests for TF-762: HTML escaping of user-supplied values in
``EmailService`` (``services/email_service.py`` -- the flat, actually-wired
module used by ``api/auth.py``, not the parallel ``services/email/``
package).

``send_impersonation_ended_email`` was already fixed as a TF-742 review
follow-up (see ``test_impersonation_ended_email.py``). This file covers the
two functions that carried the same unescaped-interpolation pattern and
had no existing tests at all: ``send_verification_email`` and
``send_welcome_email``, both of which interpolate the user-supplied
``first_name`` (set freely at registration) directly into the HTML body.
"""

from unittest.mock import patch

from services.email_service import EmailService

MALICIOUS_FIRST_NAME = '<img src=x onerror="alert(document.cookie)">'


def test_send_verification_email_escapes_html_in_first_name():
    with patch.object(EmailService, "_send_email") as mock_send:
        mock_send.return_value = {"id": "email_1"}

        EmailService.send_verification_email(
            email="target@example.com",
            first_name=MALICIOUS_FIRST_NAME,
            verification_token="tok123",
        )

        html = mock_send.call_args.kwargs["html"]
        # No literal "<img" tag start survives -- the browser/email client
        # never sees a real element, just inert escaped text.
        assert "<img src=x" not in html
        assert "&lt;img src=x" in html
        # Plain-text alternative can't render markup -- unescaped is fine.
        text = mock_send.call_args.kwargs["text"]
        assert MALICIOUS_FIRST_NAME in text


def test_send_verification_email_still_shows_plain_first_name():
    """The escape must not corrupt ordinary names."""
    with patch.object(EmailService, "_send_email") as mock_send:
        mock_send.return_value = {"id": "email_2"}

        EmailService.send_verification_email(
            email="target@example.com",
            first_name="Käthe O'Brien",
            verification_token="tok123",
        )

        html = mock_send.call_args.kwargs["html"]
        assert "Käthe O&#x27;Brien" in html or "Käthe O&#39;Brien" in html


def test_send_welcome_email_escapes_html_in_first_name():
    with patch.object(EmailService, "_send_email") as mock_send:
        mock_send.return_value = {"id": "email_3"}

        EmailService.send_welcome_email(
            email="target@example.com",
            first_name=MALICIOUS_FIRST_NAME,
        )

        html = mock_send.call_args.kwargs["html"]
        assert "<img src=x" not in html
        assert "&lt;img src=x" in html
        text = mock_send.call_args.kwargs["text"]
        assert MALICIOUS_FIRST_NAME in text
