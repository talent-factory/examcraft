"""
Sentry Test Endpoints

Two routers:
- ``router``: public dev-only smoke tests (API process), 403 outside development.
  Registered in main.py only when ENVIRONMENT == development.
- ``admin_router``: SuperAdmin-gated, registered in ALL environments. Lets the
  team verify the Celery worker -> Sentry pipeline in production (TF-359), which
  the dev-only endpoints above cannot do.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import logging
import os
import sentry_sdk
from config.sentry import capture_exception_with_context, capture_message_with_context
from models.auth import User
from utils.auth_utils import get_current_superuser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sentry-test", tags=["Sentry Test"])

# Always registered (see main.py) but locked to SuperAdmins, so it is safe to
# expose in production where ``router`` above is not mounted.
admin_router = APIRouter(prefix="/api/admin/sentry-test", tags=["Admin: Sentry Test"])


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


class WorkerErrorResponse(BaseModel):
    """Response model for the SuperAdmin worker-error trigger."""

    message: str
    task_id: str
    environment: str


@admin_router.post("/worker-error", response_model=WorkerErrorResponse)
async def trigger_worker_error(
    current_user: User = Depends(get_current_superuser),
) -> WorkerErrorResponse:
    """Dispatch a Celery task that fails on purpose, to verify worker -> Sentry.

    SuperAdmin-only and available in production (TF-359 acceptance criterion:
    "ein absichtlich provozierter Worker-Fehler erscheint in Sentry mit
    Stacktrace + Task-Kontext"). The dispatched task raises
    ``SentryPipelineTestError`` in the worker; ``CeleryIntegration`` captures it.

    Returns the Celery task id so the resulting Sentry event can be correlated
    (search ``diagnostic:true`` or the task id in the Sentry issue).
    """
    from celery_app import celery_app

    # Route explicitly onto a queue the worker actually consumes — the task is
    # intentionally absent from task_routes, so without this it would land on
    # the unconsumed default queue and never run.
    try:
        result = celery_app.send_task(
            "tasks.diagnostics_tasks.trigger_test_error",
            kwargs={
                "user_id": current_user.id,
                "message": (
                    f"TF-359 Sentry worker pipeline verification "
                    f"(triggered by SuperAdmin user {current_user.id})"
                ),
            },
            queue="question_generation",
        )
    except Exception as broker_error:
        # A diagnostic endpoint is most likely to be hit when the broker is
        # already degraded — return an actionable 503 (mirrors the production
        # dispatch path in api/rag_exams.py) instead of an opaque 500 that
        # can't be told apart from a broken Sentry pipeline.
        logger.error(
            "Sentry worker-test dispatch failed (broker unreachable?): %s",
            broker_error,
        )
        raise HTTPException(
            status_code=503,
            detail="Task-Queue nicht erreichbar — Broker/Worker prüfen.",
        ) from broker_error

    return WorkerErrorResponse(
        message=(
            "Worker error dispatched. Check Sentry for a SentryPipelineTestError "
            "event tagged diagnostic=true with this task_id."
        ),
        task_id=result.id,
        environment=os.getenv("ENVIRONMENT", "development"),
    )
