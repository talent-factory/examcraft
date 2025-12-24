import stripe
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self):
        self.api_key = os.getenv("STRIPE_SECRET_KEY")
        if not self.api_key:
            logger.warning("⚠️ STRIPE_SECRET_KEY not found in environment variables. Payment features will be disabled.")
        else:
            stripe.api_key = self.api_key
            logger.info("✅ Stripe PaymentService initialized")

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def create_checkout_session(
        self, 
        price_id: str, 
        success_url: str, 
        cancel_url: str, 
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout Session for a subscription
        """
        if not self.is_available():
            raise ValueError("Stripe is not configured")

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price': price_id,
                        'quantity': 1,
                    },
                ],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=customer_email,
                metadata=metadata or {},
                # Automatic tax calculation if configured in Stripe Dashboard
                automatic_tax={'enabled': True}, 
            )
            return {
                "session_id": checkout_session.id,
                "url": checkout_session.url
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe Error: {str(e)}")
            raise e
        except Exception as e:
            logger.error(f"Error creating checkout session: {str(e)}")
            raise e
