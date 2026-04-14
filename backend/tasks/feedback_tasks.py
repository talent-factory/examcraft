"""Celery task for asynchronous feedback processing (clustering + triggers)."""

import asyncio
import logging

from celery_app import celery_app
from database import SessionLocal

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a synchronous Celery worker context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


@celery_app.task(name="tasks.feedback_tasks.process_feedback", bind=True, max_retries=2)
def process_feedback_task(self, feedback_id: int) -> dict:
    """Process a feedback entry: clustering and trigger checks."""
    db = SessionLocal()
    try:
        from services.feedback_processor_service import FeedbackProcessorService

        service = FeedbackProcessorService(db)
        _run_async(service.process_feedback(feedback_id))
        return {"status": "processed", "feedback_id": feedback_id}
    except Exception as e:
        db.rollback()
        logger.error(
            f"Feedback processing failed for {feedback_id}: {e}", exc_info=True
        )
        raise self.retry(exc=e, countdown=30)
    finally:
        db.close()
