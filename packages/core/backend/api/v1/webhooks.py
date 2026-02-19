import stripe
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from sqlalchemy.orm import Session
import os
import logging
from database import get_db
from models.subscription import Subscription, SubscriptionStatus
from models.auth import Institution, User, Role, UserRole
from datetime import datetime

logger = logging.getLogger(__name__)

# Stripe API Key setzen (notwendig für stripe.Subscription.retrieve() etc.)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
router = APIRouter()


@router.get("/test-handler")
async def test_handler(db: Session = Depends(get_db)):
    """Test if handler can be called"""
    print("🔍 TEST ENDPOINT CALLED")
    test_session = {"metadata": {"institution_id": "1"}, "mode": "subscription"}
    await handle_checkout_session_completed(test_session, db)
    return {"status": "test completed"}


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
        # Invalid payload
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Debug: Log received event type
    print(f"🔍 WEBHOOK RECEIVED: {event['type']}")  # Force output to stdout
    logger.info(f"🔍 Received Stripe event: {event['type']}")

    # Handle the event
    try:
        if event["type"] == "checkout.session.completed":
            print("🔍 CALLING CHECKOUT HANDLER")  # Force output to stdout
            logger.info("🔍 Calling handle_checkout_session_completed()")
            await handle_checkout_session_completed(event["data"]["object"], db)
        elif event["type"] == "customer.subscription.created":
            logger.info("🔍 Calling handle_subscription_created()")
            await handle_subscription_created(event["data"]["object"], db)
        elif event["type"] == "customer.subscription.updated":
            logger.info("🔍 Calling handle_subscription_updated()")
            await handle_subscription_updated(event["data"]["object"], db)
        elif event["type"] == "customer.subscription.deleted":
            logger.info("🔍 Calling handle_subscription_deleted()")
            await handle_subscription_deleted(event["data"]["object"], db)
    except Exception as e:
        print(f"❌ ERROR IN WEBHOOK HANDLER: {str(e)}")
        logger.error(f"❌ Error handling webhook: {str(e)}", exc_info=True)
        # Still return 200 to acknowledge receipt

    return {"status": "success"}


async def handle_checkout_session_completed(session: dict, db: Session):
    """
    Handle successful checkout
    Create/Update subscription and link to Institution
    """
    print("🔍 HANDLER STARTED")
    logger.info("🔍 handle_checkout_session_completed() called")
    logger.info(f"🔍 Session object: {session}")

    # Get institution_id and user_id from metadata (set during checkout session creation)
    metadata = session.get("metadata", {})
    institution_id = metadata.get("institution_id")
    user_id = metadata.get("user_id")  # Billing owner

    print(f"🔍 METADATA: {metadata}")
    print(f"🔍 INSTITUTION_ID: {institution_id}")
    print(f"🔍 USER_ID (billing owner): {user_id}")
    logger.info(f"🔍 Metadata: {metadata}")
    logger.info(f"🔍 Institution ID: {institution_id}")
    logger.info(f"🔍 User ID (billing owner): {user_id}")

    if not institution_id:
        print("❌ NO INSTITUTION_ID - ABORTING")
        logger.error("❌ Error: No institution_id in session metadata")
        return

    print("✅ INSTITUTION_ID FOUND, CONTINUING...")

    # functionality depends on subscription_mode (payment vs subscription)
    session_mode = session.get("mode")
    print(f"🔍 SESSION MODE: {session_mode}")
    logger.info(f"🔍 Session mode: {session_mode}")

    if session_mode == "subscription":
        subscription_id = session.get("subscription")
        customer_id = session.get("customer")
        print(f"🔍 SUBSCRIPTION_ID: {subscription_id}, CUSTOMER_ID: {customer_id}")
        logger.info(
            f"🔍 Subscription ID: {subscription_id}, Customer ID: {customer_id}"
        )

        # Update Institution
        institution = (
            db.query(Institution).filter(Institution.id == int(institution_id)).first()
        )
        if not institution:
            print(f"❌ INSTITUTION {institution_id} NOT FOUND")
            logger.error(f"Error: Institution {institution_id} not found")
            return

        print(f"✅ INSTITUTION FOUND: {institution.name}")
        logger.info(f"✅ Institution found: {institution.name} (ID: {institution.id})")

        # Fetch actual subscription details from Stripe
        print(f"🔍 FETCHING STRIPE SUBSCRIPTION: {subscription_id}")
        stripe_sub = stripe.Subscription.retrieve(subscription_id)
        print("✅ STRIPE SUBSCRIPTION FETCHED")
        price_id = stripe_sub["items"]["data"][0]["price"]["id"]

        # Debug: Log subscription object to see available fields
        logger.info(f"🔍 Stripe Subscription Object: {stripe_sub}")
        logger.info(f"🔍 Subscription Status: {stripe_sub.get('status')}")
        logger.info(
            f"🔍 Current Period Start: {stripe_sub.get('current_period_start')}"
        )
        logger.info(f"🔍 Current Period End: {stripe_sub.get('current_period_end')}")

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
                    stripe_sub["current_period_start"]
                )
            if "current_period_end" in stripe_sub:
                existing_sub.current_period_end = datetime.fromtimestamp(
                    stripe_sub["current_period_end"]
                )
            existing_sub.cancel_at_period_end = stripe_sub.get(
                "cancel_at_period_end", False
            )
            logger.info(f"✅ Updated existing subscription {subscription_id}")
        else:
            # Create local Subscription record
            # Handle optional period fields (may not be present in all subscription states)
            period_start = None
            period_end = None
            if "current_period_start" in stripe_sub:
                period_start = datetime.fromtimestamp(
                    stripe_sub["current_period_start"]
                )
            if "current_period_end" in stripe_sub:
                period_end = datetime.fromtimestamp(stripe_sub["current_period_end"])

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
            logger.info(f"✅ Created new subscription {subscription_id}")

        # Map Price ID to Subscription Tier
        # Use REACT_APP_* variables (shared with frontend for consistency)

        # Debug: Log environment variables
        logger.info(
            f"🔍 REACT_APP_STRIPE_PRICE_STARTER: {os.getenv('REACT_APP_STRIPE_PRICE_STARTER')}"
        )
        logger.info(
            f"🔍 REACT_APP_STRIPE_PRICE_PROFESSIONAL: {os.getenv('REACT_APP_STRIPE_PRICE_PROFESSIONAL')}"
        )
        logger.info(
            f"🔍 REACT_APP_STRIPE_PRICE_ENTERPRISE: {os.getenv('REACT_APP_STRIPE_PRICE_ENTERPRISE')}"
        )

        tier_mapping = {
            os.getenv(
                "REACT_APP_STRIPE_PRICE_STARTER", "price_starter_monthly"
            ): "starter",
            os.getenv(
                "REACT_APP_STRIPE_PRICE_PROFESSIONAL", "price_professional_monthly"
            ): "professional",
            os.getenv(
                "REACT_APP_STRIPE_PRICE_ENTERPRISE", "price_enterprise_monthly"
            ): "enterprise",
        }

        logger.info(f"🔍 tier_mapping: {tier_mapping}")
        logger.info(f"🔍 Received price_id: {price_id}")

        # Determine tier from price_id
        new_tier = tier_mapping.get(price_id)

        # If no exact match, try to infer from price_id string
        if not new_tier:
            price_id_lower = price_id.lower()
            if "starter" in price_id_lower:
                new_tier = "starter"
            elif "professional" in price_id_lower or "pro" in price_id_lower:
                new_tier = "professional"
            elif "enterprise" in price_id_lower:
                new_tier = "enterprise"
            else:
                # Default to free for unknown prices (never grant paid tier accidentally)
                new_tier = "free"
                logger.warning(
                    f"⚠️  Unknown price_id {price_id}, defaulting to free tier"
                )

        institution.subscription_tier = new_tier
        print(f"✅ UPDATING INSTITUTION TIER TO: {new_tier}")
        logger.info(
            f"✅ Updated institution {institution_id} to tier: {new_tier} (price_id: {price_id})"
        )

        # Upgrade billing owner's role to dozent for paid tiers
        if new_tier != "free" and user_id:
            billing_user = db.query(User).filter(User.id == int(user_id)).first()
            if billing_user:
                dozent_role = (
                    db.query(Role).filter(Role.name == UserRole.DOZENT.value).first()
                )
                if dozent_role and dozent_role not in billing_user.roles:
                    billing_user.roles.append(dozent_role)
                    logger.info(
                        f"✅ Upgraded user {user_id} to dozent role (paid tier: {new_tier})"
                    )

        db.commit()
        print("✅ DATABASE COMMIT SUCCESSFUL")
        logger.info("✅ Database commit successful")
    else:
        print(f"⚠️ SESSION MODE IS NOT 'subscription': {session_mode}")
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
                subscription["current_period_start"]
            )
        if "current_period_end" in subscription:
            local_sub.current_period_end = datetime.fromtimestamp(
                subscription["current_period_end"]
            )

        local_sub.status = SubscriptionStatus(subscription["status"])
        local_sub.cancel_at_period_end = subscription.get("cancel_at_period_end", False)

        logger.info(
            f"✅ Subscription created {sub_id}: status={subscription['status']}, "
            f"period_start={subscription.get('current_period_start')}, "
            f"period_end={subscription.get('current_period_end')}"
        )

        db.commit()


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
                subscription["current_period_start"]
            )
        if "current_period_end" in subscription:
            local_sub.current_period_end = datetime.fromtimestamp(
                subscription["current_period_end"]
            )

        local_sub.cancel_at_period_end = subscription.get("cancel_at_period_end", False)

        logger.info(
            f"✅ Updated subscription {sub_id}: status={subscription['status']}, "
            f"period_start={subscription.get('current_period_start')}, "
            f"period_end={subscription.get('current_period_end')}"
        )

        # Sync Institution Status
        if (
            local_sub.status != SubscriptionStatus.ACTIVE
            and local_sub.status != SubscriptionStatus.TRIALING
        ):
            # Downgrade or suspend?
            # For now, just keep status synced. Gating logic can check subscription status.
            pass

        db.commit()


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
        local_sub.ended_at = datetime.now()

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
                if dozent_role and dozent_role in billing_user.roles:
                    billing_user.roles.remove(dozent_role)
                if viewer_role and viewer_role not in billing_user.roles:
                    billing_user.roles.append(viewer_role)
                logger.info(
                    f"✅ Downgraded user {local_sub.billing_owner_id} to viewer role (subscription canceled)"
                )

        db.commit()
