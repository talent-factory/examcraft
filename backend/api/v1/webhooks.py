import stripe
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from sqlalchemy.orm import Session
import os
import logging
from database import get_db
from models.subscription import Subscription, SubscriptionStatus
from models.auth import Institution, User, Role, UserRole
from utils.billing_utils import get_tier_from_price_id
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
router = APIRouter()


def _extract_price_id(stripe_sub: stripe.Subscription, sub_id: str) -> str:
    """Pull the first item's price id off a Stripe Subscription, with explicit errors."""
    items = getattr(stripe_sub, "items", None)
    items_data = getattr(items, "data", None) or []
    if not items_data:
        raise ValueError(
            f"Stripe subscription {sub_id} has no items — cannot determine price"
        )
    price = getattr(items_data[0], "price", None)
    price_id = getattr(price, "id", None) if price is not None else None
    if not price_id:
        raise ValueError(f"Stripe subscription {sub_id} item has no price id")
    return price_id


def _require_status(stripe_obj, sub_id: str) -> str:
    """Read a Stripe Subscription's status attribute, raising a clean ValueError if missing."""
    status_value = getattr(stripe_obj, "status", None)
    if not status_value:
        raise ValueError(f"Stripe subscription {sub_id} is missing status")
    return status_value


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

    if not endpoint_secret:
        logger.error("STRIPE_WEBHOOK_SECRET is not configured — rejecting webhook")
        raise HTTPException(status_code=500, detail="Webhook endpoint not configured")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event.type
    event_object = event.data.object

    logger.info(f"Received Stripe event: {event_type}")

    try:
        if event_type == "checkout.session.completed":
            await handle_checkout_session_completed(event_object, db)
        elif event_type == "customer.subscription.created":
            await handle_subscription_created(event_object, db)
        elif event_type == "customer.subscription.updated":
            await handle_subscription_updated(event_object, db)
        elif event_type == "customer.subscription.deleted":
            await handle_subscription_deleted(event_object, db)
    except ValueError as e:
        # Return 200 to prevent Stripe from retrying — this is a config/data error
        # that won't resolve on retry (e.g., unknown price_id, missing metadata)
        logger.critical(
            "Webhook data error for %s (acknowledged, no retry): %s",
            event_type,
            e,
            exc_info=True,
        )
        return {"status": "error", "message": str(e)}
    except stripe.error.StripeError as e:
        logger.error(
            "Stripe API error during webhook %s: %s", event_type, e, exc_info=True
        )
        raise HTTPException(status_code=502, detail="Upstream payment provider error")
    except Exception as e:
        logger.error(
            "Unexpected error handling webhook %s: %s: %s",
            event_type,
            type(e).__name__,
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Webhook processing failed")

    return {"status": "success"}


async def handle_checkout_session_completed(
    session: stripe.checkout.Session, db: Session
):
    """
    Handle successful checkout
    Create/Update subscription and link to Institution
    """

    logger.info("handle_checkout_session_completed() called")

    metadata = session.metadata or {}
    institution_id = metadata.get("institution_id")
    user_id = metadata.get("user_id")

    logger.debug(f"Metadata: institution_id={institution_id}, user_id={user_id}")

    if not institution_id:
        logger.error("No institution_id in session metadata")
        raise ValueError("No institution_id in session metadata")

    session_mode = session.mode
    logger.debug(f"Session mode: {session_mode}")

    if session_mode == "subscription":
        subscription_id = session.subscription
        customer_id = session.customer
        logger.debug(f"Subscription ID: {subscription_id}, Customer ID: {customer_id}")

        institution = (
            db.query(Institution).filter(Institution.id == int(institution_id)).first()
        )
        if not institution:
            logger.error(f"Institution {institution_id} not found")
            raise ValueError(f"Institution {institution_id} not found")

        logger.info(f"Institution found: {institution.name} (ID: {institution.id})")

        try:
            stripe_sub = stripe.Subscription.retrieve(subscription_id)
        except stripe.error.StripeError as e:
            logger.error(
                "Failed to retrieve Stripe subscription %s during checkout: %s",
                subscription_id,
                e,
                exc_info=True,
            )
            raise

        price_id = _extract_price_id(stripe_sub, subscription_id)
        status_value = _require_status(stripe_sub, subscription_id)

        logger.debug(f"Stripe subscription status: {status_value}")

        existing_sub = (
            db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == subscription_id)
            .first()
        )

        period_start_ts = getattr(stripe_sub, "current_period_start", None)
        period_end_ts = getattr(stripe_sub, "current_period_end", None)
        cancel_at_period_end = bool(getattr(stripe_sub, "cancel_at_period_end", False))
        period_start = (
            datetime.fromtimestamp(period_start_ts, tz=timezone.utc)
            if period_start_ts is not None
            else None
        )
        period_end = (
            datetime.fromtimestamp(period_end_ts, tz=timezone.utc)
            if period_end_ts is not None
            else None
        )

        if existing_sub:
            existing_sub.status = SubscriptionStatus(status_value)
            existing_sub.stripe_price_id = price_id
            if not existing_sub.billing_owner_id and user_id:
                existing_sub.billing_owner_id = int(user_id)
            if period_start is not None:
                existing_sub.current_period_start = period_start
            if period_end is not None:
                existing_sub.current_period_end = period_end
            existing_sub.cancel_at_period_end = cancel_at_period_end
            logger.info(f"Updated existing subscription {subscription_id}")
        else:
            new_sub = Subscription(
                institution_id=institution.id,
                billing_owner_id=int(user_id) if user_id else None,
                stripe_subscription_id=subscription_id,
                stripe_customer_id=customer_id,
                stripe_price_id=price_id,
                status=SubscriptionStatus(status_value),
                current_period_start=period_start,
                current_period_end=period_end,
                cancel_at_period_end=cancel_at_period_end,
            )
            db.add(new_sub)
            logger.info(f"Created new subscription {subscription_id}")

        new_tier = get_tier_from_price_id(price_id)

        institution.subscription_tier = new_tier

        from utils.tenant_utils import sync_institution_quotas

        sync_institution_quotas(institution, db)

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


async def handle_subscription_created(subscription: stripe.Subscription, db: Session):
    """
    Handle new subscription creation.
    Update period fields that may not be available in checkout.session.completed.
    """
    sub_id = subscription.id
    local_sub = (
        db.query(Subscription)
        .filter(Subscription.stripe_subscription_id == sub_id)
        .first()
    )

    if local_sub:
        status_value = _require_status(subscription, sub_id)
        period_start_ts = getattr(subscription, "current_period_start", None)
        period_end_ts = getattr(subscription, "current_period_end", None)

        if period_start_ts is not None:
            local_sub.current_period_start = datetime.fromtimestamp(
                period_start_ts, tz=timezone.utc
            )
        if period_end_ts is not None:
            local_sub.current_period_end = datetime.fromtimestamp(
                period_end_ts, tz=timezone.utc
            )

        local_sub.status = SubscriptionStatus(status_value)
        local_sub.cancel_at_period_end = bool(
            getattr(subscription, "cancel_at_period_end", False)
        )

        logger.info(
            f"Subscription created {sub_id}: status={status_value}, "
            f"period_start={period_start_ts}, period_end={period_end_ts}"
        )

        db.commit()
    else:
        logger.warning(
            f"Subscription {sub_id} not found locally during subscription.created event. "
            f"This may indicate the checkout.session.completed webhook failed."
        )


async def handle_subscription_updated(subscription: stripe.Subscription, db: Session):
    """Sync subscription status updates"""
    sub_id = subscription.id
    local_sub = (
        db.query(Subscription)
        .filter(Subscription.stripe_subscription_id == sub_id)
        .first()
    )

    if local_sub:
        status_value = _require_status(subscription, sub_id)
        period_start_ts = getattr(subscription, "current_period_start", None)
        period_end_ts = getattr(subscription, "current_period_end", None)

        local_sub.status = SubscriptionStatus(status_value)
        if period_start_ts is not None:
            local_sub.current_period_start = datetime.fromtimestamp(
                period_start_ts, tz=timezone.utc
            )
        if period_end_ts is not None:
            local_sub.current_period_end = datetime.fromtimestamp(
                period_end_ts, tz=timezone.utc
            )
        local_sub.cancel_at_period_end = bool(
            getattr(subscription, "cancel_at_period_end", False)
        )

        logger.info(
            f"Updated subscription {sub_id}: status={status_value}, "
            f"period_start={period_start_ts}, period_end={period_end_ts}"
        )

        # Sync tier from price_id
        items = getattr(subscription, "items", None)
        items_data = getattr(items, "data", None) or []
        if items_data:
            first_price = getattr(items_data[0], "price", None)
            price_id = getattr(first_price, "id", None) if first_price else None
            if price_id:
                new_tier = get_tier_from_price_id(price_id)
                institution = local_sub.institution
                if institution:
                    old_tier = institution.subscription_tier
                    institution.subscription_tier = new_tier

                    from utils.tenant_utils import sync_institution_quotas

                    sync_institution_quotas(institution, db)

                    logger.info(
                        f"Subscription updated: institution {institution.id} tier {old_tier} -> {new_tier} "
                        f"(price_id: {price_id})"
                    )
                else:
                    logger.error(
                        "Subscription %s has no associated institution — tier update skipped",
                        sub_id,
                    )

        db.commit()
    else:
        logger.warning(
            f"Subscription {sub_id} not found locally during subscription.updated event."
        )


async def handle_subscription_deleted(subscription: stripe.Subscription, db: Session):
    """Handle subscription cancellation"""
    sub_id = subscription.id
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

            from utils.tenant_utils import sync_institution_quotas

            sync_institution_quotas(institution, db)

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
