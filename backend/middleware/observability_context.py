"""
Observability Context Middleware (TF-865)

Adds user and request context to the currently active OTel span, replacing
the retired Sentry scope (`middleware/sentry_context.py`, pre-TF-865).

No-op when tracing is disabled/uninstrumented: ``trace.get_current_span()``
then returns an ``INVALID_SPAN`` whose ``set_attribute()`` is a safe no-op
(same fail-open behaviour as the retired Sentry setup, where an unconfigured
SDK made every ``sentry_sdk.set_*`` call a no-op too).
"""

import logging

from fastapi import Request
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware

# scrub_pii via config.observability (not directly from specula_client):
# that module already guards the import for a public/OSS build where
# specula_client isn't installed (package-fail-open, see its module
# docstring) -- scrub_pii is None there, and the try/except below already
# treats "not callable" the same as any other scrubbing failure (fail
# closed: omit the attribute rather than risk an unscrubbed leak).
from config.observability import EXTRA_PII_DENYLIST, scrub_pii

logger = logging.getLogger(__name__)


class ObservabilityContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add user and request context to the current OTel span.

    This middleware:
    - Adds authenticated user information as span attributes
    - Adds request metadata (URL, method, query params) as span attributes,
      with query params scrubbed for known-sensitive field names
    - Adds the response status code once the handler has run
    """

    async def dispatch(self, request: Request, call_next):
        """
        Process the request and add context to the current OTel span.

        Args:
            request: FastAPI Request object
            call_next: Next middleware/route handler

        Returns:
            Response from the next handler
        """
        span = trace.get_current_span()

        # Add user context if authenticated
        if hasattr(request.state, "user") and request.state.user:
            user = request.state.user
            span.set_attribute("enduser.id", str(user.id))
            if getattr(user, "email", None):
                span.set_attribute("enduser.email", user.email)
            if getattr(user, "username", None):
                span.set_attribute("enduser.username", user.username)

        # Add request context (query params scrubbed -- may carry tokens/
        # secrets from a misbehaving client, e.g. a leaked reset token or a
        # password echoed into a query string by a misconfigured caller; see
        # config.observability.EXTRA_PII_DENYLIST for why the extra terms are
        # currently redundant but kept explicit).
        if scrub_pii is None:
            # Package-fail-open (config.observability's module docstring):
            # no exporter is running in this case either (instrument_app()
            # is a no-op too), so this is silent by design, not a warning.
            scrubbed_query_params = None
        else:
            try:
                scrubbed_query_params = scrub_pii(
                    dict(request.query_params), extra_denylist=EXTRA_PII_DENYLIST
                )
            except (TypeError, ValueError):
                # Fail closed (see config.observability.record_exception's
                # same rationale): never fall back to the unscrubbed params,
                # and never let a scrubbing bug break the actual request.
                logger.warning(
                    "[Observability] query params could not be scrubbed, "
                    "omitting http.query_params from this span",
                    exc_info=True,
                )
                scrubbed_query_params = None

        if scrubbed_query_params is not None:
            span.set_attribute("http.query_params", str(scrubbed_query_params))
        span.set_attribute("endpoint", request.url.path)
        span.set_attribute("method", request.method)

        # Process the request
        response = await call_next(request)

        # Add response status code attribute
        span.set_attribute("status_code", response.status_code)

        return response
