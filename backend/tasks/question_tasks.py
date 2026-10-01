"""
Celery task for asynchronous question generation with progress tracking.
Sends per-question progress updates via ProgressTask.update_progress().
Automatically persists generated questions to question_reviews (status: pending).
"""

import contextlib
import dataclasses
import enum
import json
import logging
import time
from typing import TYPE_CHECKING, Any, Dict, List, Literal, NoReturn, Optional

from celery.exceptions import Ignore, Reject
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, ProgrammingError, SQLAlchemyError

from config.observability import set_span_tag

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from celery_app import celery_app
from models.question_generation_job import QuestionGenerationJob
from schemas.task import ProgressCode
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


class JobStatusWrite(enum.Enum):
    """Outcome of ``_safe_update_job_status``.

    KEPT_SUCCESS is not an error: the row already says SUCCESS and is left
    alone (TF-964). The watchdog must not count it as reconciled nor mirror
    a FAILURE into Celery's backend for it.
    """

    WRITTEN = "written"
    KEPT_SUCCESS = "kept_success"
    FAILED = "failed"


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


def _try_update_job_status(task_id: str, status: str) -> bool:
    """Single-attempt status update.

    Opens a fresh SessionLocal so SQLAlchemy's pool_pre_ping (configured globally
    on the engine in database.py) validates the connection at checkout — this
    lets the retry loop recover from a stale pool entry without reusing a session
    whose internal transaction state may be poisoned by a prior exception.
    Raises JobNotFoundError if no matching row exists. Lets DB exceptions bubble;
    the retry loop in _update_job_status decides whether to retry.

    A SUCCESS row is never changed (TF-964): SUCCESS is committed together
    with the questions, so it is the truth about the job. A later FAILURE
    write — the task raising after that commit on its last retry, or the
    watchdog / ``/active-tasks`` mirroring Celery's FAILURE after they
    loaded the row as PENDING and the task committed SUCCESS meanwhile —
    would show a finished job as failed and offer a retry that generates
    it twice.

    Returns True if the status was written, False if a SUCCESS row was
    kept.
    """
    from database import SessionLocal

    session = SessionLocal()
    try:
        # Locked like in _save_generation: a writer that loaded the row as
        # PENDING waits for the task's SUCCESS commit and then sees it.
        job = (
            session.query(QuestionGenerationJob)
            .filter_by(task_id=task_id)
            .with_for_update()
            .first()
        )
        if job is None:
            raise JobNotFoundError(task_id, status)
        if job.status == "SUCCESS" and status != "SUCCESS":
            logger.warning(
                "Not overwriting SUCCESS with %s for task %s — the job's "
                "questions are already saved",
                status,
                task_id,
            )
            return False
        job.status = status
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _update_job_status(task_id: str, status: str) -> bool:
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

    Returns what `_try_update_job_status` returned: False if a SUCCESS row
    was kept.
    """
    attempts = len(_JOB_STATUS_UPDATE_BACKOFFS) + 1
    last_err: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            written = _try_update_job_status(task_id, status)
            if attempt > 1:
                logger.info(
                    "Recovered job status update for task %s on attempt %d/%d",
                    task_id,
                    attempt,
                    attempts,
                )
            return written
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


def _safe_update_job_status(task_id: str, status: str) -> JobStatusWrite:
    """Best-effort status update used by Celery task body and the TF-329
    watchdog. Swallows `JobStatusUpdateError` and `JobNotFoundError` after
    logging at CRITICAL so a status-write failure never overrides the actual
    task outcome (e.g., losing a successful generation because the DB write
    failed, or the row vanished).

    Returns:
        ``WRITTEN`` if the row was updated, ``KEPT_SUCCESS`` if it already
        said SUCCESS and was left alone (TF-964), ``FAILED`` on any swallowed
        failure. Callers like the watchdog need this signal to keep their
        counters honest — previously the watchdog incremented ``reconciled``
        unconditionally, so beat-health metrics looked green during a real
        DB outage.
    """
    try:
        if _update_job_status(task_id, status):
            return JobStatusWrite.WRITTEN
        return JobStatusWrite.KEPT_SUCCESS
    except JobStatusUpdateError:
        logger.critical(
            "Could not persist %s status for task %s after retries — "
            "job will appear PENDING until reconciliation",
            status,
            task_id,
            exc_info=True,
        )
        return JobStatusWrite.FAILED
    except JobNotFoundError:
        logger.critical(
            "Cannot update status to %s for task %s: no QuestionGenerationJob row "
            "found (data-integrity issue — possible row deletion or stale task_id)",
            status,
            task_id,
            exc_info=True,
        )
        return JobStatusWrite.FAILED


# TF-964: the Nth redelivery of a job's message (N = _MAX_REDELIVERIES) is
# rejected without running, i.e. the original run plus at most N-1
# redelivered runs. A redelivery happens whenever the worker is lost
# mid-task (see reject_on_worker_lost on the task): an OOM kill of the
# prefork child or a worker restart during a deploy. RabbitMQ also
# redelivers when the broker connection drops; Celery then cancels the
# original run (TF-1009). Guards against a
# loop where every attempt is killed the same way.
_MAX_REDELIVERIES = 3


class GenerationRejected(RuntimeError):
    """Stored in Celery's result backend when a generation is given up
    without running (TF-964), see ``_reject_generation``."""


def _is_context_limited(quality_metrics: Any) -> bool:
    return (
        isinstance(quality_metrics, dict)
        and quality_metrics.get("context_limited") is True
    )


def _reject_generation(task_id: str, reason: str) -> NoReturn:
    """Drop the message without requeue and mark the Celery result FAILURE.

    Celery's ``Reject`` writes nothing to the result backend
    (``handle_reject`` in celery/app/trace.py only logs). With
    ``task_track_started`` the result would stay STARTED, and the progress
    WebSocket would report a running task forever. Best-effort, like the
    watchdog's mirror: the DB row already carries the outcome.
    """
    try:
        celery_app.backend.mark_as_failure(task_id, GenerationRejected(reason))
    except Exception:
        logger.error(
            "Could not mark rejected task %s as FAILURE in Celery's backend "
            "— the progress view may keep showing it as running",
            task_id,
            exc_info=True,
        )
    raise Reject(reason, requeue=False)


def _check_job_at_start(
    task_id: str, redelivered: bool
) -> tuple[bool, Optional[Dict[str, Any]]]:
    """Idempotency guard, run before anything is generated (TF-964).

    The task can run more than once for the same job: RabbitMQ redelivers
    the message with the same task_id when the worker is lost
    (``task_acks_late`` + ``reject_on_worker_lost``), and an autoretry
    re-runs it after an exception. If the job already committed its
    questions, running again would generate and store a second set and
    charge the quota twice.

    Returns ``(True, result)`` when the job has finished: SUCCESS or
    questions linked to it. ``result`` is rebuilt from the DB; it is None if
    no questions are linked (job finished before TF-964, without questions,
    or its questions were deleted since). Returns ``(False, None)`` when the
    task should generate.

    Rejects the message without requeue (see ``_reject_generation``) when
    the job is already FAILURE or REVOKED: nothing re-runs such a job — a
    retry creates a new job with a new task_id — so this is a stale message,
    e.g. one the watchdog gave up on while it waited in the queue. Running
    it would add a second set next to the user's retry.

    Counts redeliveries on the row. Once ``_MAX_REDELIVERIES`` is reached
    without saved questions, the job goes to FAILURE and the message is
    rejected the same way, so it can't loop.
    """
    from database import SessionLocal
    from services.generation_job_result import build_job_result, linked_question_ids

    db = SessionLocal()
    try:
        job = db.query(QuestionGenerationJob).filter_by(task_id=task_id).first()
        if job is None:
            logger.critical(
                "No QuestionGenerationJob row for task %s at start "
                "(redelivered=%s) — idempotency and redelivery limit are off "
                "for this run",
                task_id,
                redelivered,
            )
            return False, None

        if job.status == "SUCCESS" or linked_question_ids(db, job):
            if job.status != "SUCCESS":
                logger.warning(
                    "Generation job for task %s had status %s despite linked "
                    "questions — repaired to SUCCESS",
                    task_id,
                    job.status,
                )
                job.status = "SUCCESS"
                db.commit()
            logger.info(
                "Generation job for task %s already finished — not generating "
                "again (redelivered=%s), returning the stored result",
                task_id,
                redelivered,
            )
            return True, build_job_result(db, job)

        if job.status in ("FAILURE", "REVOKED"):
            status = job.status
            db.rollback()
            logger.warning(
                "Generation job for task %s is already %s — dropping the "
                "stale message without generating (redelivered=%s)",
                task_id,
                status,
                redelivered,
            )
            _reject_generation(
                task_id, f"Task {task_id} verworfen: Auftrag ist bereits {status}."
            )

        if redelivered:
            job.redelivery_count += 1
            if job.redelivery_count >= _MAX_REDELIVERIES:
                job.status = "FAILURE"
                db.commit()
                logger.error(
                    "Generation job for task %s redelivered %d times without "
                    "saved questions — giving up (FAILURE, no requeue)",
                    task_id,
                    job.redelivery_count,
                )
                _reject_generation(
                    task_id,
                    f"Task {task_id} nach {job.redelivery_count} erneuten "
                    "Zustellungen verworfen.",
                )
            db.commit()
            logger.warning(
                "Generation job for task %s redelivered (%d/%d)",
                task_id,
                job.redelivery_count,
                _MAX_REDELIVERIES,
            )
        return False, None
    except Exception:
        with contextlib.suppress(Exception):
            db.rollback()
        raise
    finally:
        db.close()


def _save_generation(
    task_id: str,
    result: Any,
    rag_request: Any,
    user_id: int,
    institution_id: Optional[int],
) -> Optional[List[int]]:
    """Store the questions and finish the job in ONE commit (TF-964).

    Questions (linked via ``generation_job_id``), ``generated_question_count``,
    ``context_limited`` and ``status = "SUCCESS"`` are written together:
    either all of it is there and ``_check_job_at_start`` stops any re-run,
    or none of it and a re-run is a legitimate first attempt.

    The job row is locked for the save. If it is no longer PENDING — a
    second delivery of the same message ran in parallel and saved first, or
    the job was given up meanwhile — nothing is saved and None is returned;
    the caller asks ``_check_job_at_start`` what the job's outcome is. If
    the row is missing, the questions are committed unlinked (logged
    CRITICAL); idempotency is off for that run.

    Rolls back and re-raises on failure; the task's retry policy applies.
    """
    from database import SessionLocal
    from services.generation_job_result import linked_question_ids

    db = SessionLocal()
    try:
        job = (
            db.query(QuestionGenerationJob)
            .filter_by(task_id=task_id)
            .with_for_update()
            .first()
        )
        if job is not None and (
            job.status != "PENDING" or linked_question_ids(db, job)
        ):
            logger.error(
                "Generation job for task %s is %s at save time — another run "
                "finished or gave it up meanwhile; discarding this run's "
                "questions",
                task_id,
                job.status,
            )
            db.rollback()
            return None
        review_question_ids = _persist_questions(
            questions=result.questions,
            exam_id=result.exam_id,
            topic=rag_request.topic,
            language=rag_request.language,
            user_id=user_id,
            institution_id=institution_id,
            tag_ids=rag_request.tag_ids or [],
            framework_id=rag_request.framework_id,
            db=db,
            generation_job_id=job.id if job is not None else None,
        )
        if job is not None:
            # TF-736: the outcome survives the Celery result's expiry.
            job.generated_question_count = len(result.questions)
            job.context_limited = _is_context_limited(result.quality_metrics)
            job.status = "SUCCESS"
        else:
            logger.critical(
                "No QuestionGenerationJob row for task %s — questions are "
                "saved without a job link (data-integrity issue — possible "
                "row deletion or stale task_id)",
                task_id,
            )
        db.commit()
        return review_question_ids
    except Exception:
        # A broken connection can fail the rollback too; the original error
        # is the one that matters.
        with contextlib.suppress(Exception):
            db.rollback()
        raise
    finally:
        db.close()


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
    generation_job_id: Optional[int] = None,
) -> List[int]:
    """
    Persists generated questions to question_reviews with status 'pending'.
    Creates ReviewHistory entries for the audit trail.

    Args:
        framework_id: Competency framework (TF-400). Its competencies are
            preloaded ONCE as a {code: id} map to resolve competency_code →
            competency_id per question (no N+1). None → no resolution.
        db: Optional injected session. If None, the function opens its own
            session via SessionLocal, commits and closes it. An injected
            session belongs to the caller: the rows are only flushed, the
            caller commits them (TF-964: generate_questions_task commits the
            questions together with the job's SUCCESS), and the session is
            neither rolled back nor closed here.
        generation_job_id: The QuestionGenerationJob that creates these
            questions (TF-964). Linking them is what lets a redelivered or
            retried task see that its job already produced its questions.

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
                generation_job_id=generation_job_id,
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

        if owns_session:
            db.commit()
        else:
            db.flush()
        return review_ids
    except Exception:
        # Only roll back a session we opened ourselves. An injected session
        # belongs to the caller (e.g. _save_generation, which rolls back the
        # questions together with the job update).
        if owns_session:
            db.rollback()
        raise
    finally:
        # An injected session belongs to the caller — do not close it.
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
    # TF-964: with task_acks_late=True (celery_app.py) alone, a task whose
    # worker process dies (OOM kill of the prefork child) is acknowledged
    # and marked FAILURE, and the user's retry generates a second set of
    # questions. With this flag the message is requeued instead, and
    # _check_job_at_start decides on redelivery: return the saved result,
    # generate (nothing was saved), or give up after _MAX_REDELIVERIES.
    reject_on_worker_lost=True,
)
def generate_questions_task(
    self,
    request_data: Dict[str, Any],
    user_id: str,
    institution_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Asynchronous question generation with per-question progress updates.

    Args:
        request_data: Serialized RAGExamRequest as dict (via model_dump(mode='json'))
        user_id: ID of the user (for logging and persistence)
        institution_id: Institution ID for multi-tenancy (optional)

    Returns:
        Dict with exam_id, topic, questions, generation_time, quality_metrics, review_question_ids,
        or None if the job had already finished and no questions are linked to
        rebuild its result from (TF-964, see _check_job_at_start).
    """
    # TF-359/TF-865: tag the current OTel span so a generation failure carries
    # the task context the on-call needs to triage. Celery instrumentation
    # attaches the task id automatically, but not arbitrary task kwargs like
    # user_id/topic -- those need tagging explicitly, same reasoning as the
    # retired sentry_sdk setup (which additionally kept them off the event
    # body via send_default_pii=False; OTel span attributes have no such
    # blanket body-capture to opt out of in the first place). No-op when
    # observability is disabled. user_id is set first so even an early Reject
    # (Premium RAGService missing) or a ValidationError on request_data
    # carries it; topic follows once parsed.
    set_span_tag("user_id", str(user_id))

    if RAGService is None:
        _safe_update_job_status(self.request.id, "FAILURE")
        raise Reject(
            "Premium RAGService nicht verfügbar (Core-Deployment). Task wird nicht wiederholt.",
            requeue=False,
        )

    # TF-964: a redelivery or an autoretry after the commit below must not
    # generate a second set of questions.
    redelivered = bool((self.request.delivery_info or {}).get("redelivered"))
    finished, stored_result = _check_job_at_start(self.request.id, redelivered)
    if finished:
        return stored_result

    from services.rag_service import RAGExamRequest

    rag_request = RAGExamRequest(**request_data)
    # TF-410: thread tenant context so institution-specific default templates win
    # over the system default (own institution → system precedence).
    if institution_id is not None:
        rag_request.institution_id = institution_id
    question_count = rag_request.question_count

    # Re-raised "No context available" ValueError from TF-358 is raised later in
    # the service call below; topic is known now, so tag it here.
    set_span_tag("topic", rag_request.topic)
    # Progress in N+2 steps, N = the service's EFFECTIVE count:
    #   Step 0:      task start (emitted by the task)
    #   Step 1:      context loaded (emitted via callback)
    #   Steps 2..N+1: questions 1..N (emitted via callback)
    # The service may cap the question count to the available chunk material
    # (TF-358); N is only known once the context is loaded. Step 0 therefore
    # carries no count at all (0 of 1 = 0 %) instead of guessing with the
    # requested count — that guess made the bar and the "question i of N"
    # text disagree whenever capping occurred (TF-736, cause 3). From step 1
    # on, every update reports against the same N.
    # Updates carry a code plus parameters instead of a German text; the
    # frontend renders them in the user's language (TF-736).
    self.update_progress(0, 1, code=ProgressCode.GENERATION_STARTED.value)

    def progress_callback(
        current: int, total: int, code: str, params: Dict[str, Any]
    ) -> None:
        self.update_progress(current, total, code=code, params=params)

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

        # Persist questions to question_reviews (status: pending) and mark
        # the job SUCCESS in one commit (TF-964, see _save_generation). If
        # that fails, we treat the task as FAILURE instead of
        # SUCCESS-with-warning: from the user's perspective, a "successful"
        # generation with no retrievable review queue is indistinguishable
        # from a pipeline failure. Re-raising lets Celery retry the task — if
        # retry budget remains — otherwise the task goes FAILURE through the
        # generic except below.
        review_question_ids = _save_generation(
            self.request.id,
            result,
            rag_request,
            user_id=int(user_id),
            institution_id=institution_id,
        )
        if review_question_ids is None:
            # TF-964: another delivery of this message saved first, or the
            # job was given up meanwhile. Report that outcome instead of
            # this run's (discarded) questions; a given-up job rejects here.
            _, stored_result = _check_job_at_start(self.request.id, False)
            return stored_result
        logger.info(
            f"Fragen persistiert: {len(review_question_ids)} Reviews für Exam {result.exam_id}"
        )

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
