"""Impersonation Context Middleware (TF-741).

Resets the request-scoped impersonation ContextVar (see
``utils/impersonation_context.py``) to ``None`` around every request so
a value set by one request's ``get_current_user`` call can never leak
into a later, unrelated request — regardless of how the ASGI server
schedules/reuses tasks under the hood.
"""

from starlette.middleware.base import BaseHTTPMiddleware

from utils.impersonation_context import set_impersonation_context


class ImpersonationContextMiddleware(BaseHTTPMiddleware):
    """Ensures the impersonation context starts and ends clean per request."""

    async def dispatch(self, request, call_next):
        set_impersonation_context(None)
        try:
            return await call_next(request)
        finally:
            set_impersonation_context(None)
