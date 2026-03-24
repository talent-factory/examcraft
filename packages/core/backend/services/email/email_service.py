"""
Unified Email Service Router für ExamCraft AI

Routes emails to the appropriate provider:
- Transactional -> Resend (verification, password reset, payments)
- Marketing -> Kit (future: welcome series, nurture campaigns)

This service provides a single interface for all email operations.
"""

import logging
from typing import Any, Optional

from .resend_service import ResendService

logger = logging.getLogger(__name__)


class EmailService:
    """
    Unified Email Service - Routes emails to appropriate provider.

    Routing Logic:
    - Transactional -> Resend (verification, password reset, payments)
    - Marketing -> Kit (future implementation)
    """

    def __init__(self):
        """Initialize email service with all providers."""
        self.resend = ResendService()
        # Future: self.kit = KitService()

        if self.resend.is_configured:
            logger.info("Email service initialized with Resend provider")
        else:
            logger.warning("Email service running in demo mode - Resend not configured")

    @property
    def is_configured(self) -> bool:
        """Check if at least one provider is configured"""
        return self.resend.is_configured

    # ==========================================
    # TRANSACTIONAL EMAILS (Resend)
    # ==========================================

    async def send_verification_email(
        self,
        user_email: str,
        user_name: str,
        verification_url: str,
    ) -> dict[str, str]:
        """
        Send account verification email.

        Args:
            user_email: User's email address
            user_name: User's display name
            verification_url: URL for email verification

        Returns:
            dict with email_id, provider, type
        """
        email_id = await self.resend.send_verification_email(
            user_email=user_email,
            user_name=user_name,
            verification_url=verification_url,
        )

        logger.info(f"Verification email sent to {user_email}: {email_id}")

        return {
            "email_id": email_id,
            "provider": "resend",
            "type": "verification",
        }

    async def send_password_reset_email(
        self,
        user_email: str,
        user_name: str,
        reset_url: str,
    ) -> dict[str, str]:
        """
        Send password reset email.

        Args:
            user_email: User's email address
            user_name: User's display name
            reset_url: URL for password reset

        Returns:
            dict with email_id, provider, type
        """
        email_id = await self.resend.send_password_reset_email(
            user_email=user_email,
            user_name=user_name,
            reset_url=reset_url,
        )

        logger.info(f"Password reset email sent to {user_email}: {email_id}")

        return {
            "email_id": email_id,
            "provider": "resend",
            "type": "password_reset",
        }

    async def send_payment_confirmation(
        self,
        user_email: str,
        user_name: str,
        payment_details: dict[str, Any],
    ) -> dict[str, str]:
        """
        Send payment confirmation email.

        Args:
            user_email: User's email address
            user_name: User's display name
            payment_details: Payment details dict

        Returns:
            dict with email_id, provider, type
        """
        email_id = await self.resend.send_payment_confirmation(
            user_email=user_email,
            user_name=user_name,
            payment_details=payment_details,
        )

        logger.info(f"Payment confirmation sent to {user_email}: {email_id}")

        return {
            "email_id": email_id,
            "provider": "resend",
            "type": "payment_confirmation",
        }

    async def send_system_notification(
        self,
        user_email: str,
        user_name: str,
        subject: str,
        message: str,
        action_url: Optional[str] = None,
        action_text: Optional[str] = None,
    ) -> dict[str, str]:
        """
        Send generic system notification.

        Args:
            user_email: User's email address
            user_name: User's display name
            subject: Email subject
            message: Notification message
            action_url: Optional CTA URL
            action_text: Optional CTA button text

        Returns:
            dict with email_id, provider, type
        """
        email_id = await self.resend.send_system_notification(
            user_email=user_email,
            user_name=user_name,
            subject=subject,
            message=message,
            action_url=action_url,
            action_text=action_text,
        )

        logger.info(f"System notification sent to {user_email}: {email_id}")

        return {
            "email_id": email_id,
            "provider": "resend",
            "type": "notification",
        }

    # ==========================================
    # EMAIL STATUS & TRACKING
    # ==========================================

    async def get_email_status(
        self, email_id: str, provider: str = "resend"
    ) -> dict[str, Any]:
        """
        Get email delivery status.

        Args:
            email_id: The email ID from send
            provider: Provider name (default: resend)

        Returns:
            dict with status information
        """
        if provider == "resend":
            return await self.resend.get_status(email_id)

        raise ValueError(f"Unknown provider: {provider}")

    # ==========================================
    # MARKETING AUTOMATION (Kit) - Future
    # ==========================================

    # These methods will be implemented when Kit integration is added

    async def on_user_signup(
        self,
        user_email: str,
        user_name: str,
        source: str = "web",
    ) -> dict[str, Any]:
        """
        Handle new user signup - trigger marketing automation.

        Future: Will add user to Kit and trigger welcome sequence.
        Currently: Just logs the event.

        Args:
            user_email: User's email address
            user_name: User's display name
            source: Signup source (web, mobile, api)

        Returns:
            dict with status
        """
        logger.info(
            f"User signup event: {user_email} from {source} "
            "(Marketing automation not yet implemented)"
        )

        return {
            "status": "logged",
            "marketing_enabled": False,
            "message": "Marketing automation (Kit) not yet implemented",
        }

    async def on_first_exam_created(self, user_email: str) -> dict[str, Any]:
        """
        Handle first exam creation milestone.

        Future: Will trigger feature education sequence in Kit.
        Currently: Just logs the event.
        """
        logger.info(
            f"First exam milestone: {user_email} "
            "(Marketing automation not yet implemented)"
        )

        return {
            "status": "logged",
            "marketing_enabled": False,
        }

    async def on_upgrade_to_paid(
        self, user_email: str, plan_name: str
    ) -> dict[str, Any]:
        """
        Handle upgrade to paid plan.

        Future: Will update tags in Kit.
        Currently: Just logs the event.
        """
        logger.info(
            f"Plan upgrade: {user_email} -> {plan_name} "
            "(Marketing automation not yet implemented)"
        )

        return {
            "status": "logged",
            "marketing_enabled": False,
        }


# Global email service instance (singleton)
email_service = EmailService()
