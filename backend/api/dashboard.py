# core/backend/api/dashboard.py
"""Dashboard API – Statistiken und Aktivitäten.

Privacy: Lehrpersonen sehen alle Stats ihrer Institution (``/stats``),
aber im ``/activity``-Feed nur die eigenen Events. Wer alle Institution-
Events sehen will, nutzt die Seite ``/aktivitaeten`` mit dem Toggle
"Eigene/Alle" (``GET /api/v1/activity?scope=institution``).
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.activity import ActivityType
from database import get_db
from models.auth import AuditLog, User
from models.document import Document
from models.exam import Exam
from models.question_review import QuestionReview, ReviewStatus
from utils.audit_title import extract_audit_title
from utils.auth_utils import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _to_utc(dt: datetime) -> datetime:
    """Normalize datetime to UTC (handles both naive and aware)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _resolve_review_topic(db: Session, log: AuditLog, default_title: str) -> str:
    """Resolve a question-review topic from ``additional_data`` with a
    fallback to a direct ``QuestionReview`` lookup by ``resource_id``.

    Returns ``default_title`` when the ``resource_id`` is not numeric or
    the review row is gone — every fallback path is logged so the
    "why does the dashboard show a dash" question is debuggable.
    """
    title = extract_audit_title(
        log,
        fallback_title=str(log.resource_id),
        preferred_keys=("topic",),
    )
    if title != str(log.resource_id):
        return title
    try:
        q = (
            db.query(QuestionReview)
            .filter(QuestionReview.id == int(log.resource_id))
            .first()
        )
    except (ValueError, TypeError):
        logger.warning(
            "Non-int resource_id %r for action=%s log_id=%s — rendering fallback",
            log.resource_id,
            log.action,
            log.id,
        )
        return default_title
    if q is None:
        logger.warning(
            "QuestionReview id=%s referenced by audit log id=%s missing — "
            "rendering fallback",
            log.resource_id,
            log.id,
        )
        return default_title
    if not q.topic:
        logger.info(
            "QuestionReview id=%s has empty topic — rendering fallback",
            q.id,
        )
        return default_title
    return q.topic


class DashboardStatsResponse(BaseModel):
    generated_questions: int
    documents: int
    validated_questions: int
    exams: int


class DashboardActivityItem(BaseModel):
    id: str
    type: ActivityType
    title: str
    timestamp: datetime
    metadata: Optional[dict] = None


class DashboardActivityResponse(BaseModel):
    activities: list[DashboardActivityItem]


@router.get("/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    institution_id = current_user.institution_id

    if not institution_id:
        logger.info(
            "Dashboard stats requested by user_id=%s without institution — "
            "returning zeros",
            current_user.id,
        )
        return DashboardStatsResponse(
            generated_questions=0, documents=0, validated_questions=0, exams=0
        )

    generated = (
        db.query(QuestionReview)
        .filter(QuestionReview.institution_id == institution_id)
        .count()
    )

    docs = db.query(Document).filter(Document.institution_id == institution_id).count()

    validated = (
        db.query(QuestionReview)
        .filter(
            QuestionReview.institution_id == institution_id,
            QuestionReview.review_status == ReviewStatus.APPROVED.value,
        )
        .count()
    )

    exams = db.query(Exam).filter(Exam.institution_id == institution_id).count()

    return DashboardStatsResponse(
        generated_questions=generated,
        documents=docs,
        validated_questions=validated,
        exams=exams,
    )


@router.get("/activity", response_model=DashboardActivityResponse)
def get_dashboard_activity(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Top-25-Glance der eigenen Aktivitäten.

    Per-User scoped: alle 7 Quellen filtern auf
    ``AuditLog.user_id == current_user.id`` (bzw.
    ``QuestionReview.created_by == current_user.id`` für die
    QuestionReview-Quelle). Wer cross-User-Events sehen will, nutzt
    ``GET /api/v1/activity?scope=institution``.
    """
    user_id = current_user.id

    items: list[DashboardActivityItem] = []

    uploaded_logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.user_id == user_id,
            AuditLog.action == "create_document",
            AuditLog.status == "success",
        )
        .order_by(AuditLog.created_at.desc())
        .limit(25)
        .all()
    )
    for log in uploaded_logs:
        if log.created_at:
            title = extract_audit_title(
                log,
                fallback_title=str(log.resource_id),
                preferred_keys=("original_filename", "filename"),
            )
            items.append(
                DashboardActivityItem(
                    id=f"doc_{log.id}",
                    type="document_uploaded",
                    title=title,
                    timestamp=_to_utc(log.created_at),
                )
            )

    questions = (
        db.query(QuestionReview)
        .filter(QuestionReview.created_by == user_id)
        .order_by(QuestionReview.created_at.desc())
        .limit(25)
        .all()
    )
    for q in questions:
        if q.created_at:
            items.append(
                DashboardActivityItem(
                    id=f"qgen_{q.id}",
                    type="questions_generated",
                    title=q.topic or str(q.id),
                    timestamp=_to_utc(q.created_at),
                )
            )

    qapproved_logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.user_id == user_id,
            AuditLog.action == "approve_question",
            AuditLog.status == "success",
        )
        .order_by(AuditLog.created_at.desc())
        .limit(25)
        .all()
    )
    for log in qapproved_logs:
        if log.created_at:
            title = _resolve_review_topic(db, log, default_title="–")
            items.append(
                DashboardActivityItem(
                    id=f"qapproved_{log.id}",
                    type="question_approved",
                    title=title,
                    timestamp=_to_utc(log.created_at),
                )
            )

    exam_logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.user_id == user_id,
            AuditLog.action == "create_exam",
            AuditLog.status == "success",
        )
        .order_by(AuditLog.created_at.desc())
        .limit(25)
        .all()
    )
    for log in exam_logs:
        if log.created_at:
            title = extract_audit_title(
                log,
                fallback_title=str(log.resource_id),
                preferred_keys=("title",),
            )
            items.append(
                DashboardActivityItem(
                    id=f"exam_{log.id}",
                    type="exam_created",
                    title=title,
                    timestamp=_to_utc(log.created_at),
                )
            )

    qrejected_logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.user_id == user_id,
            AuditLog.action == "reject_question",
            AuditLog.status == "success",
        )
        .order_by(AuditLog.created_at.desc())
        .limit(25)
        .all()
    )
    for log in qrejected_logs:
        if log.created_at:
            title = _resolve_review_topic(db, log, default_title="–")
            items.append(
                DashboardActivityItem(
                    id=f"qrejected_{log.id}",
                    type="question_rejected",
                    title=title,
                    timestamp=_to_utc(log.created_at),
                )
            )

    exam_deleted_logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.user_id == user_id,
            AuditLog.action == "delete_exam",
            AuditLog.status == "success",
        )
        .order_by(AuditLog.created_at.desc())
        .limit(25)
        .all()
    )
    for log in exam_deleted_logs:
        if log.created_at:
            title = extract_audit_title(
                log,
                fallback_title=str(log.resource_id),
                preferred_keys=("title",),
            )
            items.append(
                DashboardActivityItem(
                    id=f"examdeleted_{log.id}",
                    type="exam_deleted",
                    title=title,
                    timestamp=_to_utc(log.created_at),
                )
            )

    deleted_logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.user_id == user_id,
            AuditLog.action == "delete_document",
            AuditLog.status == "success",
        )
        .order_by(AuditLog.created_at.desc())
        .limit(25)
        .all()
    )
    for log in deleted_logs:
        if log.created_at:
            title = extract_audit_title(
                log,
                fallback_title=str(log.resource_id),
                preferred_keys=("original_filename", "filename"),
            )
            items.append(
                DashboardActivityItem(
                    id=f"docdeleted_{log.id}",
                    type="document_deleted",
                    title=title,
                    timestamp=_to_utc(log.created_at),
                )
            )

    items.sort(key=lambda x: x.timestamp, reverse=True)
    return DashboardActivityResponse(activities=items[:25])
