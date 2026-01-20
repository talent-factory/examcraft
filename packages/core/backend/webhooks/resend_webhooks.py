"""
Resend Webhook Handler für ExamCraft AI

Handles webhook events from Resend:
- email.delivered
- email.bounced
- email.opened
- email.clicked
- email.complained (spam)

Resend uses Svix for webhook delivery with signature verification.
See: https://resend.com/docs/dashboard/webhooks/introduction
"""

import os
import hmac
import hashlib
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Header, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.email_event import (
    EmailEvent,
    EmailEventType,
    add_to_suppression_list,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_resend_signature(
    payload: bytes,
    signature: str,
    secret: str,
) -> bool:
    """
    Verify Resend webhook signature using Svix format.

    Resend uses Svix for webhook delivery. The signature format is:
    v1,<timestamp>,<signature>

    Args:
        payload: Raw request body
        signature: Svix-Signature header value
        secret: Webhook signing secret

    Returns:
        bool: True if signature is valid
    """
    if not signature or not secret:
        return False

    try:
        # Parse Svix signature format: v1,<timestamp>
        parts = signature.split(",")
        if len(parts) < 2:
            return False

        timestamp = None
        signatures = []

        for part in parts:
            if part.startswith("t="):
                timestamp = part[2:]
            elif part.startswith("v1="):
                signatures.append(part[3:])

        if not timestamp or not signatures:
            return False

        # Construct signed payload: <timestamp>.<payload>
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"

        # Compute expected signature
        expected_signature = hmac.new(
            secret.encode(),
            signed_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Check if any signature matches
        for sig in signatures:
            if hmac.compare_digest(sig, expected_signature):
                return True

        return False

    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


@router.post("/resend")
async def resend_webhook(
    request: Request,
    db: Session = Depends(get_db),
    svix_id: Optional[str] = Header(None, alias="svix-id"),
    svix_timestamp: Optional[str] = Header(None, alias="svix-timestamp"),
    svix_signature: Optional[str] = Header(None, alias="svix-signature"),
):
    """
    Handle Resend webhook events.

    Events:
    - email.sent: Email was sent to the recipient
    - email.delivered: Email was delivered to recipient's inbox
    - email.bounced: Email bounced (permanent or temporary)
    - email.opened: Recipient opened the email
    - email.clicked: Recipient clicked a link
    - email.complained: Recipient marked as spam

    Security:
    - Verifies Svix signature to ensure webhook authenticity
    - Stores all events for audit trail
    - Updates suppression list for bounces/complaints
    - Fails closed in production if RESEND_WEBHOOK_SECRET is not set
    """
    # Get webhook secret
    webhook_secret = os.getenv("RESEND_WEBHOOK_SECRET")

    # Check if we're in development mode
    is_development = os.getenv("ENVIRONMENT", "production").lower() in [
        "development",
        "dev",
        "local",
    ]

    # Get raw payload
    payload = await request.body()

    # Verify signature (fail closed in production)
    if not webhook_secret:
        if is_development:
            logger.warning(
                "RESEND_WEBHOOK_SECRET not set - skipping signature verification (DEVELOPMENT MODE ONLY)"
            )
        else:
            logger.error(
                "RESEND_WEBHOOK_SECRET not set in production - rejecting webhook"
            )
            raise HTTPException(status_code=500, detail="Webhook secret not configured")
    else:
        if not svix_signature:
            logger.warning("Missing Svix-Signature header")
            raise HTTPException(status_code=401, detail="Missing signature")

        signature_string = f"t={svix_timestamp},{svix_signature}"
        if not verify_resend_signature(payload, signature_string, webhook_secret):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse event data
    try:
        event_data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = event_data.get("type")
    data = event_data.get("data", {})

    logger.info(f"Resend webhook received: {event_type}")

    # Route to appropriate handler
    try:
        match event_type:
            case "email.sent":
                await handle_email_sent(db, data, svix_id)

            case "email.delivered":
                await handle_email_delivered(db, data, svix_id)

            case "email.bounced":
                await handle_email_bounced(db, data, svix_id)

            case "email.opened":
                await handle_email_opened(db, data, svix_id)

            case "email.clicked":
                await handle_email_clicked(db, data, svix_id)

            case "email.complained":
                await handle_email_spam_complaint(db, data, svix_id)

            case _:
                logger.warning(f"Unknown Resend event type: {event_type}")

    except Exception as e:
        logger.error(f"Error handling webhook event: {e}", exc_info=True)
        # Don't raise - acknowledge receipt to avoid retries
        # Event will be logged even if handling fails

    return {"status": "ok"}


async def handle_email_sent(db: Session, data: dict, svix_id: Optional[str]) -> None:
    """Track email sent event"""
    email_event = EmailEvent(
        email_id=data.get("email_id", ""),
        provider="resend",
        event_type=EmailEventType.SENT,
        recipient_email=_extract_recipient(data),
        event_timestamp=_parse_timestamp(data.get("created_at")),
        event_metadata={
            "svix_id": svix_id,
            "subject": data.get("subject"),
            "from": data.get("from"),
            "to": data.get("to"),
        },
    )

    db.add(email_event)
    db.commit()
    logger.info(f"Email sent: {email_event.email_id}")


async def handle_email_delivered(
    db: Session, data: dict, svix_id: Optional[str]
) -> None:
    """Track email delivery"""
    email_event = EmailEvent(
        email_id=data.get("email_id", ""),
        provider="resend",
        event_type=EmailEventType.DELIVERED,
        recipient_email=_extract_recipient(data),
        event_timestamp=_parse_timestamp(data.get("created_at")),
        event_metadata={
            "svix_id": svix_id,
            **data,
        },
    )

    db.add(email_event)
    db.commit()
    logger.info(f"Email delivered: {email_event.email_id}")


async def handle_email_bounced(db: Session, data: dict, svix_id: Optional[str]) -> None:
    """
    Handle bounce and potentially add to suppression list.

    Bounce types:
    - Permanent: Hard bounce - email doesn't exist
    - Temporary: Soft bounce - mailbox full, server down, etc.
    """
    recipient = _extract_recipient(data)
    bounce_type = data.get("bounce_type", "unknown")
    bounce_subtype = data.get("bounce_subtype")

    email_event = EmailEvent(
        email_id=data.get("email_id", ""),
        provider="resend",
        event_type=EmailEventType.BOUNCED,
        recipient_email=recipient,
        event_timestamp=_parse_timestamp(data.get("created_at")),
        event_metadata={
            "svix_id": svix_id,
            "bounce_type": bounce_type,
            "bounce_subtype": bounce_subtype,
            **data,
        },
    )

    db.add(email_event)
    db.commit()

    # Add to suppression list if hard bounce
    if bounce_type == "Permanent":
        await add_to_suppression_list(
            db=db,
            email=recipient,
            reason=EmailEventType.BOUNCED,
            provider="resend",
            event_id=data.get("email_id"),
            suppress_transactional=True,  # Can't deliver to this address
            suppress_marketing=True,
        )
        logger.warning(f"Hard bounce - added to suppression list: {recipient}")
    else:
        logger.info(f"Soft bounce (will retry): {recipient}")


async def handle_email_opened(db: Session, data: dict, svix_id: Optional[str]) -> None:
    """Track email open (may be multiple opens)"""
    email_event = EmailEvent(
        email_id=data.get("email_id", ""),
        provider="resend",
        event_type=EmailEventType.OPENED,
        recipient_email=_extract_recipient(data),
        event_timestamp=_parse_timestamp(data.get("created_at")),
        event_metadata={
            "svix_id": svix_id,
            "user_agent": data.get("user_agent"),
            "ip_address": data.get("ip_address"),
            **data,
        },
    )

    db.add(email_event)
    db.commit()
    logger.debug(f"Email opened: {email_event.email_id}")


async def handle_email_clicked(db: Session, data: dict, svix_id: Optional[str]) -> None:
    """Track link click"""
    email_event = EmailEvent(
        email_id=data.get("email_id", ""),
        provider="resend",
        event_type=EmailEventType.CLICKED,
        recipient_email=_extract_recipient(data),
        event_timestamp=_parse_timestamp(data.get("created_at")),
        event_metadata={
            "svix_id": svix_id,
            "link_url": data.get("link"),
            "user_agent": data.get("user_agent"),
            "ip_address": data.get("ip_address"),
            **data,
        },
    )

    db.add(email_event)
    db.commit()
    logger.info(f"Link clicked in email {email_event.email_id}: {data.get('link')}")


async def handle_email_spam_complaint(
    db: Session, data: dict, svix_id: Optional[str]
) -> None:
    """
    Handle spam complaint - add to suppression list.

    Spam complaints are serious - we must not send marketing emails
    to users who complained, and should be cautious with transactional.
    """
    recipient = _extract_recipient(data)

    email_event = EmailEvent(
        email_id=data.get("email_id", ""),
        provider="resend",
        event_type=EmailEventType.SPAM_COMPLAINT,
        recipient_email=recipient,
        event_timestamp=_parse_timestamp(data.get("created_at")),
        event_metadata={
            "svix_id": svix_id,
            **data,
        },
    )

    db.add(email_event)
    db.commit()

    # Add to suppression list - marketing only (transactional still allowed)
    await add_to_suppression_list(
        db=db,
        email=recipient,
        reason=EmailEventType.SPAM_COMPLAINT,
        provider="resend",
        event_id=data.get("email_id"),
        suppress_transactional=False,  # Still allow transactional
        suppress_marketing=True,  # No more marketing
    )

    logger.warning(f"Spam complaint - suppressed marketing: {recipient}")


def _extract_recipient(data: dict) -> str:
    """Extract recipient email from webhook data"""
    to = data.get("to")
    if isinstance(to, list) and to:
        return to[0]
    elif isinstance(to, str):
        return to
    return data.get("email", "unknown@unknown.com")


def _parse_timestamp(timestamp_str: Optional[str]) -> datetime:
    """Parse ISO timestamp from webhook"""
    if not timestamp_str:
        return datetime.utcnow()

    try:
        # Handle various ISO formats
        if timestamp_str.endswith("Z"):
            timestamp_str = timestamp_str[:-1] + "+00:00"
        return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except ValueError:
        return datetime.utcnow()
