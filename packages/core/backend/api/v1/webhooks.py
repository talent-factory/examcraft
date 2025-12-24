import stripe
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from sqlalchemy.orm import Session
import os
from database import get_db
from models.subscription import Subscription, SubscriptionStatus
from models.auth import Institution, User
from datetime import datetime

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
    # client_reference_id should contain Institution ID
    institution_id = session.get("client_reference_id")
    if not institution_id:
        print("Error: No client_reference_id in session")
        return

    # functionality depends on subscription_mode (payment vs subscription)
    if session.get("mode") == "subscription":
        subscription_id = session.get("subscription")
        customer_id = session.get("customer")
        
        # Determine plan based on metadata or price
        # In this simple version, we trust the checkout session resulted in a subscription
        
        # Update Institution
        institution = db.query(Institution).filter(Institution.id == institution_id).first()
        if institution:
            # Create local Subscription record
            new_sub = Subscription(
                institution_id=institution.id,
                stripe_subscription_id=subscription_id,
                stripe_customer_id=customer_id,
                stripe_price_id=session.get("amount_total"), # Warning: This is amount, not price ID. Need to fetch sub details or line items.
                status=SubscriptionStatus.ACTIVE
            )
            # Fetch actual subscription details to get dates
            stripe_sub = stripe.Subscription.retrieve(subscription_id)
            new_sub.stripe_price_id = stripe_sub["items"]["data"][0]["price"]["id"]
            new_sub.status = SubscriptionStatus(stripe_sub["status"])
            new_sub.current_period_end = datetime.fromtimestamp(stripe_sub["current_period_end"])
            
            db.add(new_sub)
            
            # Upgrade Institution Tier
            # Logic to map Price ID to Tier needed. For now assuming "starter" if purchase happened.
            # Ideally metadata contains tier info.
            # Or use settings map.
            institution.subscription_tier = "starter" # Placeholder logic
            
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
