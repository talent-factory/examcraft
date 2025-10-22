"""
Rate Limiting Middleware für ExamCraft AI
IP-based und User-based Rate Limiting mit Redis
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time
import logging

from services.redis_service import RedisService

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate Limiting Middleware

    Limits requests per IP address and per user
    Uses Redis for distributed rate limiting
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        enabled: bool = True,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.enabled = enabled
        self.redis_client = RedisService.get_ratelimit_client()

    async def dispatch(self, request: Request, call_next: Callable):
        """Process request with rate limiting"""

        if not self.enabled:
            return await call_next(request)

        # Skip rate limiting for health check endpoints
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Get client identifier (IP address)
        client_ip = self._get_client_ip(request)

        # Check rate limits
        is_limited, retry_after = self._check_rate_limit(client_ip)

        if is_limited:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")

            # Audit log: Rate limit exceeded (async, don't block request)
            try:
                from database import SessionLocal
                from services.audit_service import AuditService

                db = SessionLocal()
                AuditService.log_rate_limit_exceeded(
                    db, request=request, limit_type="ip"
                )
                db.close()
            except Exception as e:
                logger.error(f"Failed to log rate limit event: {e}")

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        # Process request
        response = await call_next(request)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request"""
        # Check X-Forwarded-For header (for proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to direct client IP
        if request.client:
            return request.client.host

        return "unknown"

    def _check_rate_limit(self, client_ip: str) -> tuple[bool, int]:
        """
        Check if client has exceeded rate limits

        Returns:
            (is_limited, retry_after_seconds)
        """
        try:
            current_time = int(time.time())

            # Check per-minute limit
            minute_key = f"ratelimit:minute:{client_ip}:{current_time // 60}"
            minute_count = self.redis_client.incr(minute_key)

            if minute_count == 1:
                # First request in this minute, set expiration
                self.redis_client.expire(minute_key, 60)

            if minute_count > self.requests_per_minute:
                retry_after = 60 - (current_time % 60)
                return True, retry_after

            # Check per-hour limit
            hour_key = f"ratelimit:hour:{client_ip}:{current_time // 3600}"
            hour_count = self.redis_client.incr(hour_key)

            if hour_count == 1:
                # First request in this hour, set expiration
                self.redis_client.expire(hour_key, 3600)

            if hour_count > self.requests_per_hour:
                retry_after = 3600 - (current_time % 3600)
                return True, retry_after

            return False, 0

        except Exception as e:
            logger.error(f"Rate limit check failed: {str(e)}")
            # On Redis failure, allow request (fail open)
            return False, 0


class UserRateLimiter:
    """
    User-based Rate Limiter

    Can be used as a dependency in FastAPI endpoints
    for more granular rate limiting per user
    """

    def __init__(self, requests_per_minute: int = 30, requests_per_hour: int = 500):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.redis_client = RedisService.get_ratelimit_client()

    def check_limit(self, user_id: int) -> None:
        """
        Check if user has exceeded rate limits

        Raises:
            HTTPException: If rate limit exceeded
        """
        try:
            current_time = int(time.time())

            # Check per-minute limit
            minute_key = f"ratelimit:user:minute:{user_id}:{current_time // 60}"
            minute_count = self.redis_client.incr(minute_key)

            if minute_count == 1:
                self.redis_client.expire(minute_key, 60)

            if minute_count > self.requests_per_minute:
                retry_after = 60 - (current_time % 60)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)},
                )

            # Check per-hour limit
            hour_key = f"ratelimit:user:hour:{user_id}:{current_time // 3600}"
            hour_count = self.redis_client.incr(hour_key)

            if hour_count == 1:
                self.redis_client.expire(hour_key, 3600)

            if hour_count > self.requests_per_hour:
                retry_after = 3600 - (current_time % 3600)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Try again in {retry_after // 60} minutes.",
                    headers={"Retry-After": str(retry_after)},
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"User rate limit check failed: {str(e)}")
            # On Redis failure, allow request (fail open)
            pass


def rate_limit_dependency(requests_per_minute: int = 30, requests_per_hour: int = 500):
    """
    FastAPI dependency for user-based rate limiting

    Usage:
        @router.post("/expensive-operation")
        async def expensive_operation(
            user: User = Depends(get_current_user),
            _: None = Depends(rate_limit_dependency(requests_per_minute=10))
        ):
            ...
    """
    limiter = UserRateLimiter(requests_per_minute, requests_per_hour)

    async def check_rate_limit(user_id: int):
        limiter.check_limit(user_id)

    return check_rate_limit
