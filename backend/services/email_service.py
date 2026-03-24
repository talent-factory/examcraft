"""
Email Service using Resend API
Handles transactional emails: verification, password reset, welcome emails
"""

import os
import logging
import httpx
from typing import Optional, Dict, Any
from datetime import datetime
import secrets

logger = logging.getLogger(__name__)

# Resend Configuration
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "noreply@examcraft.ai")
RESEND_FROM_NAME = os.getenv("RESEND_FROM_NAME", "ExamCraft AI")
RESEND_API_URL = "https://api.resend.com/emails"

# Frontend URL for email links
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


class EmailService:
    """Service for sending transactional emails via Resend"""

    @staticmethod
    def _send_email(
        to: str,
        subject: str,
        html: str,
        text: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Send email via Resend API

        Args:
            to: Recipient email address
            subject: Email subject
            html: HTML email body
            text: Plain text email body (optional)
            tags: Email tags for tracking (optional)

        Returns:
            Response from Resend API

        Raises:
            Exception: If email sending fails
        """
        if not RESEND_API_KEY:
            logger.warning("RESEND_API_KEY not configured, skipping email send")
            return {"id": "test-email-id", "status": "skipped"}

        headers = {
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "from": f"{RESEND_FROM_NAME} <{RESEND_FROM_EMAIL}>",
            "to": [to],
            "subject": subject,
            "html": html,
        }

        if text:
            payload["text"] = text

        if tags:
            payload["tags"] = [{"name": k, "value": v} for k, v in tags.items()]

        try:
            response = httpx.post(
                RESEND_API_URL, headers=headers, json=payload, timeout=10.0
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Email sent successfully to {to}: {result.get('id')}")
            return result
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to send email to {to}: {e.response.text}")
            raise Exception(f"Email sending failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {str(e)}")
            raise

    @staticmethod
    def generate_verification_token() -> str:
        """Generate a secure verification token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def send_verification_email(
        email: str,
        first_name: str,
        verification_token: str,
    ) -> Dict[str, Any]:
        """
        Send email verification email

        Args:
            email: User's email address
            first_name: User's first name
            verification_token: Verification token

        Returns:
            Response from Resend API
        """
        verification_url = f"{FRONTEND_URL}/verify-email?token={verification_token}"

        subject = "Verify your ExamCraft AI account"
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">Welcome to ExamCraft AI! 🎓</h1>
            </div>

            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <p style="font-size: 16px;">Hi {first_name},</p>

                <p style="font-size: 16px;">
                    Thank you for signing up for ExamCraft AI! We're excited to have you on board.
                </p>

                <p style="font-size: 16px;">
                    To get started, please verify your email address by clicking the button below:
                </p>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}"
                       style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                              color: white;
                              padding: 15px 40px;
                              text-decoration: none;
                              border-radius: 5px;
                              font-weight: bold;
                              display: inline-block;">
                        Verify Email Address
                    </a>
                </div>

                <p style="font-size: 14px; color: #666;">
                    Or copy and paste this link into your browser:<br>
                    <a href="{verification_url}" style="color: #667eea; word-break: break-all;">{verification_url}</a>
                </p>

                <p style="font-size: 14px; color: #666; margin-top: 30px;">
                    This link will expire in 24 hours for security reasons.
                </p>

                <p style="font-size: 14px; color: #666;">
                    If you didn't create an account with ExamCraft AI, you can safely ignore this email.
                </p>

                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">

                <p style="font-size: 12px; color: #999; text-align: center;">
                    © {datetime.now().year} ExamCraft AI. All rights reserved.
                </p>
            </div>
        </body>
        </html>
        """

        text = f"""
        Welcome to ExamCraft AI!

        Hi {first_name},

        Thank you for signing up! Please verify your email address by clicking the link below:

        {verification_url}

        This link will expire in 24 hours.

        If you didn't create an account, you can safely ignore this email.

        © {datetime.now().year} ExamCraft AI
        """

        return EmailService._send_email(
            to=email,
            subject=subject,
            html=html,
            text=text,
            tags={"type": "verification"},
        )

    @staticmethod
    def send_welcome_email(email: str, first_name: str) -> Dict[str, Any]:
        """
        Send welcome email after successful verification

        Args:
            email: User's email address
            first_name: User's first name

        Returns:
            Response from Resend API
        """
        subject = "Welcome to ExamCraft AI - Let's Get Started! 🚀"
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">You're All Set! 🎉</h1>
            </div>

            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <p style="font-size: 16px;">Hi {first_name},</p>

                <p style="font-size: 16px;">
                    Your email has been verified successfully! You're now ready to start creating amazing exam questions with AI.
                </p>

                <h2 style="color: #667eea; margin-top: 30px;">What's Next?</h2>

                <ul style="font-size: 16px; line-height: 2;">
                    <li>📄 Upload your first document</li>
                    <li>🤖 Generate AI-powered exam questions</li>
                    <li>✅ Review and refine your questions</li>
                    <li>📝 Export your exam</li>
                </ul>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{FRONTEND_URL}/dashboard"
                       style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                              color: white;
                              padding: 15px 40px;
                              text-decoration: none;
                              border-radius: 5px;
                              font-weight: bold;
                              display: inline-block;">
                        Go to Dashboard
                    </a>
                </div>

                <p style="font-size: 14px; color: #666; margin-top: 30px;">
                    Need help? Check out our <a href="{FRONTEND_URL}/docs" style="color: #667eea;">documentation</a>
                    or contact our support team.
                </p>

                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">

                <p style="font-size: 12px; color: #999; text-align: center;">
                    © {datetime.now().year} ExamCraft AI. All rights reserved.
                </p>
            </div>
        </body>
        </html>
        """

        text = f"""
        You're All Set!

        Hi {first_name},

        Your email has been verified successfully! You're now ready to start creating amazing exam questions with AI.

        What's Next?
        - Upload your first document
        - Generate AI-powered exam questions
        - Review and refine your questions
        - Export your exam

        Get started: {FRONTEND_URL}/dashboard

        © {datetime.now().year} ExamCraft AI
        """

        return EmailService._send_email(
            to=email,
            subject=subject,
            html=html,
            text=text,
            tags={"type": "welcome"},
        )
