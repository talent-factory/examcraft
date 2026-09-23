"""Submissions API — results import + lists + detail.

Endpoints:

* ``POST /api/v1/submissions/import/preview`` — parse CSV, no persistence
* ``POST /api/v1/submissions/import/commit`` — full pipeline
* ``GET /api/v1/submissions/import-jobs/{id}`` — polling
* ``GET /api/v1/submissions/?exam_id=X`` — list per exam
* ``GET /api/v1/submissions/{id}`` — detail with attempts + answers + grades

Multi-tenancy: every endpoint filters by ``current_user.institution_id``.
RBAC: ``submissions:read`` / ``submissions:import``.

Note: this module deliberately omits ``from __future__ import annotations``.
Pydantic v2 + FastAPI need real types at runtime to build the OpenAPI
schema and parse multipart form bodies (``UploadFile``, ``File()``,
``Form()``). With stringified annotations Pydantic raises
``PydanticUserError: not fully defined`` while wiring the routes. Sister
modules (``services/import_service.py`` etc.) keep ``__future__`` because
they hold no FastAPI route defs.
"""

import base64
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, joinedload

from database import get_db
from errors import AppHTTPException, api_error
from services.translation_service import t as translate
from enums import (
    AttemptSource,
    DriverName,
    GradeStatus,
    ImportJobStatus,
    ScoringStrategy,
    SubmissionGradeStatus,
)
from models.auth import User
from models.exam import Exam
from models.student import Student
from models.submission import Attempt, AttemptAnswer, ImportJob, Submission
from services.auswertung_quotas import (
    assert_driver_allowed,
    assert_exam_quota_for_import,
    assert_submission_quota_for_exam,
)
from services.audit_service import AuditService
from services.import_drivers import ImportDriverError
from services.import_service import ImportService, ImportValidationError
from services.results_deletion_service import (
    DeletionSummary,
    ResultsDeletionService,
)
from services.translation_service import get_request_locale
from tasks.import_submissions_task import Base64Str, import_submissions
from utils.auth_utils import require_permission


logger = logging.getLogger(__name__)


# Maximum upload size for CSVs. 25 MB easily covers a year of exams for
# a large institution and keeps a single request from OOMing the worker.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


router = APIRouter(prefix="/api/v1/submissions", tags=["Submissions"])


# ---------------------------------------------------------------------------
# Pydantic-Output-Schemas
# ---------------------------------------------------------------------------


_STRICT_OUT = ConfigDict(extra="forbid")


class ImportRowErrorOut(BaseModel):
    model_config = _STRICT_OUT

    row_index: int
    reason: str
    step: str | None = None
    details: dict[str, Any] | None = None


class ImportPayloadStudentOut(BaseModel):
    model_config = _STRICT_OUT

    external_id: str
    display_name: str | None = None


class ImportPayloadAttemptOut(BaseModel):
    model_config = _STRICT_OUT

    student_external_id: str
    attempt_number: int
    started_at: datetime | None = None
    submitted_at: datetime | None = None
    answer_count: int


class ImportPreviewOut(BaseModel):
    model_config = _STRICT_OUT

    exam_id: int
    driver_name: DriverName
    student_count: int
    attempt_count: int
    students: list[ImportPayloadStudentOut]
    attempts: list[ImportPayloadAttemptOut]
    warnings: list[str] = Field(default_factory=list)
    errors: list[ImportRowErrorOut] = Field(default_factory=list)
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    truncated: bool = False


class ImportJobOut(BaseModel):
    model_config = _STRICT_OUT

    id: int
    exam_id: int
    driver_name: DriverName
    status: ImportJobStatus
    rows_processed: int
    rows_failed: int
    # TF-428: live grading progress; ``graded_total`` is None until grading
    # starts, ``graded_done`` counts processed submissions (graded or failed)
    # so far.
    graded_total: int | None = None
    graded_done: int = 0
    error_log: list[ImportRowErrorOut] | None = None
    source_metadata: dict[str, Any] | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ImportJobListOut(BaseModel):
    """Recent import jobs for one exam — drives the Auswertungen status surface
    so the UI can show running/finished imports without pinning a modal open
    (TF-428)."""

    model_config = _STRICT_OUT

    items: list[ImportJobOut]
    total: int


class ImportSourceCountOut(BaseModel):
    model_config = _STRICT_OUT

    source: AttemptSource
    attempt_count: int


class ImportDeletionSummaryOut(BaseModel):
    """How much a result-import delete would remove (TF-421).

    Used both as the preview (``GET /import/summary``) for the confirmation
    dialog and as the result of the delete (``DELETE /import``).
    """

    model_config = _STRICT_OUT

    exam_id: int
    submission_count: int
    attempt_count: int
    student_count: int
    by_source: list[ImportSourceCountOut] = Field(default_factory=list)


class GradeOut(BaseModel):
    model_config = _STRICT_OUT

    id: int
    points_awarded: float
    points_max: float
    status: GradeStatus
    is_correct: bool | None
    llm_confidence: float | None = None
    llm_rationale: str | None = None
    llm_matched_aspects: list[str] | None = None
    llm_missing_aspects: list[str] | None = None
    reviewer_id: int | None = None
    reviewer_note: str | None = None


class AttemptAnswerOut(BaseModel):
    model_config = _STRICT_OUT

    id: int
    exam_question_id: int
    given_answer: str | None
    moodle_points_awarded: float | None
    grade: GradeOut | None = None


class AttemptOut(BaseModel):
    model_config = _STRICT_OUT

    id: int
    attempt_number: int
    started_at: datetime | None = None
    submitted_at: datetime | None = None
    source: AttemptSource
    source_attempt_id: str | None = None
    answers: list[AttemptAnswerOut]


class SubmissionListItemOut(BaseModel):
    model_config = _STRICT_OUT

    id: int
    exam_id: int
    student_id: int
    student_external_id: str
    student_display_name: str | None
    attempt_count: int
    total_points_awarded: float
    total_points_max: float
    percentage: float
    grade_status: SubmissionGradeStatus


class SubmissionListOut(BaseModel):
    model_config = _STRICT_OUT

    items: list[SubmissionListItemOut]
    total: int
    pending_count: int  # Submissions whose grade_status != fully_reviewed.
    limit: int
    offset: int


class SubmissionDetailOut(BaseModel):
    model_config = _STRICT_OUT

    id: int
    exam_id: int
    student_id: int
    student_external_id: str
    student_display_name: str | None
    scoring_strategy: ScoringStrategy
    graded_attempt_id: int | None
    total_points_awarded: float
    total_points_max: float
    percentage: float
    grade_status: SubmissionGradeStatus
    attempts: list[AttemptOut]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_exam_for_user(*, db: Session, user: User, exam_id: int) -> Exam:
    """Load Exam with multi-tenancy check; 404 on foreign institution.

    404 (not 403) is intentional: revealing existence-but-no-access leaks
    information about other tenants.
    """
    exam = (
        db.query(Exam)
        .options(joinedload(Exam.questions))
        .filter(
            Exam.id == exam_id,
            Exam.institution_id == user.institution_id,
        )
        .one_or_none()
    )
    if exam is None:
        raise HTTPException(status_code=404, detail="Prüfung nicht gefunden")
    return exam


def _import_error(
    exc: ImportDriverError, *, status_code: int, locale: str
) -> AppHTTPException:
    """Turn a coded import failure into the ADR 0005 response envelope.

    The exception's own sentence is the *diagnostic* one: it names the
    Moodle web-service function, the offending quiz id, the driver class,
    the count of answers that missed. It goes to the log. What the caller
    gets back is the translated sentence for ``exc.code`` plus the
    parameters that sentence actually interpolates — never ``str(exc)``,
    which is how developer wording and internal ids used to reach a
    teacher's screen (TF-773 PR 2c).

    ``status_code`` comes from the caller rather than the exception,
    keeping the existing mapping intact: driver errors stay 400,
    validation errors stay 422. One code appears under both —
    ``submissions_import_no_attempts``, raised by the JSON driver for an
    empty export and by the payload validation for a Moodle quiz nobody
    sat — because it is the same fact for the teacher and deserves the
    same sentence.
    """
    logger.warning(
        "Import abgebrochen (%s, HTTP %s): %s",
        exc.code,
        status_code,
        exc.log_message,
    )
    return api_error(status_code, exc.code, locale, **exc.params)


async def _read_upload(file: UploadFile, *, locale: str) -> bytes:
    """Read upload with a hard size cap to prevent worker OOM.

    FastAPI/Starlette sets ``UploadFile.size`` from the Content-Length
    when present; we still cap the actual read in case the client
    streams without declaring size.

    Both rejections are the same fact for the teacher — the file is over
    the limit — so they share one code. The declared size and the read
    size differ only in how the client sent it, which is a log detail.
    The limit itself is the parameter, because it is the number they act
    on (TF-773 PR 2c).
    """
    max_mb = MAX_UPLOAD_BYTES // (1024 * 1024)
    if file.size is not None and file.size > MAX_UPLOAD_BYTES:
        logger.warning(
            "Upload abgelehnt: Content-Length %s Bytes über dem Limit von %s MB",
            file.size,
            max_mb,
        )
        raise api_error(413, "submissions_import_file_too_large", locale, max_mb=max_mb)
    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        logger.warning(
            "Upload abgelehnt: %s Bytes gelesen, Limit %s MB (ohne Content-Length)",
            len(contents),
            max_mb,
        )
        raise api_error(413, "submissions_import_file_too_large", locale, max_mb=max_mb)
    return contents


def _reject_driver_without_upload_body(driver_name: str, *, locale: str) -> None:
    """Reject ``moodle_api`` on the multipart file-upload endpoints.

    ``moodle_api`` has no file to parse — it fetches from Moodle via web
    service using a Pydantic-validated ``quiz_id`` (``ApiImportIn``, see
    ``/import/api-preview``/``/import/api-commit``). Without this guard, a
    hand-crafted request to the upload endpoints could reach
    ``MoodleApiDriver.parse()`` with a ``quiz_id`` that skipped the ``gt=0``
    Pydantic check, producing ``submissions_import_quiz_id_invalid`` — a code
    the frontend registry deliberately does not carry because
    ``test_submissions_import_error_codes.HTTP_UNERREICHBAR`` documents that
    exact path as unreachable (TF-773 PR 2c review). Arbitrary unregistered
    driver names are intentionally left alone here — they still fall through
    to the tier gate below, which is what
    ``test_unbekannter_driver_scheitert_an_der_tier_sperre`` pins.
    """
    if driver_name == DriverName.MOODLE_API.value:
        raise api_error(422, "submissions_import_driver_unknown", locale)


def _import_payload_to_preview(payload, *, max_rows: int = 50) -> ImportPreviewOut:
    """Map internal ImportPayload → API schema. Truncates large lists for
    preview but flags it via ``truncated`` so the frontend can warn."""
    return ImportPreviewOut(
        exam_id=payload.exam_id,
        driver_name=DriverName(payload.driver_name),
        student_count=len(payload.students),
        attempt_count=len(payload.attempts),
        students=[
            ImportPayloadStudentOut(
                external_id=s.external_id, display_name=s.display_name
            )
            for s in payload.students[:max_rows]
        ],
        attempts=[
            ImportPayloadAttemptOut(
                student_external_id=a.student_external_id,
                attempt_number=a.attempt_number,
                started_at=a.started_at,
                submitted_at=a.submitted_at,
                answer_count=len(a.answers),
            )
            for a in payload.attempts[:max_rows]
        ],
        warnings=list(payload.warnings),
        errors=[
            ImportRowErrorOut(row_index=e.row_index, reason=e.reason)
            for e in payload.errors
        ],
        source_metadata=payload.source_metadata,
        truncated=(
            len(payload.students) > max_rows or len(payload.attempts) > max_rows
        ),
    )


def _enqueue_import(
    *,
    db: Session,
    locale: str,
    exam: Exam,
    driver_name: str,
    source_bytes: bytes,
    triggered_by: int,
    source_metadata: dict[str, Any],
) -> ImportJob:
    """Create a ``queued`` ImportJob and hand it to the Celery worker (TF-412).

    The slow part of the import — persisting attempts and, for open-ended
    questions, serial LLM grading — runs in the worker instead of the HTTP
    request, so the request can return immediately. The worker reuses this
    exact job row via ``import_job_id``, and the raw upload bytes are passed
    base64-encoded so the driver's own encoding detection still runs.

    On broker failure the job row is marked ``failed`` in place (visible via
    ``GET /import-jobs``/``GET /import-jobs/{id}`` once the caller lists or
    already knows the id) instead of being left stuck in ``queued`` forever;
    the 503 raised here carries only the coded error, not the job id itself
    — see the comment further down on why the id no longer rides along in
    the response body.
    """
    job = ImportService(db).create_queued_job(
        exam=exam,
        driver_name=driver_name,
        triggered_by=triggered_by,
        source_metadata=source_metadata,
    )
    # Captured up front: after a rollback in the failure path below the ORM
    # object is expired, so reading ``job.id`` there could trigger a reload
    # against an already-down DB. The PK is known the moment the row commits.
    job_id = job.id
    try:
        import_submissions.apply_async(
            kwargs={
                "exam_id": exam.id,
                "driver_name": driver_name,
                "source_b64": Base64Str(base64.b64encode(source_bytes).decode("ascii")),
                "import_job_id": job.id,
                "triggered_by": triggered_by,
            },
        )
    except Exception as exc:
        logger.exception(
            "Import-Job konnte nicht eingereiht werden (job_id=%s, exam_id=%s)",
            job.id,
            exam.id,
        )
        job.status = ImportJobStatus.FAILED.value
        job.finished_at = datetime.now(timezone.utc)
        job.error_log = [
            {
                "row_index": -1,
                "code": "submissions_import_enqueue_failed",
                "reason": (
                    "Import konnte nicht gestartet werden — der Hintergrund-"
                    "Dienst war nicht erreichbar. Bitte erneut versuchen."
                ),
            }
        ]
        # Persisting the terminal state is best-effort: if the DB is *also*
        # unreachable (a correlated broker+DB outage) the commit raises too.
        # Swallow that here so the original broker failure still surfaces as
        # the coded 503 below, instead of an unhandled 500 that buries the
        # broker cause. The periodic reaper age-fails the row either way, and
        # the id itself is only in the log now — see the comment further down.
        try:
            db.commit()
            db.refresh(job)
        except Exception:  # noqa: BLE001 — already in the error path
            logger.exception(
                "Konnte fehlgeschlagenen Import-Job %s nicht persistieren", job_id
            )
            try:
                db.rollback()
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Rollback ebenfalls fehlgeschlagen für Import-Job %s", job_id
                )
        # The job id used to ride along in a ``detail`` dict, which ADR 0005
        # says ``detail`` never is — and it is a support detail, not something
        # a teacher can act on. It is logged above (and again here, because
        # the persist may have failed in between); the response carries the
        # code (TF-773 PR 2c).
        logger.warning(
            "Import-Job %s nicht eingereiht — Antwort 503 mit %s",
            job_id,
            "submissions_import_enqueue_failed",
        )
        raise api_error(503, "submissions_import_enqueue_failed", locale) from exc
    return job


def _import_job_to_out(job: ImportJob, *, locale: str) -> ImportJobOut:
    """Map the persisted ``error_log`` to the response, translating as needed.

    A job-level failure recorded by ``ImportService._fail_job``, and a
    per-submission grading crash recorded by ``_finalise_job``, both carry a
    ``code``/``params`` pair (same split as ``_import_error``) because the
    async commit path can fail with the very same coded exceptions the
    synchronous preview does — so it is translated here exactly like
    ``api_error()`` translates them for the synchronous response, instead of
    ever putting the stored diagnostic sentence on the wire. Entries without
    a ``code`` are the row-level ``payload.errors`` a driver writes as a
    fixed, safe German sentence — with one known pre-existing exception,
    ``_persist_attempts``'s "unexpected IntegrityError" row error, which puts
    a raw constraint/exception-class name in ``reason`` (tracked separately,
    out of this review's scope). ``details.diagnostic``/``details.traceback``/
    ``details.exception_type`` are operator/DB-only and are stripped here
    regardless of origin (TF-773 PR 2c review).
    """
    raw_log = job.error_log or []
    structured = []
    for entry in raw_log:
        if not isinstance(entry, dict):
            continue
        code = entry.get("code")
        params = entry.get("params")
        reason = (
            translate(code, locale, **(params if isinstance(params, dict) else {}))
            if code
            else str(entry.get("reason") or "")
        )
        raw_details = entry.get("details")
        details = (
            {
                k: v
                for k, v in raw_details.items()
                if k not in ("diagnostic", "traceback", "exception_type")
            }
            if isinstance(raw_details, dict)
            else None
        )
        structured.append(
            ImportRowErrorOut(
                row_index=int(entry.get("row_index", 0) or 0),
                reason=reason,
                step=entry.get("step"),
                details=details or None,
            )
        )
    return ImportJobOut(
        id=job.id,
        exam_id=job.exam_id,
        driver_name=DriverName(job.driver_name),
        status=ImportJobStatus(job.status),
        rows_processed=job.rows_processed,
        rows_failed=job.rows_failed,
        graded_total=job.graded_total,
        graded_done=job.graded_done,
        error_log=structured if structured else None,
        source_metadata=job.source_metadata,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


# ---------------------------------------------------------------------------
# Import — Preview + Commit
# ---------------------------------------------------------------------------


@router.post("/import/preview", response_model=ImportPreviewOut)
async def import_preview(
    http_request: Request,
    exam_id: int = Form(...),
    driver_name: str = Form(DriverName.MOODLE_JSON.value),
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("submissions:import")),
    db: Session = Depends(get_db),
) -> ImportPreviewOut:
    """Stage 1: parse + validate CSV, **no** DB write.

    Frontend renders the result in a preview table (detected students,
    column mapping, warnings). Only after teacher confirmation does
    ``/import/commit`` run.
    """
    locale = get_request_locale(http_request, current_user)
    exam = _load_exam_for_user(db=db, user=current_user, exam_id=exam_id)
    _reject_driver_without_upload_body(driver_name, locale=locale)
    # Tier gate before the expensive parsing — Free/Starter may not use
    # an API driver, otherwise the preview would burn the token.
    assert_driver_allowed(user=current_user, driver_name=driver_name)
    contents = await _read_upload(file, locale=locale)

    try:
        payload = await run_in_threadpool(
            ImportService(db).preview,
            exam=exam,
            driver_name=driver_name,
            source=contents,
        )
    except ImportValidationError as exc:
        raise _import_error(exc, status_code=422, locale=locale) from exc
    except ImportDriverError as exc:
        raise _import_error(exc, status_code=400, locale=locale) from exc
    except Exception:
        logger.exception(
            "import_preview unerwartet fehlgeschlagen (exam_id=%s)", exam_id
        )
        # «siehe Server-Logs» is an instruction to an operator that used to be
        # printed on a teacher's screen. The logger.exception above keeps the
        # cause; the response says what every other programming error here
        # says (TF-773 PR 2c).
        raise api_error(500, "submissions_import_internal_error", locale)

    return _import_payload_to_preview(payload)


@router.post("/import/commit", response_model=ImportJobOut, status_code=202)
async def import_commit(
    http_request: Request,
    exam_id: int = Form(...),
    driver_name: str = Form(DriverName.MOODLE_JSON.value),
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("submissions:import")),
    db: Session = Depends(get_db),
) -> ImportJobOut:
    """Stage 2: validate synchronously, then grade asynchronously (TF-412).

    Parsing/validation is fast and runs inline, so malformed CSVs still fail
    fast with a 4xx. The slow part — persisting attempts and the serial LLM
    grading of open-ended answers — is handed to a Celery worker. We return
    202 with a ``queued`` job that the client polls via
    ``GET /import-jobs/{id}``, so the HTTP request can never hang for minutes
    on grading.
    """
    locale = get_request_locale(http_request, current_user)
    exam = _load_exam_for_user(db=db, user=current_user, exam_id=exam_id)
    _reject_driver_without_upload_body(driver_name, locale=locale)
    assert_driver_allowed(user=current_user, driver_name=driver_name)
    # The monthly limit only applies to a new exam, not to re-importing
    # the same one — the helper logic takes care of that.
    assert_exam_quota_for_import(db=db, user=current_user, exam_id=exam.id)
    contents = await _read_upload(file, locale=locale)

    # Synchronous validation (parse only — no persist, no grading, so it stays
    # fast). Malformed CSVs surface as 4xx here, *before* anything is enqueued.
    # The parsed payload also yields the student count for the submission-quota
    # pre-flight (so a Free/Starter class that is too large is rejected with
    # 402 up front instead of half-importing).
    try:
        preview_payload = await run_in_threadpool(
            ImportService(db).preview,
            exam=exam,
            driver_name=driver_name,
            source=contents,
        )
    except ImportValidationError as exc:
        raise _import_error(exc, status_code=422, locale=locale) from exc
    except ImportDriverError as exc:
        raise _import_error(exc, status_code=400, locale=locale) from exc

    assert_submission_quota_for_exam(
        db=db,
        user=current_user,
        exam_id=exam.id,
        additional=len(preview_payload.students),
    )

    job = _enqueue_import(
        db=db,
        locale=locale,
        exam=exam,
        driver_name=driver_name,
        source_bytes=contents,
        triggered_by=current_user.id,
        source_metadata={
            "filename": file.filename or "",
            "content_type": file.content_type or "",
            "size_bytes": len(contents),
        },
    )
    return _import_job_to_out(job, locale=locale)


@router.get("/import-jobs/{job_id}", response_model=ImportJobOut)
async def get_import_job(
    job_id: int,
    http_request: Request,
    current_user: User = Depends(require_permission("submissions:read")),
    db: Session = Depends(get_db),
) -> ImportJobOut:
    """Polling endpoint for import job status."""
    locale = get_request_locale(http_request, current_user)
    job = (
        db.query(ImportJob)
        .filter(
            ImportJob.id == job_id,
            ImportJob.institution_id == current_user.institution_id,
        )
        .one_or_none()
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Import-Job nicht gefunden")
    return _import_job_to_out(job, locale=locale)


@router.get("/import-jobs", response_model=ImportJobListOut)
async def list_import_jobs(
    http_request: Request,
    exam_id: int = Query(..., description="Exam whose import jobs are being listed"),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission("submissions:read")),
    db: Session = Depends(get_db),
) -> ImportJobListOut:
    """Most recent import jobs of an exam (institution-scoped, newest first).

    Feeds the Auswertungen status surface (TF-428): the page polls this
    endpoint to show running/finished imports with live progress (n/total)
    — the import no longer needs a modal held open for this.
    """
    locale = get_request_locale(http_request, current_user)
    base = db.query(ImportJob).filter(
        ImportJob.exam_id == exam_id,
        ImportJob.institution_id == current_user.institution_id,
    )
    total = base.count()
    jobs = base.order_by(ImportJob.created_at.desc()).limit(limit).offset(offset).all()
    return ImportJobListOut(
        items=[_import_job_to_out(job, locale=locale) for job in jobs],
        total=total,
    )


# ---------------------------------------------------------------------------
# Result-import deletion (TF-421)
# ---------------------------------------------------------------------------


def _deletion_summary_to_out(summary: DeletionSummary) -> ImportDeletionSummaryOut:
    return ImportDeletionSummaryOut(
        exam_id=summary.exam_id,
        submission_count=summary.submission_count,
        attempt_count=summary.attempt_count,
        student_count=summary.student_count,
        by_source=[
            ImportSourceCountOut(source=sc.source, attempt_count=sc.attempt_count)
            for sc in summary.by_source
        ],
    )


@router.get("/import/summary", response_model=ImportDeletionSummaryOut)
async def get_import_deletion_summary(
    exam_id: int,
    current_user: User = Depends(require_permission("submissions:read")),
    db: Session = Depends(get_db),
) -> ImportDeletionSummaryOut:
    """Preview how much ``DELETE /import`` would remove for ``exam_id``.

    Powers the confirmation dialog (affected students/attempts). Read-only —
    requires only ``submissions:read``.
    """
    exam = _load_exam_for_user(db=db, user=current_user, exam_id=exam_id)
    summary = ResultsDeletionService(db).summary(exam=exam)
    return _deletion_summary_to_out(summary)


@router.delete("/import", response_model=ImportDeletionSummaryOut)
async def delete_import(
    exam_id: int,
    http_request: Request,
    current_user: User = Depends(require_permission("submissions:delete")),
    db: Session = Depends(get_db),
) -> ImportDeletionSummaryOut:
    """Delete all imported results of an exam, then allow a clean re-import.

    Removes attempts + answers + grades (DB cascade) and the now-empty
    submissions, across every source. Students and import-job history are
    kept. RBAC: ``submissions:delete`` (Admin / Dozent). Multi-tenant scoped
    via :func:`_load_exam_for_user`.

    Writes an audit-log entry **in the same transaction** as the deletion: if
    the audit write fails, the whole operation rolls back (fail-closed — no
    silent data loss without a trail), mirroring the superuser-bypass policy.
    """
    exam = _load_exam_for_user(db=db, user=current_user, exam_id=exam_id)

    summary = ResultsDeletionService(db).delete_exam_results(exam=exam)

    audit = AuditService.log_action(
        db=db,
        action=AuditService.ACTION_DELETE_RESULT_IMPORT,
        user_id=current_user.id,
        resource_type=AuditService.RESOURCE_EXAM,
        resource_id=exam.id,
        additional_data={
            "exam_id": exam.id,
            "submission_count": summary.submission_count,
            "attempt_count": summary.attempt_count,
            "student_count": summary.student_count,
            "by_source": {sc.source: sc.attempt_count for sc in summary.by_source},
        },
        request=http_request,
        commit=True,
    )
    if audit is None:
        # log_action already rolled back the session, undoing the deletion.
        logger.critical(
            "delete_import refused: audit log persistence failed "
            "(exam_id=%s, user_id=%s). Deletion rolled back.",
            exam.id,
            current_user.id,
        )
        raise HTTPException(
            status_code=500,
            detail="Audit-Log nicht verfügbar; Löschung abgebrochen.",
        )

    return _deletion_summary_to_out(summary)


# ---------------------------------------------------------------------------
# Submissions — list + detail
# ---------------------------------------------------------------------------


@router.get("", response_model=SubmissionListOut)
async def list_submissions(
    exam_id: int,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_permission("submissions:read")),
    db: Session = Depends(get_db),
) -> SubmissionListOut:
    """Submissions for an exam — paged.

    The default 200 / max 1000 cap keeps a single request from OOMing
    the worker on huge classes; the frontend paginates above that.
    """
    _load_exam_for_user(db=db, user=current_user, exam_id=exam_id)

    base_query = (
        db.query(Submission, Student)
        .join(Student, Student.id == Submission.student_id)
        .filter(Submission.exam_id == exam_id)
    )
    total = base_query.with_entities(Submission.id).count()
    # Count pending separately: the frontend pagination would otherwise
    # only see the visible page and report a wrong "X of Y reviewed"
    # for classes larger than ``limit``.
    pending_count = (
        db.query(Submission.id)
        .filter(
            Submission.exam_id == exam_id,
            Submission.grade_status != "fully_reviewed",
        )
        .count()
    )
    rows = (
        base_query.options(joinedload(Submission.attempts))
        .order_by(Submission.id)
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = [
        SubmissionListItemOut(
            id=s.id,
            exam_id=s.exam_id,
            student_id=s.student_id,
            student_external_id=student.external_id,
            student_display_name=student.display_name,
            attempt_count=len(s.attempts),
            total_points_awarded=s.total_points_awarded,
            total_points_max=s.total_points_max,
            percentage=s.percentage,
            grade_status=SubmissionGradeStatus(s.grade_status),
        )
        for s, student in rows
    ]
    return SubmissionListOut(
        items=items,
        total=total,
        pending_count=pending_count,
        limit=limit,
        offset=offset,
    )


@router.get("/{submission_id}", response_model=SubmissionDetailOut)
async def get_submission(
    submission_id: int,
    current_user: User = Depends(require_permission("submissions:read")),
    db: Session = Depends(get_db),
) -> SubmissionDetailOut:
    """Detail with all attempts + answers + grades."""
    submission = (
        db.query(Submission)
        .join(Student, Student.id == Submission.student_id)
        .join(Exam, Exam.id == Submission.exam_id)
        .options(
            joinedload(Submission.student),
            joinedload(Submission.attempts)
            .joinedload(Attempt.answers)
            .joinedload(AttemptAnswer.grade),
        )
        .filter(
            Submission.id == submission_id,
            Exam.institution_id == current_user.institution_id,
        )
        .one_or_none()
    )
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission nicht gefunden")

    return SubmissionDetailOut(
        id=submission.id,
        exam_id=submission.exam_id,
        student_id=submission.student_id,
        student_external_id=submission.student.external_id,
        student_display_name=submission.student.display_name,
        scoring_strategy=ScoringStrategy(submission.scoring_strategy),
        graded_attempt_id=submission.graded_attempt_id,
        total_points_awarded=submission.total_points_awarded,
        total_points_max=submission.total_points_max,
        percentage=submission.percentage,
        grade_status=SubmissionGradeStatus(submission.grade_status),
        attempts=[
            AttemptOut(
                id=a.id,
                attempt_number=a.attempt_number,
                started_at=a.started_at,
                submitted_at=a.submitted_at,
                source=AttemptSource(a.source),
                source_attempt_id=a.source_attempt_id,
                answers=[
                    AttemptAnswerOut(
                        id=ans.id,
                        exam_question_id=ans.exam_question_id,
                        given_answer=ans.given_answer,
                        moodle_points_awarded=ans.moodle_points_awarded,
                        grade=GradeOut(
                            id=ans.grade.id,
                            points_awarded=ans.grade.points_awarded,
                            points_max=ans.grade.points_max,
                            status=GradeStatus(ans.grade.status),
                            is_correct=ans.grade.is_correct,
                            llm_confidence=ans.grade.llm_confidence,
                            llm_rationale=ans.grade.llm_rationale,
                            llm_matched_aspects=ans.grade.llm_matched_aspects,
                            llm_missing_aspects=ans.grade.llm_missing_aspects,
                            reviewer_id=ans.grade.reviewer_id,
                            reviewer_note=ans.grade.reviewer_note,
                        )
                        if ans.grade
                        else None,
                    )
                    for ans in a.answers
                ],
            )
            for a in submission.attempts
        ],
    )


# ---------------------------------------------------------------------------
# API driver import (TF-336)
# ---------------------------------------------------------------------------


class ApiImportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exam_id: int = Field(gt=0)
    quiz_id: int = Field(gt=0, description="Moodle quiz ID")


@router.post("/import/api-preview", response_model=ImportPreviewOut)
async def import_api_preview(
    body: ApiImportIn,
    http_request: Request,
    current_user: User = Depends(require_permission("submissions:import")),
    db: Session = Depends(get_db),
) -> ImportPreviewOut:
    """Preview variant for the ``moodle_api`` driver.

    Makes the web-service calls without persistence, so the frontend
    can display the detected students and answers before the teacher
    clicks "Import".
    """
    import json as _json

    locale = get_request_locale(http_request, current_user)
    exam = _load_exam_for_user(db=db, user=current_user, exam_id=body.exam_id)
    # Tier gate before any web-service calls — Free/Starter may not use
    # the API at all.
    assert_driver_allowed(user=current_user, driver_name=DriverName.MOODLE_API.value)
    source = _json.dumps({"quiz_id": body.quiz_id}).encode("utf-8")
    try:
        payload = await run_in_threadpool(
            ImportService(db).preview,
            exam=exam,
            driver_name=DriverName.MOODLE_API.value,
            source=source,
        )
    except ImportValidationError as exc:
        raise _import_error(exc, status_code=422, locale=locale) from exc
    except ImportDriverError as exc:
        raise _import_error(exc, status_code=400, locale=locale) from exc
    except Exception:
        logger.exception(
            "import_api_preview unerwartet fehlgeschlagen (exam_id=%s, quiz_id=%s)",
            body.exam_id,
            body.quiz_id,
        )
        raise api_error(500, "submissions_import_internal_error", locale)

    return _import_payload_to_preview(payload)


@router.post("/import/api-commit", response_model=ImportJobOut, status_code=202)
async def import_api_commit(
    body: ApiImportIn,
    http_request: Request,
    current_user: User = Depends(require_permission("submissions:import")),
    db: Session = Depends(get_db),
) -> ImportJobOut:
    """Moodle API import — validates synchronously, grades asynchronously (TF-412).

    Like the CSV path: web-service calls + validation run inline (early
    400/422 for a bad quiz ID / auth failure), the slow persist+grade
    pipeline is handed to a Celery worker. Response is 202 with a
    ``queued`` job that the client polls via ``GET /import-jobs/{id}``.
    Idempotent via ``source_attempt_id`` (= Moodle attempt ID).
    """
    import json as _json

    locale = get_request_locale(http_request, current_user)
    exam = _load_exam_for_user(db=db, user=current_user, exam_id=body.exam_id)
    assert_driver_allowed(user=current_user, driver_name=DriverName.MOODLE_API.value)
    assert_exam_quota_for_import(db=db, user=current_user, exam_id=exam.id)
    source_bytes = _json.dumps({"quiz_id": body.quiz_id}).encode("utf-8")

    # Synchronous validation (Moodle web-service fetch, no grading) → early
    # 400/422 for a bad quiz-id or auth failure, before anything is enqueued.
    try:
        await run_in_threadpool(
            ImportService(db).preview,
            exam=exam,
            driver_name=DriverName.MOODLE_API.value,
            source=source_bytes,
        )
    except ImportValidationError as exc:
        raise _import_error(exc, status_code=422, locale=locale) from exc
    except ImportDriverError as exc:
        raise _import_error(exc, status_code=400, locale=locale) from exc

    job = _enqueue_import(
        db=db,
        locale=locale,
        exam=exam,
        driver_name=DriverName.MOODLE_API.value,
        source_bytes=source_bytes,
        triggered_by=current_user.id,
        source_metadata={"quiz_id": body.quiz_id},
    )
    return _import_job_to_out(job, locale=locale)


# ---------------------------------------------------------------------------
# Convenience alias: ``GET /api/v1/exams/{exam_id}/submissions``
#
# The list-per-exam path is exposed at both URLs so the frontend may use
# either. Hidden from OpenAPI to avoid duplicate generated client SDKs.
# ---------------------------------------------------------------------------


exams_alias_router = APIRouter(prefix="/api/v1/exams", tags=["Submissions"])


@exams_alias_router.get(
    "/{exam_id}/submissions",
    response_model=SubmissionListOut,
    include_in_schema=False,
)
async def list_submissions_for_exam(
    exam_id: int,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_permission("submissions:read")),
    db: Session = Depends(get_db),
) -> SubmissionListOut:
    """Alias for ``GET /api/v1/submissions?exam_id=X``."""
    return await list_submissions(
        exam_id=exam_id,
        limit=limit,
        offset=offset,
        current_user=current_user,
        db=db,
    )
