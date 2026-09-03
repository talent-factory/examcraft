"""Tests for models/email_event.py's suppression-list helpers.

Extracted from the former tests/test_email_webhooks.py (TF-764): these
helpers (is_email_suppressed, add_to_suppression_list) are shared model
code, unrelated to which webhook provider (Resend, SubscribeFlow) writes
to email_events -- moved here so deleting the Resend-specific webhook
test file doesn't drop this coverage.
"""

import pytest


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

        await add_to_suppression_list(
            test_db,
            "marketing-blocked@example.com",
            EmailEventType.SPAM_COMPLAINT,
            suppress_transactional=False,
            suppress_marketing=True,
        )

        result = await is_email_suppressed(
            test_db, "marketing-blocked@example.com", check_marketing=True
        )
        assert result is True

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

        await add_to_suppression_list(
            test_db,
            "update@example.com",
            EmailEventType.SPAM_COMPLAINT,
            suppress_transactional=False,
            suppress_marketing=True,
        )
        await add_to_suppression_list(
            test_db,
            "update@example.com",
            EmailEventType.BOUNCED,
            suppress_transactional=True,
            suppress_marketing=True,
        )

        count = (
            test_db.query(EmailSuppressionList)
            .filter(EmailSuppressionList.email == "update@example.com")
            .count()
        )
        assert count == 1

        entry = (
            test_db.query(EmailSuppressionList)
            .filter(EmailSuppressionList.email == "update@example.com")
            .first()
        )
        assert entry.suppress_transactional == 1
        assert entry.suppress_marketing == 1
        assert entry.reason == EmailEventType.BOUNCED
