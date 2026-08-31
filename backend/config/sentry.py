"""
Sentry Configuration for ExamCraft Backend

Initializes Sentry for error tracking and performance monitoring.
Only enabled in staging and production environments.
"""

import os
import logging
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.scrubber import EventScrubber, DEFAULT_DENYLIST

# TF-758 review fix: sentry_sdk's EventScrubber matches denylist entries by
# *exact* key name (`key.lower() in denylist`), not substring -- its
# DEFAULT_DENYLIST covers a bare "password" but not our field names
# `admin_password` (impersonation step-up), `current_password`, and
# `new_password` (both change-password), so any of the three would reach
# Sentry in clear text if the request body were ever attached to an event
# (e.g. a future integration/version that captures it despite
# send_default_pii=False below). Extending the denylist is cheap insurance.
_ADDITIONAL_SCRUB_DENYLIST = DEFAULT_DENYLIST + [
    "admin_password",
    "current_password",
    "new_password",
]


def filter_errors(event, hint):
    """
    Filter out non-critical errors before sending to Sentry.

    Args:
        event: Sentry event dictionary
        hint: Additional context about the error

    Returns:
        Event dictionary or None to drop the event
    """
    if event.get("exception"):
        exc_info = hint.get("exc_info")
        if exc_info:
            exc_value = exc_info[1]

            # Don't send 404 errors
            if hasattr(exc_value, "status_code") and exc_value.status_code == 404:
                return None

            # Don't send validation errors (400)
            if hasattr(exc_value, "status_code") and exc_value.status_code == 400:
                return None

            # Don't send authentication errors (401) in development
            environment = os.getenv("ENVIRONMENT", "development")
            if environment == "development":
                if hasattr(exc_value, "status_code") and exc_value.status_code == 401:
                    return None

    return event


def init_sentry():
    """
    Initialize Sentry with environment-specific configuration.

    Only initializes if:
    - SENTRY_DSN is provided
    - ENABLE_SENTRY is set to "true"
    - ENVIRONMENT is not "development" (unless explicitly enabled)
    """
    dsn = os.getenv("SENTRY_DSN")
    environment = os.getenv("ENVIRONMENT", "development")
    version = os.getenv("APP_VERSION", "unknown")
    enable_sentry = os.getenv("ENABLE_SENTRY", "false").lower() == "true"

    # Only initialize if DSN is provided and Sentry is enabled
    if not dsn or not enable_sentry:
        # TF-359: surface a disabled-in-prod state loudly. Under uvicorn/celery
        # the root logger sits at WARNING, so an INFO line would be invisible
        # exactly where a misconfigured ENABLE_SENTRY/SENTRY_DSN matters most.
        level = (
            logging.WARNING
            if environment in ("staging", "production")
            else logging.INFO
        )
        logging.log(
            level,
            f"[Sentry] Disabled in {environment} "
            f"(dsn_set={bool(dsn)}, enable_sentry={enable_sentry})",
        )
        return

    # Configure logging integration
    logging_integration = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR,  # Send errors and above as events
    )

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=f"examcraft-backend@{version}",
        # Performance Monitoring
        # Sample 100% of transactions in development, 10% in production
        traces_sample_rate=1.0 if environment == "development" else 0.1,
        # Integrations
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            StarletteIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            RedisIntegration(),
            logging_integration,
            # Captures unhandled task exceptions and creates a transaction per
            # task run. Harmless in the FastAPI process (also instruments
            # .delay() dispatch); load-bearing in the Celery worker, where this
            # is the only thing that surfaces task failures to Sentry.
            CeleryIntegration(),
        ],
        # GDPR Compliance: Don't send PII by default
        send_default_pii=False,
        # TF-758: extend the default key-name denylist with our own
        # password-carrying field names (see _ADDITIONAL_SCRUB_DENYLIST above).
        event_scrubber=EventScrubber(denylist=_ADDITIONAL_SCRUB_DENYLIST),
        # Error Filtering
        before_send=filter_errors,
        # Ignore specific errors
        #
        # BUGFIX (TF-592): a bare `"OperationalError" if environment ==
        # "development" else None` here used to leave a literal `None` in
        # this list for every non-development environment. sentry_sdk's
        # `Client._is_ignored_error()` calls `issubclass(error, ignored_error)`
        # for any non-string entry — with `ignored_error=None` that raises
        # `TypeError: issubclass() arg 2 must be a class, a tuple of classes,
        # or a union` for EVERY exception Sentry tried to capture in prod/
        # staging, masking the real error (e.g. an LLM-Gateway timeout) behind
        # an unrelated TypeError. Build the list with a plain conditional
        # instead of `... else None` so no falsy placeholder ever lands here.
        ignore_errors=(
            [
                # HTTP exceptions
                "HTTPException",
                # Validation errors
                "ValidationError",
                "RequestValidationError",
            ]
            + (["OperationalError"] if environment == "development" else [])
        ),
    )

    logging.info(f"[Sentry] Initialized for {environment} with version {version}")


def capture_exception_with_context(
    exception: Exception,
    user_id: int = None,
    user_email: str = None,
    request_context: dict = None,
    extra_context: dict = None,
    tags: dict = None,
):
    """
    Capture an exception with additional context.

    Args:
        exception: The exception to capture
        user_id: User ID (if available)
        user_email: User email (if available and GDPR-compliant)
        request_context: Request-related context (URL, method, etc.)
        extra_context: Additional custom context
        tags: Custom tags for filtering in Sentry
    """
    with sentry_sdk.push_scope() as scope:
        # Add user context
        if user_id:
            scope.set_user(
                {
                    "id": str(user_id),
                    "email": user_email if user_email else None,
                }
            )

        # Add request context
        if request_context:
            scope.set_context("request", request_context)

        # Add extra context
        if extra_context:
            scope.set_context("extra", extra_context)

        # Add tags
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)

        # Capture the exception
        sentry_sdk.capture_exception(exception)


def capture_message_with_context(
    message: str,
    level: str = "info",
    user_id: int = None,
    extra_context: dict = None,
    tags: dict = None,
):
    """
    Capture a message with additional context.

    Args:
        message: The message to capture
        level: Severity level (debug, info, warning, error, fatal)
        user_id: User ID (if available)
        extra_context: Additional custom context
        tags: Custom tags for filtering in Sentry
    """
    with sentry_sdk.push_scope() as scope:
        # Add user context
        if user_id:
            scope.set_user({"id": str(user_id)})

        # Add extra context
        if extra_context:
            scope.set_context("extra", extra_context)

        # Add tags
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)

        # Capture the message
        sentry_sdk.capture_message(message, level=level)
