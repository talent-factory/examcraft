"""Unit tests for TF-760: ``ImpersonationRateLimiter``.

Per-admin hourly/daily cap on starting impersonation sessions
(``POST /api/admin/users/{id}/impersonate``). Exercises the limiter's
pure decision logic directly, against an in-memory fake of the Redis
ratelimit client -- no live Redis needed, no HTTP layer involved.
Endpoint-level wiring (429 response, ``Retry-After`` header, audit log)
is covered separately in ``test_impersonation_api.py``.
"""

import pytest

from middleware.rate_limit import ImpersonationRateLimiter


class FakeRatelimitRedis:
    """Minimal in-memory stand-in for the Redis ratelimit client -- just
    the INCR/EXPIRE operations ``ImpersonationRateLimiter`` relies on."""

    def __init__(self):
        self._counts: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]

    def expire(self, key: str, ttl: int) -> None:
        pass


@pytest.fixture
def fake_redis(monkeypatch):
    client = FakeRatelimitRedis()
    monkeypatch.setattr(
        "middleware.rate_limit.RedisService.get_ratelimit_client",
        lambda: client,
    )
    return client


def test_allows_requests_under_both_limits(fake_redis):
    limiter = ImpersonationRateLimiter(requests_per_hour=10, requests_per_day=30)

    for _ in range(9):
        is_limited, retry_after = limiter.check(admin_user_id=1)
        assert is_limited is False
        assert retry_after == 0


def test_blocks_once_hourly_limit_is_exceeded(fake_redis):
    limiter = ImpersonationRateLimiter(requests_per_hour=3, requests_per_day=30)

    for _ in range(3):
        is_limited, _ = limiter.check(admin_user_id=1)
        assert is_limited is False

    is_limited, retry_after = limiter.check(admin_user_id=1)

    assert is_limited is True
    assert 0 < retry_after <= 3600


def test_blocks_once_daily_limit_is_exceeded_even_within_hourly_budget(fake_redis):
    limiter = ImpersonationRateLimiter(requests_per_hour=100, requests_per_day=3)

    for _ in range(3):
        is_limited, _ = limiter.check(admin_user_id=1)
        assert is_limited is False

    is_limited, retry_after = limiter.check(admin_user_id=1)

    assert is_limited is True
    assert 0 < retry_after <= 86400


def test_admins_are_tracked_independently(fake_redis):
    limiter = ImpersonationRateLimiter(requests_per_hour=2, requests_per_day=30)

    limiter.check(admin_user_id=1)
    limiter.check(admin_user_id=1)
    is_limited_admin1, _ = limiter.check(admin_user_id=1)
    is_limited_admin2, _ = limiter.check(admin_user_id=2)

    assert is_limited_admin1 is True
    assert is_limited_admin2 is False


def test_fails_open_when_redis_is_unavailable(monkeypatch):
    class BrokenRedis:
        def incr(self, key):
            raise ConnectionError("redis unreachable")

    monkeypatch.setattr(
        "middleware.rate_limit.RedisService.get_ratelimit_client",
        lambda: BrokenRedis(),
    )
    limiter = ImpersonationRateLimiter(requests_per_hour=1, requests_per_day=1)

    is_limited, retry_after = limiter.check(admin_user_id=1)

    assert is_limited is False
    assert retry_after == 0
