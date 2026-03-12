import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from services.payment_service import PaymentService
from utils.auth_utils import get_current_active_user
from models.auth import User
from database import get_db

router = APIRouter()

# Erlaubte Pläne → Stripe Price IDs (serverseitig, nicht vom Client steuerbar)
PLAN_PRICE_MAPPING = {
    "starter": os.getenv("STRIPE_PRICE_STARTER", ""),
    "professional": os.getenv("STRIPE_PRICE_PROFESSIONAL", ""),
    "enterprise": os.getenv("STRIPE_PRICE_ENTERPRISE", ""),
}

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


class CheckoutRequest(BaseModel):
    plan: str


@router.post("/create-checkout-session")
async def create_checkout_session(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe Checkout Session for the current user's institution

    Requires authentication and active user status.
    The plan parameter must be one of: starter, professional, enterprise.
    Redirect URLs are controlled server-side to prevent open redirects.
    """
    payment_service = PaymentService()

    if not payment_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Payment service is not configured (missing STRIPE_SECRET_KEY)",
        )

    # Validate plan against allowed plans
    if request.plan not in PLAN_PRICE_MAPPING:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid plan. Allowed plans: {', '.join(PLAN_PRICE_MAPPING.keys())}",
        )

    price_id = PLAN_PRICE_MAPPING[request.plan]
    if not price_id:
        raise HTTPException(
            status_code=400,
            detail=f"Plan '{request.plan}' is not configured (missing Stripe Price ID)",
        )

    # Check if user has an institution
    if not current_user.institution_id:
        raise HTTPException(
            status_code=400,
            detail="User must be associated with an institution to subscribe",
        )

    # Redirect URLs serverseitig definiert (kein Open Redirect möglich)
    success_url = f"{FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{FRONTEND_URL}/billing/cancel"

    try:
        session = await payment_service.create_checkout_session(
            price_id=price_id,
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
