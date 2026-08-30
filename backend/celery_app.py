"""
Celery Application Configuration
Handles asynchronous task processing with RabbitMQ broker
"""

from celery import Celery
from celery.schedules import crontab
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


@celeryd_init.connect
def _validate_claude_model(**_kwargs):
    """Validate the active Claude model against the Models API at worker boot
    (TF-438).

    Mirrors the FastAPI lifespan check on the worker — the process that runs
    question generation — so a retired model is caught at restart time and falls
    back to a curated alternative, instead of looping on the first job (the
    TF-437 incident). Registered after the Sentry hook so its alert is captured.
    ``celeryd_init`` runs in the main worker process before the prefork pool
    spawns, in a plain sync context, so ``asyncio.run`` is safe. Fail-open.
    """
    import asyncio

    from services.claude_service import validate_claude_model_on_startup

    try:
        asyncio.run(validate_claude_model_on_startup())
    except Exception:
        logger.warning(
            "Claude model startup validation failed in worker (ignored)",
            exc_info=True,
        )


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
        "tasks.gdpr_tasks",  # TF-745 GDPR scheduled deletion
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

# Beat schedule for periodic maintenance (TF-329 watchdog) and the TF-745
# GDPR sweep. Prerequisite: a running `celery -A celery_app beat` process —
# as of TF-745 the single Fly worker runs it in-process via `--beat` on
# `fly.celery.toml` (see the comment there on the single-instance caveat).
# See docs/superpowers/plans/2026-04-28-tf329-watchdog-pending-jobs.md for
# the original deployment recipe.
celery_app.conf.beat_schedule = {
    "reconcile-stuck-jobs-every-5-minutes": {
        "task": "tasks.maintenance_tasks.reconcile_stuck_jobs",
        "schedule": 300.0,  # 5 minutes
    },
    # TF-412: age-fail ImportJob rows stuck in queued/running so the
    # polling client always converges on a terminal status.
    "reap-stuck-import-jobs-every-5-minutes": {
        "task": "tasks.maintenance_tasks.reap_stuck_import_jobs",
        "schedule": 300.0,  # 5 minutes
    },
    # TF-435: same watchdog for outbound MoodleFeedbackPushJob rows.
    "reap-stuck-moodle-feedback-jobs-every-5-minutes": {
        "task": "tasks.maintenance_tasks.reap_stuck_moodle_feedback_jobs",
        "schedule": 300.0,  # 5 minutes
    },
    # TF-741: close ImpersonationSession rows nobody ended manually once
    # their 30-minute access token has expired. Pure DB bookkeeping --
    # the token itself is already unusable via JWT exp.
    "reap-stuck-impersonation-sessions-every-5-minutes": {
        "task": "tasks.maintenance_tasks.reap_stuck_impersonation_sessions",
        "schedule": 300.0,  # 5 minutes
    },
    # TF-745: täglicher Sweep für fällige DSGVO-Löschanträge
    # (scheduled_deletion_date <= jetzt). Wall-clock-verankertes crontab
    # statt eines 86400s-Intervalls (Review-Fix): Fly setzt den In-Prozess-
    # `--beat` bei jedem Deploy/Machine-Replace neu auf, der PersistentScheduler
    # verliert dabei seinen Shelve-State — ein Intervall-Schedule würde bei
    # häufigen Deploys "letzter Lauf + 24h" ab dem letzten Neustart rechnen
    # und könnte den Sweep so über Tage hinweg verzögern. `crontab` wertet
    # stattdessen die aktuelle Uhrzeit aus (03:00 in `timezone`, siehe
    # celery_app.conf.update oben) und ist damit neustart-sicher.
    "process-scheduled-gdpr-deletions-daily": {
        "task": "tasks.gdpr_tasks.process_scheduled_deletions",
        "schedule": crontab(hour=3, minute=0),
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
    Queue(
        # TF-745 review fix: all ``beat_schedule`` tasks (the TF-329
        # watchdogs *and* the GDPR sweep/deletion tasks) previously had no
        # route and landed on the unconsumed default ``celery`` queue — see
        # the ``import_processing`` comment above for why that means the
        # task never runs at all. Beat itself was never deployed either
        # (see fly.celery.toml), so this went unnoticed until TF-745 made a
        # working daily sweep a hard compliance requirement.
        "maintenance_processing",
        default_exchange,
        routing_key="maintenance.process",
        durable=True,
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
    # TF-329 watchdogs + TF-745 GDPR sweep/deletion — all beat-scheduled
    # maintenance tasks. See the ``maintenance_processing`` queue comment.
    "tasks.maintenance_tasks.reconcile_stuck_jobs": {
        "queue": "maintenance_processing",
        "routing_key": "maintenance.process",
    },
    "tasks.maintenance_tasks.reap_stuck_import_jobs": {
        "queue": "maintenance_processing",
        "routing_key": "maintenance.process",
    },
    "tasks.maintenance_tasks.reap_stuck_moodle_feedback_jobs": {
        "queue": "maintenance_processing",
        "routing_key": "maintenance.process",
    },
    # TF-741, gemergt nach TF-745 hierher — derselbe Routing-Fix nötig, sonst
    # exakt derselbe Bug (Task landet auf der nie konsumierten Default-Queue
    # "celery"), den diese PR für die übrigen beat_schedule-Tasks behebt.
    "tasks.maintenance_tasks.reap_stuck_impersonation_sessions": {
        "queue": "maintenance_processing",
        "routing_key": "maintenance.process",
    },
    "tasks.gdpr_tasks.process_scheduled_deletions": {
        "queue": "maintenance_processing",
        "routing_key": "maintenance.process",
    },
    "tasks.gdpr_tasks.execute_gdpr_deletion": {
        "queue": "maintenance_processing",
        "routing_key": "maintenance.process",
    },
}

logger.info("Celery app initialized with RabbitMQ broker")
