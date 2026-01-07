"""
Sentry Context Middleware

Adds user and request context to Sentry events.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import sentry_sdk


class SentryContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add user and request context to Sentry events.

    This middleware:
    - Adds authenticated user information to Sentry
    - Adds request metadata (URL, method, query params)
    - Sets custom tags for filtering in Sentry
    """

    async def dispatch(self, request: Request, call_next):
        """
        Process the request and add context to Sentry.

        Args:
            request: FastAPI Request object
            call_next: Next middleware/route handler

        Returns:
            Response from the next handler
        """
        # Add user context if authenticated
        if hasattr(request.state, "user") and request.state.user:
            user = request.state.user
            sentry_sdk.set_user(
                {
                    "id": str(user.id),
                    "email": user.email if hasattr(user, "email") else None,
                    "username": user.username if hasattr(user, "username") else None,
                }
            )

        # Add request context
        sentry_sdk.set_context(
            "request",
            {
                "url": str(request.url),
                "method": request.method,
                "query_params": dict(request.query_params),
                "path": request.url.path,
            },
        )

        # Add custom tags
        sentry_sdk.set_tag("endpoint", request.url.path)
        sentry_sdk.set_tag("method", request.method)

        # Process the request
        response = await call_next(request)

        # Add response status code tag
        sentry_sdk.set_tag("status_code", response.status_code)

        return response
