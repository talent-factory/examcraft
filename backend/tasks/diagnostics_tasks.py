"""Diagnostics tasks (TF-359, TF-865).

A deliberately-failing Celery task used to verify the worker -> observability
pipeline in any environment, including production. The existing
``/api/sentry-test/*`` endpoints only exercise the API process and are
disabled outside development; this task is the only way to prove that a
*worker* exception reaches the observability backend with task context
(task_id, user_id, topic) without waiting for a real incident.

Triggered exclusively by the SuperAdmin-gated ``POST /api/admin/sentry-test/
worker-error`` endpoint. It is intentionally not routed in ``task_routes`` — the
endpoint dispatches it with an explicit ``queue=`` so it lands on a queue the
worker actually consumes.
"""

import logging

from config.observability import set_span_tag

from celery_app import celery_app

logger = logging.getLogger(__name__)


class SentryPipelineTestError(RuntimeError):
    """Raised on purpose by ``trigger_test_error`` to validate error capture.

    A dedicated type so the verification event is trivially identifiable in
    the observability backend (and so an alert rule / ignore list can target
    it precisely) and can never be confused with a genuine production
    failure. Name kept from the retired Sentry setup (TF-359) rather than
    renamed mid-migration — purely cosmetic, no external contract depends on it.
    """


@celery_app.task(
    bind=True,
    name="tasks.diagnostics_tasks.trigger_test_error",
    # No autoretry: a verification failure should produce exactly one
    # observability event, not a retry storm. acks_late (global config) still
    # acks the message on exception, so it is not requeued.
    max_retries=0,
)
def trigger_test_error(self, user_id: int, message: str | None = None) -> None:
    """Tag the current OTel span with task context and raise on purpose.

    Mirrors the context that ``generate_questions_task`` attaches so the
    verification event proves the same triage path (task_id + user_id + topic)
    that a real worker failure would exercise.
    """
    topic = "sentry-pipeline-test"
    set_span_tag("diagnostic", "true")
    set_span_tag("user_id", str(user_id))
    set_span_tag("topic", topic)

    detail = message or "TF-359 worker observability pipeline verification"
    logger.warning(
        "diagnostics.trigger_test_error: raising on purpose "
        "(task_id=%s, user_id=%s) — this is an intentional observability test, not a bug",
        self.request.id,
        user_id,
    )
    raise SentryPipelineTestError(detail)
