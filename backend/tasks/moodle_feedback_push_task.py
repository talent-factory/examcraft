"""Celery task: push graded feedback back to Moodle (TF-435)."""

from __future__ import annotations

import logging

from celery_app import celery_app
from database import SessionLocal
from services.moodle_feedback.service import MoodleFeedbackPushService

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="tasks.moodle_feedback_push_task.push_moodle_feedback",
    priority=5,
    acks_late=True,
)
def push_moodle_feedback(  # type: ignore[no-untyped-def]
    self, *, job_id: int, force_transport: str | None = None
) -> dict:
    db = SessionLocal()
    try:
        MoodleFeedbackPushService(db).run(
            job_id=job_id, force_transport=force_transport
        )
        # The job row itself carries the authoritative status; the task return
        # value is only a Celery breadcrumb, so keep it minimal to avoid a
        # second, drifting "status" vocabulary.
        return {"job_id": job_id}
    finally:
        db.close()
