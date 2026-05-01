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

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, joinedload

from database import get_db
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
from services.import_drivers import ImportDriverError
from services.import_service import ImportService, ImportValidationError
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
    error_log: list[ImportRowErrorOut] | None = None
    source_metadata: dict[str, Any] | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


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


async def _read_upload(file: UploadFile) -> bytes:
    """Read upload with a hard size cap to prevent worker OOM.

    FastAPI/Starlette sets ``UploadFile.size`` from the Content-Length
    when present; we still cap the actual read in case the client
    streams without declaring size.
    """
    if file.size is not None and file.size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Datei zu gross ({file.size} Bytes). Maximum: "
                f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
            ),
        )
    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Datei überschreitet das Maximum von "
                f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
            ),
        )
    return contents


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


def _latest_failed_job_id(
    *, db: Session, exam_id: int, institution_id: int
) -> int | None:
    """Best-effort lookup of the most recent failed ImportJob for this
    exam — used to enrich a 500 response so the client can poll the
    job detail rather than rely on server logs."""
    row = (
        db.query(ImportJob.id)
        .filter(
            ImportJob.exam_id == exam_id,
            ImportJob.institution_id == institution_id,
            ImportJob.status == ImportJobStatus.FAILED.value,
        )
        .order_by(ImportJob.id.desc())
        .first()
    )
    return row[0] if row else None


def _import_job_to_out(job: ImportJob) -> ImportJobOut:
    raw_log = job.error_log or []
    structured = [
        ImportRowErrorOut(
            row_index=int(entry.get("row_index", 0) or 0),
            reason=str(entry.get("reason") or ""),
            step=entry.get("step"),
            details=entry.get("details")
            if isinstance(entry.get("details"), dict)
            else None,
        )
        for entry in raw_log
        if isinstance(entry, dict)
    ]
    return ImportJobOut(
        id=job.id,
        exam_id=job.exam_id,
        driver_name=DriverName(job.driver_name),
        status=ImportJobStatus(job.status),
        rows_processed=job.rows_processed,
        rows_failed=job.rows_failed,
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
    exam_id: int = Form(...),
    driver_name: str = Form(DriverName.MOODLE_CSV.value),
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("submissions:import")),
    db: Session = Depends(get_db),
) -> ImportPreviewOut:
    """Stage 1: parse + validate CSV, **no** DB write.

    Frontend renders the result in a preview table (detected students,
    column mapping, warnings). Only after teacher confirmation does
    ``/import/commit`` run.
    """
    exam = _load_exam_for_user(db=db, user=current_user, exam_id=exam_id)
    contents = await _read_upload(file)

    try:
        payload = await run_in_threadpool(
            ImportService(db).preview,
            exam=exam,
            driver_name=driver_name,
            source=contents,
        )
    except ImportDriverError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ImportValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"message": str(exc), "issues": exc.issues},
        ) from exc
    except Exception:
        logger.exception(
            "import_preview unerwartet fehlgeschlagen (exam_id=%s)", exam_id
        )
        raise HTTPException(
            status_code=500,
            detail="Import-Vorschau fehlgeschlagen — siehe Server-Logs.",
        )

    return _import_payload_to_preview(payload)


@router.post("/import/commit", response_model=ImportJobOut)
async def import_commit(
    exam_id: int = Form(...),
    driver_name: str = Form(DriverName.MOODLE_CSV.value),
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("submissions:import")),
    db: Session = Depends(get_db),
) -> ImportJobOut:
    """Stage 2: full pipeline — persist + grade + aggregate.

    The pipeline does sync DB + grading work; we run it in a threadpool
    so the FastAPI event loop stays responsive while a large CSV is
    being imported.
    """
    exam = _load_exam_for_user(db=db, user=current_user, exam_id=exam_id)
    contents = await _read_upload(file)

    try:
        job = await run_in_threadpool(
            ImportService(db).commit,
            exam=exam,
            driver_name=driver_name,
            source=contents,
            triggered_by=current_user.id,
            source_metadata={
                "filename": file.filename or "",
                "content_type": file.content_type or "",
                "size_bytes": len(contents),
            },
        )
    except ImportDriverError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ImportValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"message": str(exc), "issues": exc.issues},
        ) from exc
    except Exception as exc:
        logger.exception(
            "import_commit unerwartet fehlgeschlagen (exam_id=%s)", exam_id
        )
        # ImportService persists a failed ImportJob with diagnostic
        # error_log before raising — surface its id so the client can
        # poll /import-jobs/{id} instead of needing log access.
        job_id = _latest_failed_job_id(
            db=db, exam_id=exam.id, institution_id=current_user.institution_id
        )
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Import fehlgeschlagen — siehe Job-Detail.",
                "import_job_id": job_id,
                "exception": type(exc).__name__,
            },
        ) from exc

    return _import_job_to_out(job)


@router.get("/import-jobs/{job_id}", response_model=ImportJobOut)
async def get_import_job(
    job_id: int,
    current_user: User = Depends(require_permission("submissions:read")),
    db: Session = Depends(get_db),
) -> ImportJobOut:
    """Polling endpoint for import job status."""
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
    return _import_job_to_out(job)


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
    return SubmissionListOut(items=items, total=total, limit=limit, offset=offset)


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
