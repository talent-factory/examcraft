import stripe
import os
import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from services.payment_service import PaymentService
from utils.auth_utils import get_current_active_user
from utils.billing_utils import get_allowed_price_ids, get_tier_from_price_id
from models.auth import User, Institution
from models.subscription import Subscription, SubscriptionStatus
from database import get_db

logger = logging.getLogger(__name__)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

router = APIRouter()


class CheckoutRequest(BaseModel):
    price_id: str


class SubscriptionResponse(BaseModel):
    id: str
    status: str
    tier: str
    current_period_start: Optional[str]
    current_period_end: Optional[str]
    cancel_at_period_end: bool
    canceled_at: Optional[str]
    plan: Optional[dict]
    default_payment_method: Optional[dict]


class InvoiceResponse(BaseModel):
    id: str
    number: Optional[str]
    status: str
    amount_due: float
    amount_paid: float
    currency: str
    created: str
    due_date: Optional[str]
    paid_at: Optional[str]
    invoice_pdf: Optional[str]
    hosted_invoice_url: Optional[str]


class PaymentMethodResponse(BaseModel):
    id: str
    type: str
    card: Optional[dict]


def _is_billing_owner(user: User, subscription: Subscription) -> bool:
    """
    Check if the user is the billing owner of the subscription.
    Only the billing owner can view invoices, payment methods, and manage the subscription.
    """
    if not subscription:
        return False
    if not subscription.billing_owner_id:
        logger.warning(
            f"Subscription {subscription.id} has no billing_owner_id set - denying access"
        )
        return False
    return user.id == subscription.billing_owner_id


@router.get("/subscription")
async def get_subscription(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get current subscription details for the user's institution.

    The tier is read from institution.subscription_tier (Single Source of Truth).
    """
    payment_service = PaymentService()

    if not current_user.institution_id:
        return {
            "id": None,
            "status": "free",
            "tier": "free",
            "current_period_start": None,
            "current_period_end": None,
            "cancel_at_period_end": False,
            "canceled_at": None,
            "plan": None,
            "default_payment_method": None,
            "is_billing_owner": False,
        }

    institution = (
        db.query(Institution)
        .filter(Institution.id == current_user.institution_id)
        .first()
    )
    if not institution:
        logger.error(
            f"Institution {current_user.institution_id} not found for user {current_user.id}"
        )
        return {
            "id": None,
            "status": "free",
            "tier": "free",
            "current_period_start": None,
            "current_period_end": None,
            "cancel_at_period_end": False,
            "canceled_at": None,
            "plan": None,
            "default_payment_method": None,
            "is_billing_owner": False,
        }

    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.institution_id == current_user.institution_id,
            Subscription.status.in_(
                [
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.TRIALING,
                    SubscriptionStatus.PAST_DUE,
                ]
            ),
        )
        .order_by(Subscription.created_at.desc())
        .first()
    )

    if not subscription:
        tier = institution.subscription_tier or "free"
        status = "active" if tier != "free" else "free"

        return {
            "id": None,
            "status": status,
            "tier": tier,
            "current_period_start": None,
            "current_period_end": None,
            "cancel_at_period_end": False,
            "canceled_at": None,
            "plan": None,
            "default_payment_method": None,
            "is_billing_owner": False,
        }

    payment_method = None
    plan_details = {
        "id": subscription.stripe_price_id,
        "currency": "CHF",
        "amount": 0,
        "interval": "month",
    }

    if payment_service.is_available() and subscription.stripe_subscription_id:
        try:
            stripe_data = await payment_service.get_subscription(
                subscription.stripe_subscription_id
            )
            payment_method = stripe_data.get("default_payment_method")

            if stripe_data.get("plan"):
                plan_details = stripe_data["plan"]
        except stripe.error.StripeError as e:
            logger.warning(
                "Stripe API unavailable while enriching subscription %s: %s",
                subscription.stripe_subscription_id,
                e,
            )
        except Exception as e:
            logger.error(
                "Unexpected error enriching subscription %s: %s",
                subscription.stripe_subscription_id,
                e,
                exc_info=True,
            )

    return {
        "id": subscription.stripe_subscription_id,
        "status": subscription.status.value,
        "tier": institution.subscription_tier or "free",
        "current_period_start": subscription.current_period_start.isoformat()
        if subscription.current_period_start
        else None,
        "current_period_end": subscription.current_period_end.isoformat()
        if subscription.current_period_end
        else None,
        "cancel_at_period_end": subscription.cancel_at_period_end,
        "canceled_at": subscription.canceled_at.isoformat()
        if subscription.canceled_at
        else None,
        "plan": plan_details,
        "default_payment_method": payment_method,
        "is_billing_owner": _is_billing_owner(current_user, subscription),
    }


@router.get("/invoices", response_model=List[InvoiceResponse])
async def get_invoices(
    limit: int = Query(default=10, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get billing history (invoices) for the user's institution.
    Only the billing owner can view invoices.
    """
    payment_service = PaymentService()

    if not payment_service.is_available():
        raise HTTPException(status_code=503, detail="Payment service is not configured")

    if not current_user.institution_id:
        return []

    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.institution_id == current_user.institution_id,
            Subscription.status.in_(
                [
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.TRIALING,
                    SubscriptionStatus.PAST_DUE,
                ]
            ),
        )
        .order_by(Subscription.created_at.desc())
        .first()
    )

    if not subscription or not subscription.stripe_customer_id:
        return []

    if not _is_billing_owner(current_user, subscription):
        logger.warning(
            "User %s denied access to invoices - not billing owner",
            current_user.id,
        )
        raise HTTPException(
            status_code=403, detail="Only the billing owner can view invoices."
        )

    try:
        invoices = await payment_service.get_invoices(
            subscription.stripe_customer_id, limit=limit
        )
        return invoices
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching invoices: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while fetching invoices. Please try again.",
        )


@router.get("/payment-methods", response_model=List[PaymentMethodResponse])
async def get_payment_methods(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get payment methods for the user's institution.
    Only the billing owner can view payment methods.
    """
    payment_service = PaymentService()

    if not payment_service.is_available():
        raise HTTPException(status_code=503, detail="Payment service is not configured")

    if not current_user.institution_id:
        return []

    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.institution_id == current_user.institution_id,
            Subscription.status.in_(
                [
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.TRIALING,
                    SubscriptionStatus.PAST_DUE,
                ]
            ),
        )
        .order_by(Subscription.created_at.desc())
        .first()
    )

    if not subscription or not subscription.stripe_customer_id:
        return []

    if not _is_billing_owner(current_user, subscription):
        logger.warning(
            "User %s denied access to payment methods - not billing owner",
            current_user.id,
        )
        raise HTTPException(
            status_code=403,
            detail="Only the billing owner can view payment methods.",
        )

    try:
        payment_methods = await payment_service.get_payment_methods(
            subscription.stripe_customer_id
        )
        return payment_methods
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching payment methods: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while fetching payment methods. Please try again.",
        )


@router.post("/customer-portal")
async def create_customer_portal(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe Customer Portal session for managing subscription and payment methods.
    Only the billing owner can access the customer portal.
    """
    payment_service = PaymentService()

    if not payment_service.is_available():
        raise HTTPException(status_code=503, detail="Payment service is not configured")

    if not current_user.institution_id:
        raise HTTPException(
            status_code=400, detail="User must be associated with an institution"
        )

    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.institution_id == current_user.institution_id,
            Subscription.status.in_(
                [
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.TRIALING,
                    SubscriptionStatus.PAST_DUE,
                ]
            ),
        )
        .order_by(Subscription.created_at.desc())
        .first()
    )

    if not subscription or not subscription.stripe_customer_id:
        raise HTTPException(
            status_code=404, detail="No subscription found for this institution"
        )

    if not _is_billing_owner(current_user, subscription):
        logger.warning(
            f"User {current_user.id} denied access to customer portal - not billing owner"
        )
        raise HTTPException(
            status_code=403,
            detail="Only the billing owner can manage subscription settings",
        )

    try:
        return_url = f"{FRONTEND_URL}/subscription"
        session = await payment_service.create_customer_portal_session(
            stripe_customer_id=subscription.stripe_customer_id,
            return_url=return_url,
        )
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating customer portal session: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while creating the portal session. Please try again.",
        )


@router.post("/create-checkout-session")
async def create_checkout_session(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe Checkout Session for the current user's institution.

    Requires authentication and active user status.
    The success/cancel URLs are constructed server-side for security.
    """
    payment_service = PaymentService()

    if not payment_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Payment service is not configured (missing STRIPE_SECRET_KEY)",
        )

    if not current_user.institution_id:
        raise HTTPException(
            status_code=400,
            detail="User must be associated with an institution to subscribe",
        )

    # Prevent duplicate subscriptions
    existing_active = (
        db.query(Subscription)
        .filter(
            Subscription.institution_id == current_user.institution_id,
            Subscription.status.in_(
                [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]
            ),
        )
        .first()
    )
    if existing_active:
        raise HTTPException(
            status_code=409,
            detail="Institution already has an active subscription. Use the subscription management page to change plans.",
        )

    # Validate price_id against allowed prices (fail-closed)
    allowed_prices = get_allowed_price_ids()
    if not allowed_prices:
        logger.error(
            "No allowed Stripe price IDs configured - STRIPE_PRICE_* env vars missing"
        )
        raise HTTPException(
            status_code=503,
            detail="Subscription plans are not configured. Please contact support.",
        )
    if request.price_id not in allowed_prices:
        raise HTTPException(
            status_code=400,
            detail="Invalid price ID. Please select a valid subscription plan.",
        )

    success_url = f"{FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{FRONTEND_URL}/billing/cancel"

    try:
        session = await payment_service.create_checkout_session(
            price_id=request.price_id,
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=current_user.email,
            metadata={
                "institution_id": str(current_user.institution_id),
                "user_id": str(current_user.id),
                "user_email": current_user.email,
            },
        )
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while creating the checkout session. Please try again.",
        )


@router.post("/sync-subscription")
async def sync_subscription_from_stripe(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Sync subscription from Stripe to local database.

    Useful when webhooks fail or for local development.
    """
    payment_service = PaymentService()

    if not payment_service.is_available():
        raise HTTPException(status_code=503, detail="Payment service is not configured")

    if not current_user.institution_id:
        raise HTTPException(
            status_code=400, detail="User must be associated with an institution"
        )

    institution = (
        db.query(Institution)
        .filter(Institution.id == current_user.institution_id)
        .first()
    )

    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    try:
        if not payment_service.is_available():
            raise HTTPException(status_code=503, detail="Stripe API key not configured")

        customers = stripe.Customer.list(email=current_user.email, limit=1)

        if not customers.data:
            return {
                "status": "no_customer",
                "message": "No Stripe customer found for this email",
                "synced": False,
            }

        customer = customers.data[0]
        customer_id = customer.id

        subscriptions = stripe.Subscription.list(
            customer=customer_id, status="active", limit=1
        )

        if not subscriptions.data:
            subscriptions = stripe.Subscription.list(
                customer=customer_id, status="trialing", limit=1
            )

        if not subscriptions.data:
            return {
                "status": "no_subscription",
                "message": "No active subscription found in Stripe",
                "synced": False,
            }

        stripe_sub = subscriptions.data[0]
        price_id = stripe_sub.items.data[0].price.id if stripe_sub.items.data else None

        existing_sub = (
            db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == stripe_sub.id)
            .first()
        )

        if existing_sub:
            existing_sub.status = SubscriptionStatus(stripe_sub.status)
            existing_sub.stripe_price_id = price_id
            existing_sub.current_period_start = datetime.fromtimestamp(
                stripe_sub.current_period_start, tz=timezone.utc
            )
            existing_sub.current_period_end = datetime.fromtimestamp(
                stripe_sub.current_period_end, tz=timezone.utc
            )
            existing_sub.cancel_at_period_end = stripe_sub.cancel_at_period_end
            if not existing_sub.billing_owner_id:
                stripe_customer_email = customer.get("email", "").lower()
                is_same_institution = (
                    current_user.institution_id == existing_sub.institution_id
                )
                if is_same_institution and (
                    current_user.has_role("admin")
                    or current_user.email.lower() == stripe_customer_email
                ):
                    existing_sub.billing_owner_id = current_user.id
                else:
                    logger.warning(
                        f"User {current_user.id} ({current_user.email}) attempted to claim billing ownership "
                        f"but Stripe customer email is {stripe_customer_email}"
                    )
            logger.info(f"Updated subscription {stripe_sub.id}")
        else:
            new_sub = Subscription(
                institution_id=institution.id,
                billing_owner_id=current_user.id,
                stripe_subscription_id=stripe_sub.id,
                stripe_customer_id=customer_id,
                stripe_price_id=price_id,
                status=SubscriptionStatus(stripe_sub.status),
                current_period_start=datetime.fromtimestamp(
                    stripe_sub.current_period_start, tz=timezone.utc
                ),
                current_period_end=datetime.fromtimestamp(
                    stripe_sub.current_period_end, tz=timezone.utc
                ),
                cancel_at_period_end=stripe_sub.cancel_at_period_end,
            )
            db.add(new_sub)
            logger.info(f"Created subscription {stripe_sub.id}")

        tier = get_tier_from_price_id(price_id) if price_id else "free"

        old_tier = institution.subscription_tier
        institution.subscription_tier = tier

        db.commit()

        logger.info(
            f"Synced subscription for institution {institution.id}: {old_tier} -> {tier}"
        )

        return {
            "status": "success",
            "message": "Subscription synced successfully",
            "synced": True,
            "subscription_id": stripe_sub.id,
            "tier": tier,
            "old_tier": old_tier,
            "price_id": price_id,
        }

    except HTTPException:
        raise
    except ValueError as e:
        logger.error("Tier mapping failed during subscription sync: %s", e, exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Subscription plan configuration error. Please contact support.",
        )
    except stripe.error.StripeError as e:
        logger.error("Stripe error during sync: %s", e, exc_info=True)
        raise HTTPException(
            status_code=400,
            detail="A payment provider error occurred. Please try again.",
        )
    except Exception as e:
        logger.error("Error syncing subscription: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while syncing subscription data. Please try again.",
        )
