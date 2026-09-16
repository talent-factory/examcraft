"""Regression: /api/v1/activity/heartbeat is exempt from IP rate limiting
(TF-833/ADR-0007) — analog to /health, /docs, etc. Institutions behind a
shared NAT IP with several concurrently active people would otherwise hit
the existing 60-req/min IP limit quickly at ~4 heartbeats/min/person.
"""

from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from middleware.rate_limit import RateLimitMiddleware


def _make_app() -> FastAPI:
    app = FastAPI()

    @app.post("/api/v1/activity/heartbeat")
    def heartbeat():
        return {"ok": True}

    @app.get("/some-other-endpoint")
    def other():
        return {"ok": True}

    app.add_middleware(RateLimitMiddleware, requests_per_minute=1)
    return app


def _over_limit_redis() -> MagicMock:
    """A rate-limit Redis stub that always reports the client as already
    over the per-minute limit."""
    redis_mock = MagicMock()
    redis_mock.incr.return_value = 9999
    return redis_mock


class TestHeartbeatSkipsIpRateLimiting:
    def test_heartbeat_path_is_never_rate_limited(self):
        app = _make_app()

        # Patch spans app construction AND every request: Starlette builds
        # the middleware stack (and so calls RateLimitMiddleware.__init__,
        # which fetches the Redis client) lazily on the first request, not
        # at add_middleware() time.
        with patch(
            "middleware.rate_limit.RedisService.get_ratelimit_client",
            return_value=_over_limit_redis(),
        ):
            client = TestClient(app)
            for _ in range(3):
                response = client.post(
                    "/api/v1/activity/heartbeat",
                    headers={"X-Forwarded-For": "203.0.113.5"},
                )
                assert response.status_code == 200

    def test_other_endpoints_are_still_rate_limited(self):
        app = _make_app()

        # A 429 response makes RateLimitMiddleware write a real, committed
        # AuditLog row via a fresh SessionLocal() (middleware/rate_limit.py's
        # log_rate_limit_exceeded call) — irrelevant to what this test
        # verifies (the status code) and, left uncommented, an un-torn-down
        # row in the shared CI Postgres.
        with (
            patch(
                "middleware.rate_limit.RedisService.get_ratelimit_client",
                return_value=_over_limit_redis(),
            ),
            patch("services.audit_service.AuditService.log_rate_limit_exceeded"),
        ):
            client = TestClient(app)
            response = client.get(
                "/some-other-endpoint", headers={"X-Forwarded-For": "203.0.113.5"}
            )

        assert response.status_code == 429
