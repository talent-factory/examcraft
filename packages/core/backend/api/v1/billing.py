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
from models.auth import User, Institution
from models.subscription import Subscription, SubscriptionStatus
from database import get_db

logger = logging.getLogger(__name__)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

router = APIRouter()


class CheckoutRequest(BaseModel):
    price_id: str


class PortalRequest(BaseModel):
    return_url: str


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


def _get_allowed_price_ids() -> set:
    """Get the set of allowed Stripe price IDs from environment variables"""
    price_ids = set()
    for env_var in [
        "REACT_APP_STRIPE_PRICE_STARTER",
        "REACT_APP_STRIPE_PRICE_PROFESSIONAL",
        "REACT_APP_STRIPE_PRICE_ENTERPRISE",
    ]:
        price_id = os.getenv(env_var)
        if price_id:
            price_ids.add(price_id)
    return price_ids


def _get_tier_from_price_id(price_id: str) -> str:
    """Map Stripe price ID to tier name using environment variables"""
    price_to_tier = {
        os.getenv("REACT_APP_STRIPE_PRICE_STARTER", "price_starter_monthly"): "starter",
        os.getenv(
            "REACT_APP_STRIPE_PRICE_PROFESSIONAL", "price_professional_monthly"
        ): "professional",
        os.getenv(
            "REACT_APP_STRIPE_PRICE_ENTERPRISE", "price_enterprise_monthly"
        ): "enterprise",
    }

    tier = price_to_tier.get(price_id)
    if tier:
        return tier

    # Fallback: infer from price_id string
    price_id_lower = price_id.lower()
    if "starter" in price_id_lower:
        return "starter"
    elif "professional" in price_id_lower or "pro" in price_id_lower:
        return "professional"
    elif "enterprise" in price_id_lower:
        return "enterprise"

    return "free"


def _is_billing_owner(user: User, subscription: Subscription) -> bool:
    """
    Check if the user is the billing owner of the subscription.
    Only the billing owner can view invoices, payment methods, and manage the subscription.
    """
    if not subscription:
        return False
    if not subscription.billing_owner_id:
        # No billing owner set - restrict access until backfilled
        logger.warning(
            f"Subscription {subscription.id} has no billing_owner_id set - denying access"
        )
        return False
    return user.id == subscription.billing_owner_id


@router.get("/subscription")
async def get_subscription(
    current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """
    Get current subscription details for the user's institution

    IMPORTANT: The tier is read from institution.subscription_tier (Single Source of Truth)
    This is updated by the Stripe webhook handler when subscriptions change.
    """
    payment_service = PaymentService()

    # Check if user has an institution
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

    # Get institution to read subscription_tier (Single Source of Truth)
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

    # Get subscription from database (LATEST one)
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
        .order_by(Subscription.created_at.desc())  # Get most recent subscription
        .first()
    )

    if not subscription:
        # No active subscription - return institution tier
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

    # Fetch subscription details from Stripe (includes price the user actually pays)
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

            # Get price details from the Stripe subscription (what the user actually pays)
            if stripe_data.get("plan"):
                plan_details = stripe_data["plan"]
        except Exception as e:
            # Continue with database data if Stripe fails
            logger.warning(f"Failed to fetch Stripe subscription details: {e}")

    # Return database data with institution tier (primary source of truth)
    return {
        "id": subscription.stripe_subscription_id,
        "status": subscription.status.value,
        "tier": institution.subscription_tier or "free",  # Single Source of Truth
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

    # Check if user has an institution
    if not current_user.institution_id:
        return []

    # Get subscription to find customer ID
    subscription = (
        db.query(Subscription)
        .filter(Subscription.institution_id == current_user.institution_id)
        .first()
    )

    if not subscription or not subscription.stripe_customer_id:
        return []

    # Check if user is the billing owner
    if not _is_billing_owner(current_user, subscription):
        logger.info(
            f"User {current_user.id} denied access to invoices - not billing owner"
        )
        return []  # Return empty list instead of error for non-billing owners

    try:
        invoices = await payment_service.get_invoices(
            subscription.stripe_customer_id, limit=limit
        )
        return invoices
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/payment-methods", response_model=List[PaymentMethodResponse])
async def get_payment_methods(
    current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """
    Get payment methods for the user's institution.
    Only the billing owner can view payment methods.
    """
    payment_service = PaymentService()

    if not payment_service.is_available():
        raise HTTPException(status_code=503, detail="Payment service is not configured")

    # Check if user has an institution
    if not current_user.institution_id:
        return []

    # Get subscription to find customer ID
    subscription = (
        db.query(Subscription)
        .filter(Subscription.institution_id == current_user.institution_id)
        .first()
    )

    if not subscription or not subscription.stripe_customer_id:
        return []

    # Check if user is the billing owner
    if not _is_billing_owner(current_user, subscription):
        logger.info(
            f"User {current_user.id} denied access to payment methods - not billing owner"
        )
        return []  # Return empty list instead of error for non-billing owners

    try:
        payment_methods = await payment_service.get_payment_methods(
            subscription.stripe_customer_id
        )
        return payment_methods
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/customer-portal")
async def create_customer_portal(
    request: PortalRequest,
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

    # Check if user has an institution
    if not current_user.institution_id:
        raise HTTPException(
            status_code=400, detail="User must be associated with an institution"
        )

    # Get subscription to find customer ID
    subscription = (
        db.query(Subscription)
        .filter(Subscription.institution_id == current_user.institution_id)
        .first()
    )

    if not subscription or not subscription.stripe_customer_id:
        raise HTTPException(
            status_code=404, detail="No subscription found for this institution"
        )

    # Check if user is the billing owner
    if not _is_billing_owner(current_user, subscription):
        logger.warning(
            f"User {current_user.id} denied access to customer portal - not billing owner"
        )
        raise HTTPException(
            status_code=403,
            detail="Only the billing owner can manage subscription settings",
        )

    try:
        session = await payment_service.create_customer_portal_session(
            stripe_customer_id=subscription.stripe_customer_id,
            return_url=request.return_url,
        )
        return session
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/create-checkout-session")
async def create_checkout_session(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe Checkout Session for the current user's institution

    Requires authentication and active user status.
    The success/cancel URLs are constructed server-side for security.
    """
    payment_service = PaymentService()

    if not payment_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Payment service is not configured (missing STRIPE_SECRET_KEY)",
        )

    # Check if user has an institution
    if not current_user.institution_id:
        raise HTTPException(
            status_code=400,
            detail="User must be associated with an institution to subscribe",
        )

    # Validate price_id against allowed prices
    allowed_prices = _get_allowed_price_ids()
    if allowed_prices and request.price_id not in allowed_prices:
        raise HTTPException(
            status_code=400,
            detail="Invalid price ID. Please select a valid subscription plan.",
        )

    # Construct redirect URLs server-side (prevents open redirect)
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
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sync-subscription")
async def sync_subscription_from_stripe(
    current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """
    Sync subscription from Stripe to local database.

    This endpoint is useful when webhooks fail or for local development.
    It searches for active subscriptions in Stripe by customer email
    and syncs them to the local database.
    """
    payment_service = PaymentService()

    if not payment_service.is_available():
        raise HTTPException(status_code=503, detail="Payment service is not configured")

    if not current_user.institution_id:
        raise HTTPException(
            status_code=400, detail="User must be associated with an institution"
        )

    # Get institution
    institution = (
        db.query(Institution)
        .filter(Institution.id == current_user.institution_id)
        .first()
    )

    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    try:
        # Initialize Stripe API key
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

        if not stripe.api_key:
            raise HTTPException(status_code=503, detail="Stripe API key not configured")

        # Search for Stripe customer by email
        customers = stripe.Customer.list(email=current_user.email, limit=1)

        if not customers.data:
            return {
                "status": "no_customer",
                "message": "No Stripe customer found for this email",
                "synced": False,
            }

        customer = customers.data[0]
        customer_id = customer.id

        # Get active subscriptions for this customer
        subscriptions = stripe.Subscription.list(
            customer=customer_id, status="active", limit=1
        )

        if not subscriptions.data:
            # Check for trialing subscriptions
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

        # Check if subscription already exists in DB
        existing_sub = (
            db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == stripe_sub.id)
            .first()
        )

        if existing_sub:
            # Update existing
            existing_sub.status = SubscriptionStatus(stripe_sub.status)
            existing_sub.stripe_price_id = price_id
            existing_sub.current_period_start = datetime.fromtimestamp(
                stripe_sub.current_period_start, tz=timezone.utc
            )
            existing_sub.current_period_end = datetime.fromtimestamp(
                stripe_sub.current_period_end, tz=timezone.utc
            )
            existing_sub.cancel_at_period_end = stripe_sub.cancel_at_period_end
            # Set billing_owner_id if not already set
            if not existing_sub.billing_owner_id:
                existing_sub.billing_owner_id = current_user.id
            logger.info(f"Updated subscription {stripe_sub.id}")
        else:
            # Create new subscription record
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

        # Map price ID to tier (uses env vars internally)
        tier = _get_tier_from_price_id(price_id) if price_id else "free"

        # Update institution tier
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

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error during sync: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error syncing subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))
