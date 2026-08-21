"""Notenexport-Endpoint — Spec 9.

* ``GET /api/v1/exams/{exam_id}/grades/export/{format}``
  — formats: ``csv`` / ``moodle_csv`` / ``pdf``.

Wenn nicht alle Submissions ``fully_reviewed`` sind, antwortet der
Endpoint mit HTTP 409 + i18n-Key ``submissions_grade_export_blocked
_pending_review``. Die Lehrperson muss vorher die Review-Queue
abarbeiten — andernfalls würden ``proposed``-Grades unverbindlich in
die finale Notenliste einfliessen.

Multi-Tenancy via Exam-Institution-Check; RBAC: ``submissions:read``.
"""

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from database import get_db
from models.auth import Institution, User
from models.exam import Exam, ExamStatus
from models.student import Student
from models.submission import Submission
from services.grade_export_service import (
    GradeCsvExporter,
    GradeExportData,
    GradePdfExporter,
    GradeRow,
    MoodleGradeCsvExporter,
)
from services.grading_scheme_resolver import (
    resolve_scheme_config as _resolve_scheme_config,
)
from services.translation_service import get_request_locale, t
from utils.auth_utils import require_permission
from utils.download_filename import content_disposition, filename_stem

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/v1/exams", tags=["Grade Export"])


GradeExportFormat = Literal["csv", "moodle_csv", "pdf"]
# Public alias — kept since the previous private name leaked through
# OpenAPI; consumers may have generated against it.
_FormatLiteral = GradeExportFormat


def _download_filename(title: str, prefix: str, ext: str) -> str:
    """Build the download name for a grade export: ``<prefix>-<Titel>.<ext>``."""
    return f"{prefix}-{filename_stem(title)}.{ext}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_exam_for_user(db: Session, user: User, exam_id: int) -> Exam:
    exam = (
        db.query(Exam)
        .filter(
            Exam.id == exam_id,
            Exam.institution_id == user.institution_id,
        )
        .one_or_none()
    )
    if exam is None:
        raise HTTPException(status_code=404, detail="Prüfung nicht gefunden")
    return exam


def _build_export_data(db: Session, exam: Exam) -> GradeExportData:
    institution = (
        db.query(Institution)
        .filter(Institution.id == exam.institution_id)
        .one_or_none()
    )
    institution_name = institution.name if institution else ""

    rows_q = (
        db.query(Submission, Student)
        .join(Student, Student.id == Submission.student_id)
        .filter(Submission.exam_id == exam.id)
        .order_by(Student.external_id)
        .all()
    )
    rows = [
        GradeRow(
            external_id=student.external_id,
            display_name=student.display_name,
            total_points_awarded=float(submission.total_points_awarded),
            total_points_max=float(submission.total_points_max),
            percentage=float(submission.percentage),
            grade_status=submission.grade_status,
        )
        for submission, student in rows_q
    ]

    return GradeExportData(
        institution_name=institution_name,
        exam_title=exam.title,
        exam_course=exam.course,
        exam_date=exam.exam_date,
        passing_percentage=float(exam.passing_percentage or 0.0),
        scheme_config=_resolve_scheme_config(db, exam),
        rows=rows,
    )


def _ensure_exportable(db: Session, exam: Exam, locale: str) -> None:
    """Block the export with 409 if pre-conditions aren't satisfied.

    * Draft exams export nothing — questions can still change.
    * Any pending review means at least one grade is unverbindlich.
    """
    if exam.status == ExamStatus.DRAFT.value:
        raise HTTPException(
            status_code=409,
            detail=t("submissions_grade_export_blocked_draft", locale=locale),
        )

    blockers = (
        db.query(Submission.id)
        .filter(
            Submission.exam_id == exam.id,
            Submission.grade_status != "fully_reviewed",
        )
        .limit(1)
        .one_or_none()
    )
    if blockers is not None:
        raise HTTPException(
            status_code=409,
            detail=t("submissions_grade_export_blocked_pending_review", locale=locale),
        )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


_EXPORTERS: dict[str, tuple[type, str, str, str]] = {
    "csv": (GradeCsvExporter, "text/csv; charset=utf-8", "noten", "csv"),
    "moodle_csv": (
        MoodleGradeCsvExporter,
        "text/csv; charset=utf-8",
        "moodle-grades",
        "csv",
    ),
    "pdf": (GradePdfExporter, "application/pdf", "noten", "pdf"),
}


@router.get("/{exam_id}/grades/export/{export_format}")
async def export_grades(
    exam_id: int,
    export_format: GradeExportFormat,
    request: Request,
    current_user: User = Depends(require_permission("submissions:read")),
    db: Session = Depends(get_db),
):
    locale = get_request_locale(request, current_user)
    exam = _ensure_exam_for_user(db, current_user, exam_id)
    _ensure_exportable(db, exam, locale)

    data = _build_export_data(db, exam)

    exporter_entry = _EXPORTERS.get(export_format)
    if exporter_entry is None:
        # Unreachable thanks to the Literal, but FastAPI lets a malformed
        # path slip past in some test setups.
        raise HTTPException(status_code=400, detail="Unsupported export format")

    exporter_cls, media_type, prefix, ext = exporter_entry
    try:
        body = exporter_cls.export(data)
    except Exception:
        # Reportlab/csv exceptions are otherwise logless 500s. Anchor the
        # log to exam_id + format so support can find the failing call
        # without grep-archaeology.
        logger.exception(
            "Notenexport failed: format=%s exam_id=%d", export_format, exam_id
        )
        raise HTTPException(
            status_code=500,
            detail=t("submissions_grade_export_internal_error", locale=locale),
        )

    filename = _download_filename(exam.title, prefix, ext)
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": content_disposition(filename)},
    )
