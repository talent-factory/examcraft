"""
Tests for Stripe webhook handlers in api/v1/webhooks.py.

Focus: verify Stripe SDK v15 attribute-style access works end-to-end and
that the new defensive guards raise clean ValueErrors instead of
AttributeError/IndexError on incomplete payloads.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from api.v1.webhooks import (
    _extract_price_id,
    _require_status,
    handle_checkout_session_completed,
    handle_subscription_created,
    handle_subscription_deleted,
    handle_subscription_updated,
)
from models.auth import Institution, User
from models.subscription import Subscription, SubscriptionStatus

asyncio = pytest.mark.asyncio


def _set_tier_price(monkeypatch, tier_env: str, value: str):
    """Override both the REACT_APP_ and bare STRIPE_PRICE_ env vars so that
    get_tier_from_price_id picks our test value regardless of which one is
    populated from .env in the surrounding environment."""
    monkeypatch.setenv(f"REACT_APP_STRIPE_PRICE_{tier_env}", value)
    monkeypatch.setenv(f"STRIPE_PRICE_{tier_env}", value)


def _stripe_sub(
    *,
    sub_id="sub_test_123",
    customer="cus_test",
    status="active",
    price_id="price_starter",
    period_start=1_700_000_000,
    period_end=1_702_000_000,
    cancel_at_period_end=False,
    omit_periods=False,
):
    """Build a SimpleNamespace mimicking a Stripe SDK v15 Subscription object."""
    sub = SimpleNamespace(
        id=sub_id,
        customer=customer,
        status=status,
        items=SimpleNamespace(
            data=[SimpleNamespace(price=SimpleNamespace(id=price_id))]
        ),
        cancel_at_period_end=cancel_at_period_end,
    )
    if not omit_periods:
        sub.current_period_start = period_start
        sub.current_period_end = period_end
    return sub


def _stripe_session(
    *,
    institution_id="1",
    user_id="42",
    mode="subscription",
    subscription_id="sub_test_123",
    customer_id="cus_test",
    metadata_is_none=False,
):
    """Build a SimpleNamespace mimicking a Stripe checkout.Session object."""
    if metadata_is_none:
        metadata = None
    else:
        metadata = {"institution_id": institution_id, "user_id": user_id}
    return SimpleNamespace(
        metadata=metadata,
        mode=mode,
        subscription=subscription_id,
        customer=customer_id,
    )


def _seed_institution(db, *, tier="free"):
    """Ids come from the database: hardcoded primary keys collide with rows
    other modules leave in the shared test DB once the order changes (TF-660).
    """
    inst = Institution(
        name="Webhook Test Inst",
        slug="webhook-test-inst",
        subscription_tier=tier,
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


def _seed_user(db, *, institution_id):
    user = User(
        email="user@webhook-test.example",
        first_name="Test",
        last_name="User",
        institution_id=institution_id,
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _seed_local_sub(
    db, *, institution_id, sub_id="sub_test_123", tier_price="price_starter"
):
    sub = Subscription(
        institution_id=institution_id,
        stripe_subscription_id=sub_id,
        stripe_customer_id="cus_test",
        stripe_price_id=tier_price,
        status=SubscriptionStatus.INCOMPLETE,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


# ---------------------------------------------------------------------------
# _extract_price_id / _require_status (pure helpers)
# ---------------------------------------------------------------------------


def test_extract_price_id_returns_first_price():
    stripe_sub = _stripe_sub(price_id="price_pro")
    assert _extract_price_id(stripe_sub, "sub_1") == "price_pro"


def test_extract_price_id_raises_when_items_missing():
    stripe_sub = SimpleNamespace(id="sub_1")  # no items at all
    with pytest.raises(ValueError, match="has no items"):
        _extract_price_id(stripe_sub, "sub_1")


def test_extract_price_id_raises_when_items_data_empty():
    stripe_sub = SimpleNamespace(items=SimpleNamespace(data=[]))
    with pytest.raises(ValueError, match="has no items"):
        _extract_price_id(stripe_sub, "sub_1")


def test_extract_price_id_raises_when_price_id_missing():
    stripe_sub = SimpleNamespace(
        items=SimpleNamespace(data=[SimpleNamespace(price=SimpleNamespace(id=None))])
    )
    with pytest.raises(ValueError, match="no price id"):
        _extract_price_id(stripe_sub, "sub_1")


def test_require_status_returns_value():
    assert _require_status(SimpleNamespace(status="active"), "sub_1") == "active"


def test_require_status_raises_when_missing():
    with pytest.raises(ValueError, match="missing status"):
        _require_status(SimpleNamespace(), "sub_1")


# ---------------------------------------------------------------------------
# handle_checkout_session_completed
# ---------------------------------------------------------------------------


@asyncio
async def test_checkout_completed_creates_new_subscription(test_db, monkeypatch):
    _set_tier_price(monkeypatch, "STARTER", "price_starter")
    inst = _seed_institution(test_db)
    user = _seed_user(test_db, institution_id=inst.id)
    stripe_sub = _stripe_sub(price_id="price_starter")

    with patch("api.v1.webhooks.stripe.Subscription.retrieve", return_value=stripe_sub):
        await handle_checkout_session_completed(
            _stripe_session(institution_id=str(inst.id), user_id=str(user.id)), test_db
        )

    persisted = (
        test_db.query(Subscription)
        .filter_by(stripe_subscription_id="sub_test_123")
        .one()
    )
    assert persisted.status == SubscriptionStatus.ACTIVE
    assert persisted.stripe_price_id == "price_starter"
    assert persisted.cancel_at_period_end is False
    assert persisted.current_period_start is not None
    assert persisted.current_period_end is not None
    test_db.refresh(inst)
    assert inst.subscription_tier == "starter"


@asyncio
async def test_checkout_completed_updates_existing_subscription(test_db, monkeypatch):
    _set_tier_price(monkeypatch, "STARTER", "price_starter")
    inst = _seed_institution(test_db)
    user = _seed_user(test_db, institution_id=inst.id)
    existing = _seed_local_sub(test_db, institution_id=inst.id)
    stripe_sub = _stripe_sub(status="trialing", price_id="price_starter")

    with patch("api.v1.webhooks.stripe.Subscription.retrieve", return_value=stripe_sub):
        await handle_checkout_session_completed(
            _stripe_session(institution_id=str(inst.id), user_id=str(user.id)), test_db
        )

    test_db.refresh(existing)
    assert existing.status == SubscriptionStatus.TRIALING
    assert existing.stripe_price_id == "price_starter"


@asyncio
async def test_checkout_completed_metadata_none_raises_clean_error(test_db):
    """Regression: session.metadata=None must surface as ValueError, not AttributeError."""
    session = _stripe_session(metadata_is_none=True)
    with pytest.raises(ValueError, match="No institution_id"):
        await handle_checkout_session_completed(session, test_db)


@asyncio
async def test_checkout_completed_items_empty_raises_value_error(test_db):
    """Regression: empty Stripe items must raise clean ValueError, not IndexError."""
    inst = _seed_institution(test_db)
    stripe_sub_empty = SimpleNamespace(
        id="sub_test_123",
        customer="cus_test",
        status="active",
        items=SimpleNamespace(data=[]),
        cancel_at_period_end=False,
        current_period_start=1_700_000_000,
        current_period_end=1_702_000_000,
    )

    with patch(
        "api.v1.webhooks.stripe.Subscription.retrieve", return_value=stripe_sub_empty
    ):
        with pytest.raises(ValueError, match="has no items"):
            # No user seeded here: the handler raises on the empty items
            # list long before it looks at user_id.
            await handle_checkout_session_completed(
                _stripe_session(institution_id=str(inst.id)), test_db
            )


@asyncio
async def test_checkout_completed_missing_period_fields_ok(test_db, monkeypatch):
    """Optional current_period_* fields absent should not crash."""
    _set_tier_price(monkeypatch, "STARTER", "price_starter")
    inst = _seed_institution(test_db)
    user = _seed_user(test_db, institution_id=inst.id)
    stripe_sub = _stripe_sub(price_id="price_starter", omit_periods=True)

    with patch("api.v1.webhooks.stripe.Subscription.retrieve", return_value=stripe_sub):
        await handle_checkout_session_completed(
            _stripe_session(institution_id=str(inst.id), user_id=str(user.id)), test_db
        )

    persisted = (
        test_db.query(Subscription)
        .filter_by(stripe_subscription_id="sub_test_123")
        .one()
    )
    assert persisted.current_period_start is None
    assert persisted.current_period_end is None


# ---------------------------------------------------------------------------
# handle_subscription_created
# ---------------------------------------------------------------------------


@asyncio
async def test_subscription_created_syncs_local_sub(test_db):
    inst = _seed_institution(test_db)
    _seed_local_sub(test_db, institution_id=inst.id)
    incoming = _stripe_sub(status="active")

    await handle_subscription_created(incoming, test_db)

    persisted = (
        test_db.query(Subscription)
        .filter_by(stripe_subscription_id="sub_test_123")
        .one()
    )
    assert persisted.status == SubscriptionStatus.ACTIVE
    assert persisted.current_period_start is not None


@asyncio
async def test_subscription_created_missing_status_raises(test_db):
    inst = _seed_institution(test_db)
    _seed_local_sub(test_db, institution_id=inst.id)
    incoming = SimpleNamespace(
        id="sub_test_123",
        items=SimpleNamespace(
            data=[SimpleNamespace(price=SimpleNamespace(id="price_starter"))]
        ),
        cancel_at_period_end=False,
    )  # no status

    with pytest.raises(ValueError, match="missing status"):
        await handle_subscription_created(incoming, test_db)


@asyncio
async def test_subscription_created_no_local_sub_logs_warning(test_db):
    """If local sub doesn't exist, handler must warn (not crash).

    The handler's logger is patched at the module level rather than via
    caplog, which relies on propagation to the root logger and is unreliable
    across the full suite. Patching the symbol on the module is exact.

    Historically there was a second reason: the lifespan loaded webhooks.py
    under a synthetic module name, so two modules with two distinct loggers
    existed and neither caplog nor a name-based patch could be trusted. Since
    TF-660 main.py loads it as "api.v1.webhooks" and there is only one.
    """
    incoming = _stripe_sub(sub_id="sub_unknown")
    mock_logger = MagicMock()
    with patch("api.v1.webhooks.logger", mock_logger):
        await handle_subscription_created(incoming, test_db)
    assert mock_logger.warning.called, "expected a warning log"
    assert any(
        "not found locally" in str(call.args[0])
        for call in mock_logger.warning.call_args_list
    )


# ---------------------------------------------------------------------------
# handle_subscription_updated
# ---------------------------------------------------------------------------


@asyncio
async def test_subscription_updated_changes_tier(test_db, monkeypatch):
    _set_tier_price(monkeypatch, "PROFESSIONAL", "price_pro")
    inst = _seed_institution(test_db, tier="starter")
    _seed_local_sub(test_db, institution_id=inst.id, tier_price="price_starter")
    incoming = _stripe_sub(price_id="price_pro", status="active")

    await handle_subscription_updated(incoming, test_db)

    test_db.refresh(inst)
    assert inst.subscription_tier == "professional"


@asyncio
async def test_subscription_updated_handles_missing_items_attribute(test_db):
    """If Stripe object lacks .items entirely, handler must not AttributeError."""
    inst = _seed_institution(test_db, tier="starter")
    _seed_local_sub(test_db, institution_id=inst.id)
    incoming = SimpleNamespace(
        id="sub_test_123",
        status="active",
        cancel_at_period_end=False,
    )  # no items attribute, no period fields

    await handle_subscription_updated(incoming, test_db)

    persisted = (
        test_db.query(Subscription)
        .filter_by(stripe_subscription_id="sub_test_123")
        .one()
    )
    assert persisted.status == SubscriptionStatus.ACTIVE
    test_db.refresh(inst)
    assert inst.subscription_tier == "starter"  # unchanged because no price_id


# ---------------------------------------------------------------------------
# handle_subscription_deleted
# ---------------------------------------------------------------------------


@asyncio
async def test_subscription_deleted_downgrades_institution(test_db):
    inst = _seed_institution(test_db, tier="professional")
    _seed_local_sub(test_db, institution_id=inst.id)
    incoming = SimpleNamespace(id="sub_test_123")

    await handle_subscription_deleted(incoming, test_db)

    test_db.refresh(inst)
    assert inst.subscription_tier == "free"
    persisted = (
        test_db.query(Subscription)
        .filter_by(stripe_subscription_id="sub_test_123")
        .one()
    )
    assert persisted.status == SubscriptionStatus.CANCELED
    assert persisted.ended_at is not None


@asyncio
async def test_subscription_deleted_unknown_sub_logs_warning(test_db):
    # See test_subscription_created_no_local_sub_logs_warning above for why
    # we patch the module-level logger instead of using caplog.
    incoming = SimpleNamespace(id="sub_unknown")
    mock_logger = MagicMock()
    with patch("api.v1.webhooks.logger", mock_logger):
        await handle_subscription_deleted(incoming, test_db)
    assert mock_logger.warning.called, "expected a warning log"
    assert any(
        "not found locally" in str(call.args[0])
        for call in mock_logger.warning.call_args_list
    )
