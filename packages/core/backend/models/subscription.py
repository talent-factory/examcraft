from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Enum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import sys
import os

# Add parent directory to path to import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Base


class SubscriptionStatus(str, enum.Enum):
    """Stripe Subscription Status"""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    TRIALING = "trialing"
    UNPAID = "unpaid"
    PAUSED = "paused"


class Subscription(Base):
    """
    Subscription Model
    Stores Stripe subscription details for an Institution.
    """
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Institution Association (One Subscription per Institution usually, but can support history)
    institution_id = Column(
        Integer, 
        ForeignKey("institutions.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )

    # Stripe Identifiers
    stripe_subscription_id = Column(String(255), unique=True, nullable=False, index=True)
    stripe_customer_id = Column(String(255), nullable=False, index=True)
    stripe_price_id = Column(String(255), nullable=False)
    
    # Status
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.INCOMPLETE, nullable=False)
    
    # Period
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship to Institution
    institution = relationship("Institution", back_populates="subscriptions")

    def __repr__(self):
        return f"<Subscription(id={self.id}, status='{self.status}', institution_id={self.institution_id})>"
