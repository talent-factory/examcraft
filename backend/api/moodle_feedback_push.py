"""Endpoints to push graded feedback back to Moodle (TF-435).

* ``POST /api/v1/exams/{exam_id}/moodle/push-feedback`` — enqueue a push
  job (202 + job record), then poll:
* ``GET  /api/v1/exams/{exam_id}/moodle/push-feedback/{job_id}``.

Multi-Tenancy: institution match AND ``ExamVisibility`` (TF-643) — a
same-institution colleague without visibility into a PRIVATE/off-team exam
gets 404, same as every other exam mutation. RBAC:
``submissions:moodle_feedback_push``. The actual transport (plugin vs.
gradebook) is chosen by the background service.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from database import get_db
from enums import FeedbackTransportName, MoodleFeedbackPushStatus
from models.auth import User
from models.exam import Exam, ExamQuestion
from models.submission import MoodleConnection, MoodleFeedbackPushJob
from services.audit_service import AuditService
from tasks.moodle_feedback_push_task import push_moodle_feedback
from errors import api_error
from services.translation_service import DEFAULT_LOCALE, get_request_locale
from utils.auth_utils import require_permission
from utils.exam_visibility import assert_exam_visible_for

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/exams", tags=["Moodle Feedback Push"])

_PERMISSION = "submissions:moodle_feedback_push"


class PushJobOut(BaseModel):
    id: int
    status: MoodleFeedbackPushStatus
    transport: FeedbackTransportName | None
    students_total: int
    students_pushed: int
    students_skipped: int
    students_failed: int
    error_log: list | None

    model_config = ConfigDict(from_attributes=True)


# `from __future__ import annotations` turns the enum field annotations into
# strings, so Pydantic has to resolve MoodleFeedbackPushStatus /
# FeedbackTransportName lazily, through `sys.modules[cls.__module__]`. That
# lookup used to fail outright: main.py loaded this file under the synthetic
# name "core_api_moodle_feedback_push", which was never in sys.modules.
# TF-660 moved the loader to the canonical "api.moodle_feedback_push", so the
# lookup now resolves — but rebuilding eagerly here, where both enums are in
# the module namespace, keeps the schema defined under every load path and
# costs nothing.
PushJobOut.model_rebuild()


def _ensure_exam_for_user(
    db: Session, user: User, exam_id: int, locale: str = DEFAULT_LOCALE
) -> Exam:
    """Load exam by id, 404 unless institution matches AND ``user`` has
    ExamVisibility access (TF-643) — pushing feedback is a mutation, so this
    is gated exactly like every other exam-mutation endpoint
    (``allow_read_all_bypass=False``, ``require_same_institution=True``; see
    ``api.exams._get_exam_or_404``)."""
    exam = db.query(Exam).filter(Exam.id == exam_id).one_or_none()
    if exam is None:
        raise api_error(404, "exams_not_found", locale)
    assert_exam_visible_for(
        user,
        exam,
        db,
        detail="Prüfung nicht gefunden",
        allow_read_all_bypass=False,
        require_same_institution=True,
    )
    return exam


def _exam_has_quiz_id(db: Session, exam_id: int) -> bool:
    rows = (
        db.query(ExamQuestion.external_refs)
        .filter(ExamQuestion.exam_id == exam_id)
        .all()
    )
    return any(refs and refs.get("moodle_quiz_id") for (refs,) in rows)


@router.post(
    "/{exam_id}/moodle/push-feedback",
    response_model=PushJobOut,
    status_code=202,
)
def push_feedback(
    exam_id: int,
    request: Request,
    current_user: User = Depends(require_permission(_PERMISSION)),
    db: Session = Depends(get_db),
) -> PushJobOut:
    locale = get_request_locale(request, current_user)
    exam = _ensure_exam_for_user(db, current_user, exam_id, locale)

    connection = (
        db.query(MoodleConnection)
        .filter(MoodleConnection.institution_id == current_user.institution_id)
        .one_or_none()
    )
    if connection is None:
        raise api_error(412, "moodle_feedback_push_no_connection", locale)
    if not _exam_has_quiz_id(db, exam.id):
        raise api_error(412, "moodle_feedback_push_no_quiz_id", locale)

    job = MoodleFeedbackPushJob(
        institution_id=current_user.institution_id,
        exam_id=exam.id,
        triggered_by=current_user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    AuditService.log_action(
        db=db,
        action="moodle_feedback_push",
        status="success",
        user_id=current_user.id,
        resource_type="exam",
        resource_id=str(exam.id),
        additional_data={"job_id": job.id},
        request=request,
    )

    try:
        push_moodle_feedback.apply_async(
            kwargs={"job_id": job.id, "force_transport": None}
        )
    except Exception as exc:  # noqa: BLE001 — broker down → fail the job, surface 503
        logger.exception("Feedback-Push konnte nicht eingereiht werden")
        job.status = MoodleFeedbackPushStatus.FAILED.value
        job.finished_at = datetime.now(timezone.utc)
        job.error_log = [
            {"scope": "job", "reason": "Hintergrund-Dienst nicht erreichbar."}
        ]
        db.commit()
        raise api_error(503, "moodle_feedback_push_queue_unavailable", locale) from exc

    return PushJobOut.model_validate(job)


@router.get(
    "/{exam_id}/moodle/push-feedback/{job_id}",
    response_model=PushJobOut,
)
def get_push_job(
    exam_id: int,
    job_id: int,
    request: Request,
    current_user: User = Depends(require_permission(_PERMISSION)),
    db: Session = Depends(get_db),
) -> PushJobOut:
    job = (
        db.query(MoodleFeedbackPushJob)
        .filter(
            MoodleFeedbackPushJob.id == job_id,
            MoodleFeedbackPushJob.exam_id == exam_id,
            MoodleFeedbackPushJob.institution_id == current_user.institution_id,
        )
        .one_or_none()
    )
    if job is None:
        raise api_error(
            404,
            "moodle_feedback_push_job_not_found",
            get_request_locale(request, current_user),
        )
    return PushJobOut.model_validate(job)
