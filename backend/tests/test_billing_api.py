"""Tests for billing utility functions and billing API helpers (TF-202)"""

import os
import pytest
from unittest.mock import patch, MagicMock


class TestTierMapping:
    """Tests for get_tier_from_price_id helper"""

    def test_maps_starter_price(self):
        from utils.billing_utils import get_tier_from_price_id

        with patch.dict(
            "os.environ",
            {"REACT_APP_STRIPE_PRICE_STARTER": "price_test_starter"},
        ):
            assert get_tier_from_price_id("price_test_starter") == "starter"

    def test_maps_professional_price(self):
        from utils.billing_utils import get_tier_from_price_id

        with patch.dict(
            "os.environ",
            {"REACT_APP_STRIPE_PRICE_PROFESSIONAL": "price_test_pro"},
        ):
            assert get_tier_from_price_id("price_test_pro") == "professional"

    def test_maps_enterprise_price(self):
        from utils.billing_utils import get_tier_from_price_id

        with patch.dict(
            "os.environ",
            {"REACT_APP_STRIPE_PRICE_ENTERPRISE": "price_test_ent"},
        ):
            assert get_tier_from_price_id("price_test_ent") == "enterprise"

    def test_unknown_raises_value_error(self):
        from utils.billing_utils import get_tier_from_price_id

        with pytest.raises(ValueError, match="Unknown price_id"):
            get_tier_from_price_id("price_xyz_unknown")

    def test_supports_legacy_env_var_names(self):
        from utils.billing_utils import get_tier_from_price_id

        # Clear REACT_APP_ variants so legacy STRIPE_PRICE_ fallback is used
        clean_env = {
            k: "" for k in os.environ if k.startswith("REACT_APP_STRIPE_PRICE_")
        }
        clean_env["STRIPE_PRICE_STARTER"] = "price_legacy_starter"
        with patch.dict("os.environ", clean_env):
            assert get_tier_from_price_id("price_legacy_starter") == "starter"


class TestAllowedPriceIds:
    """Tests for get_allowed_price_ids helper"""

    def test_returns_empty_when_no_env_vars(self):
        from utils.billing_utils import get_allowed_price_ids

        with patch.dict("os.environ", {}, clear=True):
            assert get_allowed_price_ids() == set()

    def test_returns_configured_prices(self):
        from utils.billing_utils import get_allowed_price_ids

        with patch.dict(
            "os.environ",
            {
                "REACT_APP_STRIPE_PRICE_STARTER": "price_s",
                "REACT_APP_STRIPE_PRICE_PROFESSIONAL": "price_p",
            },
        ):
            result = get_allowed_price_ids()
            assert "price_s" in result
            assert "price_p" in result

    def test_supports_legacy_env_var_names(self):
        from utils.billing_utils import get_allowed_price_ids

        env = {"STRIPE_PRICE_STARTER": "price_legacy"}
        # Remove REACT_APP_ variant so legacy fallback is used
        for key in list(os.environ.keys()):
            if key.startswith("REACT_APP_STRIPE_PRICE_") or key.startswith(
                "STRIPE_PRICE_"
            ):
                env[key] = ""
        env["STRIPE_PRICE_STARTER"] = "price_legacy"
        with patch.dict("os.environ", env):
            result = get_allowed_price_ids()
            assert "price_legacy" in result


class TestIsBillingOwner:
    """Tests for _is_billing_owner helper"""

    def test_returns_false_when_no_subscription(self):
        from api.v1.billing import _is_billing_owner

        user = MagicMock()
        assert _is_billing_owner(user, None) is False

    def test_returns_false_when_no_billing_owner_set(self):
        from api.v1.billing import _is_billing_owner

        user = MagicMock()
        subscription = MagicMock()
        subscription.billing_owner_id = None
        assert _is_billing_owner(user, subscription) is False

    def test_returns_true_when_user_is_owner(self):
        from api.v1.billing import _is_billing_owner

        user = MagicMock()
        user.id = 42
        subscription = MagicMock()
        subscription.billing_owner_id = 42
        assert _is_billing_owner(user, subscription) is True

    def test_returns_false_when_user_is_not_owner(self):
        from api.v1.billing import _is_billing_owner

        user = MagicMock()
        user.id = 42
        subscription = MagicMock()
        subscription.billing_owner_id = 99
        assert _is_billing_owner(user, subscription) is False
