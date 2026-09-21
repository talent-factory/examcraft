"""
Sentry Test Endpoints

Two routers:
- ``router``: public dev-only smoke tests (API process), 403 outside development.
  Registered in main.py only when ENVIRONMENT == development.
- ``admin_router``: SuperAdmin-gated, registered in ALL environments. Lets the
  team verify the Celery worker -> observability pipeline in production
  (TF-359), which the dev-only endpoints above cannot do.

TF-865: internals migrated off sentry_sdk onto specula-client-python/OTel so
this module still imports once sentry-sdk is removed from the dependency
tree. Renaming the routes/module itself to a "Specula smoke test" identity is
tracked separately (TF-868) — out of scope here.
"""

from fastapi import APIRouter, Depends, HTTPException
from opentelemetry import trace
from pydantic import BaseModel
import logging
import os
from config.observability import record_exception, set_span_tag
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
    Check if the observability backend is enabled and configured.

    Returns:
        SentryTestResponse: Observability configuration status
    """
    environment = os.getenv("ENVIRONMENT", "development")
    otel_exporter_endpoint = os.getenv("OTEL_EXPORTER_ENDPOINT")
    specula_team_api_key = os.getenv("SPECULA_TEAM_API_KEY")

    return SentryTestResponse(
        message="Observability configuration status",
        sentry_enabled=bool(otel_exporter_endpoint) and bool(specula_team_api_key),
        environment=environment,
    )


@router.post("/error", response_model=SentryTestResponse)
async def trigger_error():
    """
    Trigger a test error to verify observability error tracking.

    Only available in development environment.

    Raises:
        HTTPException: If not in development environment
        Exception: Test exception to be recorded on the current OTel span
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
        # Record with context
        record_exception(
            e,
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
    Send a test message to the observability backend.

    Only available in development environment. Logged at ERROR level so it
    clears the SpeculaLogHandler's level gate (see config/observability.py) —
    a lower level would silently never reach the collector.

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

    # Send a test message. `specula_*` extras are forwarded as OTLP log
    # attributes by SpeculaLogHandler (see specula_client.logging).
    logger.error(
        "🧪 Sentry Test Message: This is a test message sent manually",
        extra={
            "specula_test_type": "manual_message_trigger",
            "specula_endpoint": "/api/sentry-test/message",
        },
    )
    set_span_tag("test", "true")
    set_span_tag("feature", "sentry_integration")

    return SentryTestResponse(
        message="Test message sent successfully",
        sentry_enabled=True,
        environment=environment,
    )


@router.post("/performance", response_model=SentryTestResponse)
async def trigger_performance():
    """
    Trigger a nested-span trace to test observability performance monitoring.

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

    # Create a nested-span trace
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("sentry_performance_test"):
        # Simulate some work
        import time

        with tracer.start_as_current_span("db.Simulated DB Query"):
            time.sleep(0.1)

        with tracer.start_as_current_span("http.Simulated API Call"):
            time.sleep(0.2)

    return SentryTestResponse(
        message="Performance trace sent successfully",
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
    """Dispatch a Celery task that fails on purpose, to verify worker -> observability.

    SuperAdmin-only and available in production (TF-359 acceptance criterion:
    "ein absichtlich provozierter Worker-Fehler erscheint in Sentry mit
    Stacktrace + Task-Kontext"). The dispatched task raises
    ``SentryPipelineTestError`` in the worker; OTel's Celery instrumentation
    (TF-865, ``instrument_celery=True`` in ``config/observability.py``)
    captures it as a span exception.

    Returns the Celery task id so the resulting trace can be correlated
    (search ``diagnostic:true`` or the task id in the observability backend).
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
                    f"TF-359 observability worker pipeline verification "
                    f"(triggered by SuperAdmin user {current_user.id})"
                ),
            },
            queue="question_generation",
        )
    except Exception as broker_error:
        # A diagnostic endpoint is most likely to be hit when the broker is
        # already degraded — return an actionable 503 (mirrors the production
        # dispatch path in api/rag_exams.py) instead of an opaque 500 that
        # can't be told apart from a broken observability pipeline.
        logger.error(
            "Observability worker-test dispatch failed (broker unreachable?): %s",
            broker_error,
        )
        raise HTTPException(
            status_code=503,
            detail="Task-Queue nicht erreichbar — Broker/Worker prüfen.",
        ) from broker_error

    return WorkerErrorResponse(
        message=(
            "Worker error dispatched. Check the observability backend for a "
            "SentryPipelineTestError event tagged diagnostic=true with this "
            "task_id."
        ),
        task_id=result.id,
        environment=os.getenv("ENVIRONMENT", "development"),
    )
