from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from services.payment_service import PaymentService
from utils.auth_utils import get_current_active_user
from models.auth import User
from database import get_db

router = APIRouter(prefix="/billing", tags=["Billing"])

class CheckoutRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str

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
