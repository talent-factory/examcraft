"""
Tests für Resend Webhook Handler

Tests für:
- Webhook signature verification
- Email event handling (delivered, bounced, opened, clicked, complained)
- Suppression list management
"""

import pytest
import hmac
import hashlib
import os
from datetime import datetime
from unittest.mock import patch


class TestWebhookSignatureVerification:
    """Tests für Webhook Signature Verification"""

    def test_verify_signature_valid(self):
        """Valid signature passes verification"""
        from webhooks.resend_webhooks import verify_resend_signature

        secret = "test_secret"  # pragma: allowlist secret
        timestamp = "1234567890"
        payload = b'{"type": "email.delivered"}'

        # Create valid signature
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        signature = hmac.new(
            secret.encode(),
            signed_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        signature_header = f"t={timestamp},v1={signature}"

        result = verify_resend_signature(payload, signature_header, secret)
        assert result is True

    def test_verify_signature_invalid(self):
        """Invalid signature fails verification"""
        from webhooks.resend_webhooks import verify_resend_signature

        secret = "test_secret"  # pragma: allowlist secret
        payload = b'{"type": "email.delivered"}'
        signature_header = "t=1234567890,v1=invalid_signature"

        result = verify_resend_signature(payload, signature_header, secret)
        assert result is False

    def test_verify_signature_missing_parts(self):
        """Missing signature parts fails verification"""
        from webhooks.resend_webhooks import verify_resend_signature

        secret = "test_secret"  # pragma: allowlist secret
        payload = b'{"type": "email.delivered"}'

        # Missing timestamp
        result = verify_resend_signature(payload, "v1=somesig", secret)
        assert result is False

        # Missing signature
        result = verify_resend_signature(payload, "t=123", secret)
        assert result is False

        # Empty signature
        result = verify_resend_signature(payload, "", secret)
        assert result is False

    def test_verify_signature_empty_secret(self):
        """Empty secret fails verification"""
        from webhooks.resend_webhooks import verify_resend_signature

        payload = b'{"type": "email.delivered"}'
        signature_header = "t=123,v1=somesig"

        result = verify_resend_signature(payload, signature_header, "")
        assert result is False


class TestWebhookEndpoint:
    """Tests für Webhook Endpoint"""

    def test_webhook_without_secret_development_mode(self, client):
        """Webhook processes without secret in development mode"""
        env = os.environ.copy()
        env.pop("RESEND_WEBHOOK_SECRET", None)
        env["ENVIRONMENT"] = "development"
        with patch.dict("os.environ", env, clear=True):
            response = client.post(
                "/webhooks/resend",
                json={
                    "type": "email.delivered",
                    "data": {
                        "email_id": "email_123",
                        "to": ["user@example.com"],
                        "created_at": "2025-01-01T12:00:00Z",
                    },
                },
            )

            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    def test_webhook_without_secret_production_mode_rejected(self, client):
        """Webhook without secret is rejected in production mode"""
        env = os.environ.copy()
        env.pop("RESEND_WEBHOOK_SECRET", None)
        env["ENVIRONMENT"] = "production"
        with patch.dict("os.environ", env, clear=True):
            response = client.post(
                "/webhooks/resend",
                json={
                    "type": "email.delivered",
                    "data": {
                        "email_id": "email_123",
                        "to": ["user@example.com"],
                        "created_at": "2025-01-01T12:00:00Z",
                    },
                },
            )

            assert response.status_code == 500
            assert "Webhook secret not configured" in response.json()["detail"]

    def test_webhook_with_invalid_signature_rejected(self, client):
        """Webhook with invalid signature is rejected when secret is set"""
        with patch.dict(
            "os.environ",
            {"RESEND_WEBHOOK_SECRET": "secret123"},  # pragma: allowlist secret
        ):
            response = client.post(
                "/webhooks/resend",
                json={"type": "email.delivered", "data": {}},
                headers={
                    "svix-id": "msg_123",
                    "svix-timestamp": "1234567890",
                    "svix-signature": "v1=invalid",
                },
            )

            assert response.status_code == 401

    def test_webhook_invalid_json_rejected(self, client):
        """Webhook with invalid JSON is rejected"""
        env = os.environ.copy()
        env.pop("RESEND_WEBHOOK_SECRET", None)
        env["ENVIRONMENT"] = "development"
        with patch.dict("os.environ", env, clear=True):
            response = client.post(
                "/webhooks/resend",
                content="not json",
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 400 or response.status_code == 422


class TestEmailEventHandlers:
    """Tests für individual event handlers"""

    @pytest.mark.asyncio
    async def test_handle_email_delivered(self, test_db):
        """handle_email_delivered creates EmailEvent record"""
        from webhooks.resend_webhooks import handle_email_delivered
        from models.email_event import EmailEvent, EmailEventType

        data = {
            "email_id": "email_123",
            "to": ["user@example.com"],
            "created_at": "2025-01-01T12:00:00Z",
        }

        await handle_email_delivered(test_db, data, "svix_abc")

        # Verify event was created
        event = (
            test_db.query(EmailEvent).filter(EmailEvent.email_id == "email_123").first()
        )
        assert event is not None
        assert event.event_type == EmailEventType.DELIVERED
        assert event.recipient_email == "user@example.com"
        assert event.provider == "resend"

    @pytest.mark.asyncio
    async def test_handle_email_bounced_hard(self, test_db):
        """handle_email_bounced adds to suppression list for hard bounce"""
        from webhooks.resend_webhooks import handle_email_bounced
        from models.email_event import (
            EmailEvent,
            EmailEventType,
            EmailSuppressionList,
        )

        data = {
            "email_id": "email_456",
            "to": ["bounced@example.com"],
            "bounce_type": "Permanent",
            "bounce_subtype": "NoEmail",
            "created_at": "2025-01-01T12:00:00Z",
        }

        await handle_email_bounced(test_db, data, "svix_xyz")

        # Verify event was created
        event = (
            test_db.query(EmailEvent).filter(EmailEvent.email_id == "email_456").first()
        )
        assert event is not None
        assert event.event_type == EmailEventType.BOUNCED

        # Verify suppression list entry
        suppression = (
            test_db.query(EmailSuppressionList)
            .filter(EmailSuppressionList.email == "bounced@example.com")
            .first()
        )
        assert suppression is not None
        assert suppression.suppress_transactional == 1
        assert suppression.suppress_marketing == 1

    @pytest.mark.asyncio
    async def test_handle_email_bounced_soft(self, test_db):
        """handle_email_bounced does NOT add to suppression for soft bounce"""
        from webhooks.resend_webhooks import handle_email_bounced
        from models.email_event import EmailSuppressionList

        data = {
            "email_id": "email_789",
            "to": ["softbounce@example.com"],
            "bounce_type": "Temporary",
            "bounce_subtype": "MailboxFull",
            "created_at": "2025-01-01T12:00:00Z",
        }

        await handle_email_bounced(test_db, data, "svix_123")

        # Verify no suppression list entry for soft bounce
        suppression = (
            test_db.query(EmailSuppressionList)
            .filter(EmailSuppressionList.email == "softbounce@example.com")
            .first()
        )
        assert suppression is None

    @pytest.mark.asyncio
    async def test_handle_email_opened(self, test_db):
        """handle_email_opened creates EmailEvent record"""
        from webhooks.resend_webhooks import handle_email_opened
        from models.email_event import EmailEvent, EmailEventType

        data = {
            "email_id": "email_open_1",
            "to": ["reader@example.com"],
            "created_at": "2025-01-01T12:00:00Z",
            "user_agent": "Mozilla/5.0",
            "ip_address": "192.168.1.1",
        }

        await handle_email_opened(test_db, data, "svix_open")

        event = (
            test_db.query(EmailEvent)
            .filter(EmailEvent.email_id == "email_open_1")
            .first()
        )
        assert event is not None
        assert event.event_type == EmailEventType.OPENED
        assert event.event_metadata.get("user_agent") == "Mozilla/5.0"

    @pytest.mark.asyncio
    async def test_handle_email_clicked(self, test_db):
        """handle_email_clicked creates EmailEvent record with link"""
        from webhooks.resend_webhooks import handle_email_clicked
        from models.email_event import EmailEvent, EmailEventType

        data = {
            "email_id": "email_click_1",
            "to": ["clicker@example.com"],
            "created_at": "2025-01-01T12:00:00Z",
            "link": "https://examcraft.ai/verify/token",
        }

        await handle_email_clicked(test_db, data, "svix_click")

        event = (
            test_db.query(EmailEvent)
            .filter(EmailEvent.email_id == "email_click_1")
            .first()
        )
        assert event is not None
        assert event.event_type == EmailEventType.CLICKED
        assert (
            event.event_metadata.get("link_url") == "https://examcraft.ai/verify/token"
        )

    @pytest.mark.asyncio
    async def test_handle_email_spam_complaint(self, test_db):
        """handle_email_spam_complaint adds to suppression list (marketing only)"""
        from webhooks.resend_webhooks import handle_email_spam_complaint
        from models.email_event import (
            EmailEvent,
            EmailEventType,
            EmailSuppressionList,
        )

        data = {
            "email_id": "email_spam_1",
            "to": ["complainer@example.com"],
            "created_at": "2025-01-01T12:00:00Z",
        }

        await handle_email_spam_complaint(test_db, data, "svix_spam")

        # Verify event was created
        event = (
            test_db.query(EmailEvent)
            .filter(EmailEvent.email_id == "email_spam_1")
            .first()
        )
        assert event is not None
        assert event.event_type == EmailEventType.SPAM_COMPLAINT

        # Verify suppression list entry (marketing only)
        suppression = (
            test_db.query(EmailSuppressionList)
            .filter(EmailSuppressionList.email == "complainer@example.com")
            .first()
        )
        assert suppression is not None
        assert suppression.suppress_transactional == 0  # Still allow transactional
        assert suppression.suppress_marketing == 1  # Block marketing


class TestSuppressionList:
    """Tests für Suppression List Management"""

    @pytest.mark.asyncio
    async def test_is_email_suppressed_not_on_list(self, test_db):
        """is_email_suppressed returns False for emails not on list"""
        from models.email_event import is_email_suppressed

        result = await is_email_suppressed(
            test_db, "clean@example.com", check_marketing=True
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_is_email_suppressed_marketing_only(self, test_db):
        """is_email_suppressed respects marketing-only suppression"""
        from models.email_event import (
            add_to_suppression_list,
            is_email_suppressed,
            EmailEventType,
        )

        # Add to suppression (marketing only)
        await add_to_suppression_list(
            test_db,
            "marketing-blocked@example.com",
            EmailEventType.SPAM_COMPLAINT,
            suppress_transactional=False,
            suppress_marketing=True,
        )

        # Marketing should be blocked
        result = await is_email_suppressed(
            test_db, "marketing-blocked@example.com", check_marketing=True
        )
        assert result is True

        # Transactional should be allowed
        result = await is_email_suppressed(
            test_db,
            "marketing-blocked@example.com",
            check_transactional=True,
            check_marketing=False,
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_add_to_suppression_list_updates_existing(self, test_db):
        """add_to_suppression_list updates existing entries"""
        from models.email_event import (
            add_to_suppression_list,
            EmailEventType,
            EmailSuppressionList,
        )

        # First add (spam complaint - marketing only)
        await add_to_suppression_list(
            test_db,
            "update@example.com",
            EmailEventType.SPAM_COMPLAINT,
            suppress_transactional=False,
            suppress_marketing=True,
        )

        # Second add (hard bounce - both)
        await add_to_suppression_list(
            test_db,
            "update@example.com",
            EmailEventType.BOUNCED,
            suppress_transactional=True,
            suppress_marketing=True,
        )

        # Should still be one entry
        count = (
            test_db.query(EmailSuppressionList)
            .filter(EmailSuppressionList.email == "update@example.com")
            .count()
        )
        assert count == 1

        # Should now block both
        entry = (
            test_db.query(EmailSuppressionList)
            .filter(EmailSuppressionList.email == "update@example.com")
            .first()
        )
        assert entry.suppress_transactional == 1
        assert entry.suppress_marketing == 1
        assert entry.reason == EmailEventType.BOUNCED


class TestHelperFunctions:
    """Tests für helper functions"""

    def test_extract_recipient_from_list(self):
        """_extract_recipient handles list format"""
        from webhooks.resend_webhooks import _extract_recipient

        data = {"to": ["user@example.com", "other@example.com"]}
        result = _extract_recipient(data)
        assert result == "user@example.com"

    def test_extract_recipient_from_string(self):
        """_extract_recipient handles string format"""
        from webhooks.resend_webhooks import _extract_recipient

        data = {"to": "user@example.com"}
        result = _extract_recipient(data)
        assert result == "user@example.com"

    def test_extract_recipient_fallback(self):
        """_extract_recipient falls back to email field"""
        from webhooks.resend_webhooks import _extract_recipient

        data = {"email": "fallback@example.com"}
        result = _extract_recipient(data)
        assert result == "fallback@example.com"

    def test_parse_timestamp_valid(self):
        """_parse_timestamp handles valid ISO timestamp"""
        from webhooks.resend_webhooks import _parse_timestamp

        result = _parse_timestamp("2025-01-01T12:00:00Z")
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 1

    def test_parse_timestamp_invalid(self):
        """_parse_timestamp returns now for invalid timestamp"""
        from webhooks.resend_webhooks import _parse_timestamp

        result = _parse_timestamp("invalid")
        assert isinstance(result, datetime)

    def test_parse_timestamp_none(self):
        """_parse_timestamp returns now for None"""
        from webhooks.resend_webhooks import _parse_timestamp

        result = _parse_timestamp(None)
        assert isinstance(result, datetime)
