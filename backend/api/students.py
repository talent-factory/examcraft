"""Students API — Liste + Verlauf-Statistik (TF-336 Subarea B).

Endpoints:

* ``GET /api/v1/students``                — Stammdaten-Liste mit Filter
* ``GET /api/v1/students/{id}``           — Detail (Klassen, Submission-Count)
* ``GET /api/v1/students/{id}/stats``     — Cross-Exam-Verlauf

Multi-Tenancy: jeder Endpoint filtert auf ``current_user.institution_id``.
RBAC: ``students:manage`` — gemäss Spec ist die Stammdatenpflege
ausschliesslich Admin-Aufgabe.

Note: kein ``from __future__ import annotations`` (FastAPI/Pydantic
brauchen reale Typen für die OpenAPI-Generierung).
"""

import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func as sa_func, or_
from sqlalchemy.orm import Session

from database import get_db
from models.auth import User
from models.exam import Exam
from models.student import Student, StudentClass, StudentClassMembership
from models.submission import Submission
from services.auswertung_quotas import assert_class_history_allowed
from services.statistics_service import StatisticsService
from utils.auth_utils import require_permission


logger = logging.getLogger(__name__)


_STRICT_OUT = ConfigDict(extra="forbid")


router = APIRouter(prefix="/api/v1/students", tags=["Students"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class StudentClassRefOut(BaseModel):
    model_config = _STRICT_OUT

    class_id: int
    class_name: str


class StudentListItemOut(BaseModel):
    model_config = _STRICT_OUT

    id: int
    external_id: str
    display_name: str | None
    submission_count: int
    avg_percentage: float | None
    classes: list[StudentClassRefOut]


class StudentListOut(BaseModel):
    model_config = _STRICT_OUT

    items: list[StudentListItemOut]
    total: int
    limit: int
    offset: int


class StudentDetailOut(BaseModel):
    model_config = _STRICT_OUT

    id: int
    external_id: str
    display_name: str | None
    created_at: datetime
    updated_at: datetime
    submission_count: int
    classes: list[StudentClassRefOut]


class StudentSubmissionRecordOut(BaseModel):
    model_config = _STRICT_OUT

    submission_id: int
    exam_id: int
    exam_title: str
    exam_date: date | None
    percentage: float
    grade_status: str


class TopicAggregateOut(BaseModel):
    model_config = _STRICT_OUT

    topic: str
    points_awarded: float
    points_max: float
    percentage: float


class StudentHistoryStatsOut(BaseModel):
    model_config = _STRICT_OUT

    student_id: int
    external_id: str
    display_name: str | None
    submission_count: int
    avg_percentage: float | None
    submissions: list[StudentSubmissionRecordOut]
    # Bloom levels travel as string keys for JSON; clients cast as needed.
    bloom_mix: dict[str, int]
    topic_heatmap: list[TopicAggregateOut]
    classes: list[StudentClassRefOut]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_student_for_user(*, db: Session, user: User, student_id: int) -> Student:
    student = (
        db.query(Student)
        .filter(
            Student.id == student_id,
            Student.institution_id == user.institution_id,
        )
        .one_or_none()
    )
    if student is None:
        raise HTTPException(status_code=404, detail="Studi nicht gefunden")
    return student


def _classes_for_students(
    db: Session, institution_id: int, student_ids: list[int]
) -> dict[int, list[tuple[int, str]]]:
    """Map student_id → list of ``(class_id, class_name)`` (one query)."""
    if not student_ids:
        return {}
    rows = (
        db.query(StudentClassMembership.student_id, StudentClass.id, StudentClass.name)
        .join(StudentClass, StudentClass.id == StudentClassMembership.class_id)
        .filter(
            StudentClassMembership.student_id.in_(student_ids),
            StudentClass.institution_id == institution_id,
        )
        .all()
    )
    out: dict[int, list[tuple[int, str]]] = {}
    for student_id, class_id, class_name in rows:
        out.setdefault(student_id, []).append((class_id, class_name))
    return out


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=StudentListOut)
async def list_students(
    search: str | None = Query(default=None, max_length=200),
    class_id: int | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_permission("students:manage")),
    db: Session = Depends(get_db),
) -> StudentListOut:
    """Liste der Studis (institutionsbezogen) mit optionalem Suchfilter
    auf ``external_id`` / ``display_name``."""
    base = db.query(Student).filter(
        Student.institution_id == current_user.institution_id
    )
    if search:
        like = f"%{search.strip()}%"
        base = base.filter(
            or_(
                Student.external_id.ilike(like),
                Student.display_name.ilike(like),
            )
        )
    if class_id is not None:
        base = base.join(
            StudentClassMembership,
            StudentClassMembership.student_id == Student.id,
        ).filter(StudentClassMembership.class_id == class_id)

    total = base.with_entities(sa_func.count(Student.id)).scalar() or 0

    students = (
        base.order_by(Student.display_name.nullslast(), Student.external_id)
        .offset(offset)
        .limit(limit)
        .all()
    )
    student_ids = [s.id for s in students]

    submission_rows = (
        db.query(
            Submission.student_id,
            sa_func.count(Submission.id).label("submission_count"),
            sa_func.avg(Submission.percentage).label("avg_percentage"),
        )
        .join(Exam, Exam.id == Submission.exam_id)
        .filter(
            Submission.student_id.in_(student_ids),
            Exam.institution_id == current_user.institution_id,
        )
        .group_by(Submission.student_id)
        .all()
        if student_ids
        else []
    )
    aggs = {
        row.student_id: (int(row.submission_count or 0), float(row.avg_percentage or 0))
        for row in submission_rows
    }
    classes_by_student = _classes_for_students(
        db, current_user.institution_id, student_ids
    )

    items = []
    for s in students:
        sub_count, avg_pct = aggs.get(s.id, (0, None))
        items.append(
            StudentListItemOut(
                id=s.id,
                external_id=s.external_id,
                display_name=s.display_name,
                submission_count=sub_count,
                avg_percentage=avg_pct if sub_count > 0 else None,
                classes=[
                    StudentClassRefOut(class_id=cid, class_name=cname)
                    for cid, cname in classes_by_student.get(s.id, [])
                ],
            )
        )

    return StudentListOut(items=items, total=int(total), limit=limit, offset=offset)


@router.get("/{student_id}", response_model=StudentDetailOut)
async def get_student(
    student_id: int,
    current_user: User = Depends(require_permission("students:manage")),
    db: Session = Depends(get_db),
) -> StudentDetailOut:
    """Detail eines Studis: Klassen + Anzahl Submissions."""
    student = _load_student_for_user(db=db, user=current_user, student_id=student_id)
    submission_count = (
        db.query(sa_func.count(Submission.id))
        .join(Exam, Exam.id == Submission.exam_id)
        .filter(
            Submission.student_id == student_id,
            Exam.institution_id == current_user.institution_id,
        )
        .scalar()
        or 0
    )
    classes_by_student = _classes_for_students(
        db, current_user.institution_id, [student_id]
    )
    return StudentDetailOut(
        id=student.id,
        external_id=student.external_id,
        display_name=student.display_name,
        created_at=student.created_at,
        updated_at=student.updated_at,
        submission_count=int(submission_count),
        classes=[
            StudentClassRefOut(class_id=cid, class_name=cname)
            for cid, cname in classes_by_student.get(student_id, [])
        ],
    )


@router.get("/{student_id}/stats", response_model=StudentHistoryStatsOut)
async def get_student_history(
    student_id: int,
    current_user: User = Depends(require_permission("students:manage")),
    db: Session = Depends(get_db),
) -> StudentHistoryStatsOut:
    """Cross-Exam-Verlauf eines Studis — Spec 7.5 / 8.

    Liefert chronologisch alle Submissions, Bloom-Mix und Topic-Heatmap
    aggregiert über alle Prüfungen der Institution.

    Tier-Gate: nur Enterprise. 402 mit ``error_code`` für i18n-Banner.
    """
    assert_class_history_allowed(current_user)
    _load_student_for_user(db=db, user=current_user, student_id=student_id)

    stats = StatisticsService(db).student_history(
        student_id=student_id, institution_id=current_user.institution_id
    )
    if stats is None:
        raise HTTPException(status_code=404, detail="Studi nicht gefunden")

    return StudentHistoryStatsOut(
        student_id=stats.student_id,
        external_id=stats.external_id,
        display_name=stats.display_name,
        submission_count=stats.submission_count,
        avg_percentage=stats.avg_percentage,
        submissions=[
            StudentSubmissionRecordOut(
                submission_id=r.submission_id,
                exam_id=r.exam_id,
                exam_title=r.exam_title,
                exam_date=r.exam_date,
                percentage=r.percentage,
                grade_status=r.grade_status,
            )
            for r in stats.submissions
        ],
        # Bloom levels round-trip as strings — JSON has no integer keys.
        bloom_mix={str(k): v for k, v in stats.bloom_mix.items()},
        topic_heatmap=[
            TopicAggregateOut(
                topic=t.topic,
                points_awarded=t.points_awarded,
                points_max=t.points_max,
                percentage=t.percentage,
            )
            for t in stats.topic_heatmap
        ],
        classes=[
            StudentClassRefOut(class_id=c.class_id, class_name=c.class_name)
            for c in stats.classes
        ],
    )
