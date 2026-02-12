"""
Celery Application Configuration for Flower Monitoring
Lightweight version without task imports - only broker/backend config needed.
"""

from celery import Celery
import os

celery_app = Celery(
    "examcraft",
    broker=os.getenv("CELERY_BROKER_URL", "amqp://examcraft:password@rabbitmq:5672/"),
    backend=os.getenv(
        "CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://redis:6379/1")
    ),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Zurich",
    enable_utc=True,
)
