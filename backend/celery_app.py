"""
Celery Application Configuration
Handles asynchronous task processing with RabbitMQ broker
"""

from celery import Celery
from kombu import Exchange, Queue
import os
import logging

logger = logging.getLogger(__name__)

# Celery App Initialization
celery_app = Celery(
    "examcraft",
    broker=os.getenv(
        "CELERY_BROKER_URL",
        "amqp://examcraft:secure_password_here@rabbitmq:5672/",  # pragma: allowlist secret
    ),
    backend=os.getenv(
        "CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://redis:6379/3")
    ),
    include=[
        "tasks.document_tasks",
        "tasks.question_tasks",
        # "tasks.rag_tasks",  # Requires Premium RAGService
        "tasks.session_cleanup",
        "tasks.feedback_tasks",
        "tasks.maintenance_tasks",
    ],
)

# Celery Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Zurich",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300,  # 55 minutes warning
    worker_prefetch_multiplier=1,  # Fair distribution
    worker_max_tasks_per_child=50,  # Prevent memory leaks
    task_acks_late=True,  # Acknowledge after task completion
    worker_disable_rate_limits=False,
)

# Beat-Schedule für periodische Wartung (TF-329 Watchdog).
# Voraussetzung: ein laufender `celery -A celery_app beat`-Process. In der
# Fly.io-Deployment können wir das via einer separaten Process-Group im
# fly.toml von `examcraft-celery` realisieren — oder als `--beat`-Flag auf dem
# Worker für Single-Instance-Setup. Siehe TF-329 PR-Body für Details.
celery_app.conf.beat_schedule = {
    "reconcile-stuck-jobs-every-5-minutes": {
        "task": "tasks.maintenance_tasks.reconcile_stuck_jobs",
        "schedule": 300.0,  # 5 Minuten
    },
}

# Queue Definitions
default_exchange = Exchange("default", type="direct")

celery_app.conf.task_queues = (
    Queue(
        "document_processing",
        default_exchange,
        routing_key="document.process",
        durable=True,
        queue_arguments={"x-max-priority": 10},
    ),
    Queue(
        "rag_embedding",
        default_exchange,
        routing_key="rag.embed",
        durable=True,
    ),
    Queue(
        "question_generation",
        default_exchange,
        routing_key="question.generate",
        durable=True,
    ),
    Queue(
        "notifications",
        default_exchange,
        routing_key="notification.send",
        durable=True,
    ),
    Queue(
        "feedback_processing",
        default_exchange,
        routing_key="feedback.process",
        durable=True,
    ),
)

# Task Routes
celery_app.conf.task_routes = {
    "tasks.document_tasks.process_document": {
        "queue": "document_processing",
        "routing_key": "document.process",
    },
    "tasks.rag_tasks.create_embeddings": {
        "queue": "rag_embedding",
        "routing_key": "rag.embed",
    },
    "tasks.notification_tasks.subscribe_to_newsletter": {
        "queue": "notifications",
        "routing_key": "notification.send",
    },
    "tasks.question_tasks.generate_questions": {
        "queue": "question_generation",
        "routing_key": "question.generate",
    },
    "tasks.feedback_tasks.process_feedback": {
        "queue": "feedback_processing",
        "routing_key": "feedback.process",
    },
}

logger.info("Celery app initialized with RabbitMQ broker")
