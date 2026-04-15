import stripe
import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self):
        self.api_key = os.getenv("STRIPE_SECRET_KEY")
        if not self.api_key:
            logger.warning(
                "STRIPE_SECRET_KEY not found in environment variables. Payment features will be disabled."
            )
        else:
            stripe.api_key = self.api_key
            logger.info("Stripe PaymentService initialized")

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def create_checkout_session(
        self,
        price_id: str,
        success_url: str,
        cancel_url: str,
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout Session for a subscription
        """
        if not self.is_available():
            raise ValueError("Stripe is not configured")

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    },
                ],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=customer_email,
                metadata=metadata or {},
                automatic_tax={"enabled": False},
            )
            return {"session_id": checkout_session.id, "url": checkout_session.url}
        except stripe.error.StripeError as e:
            logger.error(f"Stripe Error: {str(e)}")
            raise e
        except Exception as e:
            logger.error(f"Error creating checkout session: {str(e)}")
            raise e

    async def get_subscription(self, stripe_subscription_id: str) -> Dict[str, Any]:
        """
        Get subscription details from Stripe
        """
        if not self.is_available():
            raise ValueError("Stripe is not configured")

        try:
            subscription = stripe.Subscription.retrieve(
                stripe_subscription_id,
                expand=["latest_invoice", "default_payment_method"],
            )

            current_period_start = None
            current_period_end = None
            if (
                hasattr(subscription, "current_period_start")
                and subscription.current_period_start
            ):
                current_period_start = datetime.fromtimestamp(
                    subscription.current_period_start, tz=timezone.utc
                ).isoformat()
            if (
                hasattr(subscription, "current_period_end")
                and subscription.current_period_end
            ):
                current_period_end = datetime.fromtimestamp(
                    subscription.current_period_end, tz=timezone.utc
                ).isoformat()

            return {
                "id": subscription.id,
                "status": subscription.status,
                "current_period_start": current_period_start,
                "current_period_end": current_period_end,
                "cancel_at_period_end": subscription.cancel_at_period_end
                if hasattr(subscription, "cancel_at_period_end")
                else False,
                "canceled_at": datetime.fromtimestamp(
                    subscription.canceled_at, tz=timezone.utc
                ).isoformat()
                if subscription.canceled_at
                else None,
                "plan": {
                    "id": subscription["items"]["data"][0]["price"]["id"]
                    if subscription.get("items", {}).get("data")
                    else None,
                    "amount": subscription["items"]["data"][0]["price"]["unit_amount"]
                    / 100
                    if subscription.get("items", {}).get("data")
                    else 0,
                    "currency": subscription["items"]["data"][0]["price"][
                        "currency"
                    ].upper()
                    if subscription.get("items", {}).get("data")
                    else "CHF",
                    "interval": subscription["items"]["data"][0]["price"]["recurring"][
                        "interval"
                    ]
                    if subscription.get("items", {}).get("data")
                    else None,
                },
                "default_payment_method": self._format_payment_method(
                    subscription.default_payment_method
                )
                if subscription.default_payment_method
                else None,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe Error getting subscription: {str(e)}")
            raise e

    async def get_invoices(
        self, stripe_customer_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get invoice history for a customer
        """
        if not self.is_available():
            raise ValueError("Stripe is not configured")

        try:
            invoices = stripe.Invoice.list(customer=stripe_customer_id, limit=limit)

            return [
                {
                    "id": invoice.id,
                    "number": invoice.number,
                    "status": invoice.status,
                    "amount_due": invoice.amount_due / 100,
                    "amount_paid": invoice.amount_paid / 100,
                    "currency": invoice.currency.upper(),
                    "created": datetime.fromtimestamp(
                        invoice.created, tz=timezone.utc
                    ).isoformat(),
                    "due_date": datetime.fromtimestamp(
                        invoice.due_date, tz=timezone.utc
                    ).isoformat()
                    if invoice.due_date
                    else None,
                    "paid_at": datetime.fromtimestamp(
                        invoice.status_transitions.paid_at, tz=timezone.utc
                    ).isoformat()
                    if invoice.status_transitions and invoice.status_transitions.paid_at
                    else None,
                    "invoice_pdf": invoice.invoice_pdf,
                    "hosted_invoice_url": invoice.hosted_invoice_url,
                }
                for invoice in invoices.data
            ]
        except stripe.error.StripeError as e:
            logger.error(f"Stripe Error getting invoices: {str(e)}")
            raise e

    async def get_payment_methods(
        self, stripe_customer_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get payment methods for a customer
        """
        if not self.is_available():
            raise ValueError("Stripe is not configured")

        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=stripe_customer_id, type="card"
            )

            return [self._format_payment_method(pm) for pm in payment_methods.data]
        except stripe.error.StripeError as e:
            logger.error(f"Stripe Error getting payment methods: {str(e)}")
            raise e

    def _format_payment_method(self, pm: Any) -> Dict[str, Any]:
        """Format a Stripe PaymentMethod object"""
        if isinstance(pm, str):
            return {"id": pm}

        return {
            "id": pm.id,
            "type": pm.type,
            "card": {
                "brand": pm.card.brand if pm.card else None,
                "last4": pm.card.last4 if pm.card else None,
                "exp_month": pm.card.exp_month if pm.card else None,
                "exp_year": pm.card.exp_year if pm.card else None,
            }
            if pm.card
            else None,
        }

    async def create_customer_portal_session(
        self, stripe_customer_id: str, return_url: str
    ) -> Dict[str, Any]:
        """
        Create a Stripe Customer Portal Session for managing subscription
        """
        if not self.is_available():
            raise ValueError("Stripe is not configured")

        try:
            session = stripe.billing_portal.Session.create(
                customer=stripe_customer_id,
                return_url=return_url,
            )
            return {"url": session.url}
        except stripe.error.StripeError as e:
            logger.error(f"Stripe Error creating portal session: {str(e)}")
            raise e
