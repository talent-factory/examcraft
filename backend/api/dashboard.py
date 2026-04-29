# core/backend/api/dashboard.py
"""Dashboard API – Statistiken und Aktivitäten (TF-319)"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

import json

from database import get_db
from models.auth import AuditLog, User
from models.document import Document
from models.exam import Exam
from models.question_review import QuestionReview, ReviewStatus
from utils.auth_utils import get_current_active_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _to_utc(dt: datetime) -> datetime:
    """Normalize datetime to UTC (handles both naive and aware)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class DashboardStatsResponse(BaseModel):
    generated_questions: int
    documents: int
    validated_questions: int
    exams: int


class ActivityItem(BaseModel):
    id: str
    type: str
    title: str
    timestamp: datetime
    metadata: Optional[dict] = None


class DashboardActivityResponse(BaseModel):
    activities: list[ActivityItem]


@router.get("/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    institution_id = current_user.institution_id

    if not institution_id:
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
    institution_id = current_user.institution_id

    if not institution_id:
        return DashboardActivityResponse(activities=[])

    items: list[ActivityItem] = []

    # 1. Dokumente hochgeladen (aus AuditLog, damit gelöschte Dokumente sichtbar bleiben)
    uploaded_logs = (
        db.query(AuditLog)
        .join(User, AuditLog.user_id == User.id)
        .filter(
            User.institution_id == institution_id,
            AuditLog.action == "create_document",
            AuditLog.status == "success",
        )
        .order_by(AuditLog.created_at.desc())
        .limit(25)
        .all()
    )
    for log in uploaded_logs:
        if log.created_at:
            title = str(log.resource_id)
            if log.additional_data:
                try:
                    data = json.loads(log.additional_data)
                    title = (
                        data.get("original_filename") or data.get("filename") or title
                    )
                except (json.JSONDecodeError, AttributeError):
                    pass
            items.append(
                ActivityItem(
                    id=f"doc_{log.id}",
                    type="document_uploaded",
                    title=title,
                    timestamp=_to_utc(log.created_at),
                )
            )

    # 2. Fragen generiert (QuestionReview-Tabelle, nach Erstellungsdatum)
    questions = (
        db.query(QuestionReview)
        .filter(QuestionReview.institution_id == institution_id)
        .order_by(QuestionReview.created_at.desc())
        .limit(25)
        .all()
    )
    for q in questions:
        if q.created_at:
            items.append(
                ActivityItem(
                    id=f"qgen_{q.id}",
                    type="questions_generated",
                    title=q.topic or str(q.id),
                    timestamp=_to_utc(q.created_at),
                )
            )

    # 3. Fragen validiert (aus AuditLog, damit gelöschte Fragen sichtbar bleiben)
    qapproved_logs = (
        db.query(AuditLog)
        .join(User, AuditLog.user_id == User.id)
        .filter(
            User.institution_id == institution_id,
            AuditLog.action == "approve_question",
            AuditLog.status == "success",
        )
        .order_by(AuditLog.created_at.desc())
        .limit(25)
        .all()
    )
    for log in qapproved_logs:
        if log.created_at:
            title = str(log.resource_id)
            if log.additional_data:
                try:
                    data = json.loads(log.additional_data)
                    title = data.get("topic") or title
                except (json.JSONDecodeError, AttributeError):
                    pass
            if title == str(log.resource_id):
                try:
                    q = (
                        db.query(QuestionReview)
                        .filter(QuestionReview.id == int(log.resource_id))
                        .first()
                    )
                    title = q.topic if (q and q.topic) else "–"
                except (ValueError, TypeError):
                    title = "–"
            items.append(
                ActivityItem(
                    id=f"qapproved_{log.id}",
                    type="question_approved",
                    title=title,
                    timestamp=_to_utc(log.created_at),
                )
            )

    # 4. Prüfungen erstellt (aus AuditLog, damit gelöschte Prüfungen sichtbar bleiben)
    exam_logs = (
        db.query(AuditLog)
        .join(User, AuditLog.user_id == User.id)
        .filter(
            User.institution_id == institution_id,
            AuditLog.action == "create_exam",
            AuditLog.status == "success",
        )
        .order_by(AuditLog.created_at.desc())
        .limit(25)
        .all()
    )
    for log in exam_logs:
        if log.created_at:
            title = str(log.resource_id)
            if log.additional_data:
                try:
                    data = json.loads(log.additional_data)
                    title = data.get("title") or title
                except (json.JSONDecodeError, AttributeError):
                    pass
            items.append(
                ActivityItem(
                    id=f"exam_{log.id}",
                    type="exam_created",
                    title=title,
                    timestamp=_to_utc(log.created_at),
                )
            )

    # 5. Fragen abgelehnt (aus AuditLog)
    qrejected_logs = (
        db.query(AuditLog)
        .join(User, AuditLog.user_id == User.id)
        .filter(
            User.institution_id == institution_id,
            AuditLog.action == "reject_question",
            AuditLog.status == "success",
        )
        .order_by(AuditLog.created_at.desc())
        .limit(25)
        .all()
    )
    for log in qrejected_logs:
        if log.created_at:
            title = str(log.resource_id)
            if log.additional_data:
                try:
                    data = json.loads(log.additional_data)
                    title = data.get("topic") or title
                except (json.JSONDecodeError, AttributeError):
                    pass
            if title == str(log.resource_id):
                try:
                    q = (
                        db.query(QuestionReview)
                        .filter(QuestionReview.id == int(log.resource_id))
                        .first()
                    )
                    title = q.topic if (q and q.topic) else "–"
                except (ValueError, TypeError):
                    title = "–"
            items.append(
                ActivityItem(
                    id=f"qrejected_{log.id}",
                    type="question_rejected",
                    title=title,
                    timestamp=_to_utc(log.created_at),
                )
            )

    # 6. Prüfungen gelöscht (aus AuditLog)
    exam_deleted_logs = (
        db.query(AuditLog)
        .join(User, AuditLog.user_id == User.id)
        .filter(
            User.institution_id == institution_id,
            AuditLog.action == "delete_exam",
            AuditLog.status == "success",
        )
        .order_by(AuditLog.created_at.desc())
        .limit(25)
        .all()
    )
    for log in exam_deleted_logs:
        if log.created_at:
            title = str(log.resource_id)
            if log.additional_data:
                try:
                    data = json.loads(log.additional_data)
                    title = data.get("title") or title
                except (json.JSONDecodeError, AttributeError):
                    pass
            items.append(
                ActivityItem(
                    id=f"examdeleted_{log.id}",
                    type="exam_deleted",
                    title=title,
                    timestamp=_to_utc(log.created_at),
                )
            )

    # 7. Dokumente gelöscht (aus AuditLog, gefiltert über User.institution_id)
    deleted_logs = (
        db.query(AuditLog)
        .join(User, AuditLog.user_id == User.id)
        .filter(
            User.institution_id == institution_id,
            AuditLog.action == "delete_document",
            AuditLog.status == "success",
        )
        .order_by(AuditLog.created_at.desc())
        .limit(25)
        .all()
    )
    for log in deleted_logs:
        if log.created_at:
            title = str(log.resource_id)
            if log.additional_data:
                try:
                    data = json.loads(log.additional_data)
                    title = (
                        data.get("original_filename") or data.get("filename") or title
                    )
                except (json.JSONDecodeError, AttributeError):
                    pass
            items.append(
                ActivityItem(
                    id=f"docdeleted_{log.id}",
                    type="document_deleted",
                    title=title,
                    timestamp=_to_utc(log.created_at),
                )
            )

    items.sort(key=lambda x: x.timestamp, reverse=True)
    return DashboardActivityResponse(activities=items[:25])
