import stripe
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from sqlalchemy.orm import Session
import os
import logging
from database import get_db
from models.subscription import Subscription, SubscriptionStatus
from models.auth import Institution, User, Role, UserRole
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Stripe API Key setzen (notwendig fuer stripe.Subscription.retrieve() etc.)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
router = APIRouter()


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: Session = Depends(get_db),
):
    """
    Handle Stripe Webhooks
    Syncs Stripe events with local database
    """
    payload = await request.body()
    sig_header = stripe_signature
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    logger.info(f"Received Stripe event: {event['type']}")

    # Handle the event - return 500 on transient errors so Stripe retries
    try:
        if event["type"] == "checkout.session.completed":
            await handle_checkout_session_completed(event["data"]["object"], db)
        elif event["type"] == "customer.subscription.created":
            await handle_subscription_created(event["data"]["object"], db)
        elif event["type"] == "customer.subscription.updated":
            await handle_subscription_updated(event["data"]["object"], db)
        elif event["type"] == "customer.subscription.deleted":
            await handle_subscription_deleted(event["data"]["object"], db)
    except Exception as e:
        logger.error(f"Error handling webhook {event['type']}: {str(e)}", exc_info=True)
        # Return 500 so Stripe retries the webhook for transient failures
        raise HTTPException(status_code=500, detail="Webhook processing failed")

    return {"status": "success"}


async def handle_checkout_session_completed(session: dict, db: Session):
    """
    Handle successful checkout
    Create/Update subscription and link to Institution
    """
    # Import shared tier mapping function
    from api.v1.billing import _get_tier_from_price_id

    logger.info("handle_checkout_session_completed() called")

    # Get institution_id and user_id from metadata (set during checkout session creation)
    metadata = session.get("metadata", {})
    institution_id = metadata.get("institution_id")
    user_id = metadata.get("user_id")  # Billing owner

    logger.debug(f"Metadata: institution_id={institution_id}, user_id={user_id}")

    if not institution_id:
        logger.error("No institution_id in session metadata")
        return

    # functionality depends on subscription_mode (payment vs subscription)
    session_mode = session.get("mode")
    logger.debug(f"Session mode: {session_mode}")

    if session_mode == "subscription":
        subscription_id = session.get("subscription")
        customer_id = session.get("customer")
        logger.debug(f"Subscription ID: {subscription_id}, Customer ID: {customer_id}")

        # Update Institution
        institution = (
            db.query(Institution).filter(Institution.id == int(institution_id)).first()
        )
        if not institution:
            logger.error(f"Institution {institution_id} not found")
            return

        logger.info(f"Institution found: {institution.name} (ID: {institution.id})")

        # Fetch actual subscription details from Stripe
        stripe_sub = stripe.Subscription.retrieve(subscription_id)
        price_id = stripe_sub["items"]["data"][0]["price"]["id"]

        logger.debug(f"Stripe subscription status: {stripe_sub.get('status')}")

        # Check if subscription already exists
        existing_sub = (
            db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == subscription_id)
            .first()
        )

        if existing_sub:
            # Update existing subscription
            existing_sub.status = SubscriptionStatus(stripe_sub["status"])
            existing_sub.stripe_price_id = price_id
            # Set billing owner if not already set
            if not existing_sub.billing_owner_id and user_id:
                existing_sub.billing_owner_id = int(user_id)
            if "current_period_start" in stripe_sub:
                existing_sub.current_period_start = datetime.fromtimestamp(
                    stripe_sub["current_period_start"], tz=timezone.utc
                )
            if "current_period_end" in stripe_sub:
                existing_sub.current_period_end = datetime.fromtimestamp(
                    stripe_sub["current_period_end"], tz=timezone.utc
                )
            existing_sub.cancel_at_period_end = stripe_sub.get(
                "cancel_at_period_end", False
            )
            logger.info(f"Updated existing subscription {subscription_id}")
        else:
            # Create local Subscription record
            period_start = None
            period_end = None
            if "current_period_start" in stripe_sub:
                period_start = datetime.fromtimestamp(
                    stripe_sub["current_period_start"], tz=timezone.utc
                )
            if "current_period_end" in stripe_sub:
                period_end = datetime.fromtimestamp(
                    stripe_sub["current_period_end"], tz=timezone.utc
                )

            new_sub = Subscription(
                institution_id=institution.id,
                billing_owner_id=int(user_id) if user_id else None,
                stripe_subscription_id=subscription_id,
                stripe_customer_id=customer_id,
                stripe_price_id=price_id,
                status=SubscriptionStatus(stripe_sub["status"]),
                current_period_start=period_start,
                current_period_end=period_end,
                cancel_at_period_end=stripe_sub.get("cancel_at_period_end", False),
            )
            db.add(new_sub)
            logger.info(f"Created new subscription {subscription_id}")

        # Map Price ID to Subscription Tier using shared function
        new_tier = _get_tier_from_price_id(price_id)

        institution.subscription_tier = new_tier
        logger.info(
            f"Updated institution {institution_id} to tier: {new_tier} (price_id: {price_id})"
        )

        # Upgrade billing owner's role to dozent for paid tiers
        if new_tier != "free" and user_id:
            billing_user = db.query(User).filter(User.id == int(user_id)).first()
            if billing_user:
                dozent_role = (
                    db.query(Role).filter(Role.name == UserRole.DOZENT.value).first()
                )
                if dozent_role and not any(
                    r.id == dozent_role.id for r in billing_user.roles
                ):
                    billing_user.roles.append(dozent_role)
                    logger.info(
                        f"Upgraded user {user_id} to dozent role (paid tier: {new_tier})"
                    )

        db.commit()
        logger.info("Database commit successful")
    else:
        logger.warning(f"Session mode is not 'subscription': {session_mode}")


async def handle_subscription_created(subscription: dict, db: Session):
    """
    Handle new subscription creation
    Update period fields that may not be available in checkout.session.completed
    """
    sub_id = subscription["id"]
    local_sub = (
        db.query(Subscription)
        .filter(Subscription.stripe_subscription_id == sub_id)
        .first()
    )

    if local_sub:
        # Update period fields if available
        if "current_period_start" in subscription:
            local_sub.current_period_start = datetime.fromtimestamp(
                subscription["current_period_start"], tz=timezone.utc
            )
        if "current_period_end" in subscription:
            local_sub.current_period_end = datetime.fromtimestamp(
                subscription["current_period_end"], tz=timezone.utc
            )

        local_sub.status = SubscriptionStatus(subscription["status"])
        local_sub.cancel_at_period_end = subscription.get("cancel_at_period_end", False)

        logger.info(
            f"Subscription created {sub_id}: status={subscription['status']}, "
            f"period_start={subscription.get('current_period_start')}, "
            f"period_end={subscription.get('current_period_end')}"
        )

        db.commit()
    else:
        logger.warning(
            f"Subscription {sub_id} not found locally during subscription.created event. "
            f"This may indicate the checkout.session.completed webhook failed."
        )


async def handle_subscription_updated(subscription: dict, db: Session):
    """Sync subscription status updates"""
    sub_id = subscription["id"]
    local_sub = (
        db.query(Subscription)
        .filter(Subscription.stripe_subscription_id == sub_id)
        .first()
    )

    if local_sub:
        local_sub.status = SubscriptionStatus(subscription["status"])

        # Update period fields if available
        if "current_period_start" in subscription:
            local_sub.current_period_start = datetime.fromtimestamp(
                subscription["current_period_start"], tz=timezone.utc
            )
        if "current_period_end" in subscription:
            local_sub.current_period_end = datetime.fromtimestamp(
                subscription["current_period_end"], tz=timezone.utc
            )

        local_sub.cancel_at_period_end = subscription.get("cancel_at_period_end", False)

        logger.info(
            f"Updated subscription {sub_id}: status={subscription['status']}, "
            f"period_start={subscription.get('current_period_start')}, "
            f"period_end={subscription.get('current_period_end')}"
        )

        # Sync Institution Status
        if (
            local_sub.status != SubscriptionStatus.ACTIVE
            and local_sub.status != SubscriptionStatus.TRIALING
        ):
            # For now, just keep status synced. Gating logic can check subscription status.
            pass

        db.commit()
    else:
        logger.warning(
            f"Subscription {sub_id} not found locally during subscription.updated event."
        )


async def handle_subscription_deleted(subscription: dict, db: Session):
    """Handle subscription cancellation"""
    sub_id = subscription["id"]
    local_sub = (
        db.query(Subscription)
        .filter(Subscription.stripe_subscription_id == sub_id)
        .first()
    )

    if local_sub:
        local_sub.status = SubscriptionStatus.CANCELED
        local_sub.ended_at = datetime.now(tz=timezone.utc)

        # Downgrade Institution
        institution = local_sub.institution
        if institution:
            institution.subscription_tier = "free"

        # Downgrade billing owner's role from dozent back to viewer
        if local_sub.billing_owner_id:
            billing_user = (
                db.query(User).filter(User.id == local_sub.billing_owner_id).first()
            )
            if billing_user and not billing_user.has_role("admin"):
                dozent_role = (
                    db.query(Role).filter(Role.name == UserRole.DOZENT.value).first()
                )
                viewer_role = (
                    db.query(Role).filter(Role.name == UserRole.VIEWER.value).first()
                )
                if dozent_role and any(
                    r.id == dozent_role.id for r in billing_user.roles
                ):
                    billing_user.roles.remove(dozent_role)
                if viewer_role and not any(
                    r.id == viewer_role.id for r in billing_user.roles
                ):
                    billing_user.roles.append(viewer_role)
                logger.info(
                    f"Downgraded user {local_sub.billing_owner_id} to viewer role (subscription canceled)"
                )

        db.commit()
    else:
        logger.warning(
            f"Subscription {sub_id} not found locally during subscription.deleted event."
        )
