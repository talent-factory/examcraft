"""
HTTP-Flow tests for the billing API endpoints in api/v1/billing.py (TF-389).

test_billing_api.py already covers the pure helper functions
(_is_billing_owner, get_tier_from_price_id, get_allowed_price_ids) — this
file targets the six FastAPI endpoints themselves, which had zero HTTP-layer
coverage. Stripe and PaymentService are mocked throughout; no real network
calls are made.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import stripe
from fastapi.testclient import TestClient

from api.v1 import billing
from database import get_db
from main import app
from models.auth import Institution, User, UserStatus
from models.subscription import Subscription, SubscriptionStatus
from services.auth_service import AuthService
from tests.conftest import login_headers as _login_headers
from utils.auth_utils import get_current_user


@pytest.fixture(scope="function")
def db(test_db):
    institution = Institution(
        name="Billing Test Institution",
        slug="billing-test-institution",
        subscription_tier="free",
        max_users=10,
        max_documents=100,
        max_questions_per_month=500,
    )
    test_db.add(institution)
    test_db.commit()
    yield test_db


@pytest.fixture(scope="function")
def test_client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    from api import auth

    # Idempotent: avoid appending duplicate routes on every call.
    if not any(getattr(r, "path", None) == "/api/auth/login" for r in app.routes):
        app.include_router(auth.router)
    if not any(
        getattr(r, "path", None) == "/api/v1/billing/subscription" for r in app.routes
    ):
        app.include_router(billing.router, prefix="/api/v1/billing")
    app.dependency_overrides[get_db] = override_get_db
    api_client = TestClient(app)
    yield api_client
    app.dependency_overrides.clear()


@pytest.fixture
def billing_test_user(db):
    institution = db.query(Institution).first()
    user = User(
        email="billing-flow@billing-test-institution.ch",
        password_hash=AuthService.get_password_hash("testpassword123"),
        first_name="Billing",
        last_name="Flow",
        institution_id=institution.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_subscription(db, institution_id, user_id, **overrides):
    defaults = dict(
        institution_id=institution_id,
        billing_owner_id=user_id,
        stripe_subscription_id="sub_test_123",
        stripe_customer_id="cus_test_123",
        stripe_price_id="price_test_starter",
        status=SubscriptionStatus.ACTIVE,
        current_period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        current_period_end=datetime(2026, 2, 1, tzinfo=timezone.utc),
        cancel_at_period_end=False,
    )
    defaults.update(overrides)
    subscription = Subscription(**defaults)
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def _invoice_payload(**overrides):
    payload = dict(
        id="in_123",
        number="INV-001",
        status="paid",
        amount_due=10.0,
        amount_paid=10.0,
        currency="chf",
        created="2026-01-01T00:00:00Z",
        due_date=None,
        paid_at="2026-01-01T00:00:00Z",
        invoice_pdf=None,
        hosted_invoice_url=None,
    )
    payload.update(overrides)
    return payload


def _override_current_user_without_institution(institution_id=None):
    fake_user = User(
        id=999999,
        email="no-institution@test.com",
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    app.dependency_overrides[get_current_user] = lambda: fake_user
    return fake_user


# ============================================================================
# GET /subscription
# ============================================================================


class TestGetSubscription:
    def test_no_institution_returns_free_placeholder(self, test_client):
        _override_current_user_without_institution()

        response = test_client.get("/api/v1/billing/subscription")

        assert response.status_code == 200
        data = response.json()
        assert data == {
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

    def test_institution_not_found_returns_free_placeholder(self, test_client):
        _override_current_user_without_institution(institution_id=999999)

        response = test_client.get("/api/v1/billing/subscription")

        assert response.status_code == 200
        assert response.json()["tier"] == "free"

    def test_no_active_subscription_returns_institution_tier(
        self, test_client, billing_test_user, db
    ):
        db.query(Institution).filter(
            Institution.id == billing_test_user.institution_id
        ).update({"subscription_tier": "starter"})
        db.commit()
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        response = test_client.get("/api/v1/billing/subscription", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == "starter"
        assert data["status"] == "active"
        assert data["id"] is None

    def test_active_subscription_payment_service_unavailable(
        self, test_client, billing_test_user, db
    ):
        _make_subscription(db, billing_test_user.institution_id, billing_test_user.id)
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        with patch.object(billing.PaymentService, "is_available", return_value=False):
            response = test_client.get("/api/v1/billing/subscription", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert data["is_billing_owner"] is True
        assert data["plan"]["id"] == "price_test_starter"
        assert data["default_payment_method"] is None

    def test_active_subscription_stripe_enrichment_success(
        self, test_client, billing_test_user, db
    ):
        _make_subscription(db, billing_test_user.institution_id, billing_test_user.id)
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        with (
            patch.object(billing.PaymentService, "is_available", return_value=True),
            patch.object(
                billing.PaymentService,
                "get_subscription",
                AsyncMock(
                    return_value={
                        "default_payment_method": {"id": "pm_123"},
                        "plan": {"id": "price_test_starter", "amount": 1000},
                    }
                ),
            ),
        ):
            response = test_client.get("/api/v1/billing/subscription", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["default_payment_method"] == {"id": "pm_123"}
        assert data["plan"] == {"id": "price_test_starter", "amount": 1000}

    def test_active_subscription_stripe_error_falls_back_gracefully(
        self, test_client, billing_test_user, db
    ):
        _make_subscription(db, billing_test_user.institution_id, billing_test_user.id)
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        with (
            patch.object(billing.PaymentService, "is_available", return_value=True),
            patch.object(
                billing.PaymentService,
                "get_subscription",
                AsyncMock(side_effect=stripe.error.StripeError("boom")),
            ),
            patch.object(billing.logger, "warning") as mock_warning,
        ):
            response = test_client.get("/api/v1/billing/subscription", headers=headers)

        assert response.status_code == 200
        assert response.json()["plan"]["id"] == "price_test_starter"
        # Fallback must stay observable, not just silent — patch the module
        # logger directly (caplog is unreliable in the full suite, see
        # test_gdpr_api.py's question-export test for the same pattern).
        mock_warning.assert_called_once()

    def test_active_subscription_unexpected_error_falls_back_gracefully(
        self, test_client, billing_test_user, db
    ):
        _make_subscription(db, billing_test_user.institution_id, billing_test_user.id)
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        with (
            patch.object(billing.PaymentService, "is_available", return_value=True),
            patch.object(
                billing.PaymentService,
                "get_subscription",
                AsyncMock(side_effect=RuntimeError("boom")),
            ),
            patch.object(billing.logger, "error") as mock_error,
        ):
            response = test_client.get("/api/v1/billing/subscription", headers=headers)

        assert response.status_code == 200
        assert response.json()["plan"]["id"] == "price_test_starter"
        mock_error.assert_called_once()
        assert mock_error.call_args.kwargs.get("exc_info") is True


# ============================================================================
# GET /invoices
# ============================================================================


class TestGetInvoices:
    def test_service_not_configured_returns_503(self, test_client, billing_test_user):
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        with patch.object(billing.PaymentService, "is_available", return_value=False):
            response = test_client.get("/api/v1/billing/invoices", headers=headers)

        assert response.status_code == 503
        assert response.json()["error_code"] == "billing_service_not_configured"

    def test_no_institution_returns_empty_list(self, test_client):
        _override_current_user_without_institution()

        with patch.object(billing.PaymentService, "is_available", return_value=True):
            response = test_client.get("/api/v1/billing/invoices")

        assert response.status_code == 200
        assert response.json() == []

    def test_no_subscription_returns_empty_list(self, test_client, billing_test_user):
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        with patch.object(billing.PaymentService, "is_available", return_value=True):
            response = test_client.get("/api/v1/billing/invoices", headers=headers)

        assert response.status_code == 200
        assert response.json() == []

    def test_not_billing_owner_returns_403(self, test_client, billing_test_user, db):
        _make_subscription(db, billing_test_user.institution_id, None)
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        with patch.object(billing.PaymentService, "is_available", return_value=True):
            response = test_client.get("/api/v1/billing/invoices", headers=headers)

        assert response.status_code == 403
        assert response.json()["error_code"] == "billing_invoices_owner_only"

    def test_owner_success_returns_invoices(self, test_client, billing_test_user, db):
        _make_subscription(db, billing_test_user.institution_id, billing_test_user.id)
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        with (
            patch.object(billing.PaymentService, "is_available", return_value=True),
            patch.object(
                billing.PaymentService,
                "get_invoices",
                AsyncMock(return_value=[_invoice_payload()]),
            ),
        ):
            response = test_client.get("/api/v1/billing/invoices", headers=headers)

        assert response.status_code == 200
        assert response.json()[0]["id"] == "in_123"

    def test_stripe_error_returns_500(self, test_client, billing_test_user, db):
        _make_subscription(db, billing_test_user.institution_id, billing_test_user.id)
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        with (
            patch.object(billing.PaymentService, "is_available", return_value=True),
            patch.object(
                billing.PaymentService,
                "get_invoices",
                AsyncMock(side_effect=RuntimeError("boom")),
            ),
        ):
            response = test_client.get("/api/v1/billing/invoices", headers=headers)

        assert response.status_code == 500
        assert response.json()["error_code"] == "billing_invoices_fetch_failed"


# ============================================================================
# GET /payment-methods
# ============================================================================


class TestGetPaymentMethods:
    def test_service_not_configured_returns_503(self, test_client, billing_test_user):
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        with patch.object(billing.PaymentService, "is_available", return_value=False):
            response = test_client.get(
                "/api/v1/billing/payment-methods", headers=headers
            )

        assert response.status_code == 503
        assert response.json()["error_code"] == "billing_service_not_configured"

    def test_not_billing_owner_returns_403(self, test_client, billing_test_user, db):
        _make_subscription(db, billing_test_user.institution_id, None)
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        with patch.object(billing.PaymentService, "is_available", return_value=True):
            response = test_client.get(
                "/api/v1/billing/payment-methods", headers=headers
            )

        assert response.status_code == 403
        assert response.json()["error_code"] == "billing_payment_methods_owner_only"

    def test_owner_success_returns_payment_methods(
        self, test_client, billing_test_user, db
    ):
        _make_subscription(db, billing_test_user.institution_id, billing_test_user.id)
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        with (
            patch.object(billing.PaymentService, "is_available", return_value=True),
            patch.object(
                billing.PaymentService,
                "get_payment_methods",
                AsyncMock(
                    return_value=[{"id": "pm_123", "type": "card", "card": None}]
                ),
            ),
        ):
            response = test_client.get(
                "/api/v1/billing/payment-methods", headers=headers
            )

        assert response.status_code == 200
        assert response.json() == [{"id": "pm_123", "type": "card", "card": None}]

    def test_stripe_error_returns_500(self, test_client, billing_test_user, db):
        _make_subscription(db, billing_test_user.institution_id, billing_test_user.id)
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        with (
            patch.object(billing.PaymentService, "is_available", return_value=True),
            patch.object(
                billing.PaymentService,
                "get_payment_methods",
                AsyncMock(side_effect=RuntimeError("boom")),
            ),
        ):
            response = test_client.get(
                "/api/v1/billing/payment-methods", headers=headers
            )

        assert response.status_code == 500
        assert response.json()["error_code"] == "billing_payment_methods_fetch_failed"


# ============================================================================
# POST /customer-portal
# ============================================================================


class TestCreateCustomerPortal:
    def test_service_not_configured_returns_503(self, test_client, billing_test_user):
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        with patch.object(billing.PaymentService, "is_available", return_value=False):
            response = test_client.post(
                "/api/v1/billing/customer-portal", headers=headers
            )

        assert response.status_code == 503
        assert response.json()["error_code"] == "billing_service_not_configured"

    def test_no_institution_returns_400(self, test_client):
        _override_current_user_without_institution()

        with patch.object(billing.PaymentService, "is_available", return_value=True):
            response = test_client.post("/api/v1/billing/customer-portal")

        assert response.status_code == 400
        assert response.json()["error_code"] == "billing_no_institution"

    def test_no_subscription_returns_404(self, test_client, billing_test_user):
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        with patch.object(billing.PaymentService, "is_available", return_value=True):
            response = test_client.post(
                "/api/v1/billing/customer-portal", headers=headers
            )

        assert response.status_code == 404
        assert response.json()["error_code"] == "billing_subscription_not_found"

    def test_not_billing_owner_returns_403(self, test_client, billing_test_user, db):
        _make_subscription(db, billing_test_user.institution_id, None)
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        with patch.object(billing.PaymentService, "is_available", return_value=True):
            response = test_client.post(
                "/api/v1/billing/customer-portal", headers=headers
            )

        assert response.status_code == 403
        assert response.json()["error_code"] == "billing_portal_owner_only"

    def test_owner_success_returns_session(self, test_client, billing_test_user, db):
        _make_subscription(db, billing_test_user.institution_id, billing_test_user.id)
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        with (
            patch.object(billing.PaymentService, "is_available", return_value=True),
            patch.object(
                billing.PaymentService,
                "create_customer_portal_session",
                AsyncMock(return_value={"url": "https://billing.stripe.com/session"}),
            ),
        ):
            response = test_client.post(
                "/api/v1/billing/customer-portal", headers=headers
            )

        assert response.status_code == 200
        assert response.json() == {"url": "https://billing.stripe.com/session"}

    def test_stripe_error_returns_500(self, test_client, billing_test_user, db):
        _make_subscription(db, billing_test_user.institution_id, billing_test_user.id)
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        with (
            patch.object(billing.PaymentService, "is_available", return_value=True),
            patch.object(
                billing.PaymentService,
                "create_customer_portal_session",
                AsyncMock(side_effect=RuntimeError("boom")),
            ),
        ):
            response = test_client.post(
                "/api/v1/billing/customer-portal", headers=headers
            )

        assert response.status_code == 500
        assert response.json()["error_code"] == "billing_portal_failed"


# ============================================================================
# POST /create-checkout-session
# ============================================================================


class TestCreateCheckoutSession:
    def test_service_not_configured_returns_503(self, test_client, billing_test_user):
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        with patch.object(billing.PaymentService, "is_available", return_value=False):
            response = test_client.post(
                "/api/v1/billing/create-checkout-session",
                json={"price_id": "price_x"},
                headers=headers,
            )

        assert response.status_code == 503
        assert response.json()["error_code"] == "billing_service_not_configured"

    def test_no_institution_returns_400(self, test_client):
        _override_current_user_without_institution()

        with patch.object(billing.PaymentService, "is_available", return_value=True):
            response = test_client.post(
                "/api/v1/billing/create-checkout-session",
                json={"price_id": "price_x"},
            )

        assert response.status_code == 400
        assert response.json()["error_code"] == "billing_no_institution"

    def test_already_subscribed_returns_409(self, test_client, billing_test_user, db):
        _make_subscription(db, billing_test_user.institution_id, billing_test_user.id)
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        with patch.object(billing.PaymentService, "is_available", return_value=True):
            response = test_client.post(
                "/api/v1/billing/create-checkout-session",
                json={"price_id": "price_x"},
                headers=headers,
            )

        assert response.status_code == 409
        assert response.json()["error_code"] == "billing_already_subscribed"

    def test_no_allowed_prices_configured_returns_503(
        self, test_client, billing_test_user, monkeypatch
    ):
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )
        monkeypatch.setattr(billing, "get_allowed_price_ids", lambda: set())

        with patch.object(billing.PaymentService, "is_available", return_value=True):
            response = test_client.post(
                "/api/v1/billing/create-checkout-session",
                json={"price_id": "price_x"},
                headers=headers,
            )

        assert response.status_code == 503
        assert response.json()["error_code"] == "billing_plans_not_configured"

    def test_disallowed_price_id_returns_400(
        self, test_client, billing_test_user, monkeypatch
    ):
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )
        monkeypatch.setattr(billing, "get_allowed_price_ids", lambda: {"price_allowed"})

        with patch.object(billing.PaymentService, "is_available", return_value=True):
            response = test_client.post(
                "/api/v1/billing/create-checkout-session",
                json={"price_id": "price_not_allowed"},
                headers=headers,
            )

        assert response.status_code == 400
        assert response.json()["error_code"] == "billing_invalid_price"

    def test_success_returns_session(self, test_client, billing_test_user, monkeypatch):
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )
        monkeypatch.setattr(billing, "get_allowed_price_ids", lambda: {"price_allowed"})

        with (
            patch.object(billing.PaymentService, "is_available", return_value=True),
            patch.object(
                billing.PaymentService,
                "create_checkout_session",
                AsyncMock(return_value={"url": "https://checkout.stripe.com/session"}),
            ),
        ):
            response = test_client.post(
                "/api/v1/billing/create-checkout-session",
                json={"price_id": "price_allowed"},
                headers=headers,
            )

        assert response.status_code == 200
        assert response.json() == {"url": "https://checkout.stripe.com/session"}

    def test_stripe_invalid_request_error_returns_503(
        self, test_client, billing_test_user, monkeypatch
    ):
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )
        monkeypatch.setattr(billing, "get_allowed_price_ids", lambda: {"price_allowed"})

        with (
            patch.object(billing.PaymentService, "is_available", return_value=True),
            patch.object(
                billing.PaymentService,
                "create_checkout_session",
                AsyncMock(
                    side_effect=stripe.error.InvalidRequestError(
                        "bad config", param=None
                    )
                ),
            ),
        ):
            response = test_client.post(
                "/api/v1/billing/create-checkout-session",
                json={"price_id": "price_allowed"},
                headers=headers,
            )

        assert response.status_code == 503
        assert response.json()["error_code"] == "billing_provider_misconfigured"

    def test_stripe_error_returns_502(
        self, test_client, billing_test_user, monkeypatch
    ):
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )
        monkeypatch.setattr(billing, "get_allowed_price_ids", lambda: {"price_allowed"})

        with (
            patch.object(billing.PaymentService, "is_available", return_value=True),
            patch.object(
                billing.PaymentService,
                "create_checkout_session",
                AsyncMock(side_effect=stripe.error.StripeError("boom")),
            ),
        ):
            response = test_client.post(
                "/api/v1/billing/create-checkout-session",
                json={"price_id": "price_allowed"},
                headers=headers,
            )

        assert response.status_code == 502
        assert response.json()["error_code"] == "billing_provider_unavailable"

    def test_unexpected_error_returns_500(
        self, test_client, billing_test_user, monkeypatch
    ):
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )
        monkeypatch.setattr(billing, "get_allowed_price_ids", lambda: {"price_allowed"})

        with (
            patch.object(billing.PaymentService, "is_available", return_value=True),
            patch.object(
                billing.PaymentService,
                "create_checkout_session",
                AsyncMock(side_effect=RuntimeError("boom")),
            ),
        ):
            response = test_client.post(
                "/api/v1/billing/create-checkout-session",
                json={"price_id": "price_allowed"},
                headers=headers,
            )

        assert response.status_code == 500
        assert response.json()["error_code"] == "billing_unexpected_error"


# ============================================================================
# POST /sync-subscription
# ============================================================================


class TestSyncSubscription:
    def test_service_not_configured_returns_503(self, test_client, billing_test_user):
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        with patch.object(billing.PaymentService, "is_available", return_value=False):
            response = test_client.post(
                "/api/v1/billing/sync-subscription", headers=headers
            )

        assert response.status_code == 503
        assert response.json()["error_code"] == "billing_service_not_configured"

    def test_no_institution_returns_400(self, test_client):
        _override_current_user_without_institution()

        with patch.object(billing.PaymentService, "is_available", return_value=True):
            response = test_client.post("/api/v1/billing/sync-subscription")

        assert response.status_code == 400
        assert response.json()["error_code"] == "billing_no_institution"

    def test_institution_not_found_returns_404(self, test_client):
        _override_current_user_without_institution(institution_id=999999)

        with patch.object(billing.PaymentService, "is_available", return_value=True):
            response = test_client.post("/api/v1/billing/sync-subscription")

        assert response.status_code == 404
        assert response.json()["error_code"] == "billing_institution_not_found"

    def test_no_stripe_customer_returns_no_customer_status(
        self, test_client, billing_test_user
    ):
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )
        empty_list = MagicMock(data=[])

        with (
            patch.object(billing.PaymentService, "is_available", return_value=True),
            patch.object(stripe.Customer, "list", return_value=empty_list),
        ):
            response = test_client.post(
                "/api/v1/billing/sync-subscription", headers=headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "no_customer"
        assert data["synced"] is False

    def test_no_active_or_trialing_subscription_returns_no_subscription_status(
        self, test_client, billing_test_user
    ):
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )
        customer = MagicMock(data=[MagicMock(id="cus_test_123")])
        empty_subs = MagicMock(data=[])

        with (
            patch.object(billing.PaymentService, "is_available", return_value=True),
            patch.object(stripe.Customer, "list", return_value=customer),
            patch.object(stripe.Subscription, "list", return_value=empty_subs),
        ):
            response = test_client.post(
                "/api/v1/billing/sync-subscription", headers=headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "no_subscription"
        assert data["synced"] is False

    def test_creates_new_subscription_and_updates_tier(
        self, test_client, billing_test_user, db, monkeypatch
    ):
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )
        customer = MagicMock(
            data=[
                MagicMock(
                    id="cus_new_123",
                    get=lambda k, d=None: "billing-flow@billing-test-institution.ch",
                )
            ]
        )
        stripe_sub = MagicMock(
            id="sub_new_123",
            status="active",
            items=MagicMock(data=[MagicMock(price=MagicMock(id="price_test_starter"))]),
            current_period_start=1750000000,
            current_period_end=1752600000,
            cancel_at_period_end=False,
        )
        active_subs = MagicMock(data=[stripe_sub])
        monkeypatch.setattr(
            billing, "get_tier_from_price_id", lambda price_id: "starter"
        )

        with (
            patch.object(billing.PaymentService, "is_available", return_value=True),
            patch.object(stripe.Customer, "list", return_value=customer),
            patch.object(stripe.Subscription, "list", return_value=active_subs),
        ):
            response = test_client.post(
                "/api/v1/billing/sync-subscription", headers=headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["synced"] is True
        assert data["tier"] == "starter"

        db.expire_all()
        subscription = (
            db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == "sub_new_123")
            .first()
        )
        assert subscription is not None
        assert subscription.billing_owner_id == billing_test_user.id

        institution = db.get(Institution, billing_test_user.institution_id)
        assert institution.subscription_tier == "starter"

    def test_updates_existing_subscription_and_claims_billing_owner_via_email_match(
        self, test_client, billing_test_user, db, monkeypatch
    ):
        """An existing subscription with no billing owner yet is claimed by
        whoever's email matches the Stripe customer's — even without an
        admin role."""
        existing = _make_subscription(
            db,
            billing_test_user.institution_id,
            None,
            stripe_subscription_id="sub_existing_123",
        )
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        customer = MagicMock(
            data=[
                MagicMock(
                    id="cus_existing_123",
                    get=lambda k, d=None: billing_test_user.email,
                )
            ]
        )
        stripe_sub = MagicMock(
            id="sub_existing_123",
            status="active",
            items=MagicMock(data=[MagicMock(price=MagicMock(id="price_test_starter"))]),
            current_period_start=1750000000,
            current_period_end=1752600000,
            cancel_at_period_end=False,
        )
        active_subs = MagicMock(data=[stripe_sub])
        monkeypatch.setattr(
            billing, "get_tier_from_price_id", lambda price_id: "starter"
        )

        with (
            patch.object(billing.PaymentService, "is_available", return_value=True),
            patch.object(stripe.Customer, "list", return_value=customer),
            patch.object(stripe.Subscription, "list", return_value=active_subs),
        ):
            response = test_client.post(
                "/api/v1/billing/sync-subscription", headers=headers
            )

        assert response.status_code == 200
        db.expire_all()
        db.refresh(existing)
        assert existing.billing_owner_id == billing_test_user.id

    def test_updates_existing_subscription_does_not_claim_billing_owner_on_email_mismatch(
        self, test_client, billing_test_user, db, monkeypatch
    ):
        """A non-admin whose email doesn't match the Stripe customer must
        NOT be able to claim billing ownership of an existing subscription —
        this is the only non-trivial authorization check in this endpoint."""
        existing = _make_subscription(
            db,
            billing_test_user.institution_id,
            None,
            stripe_subscription_id="sub_existing_456",
        )
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        customer = MagicMock(
            data=[
                MagicMock(
                    id="cus_existing_456",
                    get=lambda k, d=None: "someone-else@billing-test-institution.ch",
                )
            ]
        )
        stripe_sub = MagicMock(
            id="sub_existing_456",
            status="active",
            items=MagicMock(data=[MagicMock(price=MagicMock(id="price_test_starter"))]),
            current_period_start=1750000000,
            current_period_end=1752600000,
            cancel_at_period_end=False,
        )
        active_subs = MagicMock(data=[stripe_sub])
        monkeypatch.setattr(
            billing, "get_tier_from_price_id", lambda price_id: "starter"
        )

        with (
            patch.object(billing.PaymentService, "is_available", return_value=True),
            patch.object(stripe.Customer, "list", return_value=customer),
            patch.object(stripe.Subscription, "list", return_value=active_subs),
            patch.object(billing.logger, "warning") as mock_warning,
        ):
            response = test_client.post(
                "/api/v1/billing/sync-subscription", headers=headers
            )

        assert response.status_code == 200
        db.expire_all()
        db.refresh(existing)
        assert existing.billing_owner_id is None
        mock_warning.assert_called_once()

    def test_tier_mapping_failure_returns_503(
        self, test_client, billing_test_user, monkeypatch
    ):
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )
        customer = MagicMock(
            data=[
                MagicMock(
                    id="cus_new_123",
                    get=lambda k, d=None: "billing-flow@billing-test-institution.ch",
                )
            ]
        )
        stripe_sub = MagicMock(
            id="sub_new_456",
            status="active",
            items=MagicMock(data=[MagicMock(price=MagicMock(id="price_unknown"))]),
            current_period_start=1750000000,
            current_period_end=1752600000,
            cancel_at_period_end=False,
        )
        active_subs = MagicMock(data=[stripe_sub])

        def raise_unknown_price(price_id):
            raise ValueError(f"Unknown price_id: {price_id}")

        monkeypatch.setattr(billing, "get_tier_from_price_id", raise_unknown_price)

        with (
            patch.object(billing.PaymentService, "is_available", return_value=True),
            patch.object(stripe.Customer, "list", return_value=customer),
            patch.object(stripe.Subscription, "list", return_value=active_subs),
        ):
            response = test_client.post(
                "/api/v1/billing/sync-subscription", headers=headers
            )

        assert response.status_code == 503
        assert response.json()["error_code"] == "billing_plans_not_configured"

    def test_unexpected_error_returns_500(self, test_client, billing_test_user):
        headers = _login_headers(
            test_client, billing_test_user.email, "testpassword123"
        )

        with (
            patch.object(billing.PaymentService, "is_available", return_value=True),
            patch.object(stripe.Customer, "list", side_effect=RuntimeError("boom")),
        ):
            response = test_client.post(
                "/api/v1/billing/sync-subscription", headers=headers
            )

        assert response.status_code == 500
        assert response.json()["error_code"] == "billing_sync_failed"
