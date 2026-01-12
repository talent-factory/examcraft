from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from services.payment_service import PaymentService

router = APIRouter()

class CheckoutRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str

@router.post("/create-checkout-session")
async def create_checkout_session(request: CheckoutRequest):
    """
    Create a Stripe Checkout Session
    """
    payment_service = PaymentService()
    
    if not payment_service.is_available():
        raise HTTPException(
            status_code=503, 
            detail="Payment service is not configured (missing STRIPE_SECRET_KEY)"
        )
        
    try:
        session = await payment_service.create_checkout_session(
            price_id=request.price_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            # In a real app, we would get the user email from the auth token
            # customer_email=current_user.email
        )
        return session
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
