"""
Tests für Email Service (Resend Integration)

Tests für:
- ResendService: Transactional email sending
- EmailService: Unified email router
- Webhook handling
- Email event tracking
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from services.email.base import EmailAddress, EmailTemplate, TransactionalEmail
from services.email.resend_service import ResendService
from services.email.email_service import EmailService


class TestEmailAddress:
    """Tests für EmailAddress model"""

    def test_email_address_str_with_name(self):
        """EmailAddress with name formats correctly"""
        addr = EmailAddress(email="test@example.com", name="Test User")
        assert str(addr) == "Test User <test@example.com>"

    def test_email_address_str_without_name(self):
        """EmailAddress without name returns just email"""
        addr = EmailAddress(email="test@example.com")
        assert str(addr) == "test@example.com"


class TestResendService:
    """Tests für ResendService"""

    def test_resend_service_init_without_api_key(self):
        """ResendService initializes in demo mode without API key"""
        with patch.dict("os.environ", {}, clear=True):
            service = ResendService()
            assert not service.is_configured

    def test_resend_service_init_with_api_key(self):
        """ResendService initializes correctly with API key"""
        with patch.dict(
            "os.environ",
            {"RESEND_API_KEY": "re_test_key"},  # pragma: allowlist secret
        ):
            service = ResendService()
            assert service.is_configured

    @pytest.mark.asyncio
    async def test_send_transactional_demo_mode(self):
        """send_transactional returns demo ID when not configured"""
        with patch.dict("os.environ", {}, clear=True):
            service = ResendService()

            email = TransactionalEmail(
                to=EmailAddress(email="user@example.com", name="User"),
                from_=EmailAddress(email="noreply@examcraft.ai", name="ExamCraft"),
                subject="Test Subject",
                template=EmailTemplate(
                    subject="Test Subject",
                    html="<p>Test content</p>",
                ),
            )

            result = await service.send_transactional(email)
            assert result.startswith("demo_email_")

    @pytest.mark.asyncio
    async def test_send_transactional_api_call(self):
        """send_transactional makes correct API call when configured"""
        with patch.dict(
            "os.environ",
            {
                "RESEND_API_KEY": "re_test_key",  # pragma: allowlist secret
                "RESEND_FROM_EMAIL": "noreply@test.com",
            },
        ):
            service = ResendService()

            email = TransactionalEmail(
                to=EmailAddress(email="user@example.com", name="User"),
                from_=EmailAddress(email="noreply@test.com", name="ExamCraft"),
                subject="Test Subject",
                template=EmailTemplate(
                    subject="Test Subject",
                    html="<p>Test content</p>",
                ),
                tags=["test", "verification"],
            )

            # Mock httpx response
            mock_response = MagicMock()
            mock_response.json.return_value = {"id": "email_123"}
            mock_response.raise_for_status = MagicMock()

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post = AsyncMock(return_value=mock_response)
                mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_instance.__aexit__ = AsyncMock(return_value=None)
                mock_client.return_value = mock_instance

                result = await service.send_transactional(email)

                assert result == "email_123"
                mock_instance.post.assert_called_once()

                # Verify API call payload
                call_kwargs = mock_instance.post.call_args
                assert call_kwargs[1]["json"]["to"] == ["user@example.com"]
                assert call_kwargs[1]["json"]["subject"] == "Test Subject"

    @pytest.mark.asyncio
    async def test_send_verification_email(self):
        """send_verification_email generates correct template"""
        with patch.dict("os.environ", {}, clear=True):
            service = ResendService()

            result = await service.send_verification_email(
                user_email="user@example.com",
                user_name="Test User",
                verification_url="https://examcraft.ai/verify/token123",
            )

            assert result.startswith("demo_email_")

    @pytest.mark.asyncio
    async def test_send_password_reset_email(self):
        """send_password_reset_email generates correct template"""
        with patch.dict("os.environ", {}, clear=True):
            service = ResendService()

            result = await service.send_password_reset_email(
                user_email="user@example.com",
                user_name="Test User",
                reset_url="https://examcraft.ai/reset/token456",
            )

            assert result.startswith("demo_email_")

    @pytest.mark.asyncio
    async def test_send_payment_confirmation(self):
        """send_payment_confirmation generates correct template"""
        with patch.dict("os.environ", {}, clear=True):
            service = ResendService()

            payment_details = {
                "plan_name": "Professional",
                "amount": "99.00",
                "currency": "CHF",
                "next_billing_date": "2025-02-01",
                "receipt_url": "https://examcraft.ai/receipt/123",
            }

            result = await service.send_payment_confirmation(
                user_email="user@example.com",
                user_name="Test User",
                payment_details=payment_details,
            )

            assert result.startswith("demo_email_")

    @pytest.mark.asyncio
    async def test_get_status_demo_mode(self):
        """get_status returns demo status when not configured"""
        with patch.dict("os.environ", {}, clear=True):
            service = ResendService()

            result = await service.get_status("demo_email_123")

            assert result["id"] == "demo_email_123"
            assert result["status"] == "demo"
            assert result["provider"] == "resend"


class TestEmailService:
    """Tests für EmailService (unified router)"""

    def test_email_service_init(self):
        """EmailService initializes with Resend provider"""
        with patch.dict("os.environ", {}, clear=True):
            service = EmailService()
            assert hasattr(service, "resend")
            assert isinstance(service.resend, ResendService)

    @pytest.mark.asyncio
    async def test_send_verification_email(self):
        """EmailService routes verification email correctly"""
        with patch.dict("os.environ", {}, clear=True):
            service = EmailService()

            result = await service.send_verification_email(
                user_email="user@example.com",
                user_name="Test User",
                verification_url="https://examcraft.ai/verify/token",
            )

            assert result["provider"] == "resend"
            assert result["type"] == "verification"
            assert "email_id" in result

    @pytest.mark.asyncio
    async def test_send_password_reset_email(self):
        """EmailService routes password reset email correctly"""
        with patch.dict("os.environ", {}, clear=True):
            service = EmailService()

            result = await service.send_password_reset_email(
                user_email="user@example.com",
                user_name="Test User",
                reset_url="https://examcraft.ai/reset/token",
            )

            assert result["provider"] == "resend"
            assert result["type"] == "password_reset"
            assert "email_id" in result

    @pytest.mark.asyncio
    async def test_send_payment_confirmation(self):
        """EmailService routes payment confirmation correctly"""
        with patch.dict("os.environ", {}, clear=True):
            service = EmailService()

            payment_details = {
                "plan_name": "Starter",
                "amount": "29.00",
                "currency": "CHF",
                "next_billing_date": "2025-02-01",
                "receipt_url": "https://examcraft.ai/receipt/456",
            }

            result = await service.send_payment_confirmation(
                user_email="user@example.com",
                user_name="Test User",
                payment_details=payment_details,
            )

            assert result["provider"] == "resend"
            assert result["type"] == "payment_confirmation"
            assert "email_id" in result

    @pytest.mark.asyncio
    async def test_send_system_notification(self):
        """EmailService routes system notification correctly"""
        with patch.dict("os.environ", {}, clear=True):
            service = EmailService()

            result = await service.send_system_notification(
                user_email="user@example.com",
                user_name="Test User",
                subject="Important Update",
                message="<p>Your account has been updated.</p>",
                action_url="https://examcraft.ai/dashboard",
                action_text="View Dashboard",
            )

            assert result["provider"] == "resend"
            assert result["type"] == "notification"
            assert "email_id" in result

    @pytest.mark.asyncio
    async def test_on_user_signup_logs_event(self):
        """on_user_signup logs event (marketing not yet implemented)"""
        with patch.dict("os.environ", {}, clear=True):
            service = EmailService()

            result = await service.on_user_signup(
                user_email="new@example.com",
                user_name="New User",
                source="web",
            )

            assert result["status"] == "logged"
            assert result["marketing_enabled"] is False

    @pytest.mark.asyncio
    async def test_get_email_status(self):
        """get_email_status retrieves status correctly"""
        with patch.dict("os.environ", {}, clear=True):
            service = EmailService()

            result = await service.get_email_status("demo_email_123", "resend")

            assert result["id"] == "demo_email_123"


class TestEmailTemplates:
    """Tests für Email Template Rendering"""

    def test_verification_template_contains_url(self):
        """Verification template includes verification URL"""
        service = ResendService()
        html = service._render_verification_template(
            "Test User",
            "https://examcraft.ai/verify/abc123",
        )

        assert "Test User" in html
        assert "https://examcraft.ai/verify/abc123" in html
        assert "Verify Email Address" in html
        assert "24 hours" in html

    def test_password_reset_template_contains_url(self):
        """Password reset template includes reset URL"""
        service = ResendService()
        html = service._render_password_reset_template(
            "Test User",
            "https://examcraft.ai/reset/xyz789",
        )

        assert "Test User" in html
        assert "https://examcraft.ai/reset/xyz789" in html
        assert "Reset Password" in html
        assert "1 hour" in html

    def test_payment_confirmation_template_contains_details(self):
        """Payment confirmation template includes all payment details"""
        service = ResendService()
        html = service._render_payment_confirmation_template(
            "Test User",
            {
                "plan_name": "Professional",
                "amount": "99.00",
                "currency": "CHF",
                "next_billing_date": "2025-02-01",
                "receipt_url": "https://examcraft.ai/receipt/123",
            },
        )

        assert "Test User" in html
        assert "Professional" in html
        assert "99.00" in html
        assert "CHF" in html
        assert "2025-02-01" in html

    def test_notification_template_with_action(self):
        """Notification template includes action button when provided"""
        service = ResendService()
        html = service._render_notification_template(
            "Test User",
            "<p>Your exam is ready.</p>",
            "https://examcraft.ai/exam/123",
            "View Exam",
        )

        assert "Test User" in html
        assert "Your exam is ready" in html
        assert "View Exam" in html
        assert "https://examcraft.ai/exam/123" in html

    def test_notification_template_without_action(self):
        """Notification template works without action button"""
        service = ResendService()
        html = service._render_notification_template(
            "Test User",
            "<p>Simple notification.</p>",
            None,
            None,
        )

        assert "Test User" in html
        assert "Simple notification" in html
        assert "button" not in html.lower() or "View" not in html


class TestTransactionalEmailModel:
    """Tests für TransactionalEmail Pydantic model"""

    def test_transactional_email_with_all_fields(self):
        """TransactionalEmail accepts all fields"""
        email = TransactionalEmail(
            to=EmailAddress(email="to@example.com", name="Recipient"),
            from_=EmailAddress(email="from@example.com", name="Sender"),
            subject="Test Subject",
            template=EmailTemplate(
                subject="Test Subject",
                html="<p>HTML content</p>",
                text="Text content",
            ),
            variables={"key": "value"},
            attachments=[{"filename": "test.pdf", "content": "base64..."}],
            reply_to=EmailAddress(email="reply@example.com"),
            tags=["test", "important"],
        )

        assert email.to.email == "to@example.com"
        assert email.from_address.email == "from@example.com"
        assert email.subject == "Test Subject"
        assert email.template.html == "<p>HTML content</p>"
        assert email.variables == {"key": "value"}
        assert len(email.attachments) == 1
        assert email.reply_to.email == "reply@example.com"
        assert "test" in email.tags

    def test_transactional_email_minimal(self):
        """TransactionalEmail works with minimal fields"""
        email = TransactionalEmail(
            to=EmailAddress(email="to@example.com"),
            from_=EmailAddress(email="from@example.com"),
            subject="Test",
            template=EmailTemplate(subject="Test", html="<p>Content</p>"),
        )

        assert email.to.email == "to@example.com"
        assert email.variables == {}
        assert email.attachments == []
        assert email.reply_to is None
        assert email.tags == []
