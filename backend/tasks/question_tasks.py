"""
Celery task for asynchronous question generation with progress tracking.
Sends per-question progress updates via ProgressTask.update_progress().
Automatically persists generated questions to question_reviews (status: pending).
"""

import dataclasses
import json
import logging
import time
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

import sentry_sdk
from celery.exceptions import Ignore, Reject
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, ProgrammingError, SQLAlchemyError

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from celery_app import celery_app
from models.question_generation_job import QuestionGenerationJob
from services.claude_service import ModelUnavailableError
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
    ("single_choice", "easy"): 1,
    ("single_choice", "medium"): 2,
    ("single_choice", "hard"): 3,
    ("true_false", "easy"): 1,
    ("true_false", "medium"): 1,
    ("true_false", "hard"): 2,
    ("open_ended", "easy"): 3,
    ("open_ended", "medium"): 5,
    ("open_ended", "hard"): 8,
}

# Premium package is available in the worker under /app/premium.
# In local tests, RAGService is mocked via patch("tasks.question_tasks.RAGService").
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


def _coerce_ln_level(value) -> Optional[int]:
    """Defensively clamp the LN level to 1-4, else None (TF-400).

    Source is model output (Premium already clamps, but Core persistence
    can't rely on that — tier boundary). The DB CHECK on
    question_reviews.ln_level is the backstop.
    """
    try:
        level = int(value)
    except (TypeError, ValueError):
        return None
    return level if 1 <= level <= 4 else None


def _persist_questions(
    questions: list,
    exam_id: str,
    topic: str,
    language: str,
    user_id: int,
    institution_id: Optional[int],
    tag_ids: Optional[List[int]] = None,
    framework_id: Optional[int] = None,
    db: Optional["Session"] = None,
) -> List[int]:
    """
    Persists generated questions to question_reviews with status 'pending'.
    Creates ReviewHistory entries for the audit trail.

    Args:
        framework_id: Competency framework (TF-400). Its competencies are
            preloaded ONCE as a {code: id} map to resolve competency_code →
            competency_id per question (no N+1). None → no resolution.
        db: Optional injected session (for tests only). If None, the function
            opens its own session via SessionLocal and closes it in the
            finally block. An injected session is NOT closed — its lifecycle
            belongs to the caller. Production behavior remains unchanged
            (db is only set in tests).

    Returns:
        List of generated QuestionReview IDs
    """
    from database import SessionLocal
    from models.competency import Competency
    from models.document import Document
    from models.question_review import (
        QuestionReview,
        QuestionSourceDocument,
        ReviewHistory,
        ReviewStatus,
    )
    from utils.question_options import normalize_options

    owns_session = db is None
    if owns_session:
        db = SessionLocal()
    try:
        # Preload competency code → id ONCE (no N+1 in the question loop).
        code_to_id: Dict[str, int] = {}
        if framework_id:
            code_to_id = {
                c.code: c.id
                for c in db.query(Competency).filter(
                    Competency.framework_id == framework_id
                )
            }
        reviews = []
        # TF-605: paired alongside `reviews` so the source-document linking
        # loop below can read `question.source_document_ids` (if the caller
        # supplies it) without depending on a Premium dataclass at the Core
        # tier — duck-typed via getattr, same pattern as generation_metadata.
        question_pairs: list[tuple[Any, Any]] = []
        for question in questions:
            # explanation can be str, list, or dict — Premium RAG open_ended rubrics
            # may return a dict. Serialize consistently so the TEXT column always
            # receives a string; psycopg2 cannot adapt a bare dict.
            explanation_raw = question.explanation
            if isinstance(explanation_raw, str):
                explanation_text = explanation_raw
            elif isinstance(explanation_raw, list):
                explanation_text = "; ".join(str(item) for item in explanation_raw)
            elif isinstance(explanation_raw, dict):
                explanation_text = json.dumps(explanation_raw, ensure_ascii=False)
            elif explanation_raw is not None:
                # Unexpected type — fall back to str() but warn so a new
                # Premium return shape doesn't land silently as "<obj at 0x..>".
                logger.warning(
                    "question.explanation.unexpected_type type=%s",
                    type(explanation_raw).__name__,
                )
                explanation_text = str(explanation_raw)
            else:
                explanation_text = None

            # TF-330: normalize on write so new rows are canonical List[str];
            # the read-side validator exists only for legacy rows that this
            # branch will never produce again. Multiple-choice questions
            # MUST persist a usable list — fail-loud if normalization could
            # not recover one, otherwise the question lands in the review
            # queue with no answer choices and reviewers can't tell whether
            # it's corrupt or just rendered wrong.
            normalized_options = normalize_options(question.options)
            if (
                question.question_type == "single_choice"
                and question.options is not None
                and normalized_options is None
            ):
                raise ValueError(
                    f"Refusing to persist single_choice question with "
                    f"unrecoverable options shape "
                    f"(type={type(question.options).__name__}); "
                    f"see question_options.unsafe_dict_keys / "
                    f"question_options.unsupported_type log entry above."
                )
            # correct_answer can be str, dict, or list — Premium RAG open_ended
            # rubrics return a dict. Serialize to JSON so the TEXT column receives
            # a string; psycopg2 cannot adapt a bare dict.
            correct_answer_raw = question.correct_answer
            if isinstance(correct_answer_raw, dict):
                correct_answer_text = json.dumps(correct_answer_raw, ensure_ascii=False)
            elif isinstance(correct_answer_raw, list):
                correct_answer_text = "; ".join(
                    str(item) for item in correct_answer_raw
                )
            elif correct_answer_raw is not None:
                # Unexpected type — fall back to str() but warn so a new
                # Premium return shape doesn't land silently as "<obj at 0x..>".
                logger.warning(
                    "question.correct_answer.unexpected_type type=%s",
                    type(correct_answer_raw).__name__,
                )
                correct_answer_text = str(correct_answer_raw)
            else:
                correct_answer_text = None

            # TF-400: competency assignment. Resolve competency_code against
            # the preloaded framework map (getattr keeps the tier boundary to
            # the Premium data class clean). A non-empty code with no match
            # (hallucinated or a differing rendered_text heading format) is
            # logged — analogous to source_document_unmatched — so a total
            # tagging failure doesn't stay silent. ln_level clamped to 1-4.
            raw_competency_code = getattr(question, "competency_code", None)
            competency_id = (
                code_to_id.get(raw_competency_code) if raw_competency_code else None
            )
            if raw_competency_code and competency_id is None:
                logger.warning(
                    "persist_questions.competency_code_unmatched "
                    "framework_id=%s code=%r — Modell lieferte einen "
                    "competency_code ohne Treffer in der Framework-Map; "
                    "competency_id bleibt NULL (rendered_text-Heading-Format vs. "
                    "competency_parser prüfen oder halluzinierter Code)",
                    framework_id,
                    raw_competency_code,
                )
            ln_level = _coerce_ln_level(getattr(question, "ln_level", None))

            question_review = QuestionReview(
                question_text=question.question_text,
                question_type=question.question_type,
                options=normalized_options,
                correct_answer=correct_answer_text,
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
                # TF-400: competency assignment. competency_code is resolved
                # against the preloaded framework map;
                # competency_id/ln_level resolved above (warning on code miss,
                # ln_level clamped to 1-4).
                competency_id=competency_id,
                ln_level=ln_level,
                estimated_time_minutes=TIME_ESTIMATES.get(
                    (question.question_type, question.difficulty), 3
                ),
                # TF-383: provenance snapshot of the template used. getattr so
                # Core persistence doesn't depend on a Premium data class
                # (keeps the tier boundary clean); None for question sources
                # without provenance.
                generation_metadata=getattr(question, "generation_metadata", None),
            )
            db.add(question_review)
            reviews.append(question_review)
            question_pairs.append((question, question_review))

        db.flush()

        if tag_ids:
            from models.tag import QuestionTag, Tag

            # Defense in depth: API endpoint validates tag_ids, but the task may
            # also be triggered via replayed jobs or future callers. Re-validate
            # against the persisting user's institution scope so a malformed
            # payload becomes a clean FAILURE instead of an IntegrityError that
            # the autoretry loop burns Claude credits on.
            visible = (
                db.query(Tag.id)
                .filter(
                    Tag.id.in_(tag_ids),
                    Tag.is_archived.is_(False),
                    (Tag.institution_id == institution_id) | (Tag.scope == "global"),
                )
                .all()
            )
            visible_ids = {row[0] for row in visible}
            invalid_ids = set(tag_ids) - visible_ids
            if invalid_ids:
                raise ValueError(
                    f"Ungültige oder unsichtbare Tag-IDs für die Generierung: {sorted(invalid_ids)}"
                )

            for review in reviews:
                for tag_id in tag_ids:
                    db.add(QuestionTag(question_id=review.id, tag_id=tag_id))

        # Build lookups for this institution's documents (best-effort).
        # TF-605: `question_review.source_documents` now carries the resolved
        # *display title* (Document.title), not the raw upload filename — a
        # deliberate change for the review UI's provenance display. That
        # means it can no longer double as a join key against
        # Document.original_filename (titles are free-text and not even
        # guaranteed unique). Linking therefore prefers `doc_ids` sourced
        # straight from `question.source_document_ids` (the primary keys
        # the RAG retrieval actually resolved) below; `filename_to_doc_id`
        # remains only as a fallback for callers that don't supply ids
        # (older replayed jobs, tests, non-Premium question sources).
        if institution_id is not None:
            all_docs = (
                db.query(Document.id, Document.original_filename)
                .filter(Document.institution_id == institution_id)
                .all()
            )
            valid_doc_ids = {d.id for d in all_docs}
            filename_to_doc_id = {d.original_filename: d.id for d in all_docs}
        else:
            # No institution_id → no QuestionSourceDocument rows can be
            # created, so the TF-321 source-document filter UI will return
            # empty pools for these questions. Surface so the gap is visible
            # in logs rather than appearing as a frontend bug.
            logger.info(
                "persist_questions.no_institution: skipping source-document "
                "linking for %d questions; TF-321 filter will not see them",
                len(reviews),
            )
            valid_doc_ids = set()
            filename_to_doc_id = {}

        review_ids = []
        unmatched_ids: set[int] = set()
        unmatched_filenames: set[str] = set()
        for question, question_review in question_pairs:
            history = ReviewHistory(
                question_id=question_review.id,
                action="created",
                new_status=ReviewStatus.PENDING.value,
                changed_by=str(user_id),
                change_reason="Auto-generated via RAG exam generation",
            )
            db.add(history)
            review_ids.append(question_review.id)

            # Link to source documents in the normalised join table.
            # `dict.fromkeys` deduplicates while preserving order (RAG
            # returns one entry per chunk, so the same document can appear
            # multiple times when it contributes several chunks).
            doc_ids = getattr(question, "source_document_ids", None) or []
            if doc_ids:
                for doc_id in dict.fromkeys(doc_ids):
                    if doc_id in valid_doc_ids:
                        db.merge(
                            QuestionSourceDocument(
                                question_id=question_review.id,
                                document_id=doc_id,
                            )
                        )
                    elif valid_doc_ids:
                        # Id present in question metadata but not in the
                        # institution's Document table — e.g. the document
                        # was deleted between retrieval and persistence.
                        unmatched_ids.add(doc_id)
            else:
                # No ids supplied — fall back to matching source_documents
                # (title or filename, depending on the caller) against
                # Document.original_filename. Kept for callers that predate
                # source_document_ids; expect most of these to miss now
                # that source_documents holds titles (see comment above).
                for name in dict.fromkeys(question_review.source_documents or []):
                    doc_id = filename_to_doc_id.get(name)
                    if doc_id:
                        db.merge(
                            QuestionSourceDocument(
                                question_id=question_review.id, document_id=doc_id
                            )
                        )
                    elif filename_to_doc_id:
                        unmatched_filenames.add(name)

        if unmatched_ids:
            logger.warning(
                "persist_questions.source_document_id_unmatched institution=%s "
                "count=%d sample=%s — document_id from RAG retrieval not found "
                "in this institution's Document table (deleted between "
                "retrieval and persistence?)",
                institution_id,
                len(unmatched_ids),
                sorted(unmatched_ids)[:5],
            )
        if unmatched_filenames:
            logger.warning(
                "persist_questions.source_document_unmatched institution=%s "
                "count=%d sample=%s — TF-321 source filter will miss linked "
                "questions for these names; check RAG metadata vs. "
                "Document.original_filename for normalization drift",
                institution_id,
                len(unmatched_filenames),
                sorted(unmatched_filenames)[:5],
            )

        db.commit()
        return review_ids
    except Exception:
        # Only roll back a session we opened ourselves — an injected session
        # belongs to the caller; a rollback() would unexpectedly drag its
        # transaction along. In production owns_session=True always holds, so
        # rollback behavior on errors stays unchanged.
        if owns_session:
            db.rollback()
        raise
    finally:
        # An injected test session belongs to the caller — do not close it.
        if owns_session:
            db.close()


@celery_app.task(
    bind=True,
    base=ProgressTask,
    name="tasks.question_tasks.generate_questions",
    autoretry_for=(Exception,),
    dont_autoretry_for=(
        Ignore,
        Reject,
        ValidationError,  # Invalid input data — retry won't help
        TypeError,  # Programming error — retry won't help
        ImportError,  # Deployment issue — retry won't help
        ProgrammingError,  # psycopg2 adapter/DDL error — retry won't help
        IntegrityError,  # FK violation (e.g. tag ID) — retry won't help
        ValueError,  # Domain validation (e.g. tag scope) — retry won't help
        ModelUnavailableError,  # TF-438: entire model chain 404 — permanent
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
    Asynchronous question generation with per-question progress updates.

    Args:
        request_data: Serialized RAGExamRequest as dict (via model_dump(mode='json'))
        user_id: ID of the user (for logging and persistence)
        institution_id: Institution ID for multi-tenancy (optional)

    Returns:
        Dict with exam_id, topic, questions, generation_time, quality_metrics, review_question_ids
    """
    # TF-359: tag the Sentry scope so a generation failure lands in Sentry with
    # the task context the on-call needs to triage. CeleryIntegration already
    # attaches the task id; user_id/topic do not (send_default_pii=False keeps
    # task kwargs off the event). No-op when Sentry is disabled. user_id is set
    # first so even an early Reject (Premium RAGService missing) or a
    # ValidationError on request_data carries it; topic follows once parsed.
    sentry_sdk.set_tag("user_id", str(user_id))

    if RAGService is None:
        _safe_update_job_status(self.request.id, "FAILURE")
        raise Reject(
            "Premium RAGService nicht verfügbar (Core-Deployment). Task wird nicht wiederholt.",
            requeue=False,
        )

    from services.rag_service import RAGExamRequest

    rag_request = RAGExamRequest(**request_data)
    # TF-410: thread tenant context so institution-specific default templates win
    # over the system default (own institution → system precedence).
    if institution_id is not None:
        rag_request.institution_id = institution_id
    question_count = rag_request.question_count

    # Re-raised "No context available" ValueError from TF-358 is raised later in
    # the service call below; topic is known now, so tag it here.
    sentry_sdk.set_tag("topic", rag_request.topic)
    # Progress in N+2 steps:
    #   Step 0:      task start (emitted by the task)
    #   Step 1:      context loaded (emitted via callback)
    #   Steps 2..N+1: questions 1..N (emitted via callback)
    # IMPORTANT (TF-358): the service may cap the question count to the
    # available chunk material and then emits against the EFFECTIVE count.
    # The callback therefore passes through the service's `total` instead of
    # pinning it to the originally requested count — otherwise the bar would
    # get stuck when capping occurs. The initial total is only an estimate;
    # the SUCCESS state in the WebSocket sets 100% at the end regardless.
    initial_total_steps = question_count + 2

    # Step 0: emitted by the task itself (not by the callback)
    self.update_progress(0, initial_total_steps, "Starte Fragengenerierung...")

    def progress_callback(current: int, total: int, message: str) -> None:
        self.update_progress(current, total, message)

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

        # Persist questions to question_reviews (status: pending). If
        # persistence fails, we treat the task as FAILURE instead of
        # SUCCESS-with-warning: from the user's perspective, a "successful"
        # generation with no retrievable review queue is indistinguishable
        # from a pipeline failure. Also, the watchdog would no longer pick up
        # the job (terminal SUCCESS), so the inconsistency would persist.
        # Re-raising lets Celery retry the task — if retry budget remains —
        # otherwise the task goes FAILURE through the generic except below.
        review_question_ids: List[int] = _persist_questions(
            questions=result.questions,
            exam_id=result.exam_id,
            topic=rag_request.topic,
            language=rag_request.language,
            user_id=int(user_id),
            institution_id=institution_id,
            tag_ids=rag_request.tag_ids or [],
            framework_id=rag_request.framework_id,
        )
        logger.info(
            f"Fragen persistiert: {len(review_question_ids)} Reviews für Exam {result.exam_id}"
        )

        _safe_update_job_status(self.request.id, "SUCCESS")

        # Premium RAGQuestion/RAGContext are @dataclass — use .model_dump() if switching to Pydantic
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
    except (
        Reject,
        ValidationError,
        TypeError,
        ImportError,
        ProgrammingError,
        IntegrityError,
        ValueError,
        ModelUnavailableError,  # TF-438: fail fast, no endless retry like TF-437
    ):
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
