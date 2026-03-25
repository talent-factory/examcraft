"""Shared billing utility functions used by both billing API and webhook handlers."""

import os
import logging

logger = logging.getLogger(__name__)


def get_allowed_price_ids() -> set:
    """Get the set of allowed Stripe price IDs from environment variables.

    Supports both REACT_APP_STRIPE_PRICE_* and STRIPE_PRICE_* naming conventions.
    """
    price_ids = set()
    for env_var_pairs in [
        ("REACT_APP_STRIPE_PRICE_STARTER", "STRIPE_PRICE_STARTER"),
        ("REACT_APP_STRIPE_PRICE_PROFESSIONAL", "STRIPE_PRICE_PROFESSIONAL"),
        ("REACT_APP_STRIPE_PRICE_ENTERPRISE", "STRIPE_PRICE_ENTERPRISE"),
    ]:
        for env_var in env_var_pairs:
            price_id = os.getenv(env_var)
            if price_id:
                price_ids.add(price_id)
                break
    return price_ids


def get_tier_from_price_id(price_id: str) -> str:
    """Map Stripe price ID to tier name using environment variables.

    Supports both REACT_APP_STRIPE_PRICE_* and STRIPE_PRICE_* naming conventions.
    Raises ValueError if the price ID cannot be mapped to any tier.
    """
    price_to_tier = {}
    for tier, env_vars in [
        ("starter", ("REACT_APP_STRIPE_PRICE_STARTER", "STRIPE_PRICE_STARTER")),
        (
            "professional",
            ("REACT_APP_STRIPE_PRICE_PROFESSIONAL", "STRIPE_PRICE_PROFESSIONAL"),
        ),
        (
            "enterprise",
            ("REACT_APP_STRIPE_PRICE_ENTERPRISE", "STRIPE_PRICE_ENTERPRISE"),
        ),
    ]:
        for env_var in env_vars:
            val = os.getenv(env_var)
            if val:
                price_to_tier[val] = tier
                break

    tier = price_to_tier.get(price_id)
    if tier:
        return tier

    logger.error(
        "Could not map price_id '%s' to any tier. Configured: %s. "
        "Ensure STRIPE_PRICE_* environment variables are set correctly.",
        price_id,
        list(price_to_tier.keys()),
    )
    raise ValueError(
        f"Unknown price_id '{price_id}': not mapped to any subscription tier"
    )
