"""
Celery Task für asynchrone Fragengenerierung mit Progress-Tracking.
Sendet per-Frage Progress-Updates via ProgressTask.update_progress().
Persistiert generierte Fragen automatisch in question_reviews (Status: pending).
"""

import dataclasses
import logging
import time
from typing import Any, Dict, List, Literal, Optional

from celery.exceptions import Ignore, Reject
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from celery_app import celery_app
from models.question_generation_job import QuestionGenerationJob
from tasks.document_tasks import ProgressTask, run_async

logger = logging.getLogger(__name__)


class JobStatusUpdateError(Exception):
    """Raised when _update_job_status fails after exhausting all retry attempts.

    Indicates that QuestionGenerationJob.status could not be persisted to the DB
    despite retries — caller MUST log loudly so phantom PENDING jobs are visible
    to monitoring and the reconciliation watchdog (TF-329).

    Carries structured fields so Sentry / observability tooling can tag and
    aggregate by task_id, target status, and attempt count without parsing the
    formatted message string.
    """

    def __init__(
        self,
        task_id: str,
        status: str,
        attempts: int,
        last_err: Exception,
    ) -> None:
        super().__init__(
            f"Failed to update job status to {status} for task {task_id} "
            f"after {attempts} attempts: {last_err}"
        )
        self.task_id = task_id
        self.status = status
        self.attempts = attempts
        self.last_err = last_err


class JobNotFoundError(Exception):
    """Raised when no QuestionGenerationJob row exists for the given task_id.

    Distinct from JobStatusUpdateError: NOT retriable. Indicates a data-integrity
    issue (row deleted between dispatch and status update, or wrong task_id passed)
    rather than a transient DB failure. Caller MUST log loudly so the silent-
    PENDING failure mode the original `_update_job_status` had cannot reappear
    via this code path.
    """

    def __init__(self, task_id: str, status: str) -> None:
        super().__init__(
            f"No QuestionGenerationJob found for task {task_id} "
            f"(attempted status: {status})"
        )
        self.task_id = task_id
        self.status = status


# Backoffs (seconds) BETWEEN status-update attempts. Total attempts = len + 1 = 4.
# Covers the 5-15 s Postgres restart window observed during the 2026-04-28 incident
# (TF-325): the fourth attempt fires ~17 s after the first failure, comfortably past
# typical Fly.io managed PG restart durations.
_JOB_STATUS_UPDATE_BACKOFFS: tuple[int, ...] = (2, 5, 10)

# Type alias for terminal job states (subset of QuestionGenerationJob.status values
# excluding the implicit initial "PENDING"). Constrains all status-update functions
# to prevent typo-induced phantom states like "SUKZESS" being silently written.
JobTerminalStatus = Literal["SUCCESS", "FAILURE", "REVOKED"]


# Time estimation lookup table (minutes) based on question type and difficulty
TIME_ESTIMATES = {
    ("multiple_choice", "easy"): 1,
    ("multiple_choice", "medium"): 2,
    ("multiple_choice", "hard"): 3,
    ("true_false", "easy"): 1,
    ("true_false", "medium"): 1,
    ("true_false", "hard"): 2,
    ("open_ended", "easy"): 3,
    ("open_ended", "medium"): 5,
    ("open_ended", "hard"): 8,
}

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


def _try_update_job_status(task_id: str, status: str) -> None:
    """Single-attempt status update.

    Opens a fresh SessionLocal so SQLAlchemy's pool_pre_ping (configured globally
    on the engine in database.py) validates the connection at checkout — this
    lets the retry loop recover from a stale pool entry without reusing a session
    whose internal transaction state may be poisoned by a prior exception.
    Raises JobNotFoundError if no matching row exists. Lets DB exceptions bubble;
    the retry loop in _update_job_status decides whether to retry.
    """
    from database import SessionLocal

    session = SessionLocal()
    try:
        job = session.query(QuestionGenerationJob).filter_by(task_id=task_id).first()
        if job is None:
            raise JobNotFoundError(task_id, status)
        job.status = status
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _update_job_status(task_id: str, status: str) -> None:
    """Update QuestionGenerationJob.status to terminal state, with retries.

    Calls `_try_update_job_status` up to `len(_JOB_STATUS_UPDATE_BACKOFFS) + 1`
    times (currently 4 — i.e. 3 retries on top of the initial attempt). Backoffs
    from `_JOB_STATUS_UPDATE_BACKOFFS` are slept BETWEEN attempts; no sleep after
    the final attempt before the raise.

    Retries only `(SQLAlchemyError, OSError)`. `JobNotFoundError` and any
    programmer-error exceptions (TypeError, AttributeError, ...) propagate
    immediately so they fail loudly instead of being silently retried.

    Raises `JobStatusUpdateError` (with structured task_id/status/attempts/cause
    fields) on final failure. The Celery task wraps its calls in
    `_safe_update_job_status` to ensure a status-update failure never overrides
    the actual task outcome.
    """
    attempts = len(_JOB_STATUS_UPDATE_BACKOFFS) + 1
    last_err: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            _try_update_job_status(task_id, status)
            if attempt > 1:
                logger.info(
                    "Recovered job status update for task %s on attempt %d/%d",
                    task_id,
                    attempt,
                    attempts,
                )
            return
        except (SQLAlchemyError, OSError) as err:
            last_err = err
            log = logger.error if attempt == attempts else logger.warning
            log(
                "Job status update attempt %d/%d failed for task %s: %s",
                attempt,
                attempts,
                task_id,
                err,
            )
            if attempt < attempts:
                time.sleep(_JOB_STATUS_UPDATE_BACKOFFS[attempt - 1])
    raise JobStatusUpdateError(task_id, status, attempts, last_err) from last_err


def _safe_update_job_status(task_id: str, status: str) -> bool:
    """Best-effort status update used by Celery task body and the TF-329
    watchdog. Swallows `JobStatusUpdateError` and `JobNotFoundError` after
    logging at CRITICAL so a status-write failure never overrides the actual
    task outcome (e.g., losing a successful generation because the DB write
    failed, or the row vanished).

    Returns:
        True if the row was updated, False on any swallowed failure. Callers
        like the watchdog need this signal to keep their counters honest —
        previously the watchdog incremented ``reconciled`` unconditionally,
        so beat-health metrics looked green during a real DB outage.
    """
    try:
        _update_job_status(task_id, status)
        return True
    except JobStatusUpdateError:
        logger.critical(
            "Could not persist %s status for task %s after retries — "
            "job will appear PENDING until reconciliation",
            status,
            task_id,
            exc_info=True,
        )
        return False
    except JobNotFoundError:
        logger.critical(
            "Cannot update status to %s for task %s: no QuestionGenerationJob row "
            "found (data-integrity issue — possible row deletion or stale task_id)",
            status,
            task_id,
            exc_info=True,
        )
        return False


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
    from models.document import Document
    from models.question_review import (
        QuestionReview,
        QuestionSourceDocument,
        ReviewHistory,
        ReviewStatus,
    )
    from utils.question_options import normalize_options

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
                # TF-330: normalize on write so new rows are canonical
                # List[str]; the read-side validator only exists for legacy
                # data that this branch will never produce again.
                options=normalize_options(question.options),
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
                bloom_level=getattr(question, "bloom_level", None),
                estimated_time_minutes=TIME_ESTIMATES.get(
                    (question.question_type, question.difficulty), 3
                ),
            )
            db.add(question_review)
            reviews.append(question_review)

        db.flush()

        # Build filename→document_id lookup for this institution (best-effort)
        if institution_id is not None:
            all_docs = (
                db.query(Document.id, Document.original_filename)
                .filter(Document.institution_id == institution_id)
                .all()
            )
            filename_to_doc_id = {d.original_filename: d.id for d in all_docs}
        else:
            filename_to_doc_id = {}

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

            # Link to source documents in the normalised join table
            for fname in question_review.source_documents or []:
                doc_id = filename_to_doc_id.get(fname)
                if doc_id:
                    db.merge(
                        QuestionSourceDocument(
                            question_id=question_review.id, document_id=doc_id
                        )
                    )

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
    retry_kwargs={"max_retries": 4},
    retry_backoff=30,
    retry_backoff_max=300,
    retry_jitter=True,
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
        _safe_update_job_status(self.request.id, "FAILURE")
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

        # Persistiere Fragen in question_reviews (Status: pending). Falls die
        # Persistierung scheitert, behandeln wir den Task als FAILURE statt
        # SUCCESS-mit-Warnung: aus User-Sicht ist eine "erfolgreiche"
        # Generierung ohne abrufbare Review-Queue indistinct von einem
        # Pipeline-Fehler. Außerdem würde der Watchdog den Job nicht mehr
        # einsammeln (terminal SUCCESS), so dass die Inkonsistenz dauerhaft
        # bliebe. Re-Raise lässt Celery den Task — wenn noch Retry-Budget da
        # ist — erneut versuchen, andernfalls geht der Task FAILURE durch das
        # generische except weiter unten.
        review_question_ids: List[int] = _persist_questions(
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

        _safe_update_job_status(self.request.id, "SUCCESS")

        # Premium RAGQuestion/RAGContext sind @dataclass — bei Wechsel zu Pydantic .model_dump() verwenden
        return {
            "exam_id": result.exam_id,
            "topic": result.topic,
            "questions": [dataclasses.asdict(q) for q in result.questions],
            "context_summary": dataclasses.asdict(result.context_summary),
            "generation_time": result.generation_time,
            "quality_metrics": result.quality_metrics,
            "review_question_ids": review_question_ids,
        }
    except Ignore:
        raise
    except (Reject, ValidationError, TypeError, ImportError):
        _safe_update_job_status(self.request.id, "FAILURE")
        raise
    except Exception as generation_err:
        logger.error(
            f"Fragengenerierung fehlgeschlagen für User {user_id}: {generation_err}",
            exc_info=True,
        )
        # Only mark as FAILURE on final retry attempt — autoretry_for may still retry
        max_retries = self.retry_kwargs.get("max_retries", 0)
        if self.request.retries >= max_retries:
            _safe_update_job_status(self.request.id, "FAILURE")
        raise
