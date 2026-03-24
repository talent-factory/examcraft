"""
Email Event Model für ExamCraft AI

Tracks all email events from providers (Resend, Kit) for analytics
and deliverability monitoring.
"""

from enum import Enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Enum as SQLEnum,
    JSON,
    Index,
)
from database import Base


class EmailEventType(str, Enum):
    """Email event types from providers"""

    SENT = "sent"
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    OPENED = "opened"
    CLICKED = "clicked"
    SPAM_COMPLAINT = "spam_complaint"
    UNSUBSCRIBED = "unsubscribed"


class EmailType(str, Enum):
    """Types of emails sent"""

    VERIFICATION = "verification"
    PASSWORD_RESET = "password_reset"  # pragma: allowlist secret
    PAYMENT_CONFIRMATION = "payment_confirmation"
    NOTIFICATION = "notification"
    WELCOME = "welcome"
    MARKETING = "marketing"


class EmailEvent(Base):
    """
    Email Event tracking model.

    Stores all email events from providers for:
    - Delivery tracking
    - Analytics
    - Bounce/spam handling
    """

    __tablename__ = "email_events"

    id = Column(Integer, primary_key=True, index=True)

    # Email identification
    email_id = Column(String(255), nullable=False, index=True)
    provider = Column(String(50), nullable=False)  # "resend" or "kit"

    # Event details
    event_type = Column(SQLEnum(EmailEventType), nullable=False)
    email_type = Column(SQLEnum(EmailType), nullable=True)

    # Recipient info (for analytics, stored separately from user)
    recipient_email = Column(String(255), nullable=False, index=True)

    # Timestamps
    event_timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Additional event metadata (provider-specific data, link URLs, etc.)
    # Renamed from 'metadata' to avoid SQLAlchemy reserved attribute conflict
    event_metadata = Column(JSON, nullable=True)

    # Indexes for common queries
    __table_args__ = (
        Index("ix_email_events_recipient_type", "recipient_email", "event_type"),
        Index("ix_email_events_provider_timestamp", "provider", "event_timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<EmailEvent(id={self.id}, email_id={self.email_id}, "
            f"type={self.event_type}, recipient={self.recipient_email})>"
        )


class EmailSuppressionList(Base):
    """
    Email Suppression List.

    Stores emails that should not receive certain types of emails:
    - Hard bounces (permanent delivery failures)
    - Spam complaints
    - Unsubscribes
    """

    __tablename__ = "email_suppression_list"

    id = Column(Integer, primary_key=True, index=True)

    # Email to suppress
    email = Column(String(255), nullable=False, unique=True, index=True)

    # Suppression reason
    reason = Column(
        SQLEnum(EmailEventType),
        nullable=False,
        comment="Reason for suppression (bounced, spam_complaint, unsubscribed)",
    )

    # Scope of suppression
    suppress_transactional = Column(
        Integer,
        default=0,
        nullable=False,
        comment="1 = suppress transactional emails (only for bounces)",
    )
    suppress_marketing = Column(
        Integer,
        default=1,
        nullable=False,
        comment="1 = suppress marketing emails",
    )

    # Metadata
    provider = Column(String(50), nullable=True)
    original_event_id = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<EmailSuppressionList(email={self.email}, reason={self.reason})>"


# Helper functions for suppression list management


async def is_email_suppressed(
    db,
    email: str,
    check_transactional: bool = False,
    check_marketing: bool = True,
) -> bool:
    """
    Check if an email is on the suppression list.

    Args:
        db: Database session
        email: Email to check
        check_transactional: Check for transactional suppression
        check_marketing: Check for marketing suppression

    Returns:
        bool: True if email is suppressed
    """
    query = db.query(EmailSuppressionList).filter(
        EmailSuppressionList.email == email.lower()
    )

    suppression = query.first()
    if not suppression:
        return False

    if check_transactional and suppression.suppress_transactional:
        return True

    if check_marketing and suppression.suppress_marketing:
        return True

    return False


async def add_to_suppression_list(
    db,
    email: str,
    reason: EmailEventType,
    provider: Optional[str] = None,
    event_id: Optional[str] = None,
    suppress_transactional: bool = False,
    suppress_marketing: bool = True,
) -> EmailSuppressionList:
    """
    Add an email to the suppression list.

    Args:
        db: Database session
        email: Email to suppress
        reason: Reason for suppression
        provider: Email provider
        event_id: Original event ID
        suppress_transactional: Also suppress transactional emails
        suppress_marketing: Suppress marketing emails

    Returns:
        EmailSuppressionList: Created or updated suppression entry
    """
    email_lower = email.lower()

    # Check if already exists
    existing = (
        db.query(EmailSuppressionList)
        .filter(EmailSuppressionList.email == email_lower)
        .first()
    )

    if existing:
        # Update existing entry
        existing.reason = reason
        existing.provider = provider
        existing.original_event_id = event_id
        if suppress_transactional:
            existing.suppress_transactional = 1
        if suppress_marketing:
            existing.suppress_marketing = 1
        existing.updated_at = datetime.utcnow()
        db.commit()
        return existing

    # Create new entry
    suppression = EmailSuppressionList(
        email=email_lower,
        reason=reason,
        provider=provider,
        original_event_id=event_id,
        suppress_transactional=1 if suppress_transactional else 0,
        suppress_marketing=1 if suppress_marketing else 0,
    )
    db.add(suppression)
    db.commit()
    db.refresh(suppression)

    return suppression
