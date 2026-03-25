"""
SubscribeFlow Service for ExamCraft

Manages user subscriptions to the marketing newsletter via the SubscribeFlow SDK.
Triggered when a user verifies their email (status: pending → active).
"""

import os
import logging
from typing import Optional

from subscribeflow import SubscribeFlowClient

logger = logging.getLogger(__name__)

TAG_NAME = "examcraft"


class SubscribeFlowService:
    """
    Service for managing SubscribeFlow subscriptions.

    Uses the idempotent get_or_create() pattern for both
    tags and subscribers to ensure safe, retry-able operations.
    """

    def __init__(self):
        self.api_key = os.getenv("SUBSCRIBEFLOW_API_KEY", "")
        self.base_url = os.getenv(
            "SUBSCRIBEFLOW_BASE_URL", "https://api.subscribeflow.net"
        )

    def is_available(self) -> bool:
        """Check if the service is configured."""
        return bool(self.api_key)

    async def subscribe_user(
        self,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        user_id: Optional[str] = None,
        source: str = "email_verification",
    ) -> dict:
        """
        Subscribe a user to the ExamCraft newsletter.

        Uses get_or_create() for idempotent operations:
        - Creates 'examcraft' tag if not exists
        - Creates subscriber if not exists, or returns existing

        Args:
            email: User's email address
            first_name: Optional first name
            last_name: Optional last name
            user_id: Optional ExamCraft user ID for tracking
            source: Subscription source for analytics

        Returns:
            dict with subscription details
        """
        if not self.is_available():
            logger.warning("SubscribeFlow not configured (missing API key)")
            return {"status": "skipped", "reason": "not_configured"}

        metadata = {
            "source": source,
            "product": "examcraft",
        }
        if user_id:
            metadata["examcraft_user_id"] = user_id
        if first_name:
            metadata["first_name"] = first_name
        if last_name:
            metadata["last_name"] = last_name

        async with SubscribeFlowClient(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=60.0,
        ) as client:
            # 1. Get or create the 'examcraft' tag
            tag, tag_created = await client.tags.get_or_create(
                name=TAG_NAME,
                description="ExamCraft AI newsletter subscribers",
                category="product",
            )

            if tag_created:
                logger.info(f"Created new SubscribeFlow tag: {TAG_NAME}")

            # 2. Get or create subscriber with tag
            subscriber, subscriber_created = await client.subscribers.get_or_create(
                email=email,
                tags=[str(tag.id)],
                metadata=metadata,
            )

            action = "Created new" if subscriber_created else "Found existing"
            logger.info(
                f"{action} SubscribeFlow subscriber: {email} with tag '{TAG_NAME}'"
            )

            return {
                "subscriber_id": str(subscriber.id),
                "tag_id": str(tag.id),
                "created": subscriber_created,
                "tag_name": TAG_NAME,
            }


# Singleton instance
subscribeflow_service = SubscribeFlowService()
