"""
Celery Task für asynchrone Fragengenerierung mit Progress-Tracking.
Sendet per-Frage Progress-Updates via ProgressTask.update_progress().
"""

import dataclasses
import logging
from typing import Any, Dict

from celery.exceptions import Ignore, Reject

from celery_app import celery_app
from tasks.document_tasks import ProgressTask, run_async

logger = logging.getLogger(__name__)

# Premium-Package ist im Worker unter /app/premium verfügbar.
# In lokalen Tests wird RAGService via patch("tasks.question_tasks.RAGService") gemockt.
try:
    from premium.services.rag_service import RAGService
except ImportError:
    RAGService = None  # type: ignore[assignment,misc]


@celery_app.task(
    bind=True,
    base=ProgressTask,
    name="tasks.question_tasks.generate_questions",
    autoretry_for=(Exception,),
    dont_autoretry_for=(
        Ignore,
        Reject,
    ),  # Celery-interne Exceptions nicht nochmals retry
    retry_kwargs={"max_retries": 2, "countdown": 30},
)
def generate_questions_task(
    self, request_data: Dict[str, Any], user_id: str
) -> Dict[str, Any]:
    """
    Asynchrone Fragengenerierung mit per-Frage Progress-Updates.

    Args:
        request_data: Serialisierter RAGExamRequest als dict (via model_dump(mode='json'))
        user_id: ID des Users (für Logging)

    Returns:
        Dict mit exam_id, topic, questions, generation_time, quality_metrics
    """
    if RAGService is None:
        raise Reject(
            "Premium RAGService nicht verfügbar (Core-Deployment). Task wird nicht wiederholt.",
            requeue=False,
        )

    from services.rag_service import RAGExamRequest

    rag_request = RAGExamRequest(**request_data)
    question_count = rag_request.question_count
    # total_steps = N + 2:
    #   Step 0:     Task-Start (emittiert vom Task)
    #   Step 1:     Context geladen (emittiert via Callback)
    #   Steps 2..N+1: Fragen 1..N (emittiert via Callback)
    # Der Sprung von Step N+1 (letztes PROGRESS) auf 100% erfolgt durch den SUCCESS-State im WebSocket.
    total_steps = question_count + 2

    # Step 0: Emittiert vom Task selbst (nicht vom Callback)
    self.update_progress(0, total_steps, "Starte Fragengenerierung...")

    # Progress-Callback delegiert an bestehende update_progress-Abstraktion.
    # Der `total`-Parameter vom Service (question_count + 2) ist identisch mit
    # `total_steps` und wird daher durch den Closure-Wert ersetzt — so bleibt
    # total_steps als Single Source of Truth im Task.
    def progress_callback(current: int, total: int, message: str) -> None:  # noqa: ARG001
        self.update_progress(current, total_steps, message)

    logger.info(
        f"Starte Fragengenerierung für User {user_id}: "
        f"{question_count} Fragen zum Thema '{rag_request.topic}'"
    )

    rag_service = RAGService()
    result = run_async(
        rag_service.generate_rag_exam(rag_request, progress_callback=progress_callback)
    )

    logger.info(
        f"Fragengenerierung abgeschlossen: {result.exam_id} "
        f"({question_count} Fragen in {result.generation_time:.1f}s)"
    )

    return {
        "exam_id": result.exam_id,
        "topic": result.topic,
        "questions": [dataclasses.asdict(q) for q in result.questions],
        "generation_time": result.generation_time,
        "quality_metrics": result.quality_metrics,
    }
