"""Celery task for asynchronous feedback processing (clustering + triggers)."""

import asyncio
import logging

from celery_app import celery_app
from database import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.feedback_tasks.process_feedback", bind=True, max_retries=2)
def process_feedback_task(self, feedback_id: int) -> dict:
    """Process a feedback entry: clustering and trigger checks."""
    db = SessionLocal()
    try:
        from services.feedback_processor_service import FeedbackProcessorService

        service = FeedbackProcessorService(db)
        asyncio.get_event_loop().run_until_complete(
            service.process_feedback(feedback_id)
        )
        return {"status": "processed", "feedback_id": feedback_id}
    except Exception as e:
        logger.error(f"Feedback processing failed for {feedback_id}: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=30)
    finally:
        db.close()
