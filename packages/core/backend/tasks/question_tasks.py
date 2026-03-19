"""
Celery Task für asynchrone Fragengenerierung mit Progress-Tracking.
Sendet per-Frage Progress-Updates via ProgressTask.update_progress().
Persistiert generierte Fragen automatisch in question_reviews (Status: pending).
"""

import dataclasses
import logging
from typing import Any, Dict, List, Optional

from celery.exceptions import Ignore, Reject
from pydantic import ValidationError

from celery_app import celery_app
from models.question_generation_job import QuestionGenerationJob
from tasks.document_tasks import ProgressTask, run_async

logger = logging.getLogger(__name__)

# Premium-Package ist im Worker unter /app/premium verfügbar.
# In lokalen Tests wird RAGService via patch("tasks.question_tasks.RAGService") gemockt.
try:
    from premium.services.rag_service import RAGService
except ImportError as _import_err:
    logger.warning(
        f"Premium RAGService konnte nicht importiert werden: {_import_err}. "
        "Fragengenerierung ist in diesem Worker nicht verfügbar."
    )
    RAGService = None  # type: ignore[assignment,misc]


def _update_job_status(task_id: str, status: str) -> None:
    """Update QuestionGenerationJob.status to terminal state."""
    from database import SessionLocal

    session = SessionLocal()
    try:
        job = session.query(QuestionGenerationJob).filter_by(task_id=task_id).first()
        if job:
            job.status = status
            session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to update job status for {task_id}: {e}")
    finally:
        session.close()


def _persist_questions(
    questions: list,
    exam_id: str,
    topic: str,
    language: str,
    user_id: int,
    institution_id: Optional[int],
) -> List[int]:
    """
    Persistiert generierte Fragen in question_reviews mit Status 'pending'.
    Erstellt ReviewHistory-Einträge für den Audit-Trail.

    Returns:
        Liste der generierten QuestionReview-IDs
    """
    from database import SessionLocal
    from models.question_review import QuestionReview, ReviewHistory, ReviewStatus

    db = SessionLocal()
    try:
        reviews = []
        for question in questions:
            # explanation can be str or list — Premium RAG may return a list of grading criteria
            explanation_raw = question.explanation
            if isinstance(explanation_raw, str):
                explanation_text = explanation_raw
            elif isinstance(explanation_raw, list):
                explanation_text = "; ".join(str(item) for item in explanation_raw)
            elif explanation_raw is not None:
                explanation_text = str(explanation_raw)
            else:
                explanation_text = None

            question_review = QuestionReview(
                question_text=question.question_text,
                question_type=question.question_type,
                options=question.options,
                correct_answer=question.correct_answer,
                explanation=explanation_text,
                difficulty=question.difficulty,
                topic=topic,
                language=language,
                source_chunks=question.source_chunks,
                source_documents=question.source_documents,
                confidence_score=question.confidence_score,
                review_status=ReviewStatus.PENDING.value,
                exam_id=exam_id,
                created_by=user_id,
                institution_id=institution_id,
            )
            db.add(question_review)
            reviews.append(question_review)

        db.flush()

        review_ids = []
        for question_review in reviews:
            history = ReviewHistory(
                question_id=question_review.id,
                action="created",
                new_status=ReviewStatus.PENDING.value,
                changed_by=str(user_id),
                change_reason="Auto-generated via RAG exam generation",
            )
            db.add(history)
            review_ids.append(question_review.id)

        db.commit()
        return review_ids
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(
    bind=True,
    base=ProgressTask,
    name="tasks.question_tasks.generate_questions",
    autoretry_for=(Exception,),
    dont_autoretry_for=(
        Ignore,
        Reject,
        ValidationError,  # Ungültige Eingabedaten — Retry ändert nichts
        TypeError,  # Programmierfehler — Retry ändert nichts
        ImportError,  # Deployment-Problem — Retry ändert nichts
    ),
    retry_kwargs={"max_retries": 2, "countdown": 30},
)
def generate_questions_task(
    self,
    request_data: Dict[str, Any],
    user_id: str,
    institution_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Asynchrone Fragengenerierung mit per-Frage Progress-Updates.

    Args:
        request_data: Serialisierter RAGExamRequest als dict (via model_dump(mode='json'))
        user_id: ID des Users (für Logging und Persistierung)
        institution_id: Institution-ID für Multi-Tenancy (optional)

    Returns:
        Dict mit exam_id, topic, questions, generation_time, quality_metrics, review_question_ids
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

    try:
        rag_service = RAGService()
        result = run_async(
            rag_service.generate_rag_exam(
                rag_request, progress_callback=progress_callback
            )
        )

        logger.info(
            f"Fragengenerierung abgeschlossen: {result.exam_id} "
            f"({question_count} Fragen in {result.generation_time:.1f}s)"
        )

        # Persistiere Fragen in question_reviews (Status: pending)
        review_question_ids: List[int] = []
        persistence_warning = None
        try:
            review_question_ids = _persist_questions(
                questions=result.questions,
                exam_id=result.exam_id,
                topic=rag_request.topic,
                language=rag_request.language,
                user_id=int(user_id),
                institution_id=institution_id,
            )
            logger.info(
                f"Fragen persistiert: {len(review_question_ids)} Reviews für Exam {result.exam_id}"
            )
        except Exception as persist_err:
            logger.error(
                f"Persistierung fehlgeschlagen für Exam '{result.exam_id}': {persist_err}",
                exc_info=True,
            )
            persistence_warning = (
                "Questions were generated but could not be saved to the review workflow. "
                "Please try again."
            )

        _update_job_status(self.request.id, "SUCCESS")

        # Premium RAGQuestion/RAGContext sind @dataclass — bei Wechsel zu Pydantic .model_dump() verwenden
        return {
            "exam_id": result.exam_id,
            "topic": result.topic,
            "questions": [dataclasses.asdict(q) for q in result.questions],
            "context_summary": dataclasses.asdict(result.context_summary),
            "generation_time": result.generation_time,
            "quality_metrics": result.quality_metrics,
            "review_question_ids": review_question_ids,
            "persistence_warning": persistence_warning,
        }
    except (Ignore, Reject, ValidationError, TypeError, ImportError):
        raise
    except Exception as generation_err:
        logger.error(
            f"Fragengenerierung fehlgeschlagen für User {user_id}: {generation_err}",
            exc_info=True,
        )
        _update_job_status(self.request.id, "FAILURE")
        raise
