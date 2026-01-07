"""
Sentry Test Endpoints

Endpoints to test Sentry integration (only available in development).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import sentry_sdk
from config.sentry import capture_exception_with_context, capture_message_with_context

router = APIRouter(prefix="/api/sentry-test", tags=["Sentry Test"])


class SentryTestResponse(BaseModel):
    """Response model for Sentry test endpoints"""

    message: str
    sentry_enabled: bool
    environment: str


@router.get("/status", response_model=SentryTestResponse)
async def sentry_status():
    """
    Check if Sentry is enabled and configured.

    Returns:
        SentryTestResponse: Sentry configuration status
    """
    environment = os.getenv("ENVIRONMENT", "development")
    enable_sentry = os.getenv("ENABLE_SENTRY", "false").lower() == "true"
    dsn = os.getenv("SENTRY_DSN")

    return SentryTestResponse(
        message="Sentry configuration status",
        sentry_enabled=enable_sentry and dsn is not None,
        environment=environment,
    )


@router.post("/error", response_model=SentryTestResponse)
async def trigger_error():
    """
    Trigger a test error to verify Sentry error tracking.

    Only available in development environment.

    Raises:
        HTTPException: If not in development environment
        Exception: Test exception to be captured by Sentry
    """
    environment = os.getenv("ENVIRONMENT", "development")

    if environment != "development":
        raise HTTPException(
            status_code=403,
            detail="Sentry test endpoints are only available in development",
        )

    # Trigger a test error
    try:
        raise Exception("🧪 Sentry Test Error: This is a test error triggered manually")
    except Exception as e:
        # Capture with context
        capture_exception_with_context(
            exception=e,
            extra_context={
                "test_type": "manual_error_trigger",
                "endpoint": "/api/sentry-test/error",
            },
            tags={
                "test": "true",
                "feature": "sentry_integration",
            },
        )
        raise


@router.post("/message", response_model=SentryTestResponse)
async def trigger_message():
    """
    Send a test message to Sentry.

    Only available in development environment.

    Returns:
        SentryTestResponse: Success message

    Raises:
        HTTPException: If not in development environment
    """
    environment = os.getenv("ENVIRONMENT", "development")

    if environment != "development":
        raise HTTPException(
            status_code=403,
            detail="Sentry test endpoints are only available in development",
        )

    # Send a test message
    capture_message_with_context(
        message="🧪 Sentry Test Message: This is a test message sent manually",
        level="info",
        extra_context={
            "test_type": "manual_message_trigger",
            "endpoint": "/api/sentry-test/message",
        },
        tags={
            "test": "true",
            "feature": "sentry_integration",
        },
    )

    return SentryTestResponse(
        message="Test message sent to Sentry successfully",
        sentry_enabled=True,
        environment=environment,
    )


@router.post("/performance", response_model=SentryTestResponse)
async def trigger_performance():
    """
    Trigger a performance transaction to test Sentry performance monitoring.

    Only available in development environment.

    Returns:
        SentryTestResponse: Success message

    Raises:
        HTTPException: If not in development environment
    """
    environment = os.getenv("ENVIRONMENT", "development")

    if environment != "development":
        raise HTTPException(
            status_code=403,
            detail="Sentry test endpoints are only available in development",
        )

    # Create a performance transaction
    with sentry_sdk.start_transaction(op="test", name="sentry_performance_test"):
        # Simulate some work
        import time

        with sentry_sdk.start_span(op="db", description="Simulated DB Query"):
            time.sleep(0.1)

        with sentry_sdk.start_span(op="http", description="Simulated API Call"):
            time.sleep(0.2)

    return SentryTestResponse(
        message="Performance transaction sent to Sentry successfully",
        sentry_enabled=True,
        environment=environment,
    )
