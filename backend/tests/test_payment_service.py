"""Tests for PaymentService (TF-202)"""

import pytest
from unittest.mock import patch, MagicMock
from services.payment_service import PaymentService


class TestPaymentServiceInit:
    def test_is_unavailable_without_key(self):
        with patch.dict("os.environ", {}, clear=True):
            service = PaymentService()
            assert service.is_available() is False

    def test_is_available_with_key(self):
        with patch.dict("os.environ", {"STRIPE_SECRET_KEY": "sk_test_123"}):
            service = PaymentService()
            assert service.is_available() is True


class TestCreateCheckoutSession:
    @pytest.mark.asyncio
    async def test_raises_when_not_configured(self):
        with patch.dict("os.environ", {}, clear=True):
            service = PaymentService()
            with pytest.raises(ValueError, match="not configured"):
                await service.create_checkout_session(
                    "price_test", "http://ok", "http://cancel"
                )


class TestGetSubscription:
    @pytest.mark.asyncio
    async def test_raises_when_not_configured(self):
        with patch.dict("os.environ", {}, clear=True):
            service = PaymentService()
            with pytest.raises(ValueError, match="not configured"):
                await service.get_subscription("sub_123")


class TestGetInvoices:
    @pytest.mark.asyncio
    async def test_raises_when_not_configured(self):
        with patch.dict("os.environ", {}, clear=True):
            service = PaymentService()
            with pytest.raises(ValueError, match="not configured"):
                await service.get_invoices("cus_123")


class TestGetPaymentMethods:
    @pytest.mark.asyncio
    async def test_raises_when_not_configured(self):
        with patch.dict("os.environ", {}, clear=True):
            service = PaymentService()
            with pytest.raises(ValueError, match="not configured"):
                await service.get_payment_methods("cus_123")


class TestCreateCustomerPortalSession:
    @pytest.mark.asyncio
    async def test_raises_when_not_configured(self):
        with patch.dict("os.environ", {}, clear=True):
            service = PaymentService()
            with pytest.raises(ValueError, match="not configured"):
                await service.create_customer_portal_session("cus_123", "http://return")


class TestFormatPaymentMethod:
    def test_formats_string_id(self):
        with patch.dict("os.environ", {"STRIPE_SECRET_KEY": "sk_test_123"}):
            service = PaymentService()
            result = service._format_payment_method("pm_123")
            assert result == {"id": "pm_123"}

    def test_formats_payment_method_object(self):
        with patch.dict("os.environ", {"STRIPE_SECRET_KEY": "sk_test_123"}):
            service = PaymentService()
            pm = MagicMock()
            pm.id = "pm_456"
            pm.type = "card"
            pm.card.brand = "visa"
            pm.card.last4 = "4242"
            pm.card.exp_month = 12
            pm.card.exp_year = 2027
            result = service._format_payment_method(pm)
            assert result["id"] == "pm_456"
            assert result["type"] == "card"
            assert result["card"]["brand"] == "visa"
            assert result["card"]["last4"] == "4242"

    def test_formats_payment_method_without_card(self):
        with patch.dict("os.environ", {"STRIPE_SECRET_KEY": "sk_test_123"}):
            service = PaymentService()
            pm = MagicMock()
            pm.id = "pm_789"
            pm.type = "sepa_debit"
            pm.card = None
            result = service._format_payment_method(pm)
            assert result["id"] == "pm_789"
            assert result["card"] is None
