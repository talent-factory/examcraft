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
        logging.info(f"[Sentry] Disabled in {environment}")
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
        ],
        # GDPR Compliance: Don't send PII by default
        send_default_pii=False,
        # Error Filtering
        before_send=filter_errors,
        # Ignore specific errors
        ignore_errors=[
            # HTTP exceptions
            "HTTPException",
            # Validation errors
            "ValidationError",
            "RequestValidationError",
            # Database connection errors in development
            "OperationalError" if environment == "development" else None,
        ],
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
