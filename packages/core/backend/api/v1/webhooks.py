import stripe
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from sqlalchemy.orm import Session
import os
import logging
from database import get_db
from models.subscription import Subscription, SubscriptionStatus
from models.auth import Institution, User
from datetime import datetime

logger = logging.getLogger(__name__)

# Stripe API Key setzen (notwendig für stripe.Subscription.retrieve() etc.)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
router = APIRouter()

@router.post("/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None), db: Session = Depends(get_db)):
    """
    Handle Stripe Webhooks
    Syncs Stripe events with local database
    """
    payload = await request.body()
    sig_header = stripe_signature
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event["type"] == "checkout.session.completed":
        await handle_checkout_session_completed(event["data"]["object"], db)
    elif event["type"] == "customer.subscription.updated":
        await handle_subscription_updated(event["data"]["object"], db)
    elif event["type"] == "customer.subscription.deleted":
        await handle_subscription_deleted(event["data"]["object"], db)

    return {"status": "success"}


async def handle_checkout_session_completed(session: dict, db: Session):
    """
    Handle successful checkout
    Create/Update subscription and link to Institution
    """
    # Get institution_id from metadata (set during checkout session creation)
    metadata = session.get("metadata", {})
    institution_id = metadata.get("institution_id")

    if not institution_id:
        logging.error("Error: No institution_id in session metadata")
        return

    # functionality depends on subscription_mode (payment vs subscription)
    if session.get("mode") == "subscription":
        subscription_id = session.get("subscription")
        customer_id = session.get("customer")

        # Update Institution
        institution = db.query(Institution).filter(Institution.id == int(institution_id)).first()
        if not institution:
            Loggin.error(f"Error: Institution {institution_id} not found")
            return

        # Fetch actual subscription details from Stripe
        stripe_sub = stripe.Subscription.retrieve(subscription_id)
        price_id = stripe_sub["items"]["data"][0]["price"]["id"]

        # Check if subscription already exists
        existing_sub = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()

        if existing_sub:
            # Update existing subscription
            existing_sub.status = SubscriptionStatus(stripe_sub["status"])
            existing_sub.stripe_price_id = price_id
            existing_sub.current_period_start = datetime.fromtimestamp(stripe_sub["current_period_start"])
            existing_sub.current_period_end = datetime.fromtimestamp(stripe_sub["current_period_end"])
            logging.error(f"Updated existing subscription {subscription_id}")
        else:
            # Create local Subscription record
            new_sub = Subscription(
                institution_id=institution.id,
                stripe_subscription_id=subscription_id,
                stripe_customer_id=customer_id,
                stripe_price_id=price_id,
                status=SubscriptionStatus(stripe_sub["status"]),
                current_period_start=datetime.fromtimestamp(stripe_sub["current_period_start"]),
                current_period_end=datetime.fromtimestamp(stripe_sub["current_period_end"])
            )
            db.add(new_sub)
            logging.error(f"Created new subscription {subscription_id}")

        # Map Price ID to Subscription Tier
        # TODO: Make this configurable via environment variables or database
        tier_mapping = {
            # Add your actual Stripe Price IDs here after creating products
            # "price_1abc...": "starter",
            # "price_1xyz...": "professional",
        }

        # For now, default to starter if we can't map the price
        new_tier = tier_mapping.get(price_id, "starter")
        institution.subscription_tier = new_tier
        logging.error(f"Updated institution {institution_id} to tier: {new_tier}")

        db.commit()


async def handle_subscription_updated(subscription: dict, db: Session):
    """Sync subscription status updates"""
    sub_id = subscription["id"]
    local_sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == sub_id).first()
    
    if local_sub:
        local_sub.status = SubscriptionStatus(subscription["status"])
        local_sub.current_period_end = datetime.fromtimestamp(subscription["current_period_end"])
        local_sub.cancel_at_period_end = subscription["cancel_at_period_end"]
        
        # Sync Institution Status
        if local_sub.status != SubscriptionStatus.ACTIVE and local_sub.status != SubscriptionStatus.TRIALING:
            # Downgrade or suspend?
            # For now, just keep status synced. Gating logic can check subscription status.
            pass
            
        db.commit()


async def handle_subscription_deleted(subscription: dict, db: Session):
    """Handle subscription cancellation"""
    sub_id = subscription["id"]
    local_sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == sub_id).first()
    
    if local_sub:
        local_sub.status = SubscriptionStatus.CANCELED
        local_sub.ended_at = datetime.now()
        
        # Downgrade Institution
        institution = local_sub.institution
        if institution:
            institution.subscription_tier = "free"
            
        db.commit()
