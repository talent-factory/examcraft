"""
Email Service using Resend API
Handles transactional emails: verification, password reset, welcome emails
"""

import html
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

        # TF-762: `first_name` is freely chosen at registration and lands in
        # an HTML email delivered to that same address. Without escaping, a
        # crafted name could inject markup into what looks like a trusted
        # ExamCraft notice (same class of issue fixed for
        # `send_impersonation_ended_email` under TF-742). The plain `text`
        # body below is unaffected -- it can't render markup.
        safe_first_name = html.escape(first_name)

        subject = "Verify your ExamCraft AI account"
        html_body = f"""
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
                <p style="font-size: 16px;">Hi {safe_first_name},</p>

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
            html=html_body,
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
        # TF-762: same reasoning as `send_verification_email` above --
        # `first_name` is user-supplied and must not reach the HTML body raw.
        safe_first_name = html.escape(first_name)

        subject = "Welcome to ExamCraft AI - Let's Get Started! 🚀"
        html_body = f"""
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
                <p style="font-size: 16px;">Hi {safe_first_name},</p>

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
            html=html_body,
            text=text,
            tags={"type": "welcome"},
        )

    @staticmethod
    def _format_duration(started_at: Optional[str], ended_at: Optional[str]) -> str:
        """Human-readable session duration from two ISO timestamps.
        Defensive: never raises -- unparsable/missing input just yields the
        "unknown" fallback instead of failing the whole email send.
        """
        if not started_at or not ended_at:
            return "unknown"
        try:
            start = datetime.fromisoformat(started_at)
            end = datetime.fromisoformat(ended_at)
            total_seconds = max(0, int((end - start).total_seconds()))
            minutes, seconds = divmod(total_seconds, 60)
            if minutes and seconds:
                return f"{minutes} min {seconds} sec"
            if minutes:
                return f"{minutes} min"
            return f"{seconds} sec"
        except (ValueError, TypeError):
            return "unknown"

    @staticmethod
    def send_impersonation_ended_email(
        to_email: str,
        to_name: str,
        admin_name: str,
        reason: str,
        started_at: Optional[str],
        ended_at: Optional[str],
        end_reason: str,
    ) -> Dict[str, Any]:
        """
        Notify a user that an administrator's impersonation session against
        their account has ended (TF-742).

        Args:
            to_email: Target user's email address
            to_name: Target user's display name
            admin_name: Display name of the admin who impersonated them
            reason: Reason the admin gave when starting the session
            started_at: ISO timestamp the session started, if known
            ended_at: ISO timestamp the session ended, if known
            end_reason: "manual" or "timeout"

        Returns:
            Response from Resend API
        """
        duration = EmailService._format_duration(started_at, ended_at)
        ended_how = (
            "automatically after 30 minutes"
            if end_reason == "timeout"
            else "manually by the administrator"
        )

        # TF-742 review fix: `reason` is free text the impersonating admin
        # typed (min 3 / max 500 chars, no character restriction -- see
        # ImpersonateRequest in api/admin.py). `admin_name`/`to_name` are
        # also not under this function's control. All three go into an
        # HTML email delivered to a *different* user than the one who
        # supplied them, so they must be escaped before interpolation into
        # `html` -- otherwise an admin could embed markup/links into what
        # looks like a trusted ExamCraft security notice. Mirrors the
        # existing ``html.escape()`` convention in
        # services/moodle_feedback/transports.py:_comment_html. The plain
        # `text` body below is unaffected -- it can't render markup.
        safe_to_name = html.escape(to_name)
        safe_admin_name = html.escape(admin_name)
        safe_reason = html.escape(reason)

        subject = "Your ExamCraft AI account was accessed by an administrator"
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">Account Access Notice</h1>
            </div>

            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <p style="font-size: 16px;">Hi {safe_to_name},</p>

                <p style="font-size: 16px;">
                    An administrator, <strong>{safe_admin_name}</strong>, accessed your
                    ExamCraft AI account on your behalf. This session has now
                    ended, {ended_how}.
                </p>

                <table style="width: 100%; font-size: 14px; margin: 20px 0; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 6px 0; color: #666;">Administrator</td>
                        <td style="padding: 6px 0;"><strong>{safe_admin_name}</strong></td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #666;">Reason given</td>
                        <td style="padding: 6px 0;">{safe_reason}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #666;">Started</td>
                        <td style="padding: 6px 0;">{started_at or "unknown"}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #666;">Ended</td>
                        <td style="padding: 6px 0;">{ended_at or "unknown"}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #666;">Duration</td>
                        <td style="padding: 6px 0;">{duration}</td>
                    </tr>
                </table>

                <p style="font-size: 14px; color: #666; margin-top: 30px;">
                    If you did not expect this, or have any concerns, please
                    contact your institution's administrator or ExamCraft AI
                    support.
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
        Account Access Notice

        Hi {to_name},

        An administrator, {admin_name}, accessed your ExamCraft AI account on
        your behalf. This session has now ended, {ended_how}.

        Administrator: {admin_name}
        Reason given: {reason}
        Started: {started_at or "unknown"}
        Ended: {ended_at or "unknown"}
        Duration: {duration}

        If you did not expect this, or have any concerns, please contact your
        institution's administrator or ExamCraft AI support.

        © {datetime.now().year} ExamCraft AI
        """

        return EmailService._send_email(
            to=to_email,
            subject=subject,
            html=html_body,
            text=text,
            tags={"type": "impersonation_ended"},
        )
