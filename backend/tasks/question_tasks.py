"""
Celery Task für asynchrone Fragengenerierung mit Progress-Tracking.
Sendet per-Frage Progress-Updates via ProgressTask.update_progress().
Persistiert generierte Fragen automatisch in question_reviews (Status: pending).
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


def _coerce_ln_level(value) -> Optional[int]:
    """LN-Stufe defensiv auf 1–4 begrenzen, sonst None (TF-400).

    Quelle ist Modell-Output (Premium klemmt bereits, aber die Core-Persistenz
    darf sich nicht darauf verlassen — Tier-Grenze). Der DB-CHECK auf
    question_reviews.ln_level ist der Backstop.
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
    Persistiert generierte Fragen in question_reviews mit Status 'pending'.
    Erstellt ReviewHistory-Einträge für den Audit-Trail.

    Args:
        framework_id: Kompetenzrahmen (TF-400). Dessen Kompetenzen werden EINMAL
            als {code: id}-Map vorgeladen, um pro Frage competency_code →
            competency_id aufzulösen (kein N+1). None → keine Auflösung.
        db: Optionale injizierte Session (nur für Tests). Wenn None, öffnet die
            Funktion ihre eigene Session via SessionLocal und schliesst sie im
            finally. Eine injizierte Session wird NICHT geschlossen — ihr
            Lifecycle gehört dem Aufrufer. Produktionsverhalten bleibt
            unverändert (db wird nur in Tests gesetzt).

    Returns:
        Liste der generierten QuestionReview-IDs
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
        # Kompetenz-Code → ID EINMAL vorladen (kein N+1 in der Fragen-Schleife).
        code_to_id: Dict[str, int] = {}
        if framework_id:
            code_to_id = {
                c.code: c.id
                for c in db.query(Competency).filter(
                    Competency.framework_id == framework_id
                )
            }
        reviews = []
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

            # TF-400: Kompetenz-Zuordnung. competency_code gegen die vorgeladene
            # Framework-Map auflösen (getattr hält die Tier-Grenze zur
            # Premium-Datenklasse sauber). Ein nicht-leerer Code ohne Treffer
            # (halluziniert oder abweichendes rendered_text-Heading-Format) wird
            # geloggt — analog source_document_unmatched —, damit ein totaler
            # Tagging-Ausfall nicht still bleibt. ln_level defensiv auf 1–4.
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
                # TF-400: Kompetenz-Zuordnung. competency_code wird gegen die
                # vorgeladene Framework-Map aufgelöst; ein halluzinierter/
                # competency_id/ln_level oben aufgelöst (Warning bei Code-Miss,
                # ln_level auf 1–4 begrenzt).
                competency_id=competency_id,
                ln_level=ln_level,
                estimated_time_minutes=TIME_ESTIMATES.get(
                    (question.question_type, question.difficulty), 3
                ),
                # TF-383: Provenance-Snapshot der verwendeten Vorlage. getattr,
                # damit die Core-Persistenz nicht von einer Premium-Datenklasse
                # abhängt (Tier-Grenze bleibt sauber); None für Frage-Quellen
                # ohne Herkunft.
                generation_metadata=getattr(question, "generation_metadata", None),
            )
            db.add(question_review)
            reviews.append(question_review)

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

        # Build filename→document_id lookup for this institution (best-effort)
        if institution_id is not None:
            all_docs = (
                db.query(Document.id, Document.original_filename)
                .filter(Document.institution_id == institution_id)
                .all()
            )
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
            filename_to_doc_id = {}

        review_ids = []
        unmatched_filenames: set[str] = set()
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
            # RAG returns one entry per chunk, so the same filename can appear
            # multiple times when a document contributes several chunks.
            # dict.fromkeys deduplicates while preserving order.
            for fname in dict.fromkeys(question_review.source_documents or []):
                doc_id = filename_to_doc_id.get(fname)
                if doc_id:
                    db.merge(
                        QuestionSourceDocument(
                            question_id=question_review.id, document_id=doc_id
                        )
                    )
                elif filename_to_doc_id:
                    # Filename present in question metadata but not in the
                    # institution's Document table — most likely filename
                    # normalization drift (e.g. underscores vs. spaces,
                    # case). De-duplicate the warning since the same source
                    # filename usually appears across multiple questions.
                    unmatched_filenames.add(fname)

        if unmatched_filenames:
            logger.warning(
                "persist_questions.source_document_unmatched institution=%s "
                "count=%d sample=%s — TF-321 source filter will miss linked "
                "questions for these filenames; check RAG metadata vs. "
                "Document.original_filename for normalization drift",
                institution_id,
                len(unmatched_filenames),
                sorted(unmatched_filenames)[:5],
            )

        db.commit()
        return review_ids
    except Exception:
        # Nur eine selbst eröffnete Session zurückrollen — eine injizierte
        # Session gehört dem Aufrufer; ein rollback() würde dessen Transaktion
        # überraschend mitreissen. In Produktion gilt owns_session=True, also
        # bleibt das Rollback-Verhalten bei Fehlern unverändert.
        if owns_session:
            db.rollback()
        raise
    finally:
        # Eine injizierte Test-Session gehört dem Aufrufer — nicht schliessen.
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
        ValidationError,  # Ungültige Eingabedaten — Retry ändert nichts
        TypeError,  # Programmierfehler — Retry ändert nichts
        ImportError,  # Deployment-Problem — Retry ändert nichts
        ProgrammingError,  # psycopg2-Adapter-/DDL-Fehler — Retry ändert nichts
        IntegrityError,  # FK-Verletzung (z. B. Tag-ID) — Retry ändert nichts
        ValueError,  # Domänenvalidierung (z. B. Tag-Scope) — Retry ändert nichts
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
    question_count = rag_request.question_count

    # Re-raised "No context available" ValueError from TF-358 is raised later in
    # the service call below; topic is known now, so tag it here.
    sentry_sdk.set_tag("topic", rag_request.topic)
    # Fortschritt in N+2 Schritten:
    #   Step 0:      Task-Start (emittiert vom Task)
    #   Step 1:      Context geladen (emittiert via Callback)
    #   Steps 2..N+1: Fragen 1..N (emittiert via Callback)
    # WICHTIG (TF-358): Der Service koppelt die Fragenanzahl ggf. ans verfügbare
    # Chunk-Material und emittiert dann gegen die EFFEKTIVE Anzahl. Der Callback
    # reicht das `total` des Service deshalb durch, statt es auf die ursprünglich
    # angeforderte Anzahl zu fixieren — sonst bliebe der Balken beim Capping
    # hängen. Der initiale total ist nur eine Schätzung; der SUCCESS-State im
    # WebSocket setzt am Ende ohnehin 100%.
    initial_total_steps = question_count + 2

    # Step 0: Emittiert vom Task selbst (nicht vom Callback)
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
            tag_ids=rag_request.tag_ids or [],
            framework_id=rag_request.framework_id,
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
    except (
        Reject,
        ValidationError,
        TypeError,
        ImportError,
        ProgrammingError,
        IntegrityError,
        ValueError,
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
