"""
Resend Transactional Email Service für ExamCraft AI

Handles all transactional emails:
- Account verification
- Password reset
- Payment confirmations
- System notifications

Uses Resend API: https://resend.com/docs
"""

import os
import logging
from typing import Any, Optional

import httpx

from .base import (
    TransactionalProvider,
    TransactionalEmail,
    EmailAddress,
    EmailTemplate,
)

logger = logging.getLogger(__name__)


class ResendService(TransactionalProvider):
    """
    Resend transactional email service.

    Implements the TransactionalProvider interface for sending
    transactional emails via the Resend API.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: str = "ExamCraft",
    ):
        """
        Initialize Resend service.

        Args:
            api_key: Resend API key (defaults to RESEND_API_KEY env var)
            from_email: Default sender email (defaults to RESEND_FROM_EMAIL env var)
            from_name: Default sender name
        """
        self.api_key = api_key or os.getenv("RESEND_API_KEY")
        self.from_email = from_email or os.getenv(
            "RESEND_FROM_EMAIL", "noreply@examcraft.ai"
        )
        self.from_name = from_name
        self.base_url = "https://api.resend.com"

        if not self.api_key:
            logger.warning(
                "RESEND_API_KEY not configured - email service will operate in demo mode"
            )

    @property
    def is_configured(self) -> bool:
        """Check if service is properly configured"""
        return bool(self.api_key)

    async def send_transactional(self, email: TransactionalEmail) -> str:
        """
        Send transactional email via Resend.

        Args:
            email: TransactionalEmail object with all email details

        Returns:
            str: Email ID from Resend

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        if not self.is_configured:
            logger.warning("Resend not configured - simulating email send")
            return f"demo_email_{id(email)}"

        payload: dict[str, Any] = {
            "from": str(email.from_address),
            "to": [email.to.email],
            "subject": email.subject,
        }

        # Add content (prefer HTML, fallback to text)
        if email.template.html:
            payload["html"] = email.template.html
        elif email.template.text:
            payload["text"] = email.template.text
        else:
            raise ValueError("Email template must have either html or text content")

        # Add reply-to if specified
        if email.reply_to:
            payload["reply_to"] = str(email.reply_to)

        # Add tags for tracking
        if email.tags:
            payload["tags"] = [{"name": tag, "value": "true"} for tag in email.tags]

        # Add attachments
        if email.attachments:
            payload["attachments"] = email.attachments

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/emails",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                email_id = data["id"]
                logger.info(
                    f"Resend email sent successfully: {email_id} to {email.to.email}"
                )
                return email_id

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Resend API error: {e.response.status_code} - {e.response.text}"
            )
            raise
        except httpx.RequestError as e:
            logger.error(f"Resend request failed: {str(e)}")
            raise

    async def send(self, email: TransactionalEmail) -> dict[str, Any]:
        """Send email (implements EmailProvider interface)"""
        email_id = await self.send_transactional(email)
        return {"id": email_id, "provider": "resend"}

    async def get_status(self, email_id: str) -> dict[str, Any]:
        """
        Get email status from Resend.

        Args:
            email_id: The email ID returned from send

        Returns:
            dict: Email status information
        """
        if not self.is_configured:
            return {
                "id": email_id,
                "status": "demo",
                "provider": "resend",
            }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/emails/{email_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get email status: {e.response.text}")
            raise

    # ==========================================
    # Convenience methods for common email types
    # ==========================================

    async def send_verification_email(
        self,
        user_email: str,
        user_name: str,
        verification_url: str,
    ) -> str:
        """
        Send account verification email.

        Args:
            user_email: User's email address
            user_name: User's display name
            verification_url: URL for email verification

        Returns:
            str: Email ID
        """
        html_content = self._render_verification_template(user_name, verification_url)

        email = TransactionalEmail(
            to=EmailAddress(email=user_email, name=user_name),
            from_=EmailAddress(email=self.from_email, name=self.from_name),
            subject="Verify your ExamCraft account",
            template=EmailTemplate(
                subject="Verify your ExamCraft account",
                html=html_content,
            ),
            variables={
                "username": user_name,
                "verification_url": verification_url,
            },
            tags=["verification", "transactional"],
        )

        return await self.send_transactional(email)

    async def send_password_reset_email(
        self,
        user_email: str,
        user_name: str,
        reset_url: str,
    ) -> str:
        """
        Send password reset email.

        Args:
            user_email: User's email address
            user_name: User's display name
            reset_url: URL for password reset

        Returns:
            str: Email ID
        """
        html_content = self._render_password_reset_template(user_name, reset_url)

        email = TransactionalEmail(
            to=EmailAddress(email=user_email, name=user_name),
            from_=EmailAddress(email=self.from_email, name=self.from_name),
            subject="Reset your ExamCraft password",
            template=EmailTemplate(
                subject="Reset your ExamCraft password",
                html=html_content,
            ),
            variables={
                "username": user_name,
                "reset_url": reset_url,
                "expires_in": "1 hour",
            },
            tags=["password_reset", "transactional"],
        )

        return await self.send_transactional(email)

    async def send_payment_confirmation(
        self,
        user_email: str,
        user_name: str,
        payment_details: dict[str, Any],
    ) -> str:
        """
        Send payment confirmation email.

        Args:
            user_email: User's email address
            user_name: User's display name
            payment_details: Payment details dict with:
                - plan_name: Name of the plan
                - amount: Payment amount
                - currency: Currency code
                - next_billing_date: Next billing date
                - receipt_url: URL to receipt

        Returns:
            str: Email ID
        """
        html_content = self._render_payment_confirmation_template(
            user_name, payment_details
        )

        plan_name = payment_details.get("plan_name", "ExamCraft Plan")

        email = TransactionalEmail(
            to=EmailAddress(email=user_email, name=user_name),
            from_=EmailAddress(email=self.from_email, name=self.from_name),
            subject=f"Payment Confirmation - {plan_name}",
            template=EmailTemplate(
                subject=f"Payment Confirmation - {plan_name}",
                html=html_content,
            ),
            variables={
                "username": user_name,
                **payment_details,
            },
            tags=["payment", "transactional"],
        )

        return await self.send_transactional(email)

    async def send_system_notification(
        self,
        user_email: str,
        user_name: str,
        subject: str,
        message: str,
        action_url: Optional[str] = None,
        action_text: Optional[str] = None,
    ) -> str:
        """
        Send generic system notification.

        Args:
            user_email: User's email address
            user_name: User's display name
            subject: Email subject
            message: Notification message (supports HTML)
            action_url: Optional CTA URL
            action_text: Optional CTA button text

        Returns:
            str: Email ID
        """
        html_content = self._render_notification_template(
            user_name, message, action_url, action_text
        )

        email = TransactionalEmail(
            to=EmailAddress(email=user_email, name=user_name),
            from_=EmailAddress(email=self.from_email, name=self.from_name),
            subject=subject,
            template=EmailTemplate(
                subject=subject,
                html=html_content,
            ),
            variables={
                "username": user_name,
                "message": message,
            },
            tags=["notification", "transactional"],
        )

        return await self.send_transactional(email)

    # ==========================================
    # Email templates (inline for simplicity)
    # ==========================================

    def _get_base_styles(self) -> str:
        """Return base CSS styles for email templates"""
        return """
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Ubuntu, sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 0;
                background-color: #f6f9fc;
            }
            .container {
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background-color: #ffffff;
            }
            .header {
                text-align: center;
                padding: 20px 0;
                border-bottom: 1px solid #e5e7eb;
            }
            .logo {
                font-size: 24px;
                font-weight: bold;
                color: #4f46e5;
            }
            .content {
                padding: 30px 20px;
            }
            h1 {
                color: #1f2937;
                font-size: 24px;
                margin-bottom: 20px;
            }
            p {
                color: #4b5563;
                margin-bottom: 16px;
            }
            .button {
                display: inline-block;
                background-color: #4f46e5;
                color: #ffffff !important;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 600;
                margin: 20px 0;
            }
            .button:hover {
                background-color: #4338ca;
            }
            .footer {
                text-align: center;
                padding: 20px;
                color: #9ca3af;
                font-size: 12px;
                border-top: 1px solid #e5e7eb;
            }
            .link {
                color: #4f46e5;
                word-break: break-all;
            }
        </style>
        """

    def _render_verification_template(
        self, user_name: str, verification_url: str
    ) -> str:
        """Render verification email HTML"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            {self._get_base_styles()}
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">ExamCraft AI</div>
                </div>
                <div class="content">
                    <h1>Welcome to ExamCraft!</h1>
                    <p>Hi <strong>{user_name}</strong>,</p>
                    <p>
                        Thanks for signing up! We're excited to help you create
                        better exams with AI-powered question generation.
                    </p>
                    <p>
                        To get started, please verify your email address by
                        clicking the button below:
                    </p>
                    <p style="text-align: center;">
                        <a href="{verification_url}" class="button">
                            Verify Email Address
                        </a>
                    </p>
                    <p>Or copy and paste this URL into your browser:</p>
                    <p><a href="{verification_url}" class="link">{verification_url}</a></p>
                    <p><strong>This link will expire in 24 hours.</strong></p>
                    <p style="color: #9ca3af; font-size: 14px;">
                        If you didn't create an ExamCraft account, you can safely
                        ignore this email.
                    </p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 ExamCraft AI. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

    def _render_password_reset_template(self, user_name: str, reset_url: str) -> str:
        """Render password reset email HTML"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            {self._get_base_styles()}
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">ExamCraft AI</div>
                </div>
                <div class="content">
                    <h1>Reset Your Password</h1>
                    <p>Hi <strong>{user_name}</strong>,</p>
                    <p>
                        We received a request to reset your password. Click the
                        button below to choose a new password:
                    </p>
                    <p style="text-align: center;">
                        <a href="{reset_url}" class="button">
                            Reset Password
                        </a>
                    </p>
                    <p>Or copy and paste this URL into your browser:</p>
                    <p><a href="{reset_url}" class="link">{reset_url}</a></p>
                    <p><strong>This link will expire in 1 hour.</strong></p>
                    <p style="color: #9ca3af; font-size: 14px;">
                        If you didn't request a password reset, you can safely
                        ignore this email. Your password will remain unchanged.
                    </p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 ExamCraft AI. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

    def _render_payment_confirmation_template(
        self, user_name: str, payment_details: dict[str, Any]
    ) -> str:
        """Render payment confirmation email HTML"""
        plan_name = payment_details.get("plan_name", "ExamCraft Plan")
        amount = payment_details.get("amount", "0.00")
        currency = payment_details.get("currency", "CHF")
        next_billing = payment_details.get("next_billing_date", "N/A")
        receipt_url = payment_details.get("receipt_url", "#")

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            {self._get_base_styles()}
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">ExamCraft AI</div>
                </div>
                <div class="content">
                    <h1>Payment Confirmed</h1>
                    <p>Hi <strong>{user_name}</strong>,</p>
                    <p>
                        Thank you for your payment! Your subscription to
                        <strong>{plan_name}</strong> is now active.
                    </p>
                    <table style="width: 100%; margin: 20px 0; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">
                                <strong>Plan</strong>
                            </td>
                            <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: right;">
                                {plan_name}
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">
                                <strong>Amount</strong>
                            </td>
                            <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: right;">
                                {currency} {amount}
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 10px;">
                                <strong>Next Billing Date</strong>
                            </td>
                            <td style="padding: 10px; text-align: right;">
                                {next_billing}
                            </td>
                        </tr>
                    </table>
                    <p style="text-align: center;">
                        <a href="{receipt_url}" class="button">
                            View Receipt
                        </a>
                    </p>
                    <p style="color: #9ca3af; font-size: 14px;">
                        If you have any questions about your subscription, please
                        contact our support team.
                    </p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 ExamCraft AI. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

    def _render_notification_template(
        self,
        user_name: str,
        message: str,
        action_url: Optional[str] = None,
        action_text: Optional[str] = None,
    ) -> str:
        """Render generic notification email HTML"""
        action_button = ""
        if action_url and action_text:
            action_button = f"""
            <p style="text-align: center;">
                <a href="{action_url}" class="button">{action_text}</a>
            </p>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            {self._get_base_styles()}
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">ExamCraft AI</div>
                </div>
                <div class="content">
                    <p>Hi <strong>{user_name}</strong>,</p>
                    <div>{message}</div>
                    {action_button}
                </div>
                <div class="footer">
                    <p>&copy; 2025 ExamCraft AI. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
