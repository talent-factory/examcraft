"""
Celery Application Configuration
Handles asynchronous task processing with RabbitMQ broker
"""

from celery import Celery
from celery.signals import celeryd_init
from kombu import Exchange, Queue
import os
import logging

logger = logging.getLogger(__name__)


@celeryd_init.connect
def _init_worker_sentry(**_kwargs):
    """Initialize Sentry in the Celery worker process (TF-359).

    The FastAPI process calls ``init_sentry()`` in ``main.py``; the worker
    runs ``celery -A celery_app worker`` and never imports ``main``, so without
    this hook the worker was blind to all task exceptions.

    ``celeryd_init`` fires once when the worker daemon boots, before the prefork
    pool spawns its children — the fork-safe entry point. ``CeleryIntegration``
    (added in ``config/sentry.py``) then propagates the SDK across forked
    children and on ``worker_max_tasks_per_child`` recycles. ``init_sentry()``
    is a no-op unless ``ENABLE_SENTRY=true`` and ``SENTRY_DSN`` are set, so
    booting a worker locally without those stays silent.
    """
    from config.sentry import init_sentry

    init_sentry()


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
        "tasks.diagnostics_tasks",  # TF-359 Sentry worker-pipeline verification
        "tasks.import_submissions_task",  # TF-412 async result import
        "tasks.moodle_feedback_push_task",  # TF-435 feedback push back to Moodle
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
# Fly.io-Deployment läuft Beat als Sidecar-Process in `fly.celery.toml`
# (oder als `--beat`-Flag auf dem Worker für Single-Instance-Setup). Siehe
# docs/superpowers/plans/2026-04-28-tf329-watchdog-pending-jobs.md für die
# Deployment-Rezeptur.
celery_app.conf.beat_schedule = {
    "reconcile-stuck-jobs-every-5-minutes": {
        "task": "tasks.maintenance_tasks.reconcile_stuck_jobs",
        "schedule": 300.0,  # 5 Minuten
    },
    # TF-412: age-fail ImportJob rows stuck in queued/running so the
    # polling client always converges on a terminal status.
    "reap-stuck-import-jobs-every-5-minutes": {
        "task": "tasks.maintenance_tasks.reap_stuck_import_jobs",
        "schedule": 300.0,  # 5 Minuten
    },
    # TF-435: same watchdog for outbound MoodleFeedbackPushJob rows.
    "reap-stuck-moodle-feedback-jobs-every-5-minutes": {
        "task": "tasks.maintenance_tasks.reap_stuck_moodle_feedback_jobs",
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
    Queue(
        # TF-412 async result import. x-max-priority so the task's
        # priority=5 is honoured. A task with no route lands on the
        # default ``celery`` queue, which the queue-pinned workers
        # (docker-compose --queues, and the Fly worker via task_queues)
        # never consume — the job would sit ``queued`` forever.
        "import_processing",
        default_exchange,
        routing_key="import.process",
        durable=True,
        queue_arguments={"x-max-priority": 10},
    ),
)

# Task Routes
celery_app.conf.task_routes = {
    "tasks.document_tasks.process_document": {
        "queue": "document_processing",
        "routing_key": "document.process",
    },
    "tasks.document_tasks.reprocess_document_ocr": {
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
    "tasks.import_submissions_task.import_submissions": {
        "queue": "import_processing",
        "routing_key": "import.process",
    },
}

logger.info("Celery app initialized with RabbitMQ broker")
