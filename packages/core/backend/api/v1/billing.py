from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from services.payment_service import PaymentService
from utils.auth_utils import get_current_active_user
from models.auth import User
from models.subscription import Subscription, SubscriptionStatus
from database import get_db

router = APIRouter(prefix="/billing", tags=["Billing"])

class CheckoutRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str

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


def _get_tier_from_price_id(price_id: str) -> str:
    """Map Stripe price ID to tier name"""
    # This mapping should match your Stripe price IDs
    price_to_tier = {
        "price_starter_monthly": "starter",
        "price_professional_monthly": "professional",
    }
    return price_to_tier.get(price_id, "free")


@router.get("/subscription")
async def get_subscription(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current subscription details for the user's institution
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
        }

    # Get subscription from database
    subscription = db.query(Subscription).filter(
        Subscription.institution_id == current_user.institution_id,
        Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING, SubscriptionStatus.PAST_DUE])
    ).first()

    if not subscription:
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
        }

    # If Stripe is available, get live data
    if payment_service.is_available() and subscription.stripe_subscription_id:
        try:
            stripe_data = await payment_service.get_subscription(subscription.stripe_subscription_id)
            stripe_data["tier"] = _get_tier_from_price_id(stripe_data.get("plan", {}).get("id", ""))
            return stripe_data
        except Exception as e:
            # Fall back to database data if Stripe fails
            pass

    return {
        "id": subscription.stripe_subscription_id,
        "status": subscription.status.value,
        "tier": _get_tier_from_price_id(subscription.stripe_price_id),
        "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
        "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        "cancel_at_period_end": subscription.cancel_at_period_end,
        "canceled_at": subscription.canceled_at.isoformat() if subscription.canceled_at else None,
        "plan": {
            "id": subscription.stripe_price_id,
            "currency": "CHF",
        },
        "default_payment_method": None,
    }


@router.get("/invoices", response_model=List[InvoiceResponse])
async def get_invoices(
    limit: int = Query(default=10, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get billing history (invoices) for the user's institution
    """
    payment_service = PaymentService()

    if not payment_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Payment service is not configured"
        )

    # Check if user has an institution
    if not current_user.institution_id:
        return []

    # Get subscription to find customer ID
    subscription = db.query(Subscription).filter(
        Subscription.institution_id == current_user.institution_id
    ).first()

    if not subscription or not subscription.stripe_customer_id:
        return []

    try:
        invoices = await payment_service.get_invoices(
            subscription.stripe_customer_id,
            limit=limit
        )
        return invoices
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/payment-methods", response_model=List[PaymentMethodResponse])
async def get_payment_methods(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get payment methods for the user's institution
    """
    payment_service = PaymentService()

    if not payment_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Payment service is not configured"
        )

    # Check if user has an institution
    if not current_user.institution_id:
        return []

    # Get subscription to find customer ID
    subscription = db.query(Subscription).filter(
        Subscription.institution_id == current_user.institution_id
    ).first()

    if not subscription or not subscription.stripe_customer_id:
        return []

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
    db: Session = Depends(get_db)
):
    """
    Create a Stripe Customer Portal session for managing subscription and payment methods
    """
    payment_service = PaymentService()

    if not payment_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Payment service is not configured"
        )

    # Check if user has an institution
    if not current_user.institution_id:
        raise HTTPException(
            status_code=400,
            detail="User must be associated with an institution"
        )

    # Get subscription to find customer ID
    subscription = db.query(Subscription).filter(
        Subscription.institution_id == current_user.institution_id
    ).first()

    if not subscription or not subscription.stripe_customer_id:
        raise HTTPException(
            status_code=404,
            detail="No subscription found for this institution"
        )

    try:
        session = await payment_service.create_customer_portal_session(
            stripe_customer_id=subscription.stripe_customer_id,
            return_url=request.return_url
        )
        return session
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/create-checkout-session")
async def create_checkout_session(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a Stripe Checkout Session for the current user's institution

    Requires authentication and active user status.
    """
    payment_service = PaymentService()

    if not payment_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Payment service is not configured (missing STRIPE_SECRET_KEY)"
        )

    # Check if user has an institution
    if not current_user.institution_id:
        raise HTTPException(
            status_code=400,
            detail="User must be associated with an institution to subscribe"
        )

    try:
        session = await payment_service.create_checkout_session(
            price_id=request.price_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            customer_email=current_user.email,
            metadata={
                "institution_id": str(current_user.institution_id),
                "user_id": str(current_user.id),
                "user_email": current_user.email
            }
        )
        return session
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
