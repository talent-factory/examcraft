"""
Email Service using SubscribeFlow API (TF-764)

Handles the transactional email types that are actually wired into the
app: verification, welcome, impersonation-started, impersonation-ended.
Templates and their HTML rendering (incl. autoescaping of user-supplied
values, replacing the manual html.escape() calls TF-742/TF-762 added)
live in SubscribeFlow -- see scripts/provision_subscribeflow_email.py.
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import secrets

from subscribeflow import SubscribeFlowClient

logger = logging.getLogger(__name__)

# SubscribeFlow Configuration (TF-764)
# Named after the env var it actually reads, not "SUBSCRIBEFLOW_API_KEY" --
# that's a DIFFERENT, more broadly-scoped admin key used only by
# scripts/provision_subscribeflow_email.py and services/subscribeflow_service.py.
# A same-ish name here previously invited exactly the wrong kind of "fix".
SUBSCRIBEFLOW_EMAILS_API_KEY = os.getenv("SUBSCRIBEFLOW_EMAILS_API_KEY", "")
SUBSCRIBEFLOW_BASE_URL = os.getenv(
    "SUBSCRIBEFLOW_BASE_URL", "https://api.subscribeflow.net"
)

# Frontend URL for email links
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


class EmailService:
    """Service for sending transactional emails via SubscribeFlow"""

    @staticmethod
    async def _send(
        template_slug: str,
        to: str,
        variables: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a templated transactional email via SubscribeFlow.

        Args:
            template_slug: Slug of the SubscribeFlow template to use.
            to: Recipient email address.
            variables: Raw (unescaped) template variables -- SubscribeFlow's
                sandboxed Jinja2 environment autoescapes on render, so
                pre-escaping here would double-escape.
            idempotency_key: Optional key passed through to the SDK, intended
                to let a Celery retry of the same logical send (e.g. after
                the send itself succeeded but a subsequent step raised)
                dedupe at SubscribeFlow. CAVEAT: as of this migration,
                SubscribeFlow's server-side idempotency check
                (email_send_service.py::_check_idempotency in the
                SubscribeFlow repo) is an unimplemented stub that always
                returns None -- it logs "duplicate sends possible" and does
                not actually dedupe. Passing this key currently has no
                effect; it's forwarded so no ExamCraft-side change is
                needed once SubscribeFlow implements the check for real.

        Returns:
            {"id": ..., "status": ...} -- callers only ever log or pass
            this through, never inspect further fields.

        Raises:
            Exception: propagated from the SDK on network/API errors, same
                as the previous Resend-based ``_send_email``.
        """
        if not SUBSCRIBEFLOW_EMAILS_API_KEY:
            # This is the only place a missing key is discovered, so its
            # log level has to carry the whole alerting story: a WARNING
            # never reaches Sentry (config/sentry.py's LoggingIntegration
            # only sends ERROR+ as events), which would make a misconfigured
            # key in production a *total, silent* transactional-email
            # outage -- every verification/welcome/impersonation send
            # "succeeds" as {"status": "skipped"} with nothing but a
            # scrollback line to notice it. Mirrors the dev/prod split
            # webhooks/subscribeflow_webhooks.py already uses for the
            # analogous missing-webhook-secret case.
            environment = os.getenv("ENVIRONMENT", "production").lower()
            if environment in ("development", "dev", "local"):
                logger.warning(
                    "SUBSCRIBEFLOW_EMAILS_API_KEY not configured, skipping email send"
                )
            else:
                logger.error(
                    "SUBSCRIBEFLOW_EMAILS_API_KEY not configured in "
                    f"{environment} -- skipping email send. This means "
                    "verification/welcome/impersonation emails are NOT "
                    "being sent."
                )
            return {"id": "test-email-id", "status": "skipped"}

        try:
            async with SubscribeFlowClient(
                api_key=SUBSCRIBEFLOW_EMAILS_API_KEY,
                base_url=SUBSCRIBEFLOW_BASE_URL,
                timeout=30.0,
            ) as client:
                response = await client.emails.send(
                    template_slug=template_slug,
                    to=to,
                    variables=variables,
                    idempotency_key=idempotency_key,
                )
            logger.info(
                f"Email queued via SubscribeFlow: send_id={response.id} "
                f"esp_message_id={response.esp_message_id or 'pending'} "
                f"to={to} ({template_slug})"
            )
            # response.id (the send UUID) is the same value the delivery-status
            # webhook falls back to as email_id when esp_message_id isn't set
            # yet (see webhooks/subscribeflow_webhooks.py::_correlation_id) --
            # logging both here keeps a log line and an EmailEvent row joinable.
            return {"id": str(response.id), "status": response.status}
        except Exception as e:
            logger.error(f"Failed to send {template_slug} email to {to}: {str(e)}")
            raise

    @staticmethod
    def generate_verification_token() -> str:
        """Generate a secure verification token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    async def send_verification_email(
        email: str,
        first_name: str,
        verification_token: str,
    ) -> Dict[str, Any]:
        """Send email verification email via the "verification" SubscribeFlow template."""
        verification_url = f"{FRONTEND_URL}/verify-email?token={verification_token}"
        return await EmailService._send(
            template_slug="verification",
            to=email,
            variables={"first_name": first_name, "verification_url": verification_url},
        )

    @staticmethod
    async def send_welcome_email(email: str, first_name: str) -> Dict[str, Any]:
        """Send welcome email after successful verification via the "welcome" template."""
        return await EmailService._send(
            template_slug="welcome",
            to=email,
            variables={
                "first_name": first_name,
                "dashboard_url": f"{FRONTEND_URL}/dashboard",
                "docs_url": f"{FRONTEND_URL}/docs",
            },
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
    async def send_impersonation_ended_email(
        to_email: str,
        to_name: str,
        admin_name: str,
        reason: str,
        started_at: Optional[str],
        ended_at: Optional[str],
        end_reason: str,
        session_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Notify a user that an administrator's impersonation session against
        their account has ended (TF-742), via the "impersonation-ended" template.

        Args:
            session_id: The ``ImpersonationSession.id`` this notification
                belongs to, when known (both production dispatch sites in
                ``auth_service.py`` pass it). Preferred over
                recipient+``started_at`` for the idempotency key below,
                since it's unconditionally unique and doesn't depend on an
                optional/lossy timestamp field. See ``_send``'s docstring
                for the current caveat: SubscribeFlow doesn't yet dedupe on
                this key server-side, so it has no effect today.
        """
        duration = EmailService._format_duration(started_at, ended_at)
        ended_how = (
            "automatically after 30 minutes"
            if end_reason == "timeout"
            else "manually by the administrator"
        )
        idempotency_key = (
            f"impersonation-ended:{session_id}"
            if session_id is not None
            else f"impersonation-ended:{to_email}:{started_at or 'unknown'}"
        )
        return await EmailService._send(
            template_slug="impersonation-ended",
            to=to_email,
            variables={
                "to_name": to_name,
                "admin_name": admin_name,
                "reason": reason,
                "started_at": started_at or "unknown",
                "ended_at": ended_at or "unknown",
                "duration": duration,
                "ended_how": ended_how,
            },
            idempotency_key=idempotency_key,
        )

    @staticmethod
    async def send_impersonation_started_email(
        to_email: str,
        to_name: str,
        admin_name: str,
        reason: str,
        started_at: Optional[str],
        session_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Notify a user in real time that an administrator has started an
        impersonation session on their account (TF-759), via the
        "impersonation-started" template. Sibling of
        ``send_impersonation_ended_email`` -- dispatched at session start
        instead of end; see that method's docstring for why ``session_id``
        is preferred for the idempotency key when available."""
        idempotency_key = (
            f"impersonation-started:{session_id}"
            if session_id is not None
            else f"impersonation-started:{to_email}:{started_at or 'unknown'}"
        )
        return await EmailService._send(
            template_slug="impersonation-started",
            to=to_email,
            variables={
                "to_name": to_name,
                "admin_name": admin_name,
                "reason": reason,
                "started_at": started_at or "unknown",
            },
            idempotency_key=idempotency_key,
        )
