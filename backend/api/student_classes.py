"""Student-Classes API — CRUD + member management (TF-336).

Endpoints:

* ``GET    /api/v1/student-classes`` — list with member count
* ``POST   /api/v1/student-classes`` — create a class
* ``GET    /api/v1/student-classes/{id}`` — detail incl. members
* ``GET    /api/v1/student-classes/{id}/stats`` — cross-exam history
* ``PATCH  /api/v1/student-classes/{id}`` — rename
* ``DELETE /api/v1/student-classes/{id}`` — delete
* ``POST   /api/v1/student-classes/{id}/members`` — add a member
* ``DELETE /api/v1/student-classes/{id}/members/{student_id}`` — remove

Multi-tenancy: every endpoint filters on
``current_user.institution_id``. Cross-institution lookups return 404
(not 403), so as not to leak the existence of foreign classes.

RBAC: ``students:manage`` for all endpoints — per spec, managing student
and class master data is an admin task.

Note: this module deliberately omits ``from __future__ import
annotations`` — Pydantic v2 + FastAPI need real runtime types for
OpenAPI schema generation and body parsing.
"""

import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func as sa_func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.auth import User
from models.student import Student, StudentClass, StudentClassMembership
from services.auswertung_quotas import assert_class_history_allowed
from services.statistics_service import StatisticsService
from utils.auth_utils import require_permission


logger = logging.getLogger(__name__)


_STRICT_OUT = ConfigDict(extra="forbid")


router = APIRouter(prefix="/api/v1/student-classes", tags=["StudentClasses"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class StudentClassOut(BaseModel):
    model_config = _STRICT_OUT

    id: int
    name: str
    member_count: int
    created_at: datetime
    updated_at: datetime


class StudentClassListOut(BaseModel):
    model_config = _STRICT_OUT

    items: list[StudentClassOut]
    total: int


class StudentRefOut(BaseModel):
    model_config = _STRICT_OUT

    id: int
    external_id: str
    display_name: str | None = None


class StudentClassDetailOut(BaseModel):
    model_config = _STRICT_OUT

    id: int
    name: str
    member_count: int
    created_at: datetime
    updated_at: datetime
    members: list[StudentRefOut]


class StudentClassCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)


class StudentClassUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)


class MemberAddIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: int = Field(gt=0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_class_for_user(*, db: Session, user: User, class_id: int) -> StudentClass:
    """Load a StudentClass for the current institution; 404 otherwise.

    404 (not 403) is intentional: revealing existence-but-no-access leaks
    information about other tenants.
    """
    student_class = (
        db.query(StudentClass)
        .filter(
            StudentClass.id == class_id,
            StudentClass.institution_id == user.institution_id,
        )
        .one_or_none()
    )
    if student_class is None:
        raise HTTPException(status_code=404, detail="Klasse nicht gefunden")
    return student_class


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


def _to_summary_out(student_class: StudentClass, member_count: int) -> StudentClassOut:
    return StudentClassOut(
        id=student_class.id,
        name=student_class.name,
        member_count=member_count,
        created_at=student_class.created_at,
        updated_at=student_class.updated_at,
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.get("", response_model=StudentClassListOut)
async def list_student_classes(
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_permission("students:manage")),
    db: Session = Depends(get_db),
) -> StudentClassListOut:
    """List all classes of the institution with member count.

    Default 200 / max 1000 prevents OOM for institutions with many
    classes; the frontend paginates from there.
    """
    base = db.query(StudentClass).filter(
        StudentClass.institution_id == current_user.institution_id
    )
    total = base.with_entities(sa_func.count(StudentClass.id)).scalar() or 0

    rows = (
        db.query(
            StudentClass,
            sa_func.count(StudentClassMembership.id).label("member_count"),
        )
        .outerjoin(
            StudentClassMembership,
            StudentClassMembership.class_id == StudentClass.id,
        )
        .filter(StudentClass.institution_id == current_user.institution_id)
        .group_by(StudentClass.id)
        .order_by(StudentClass.name)
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = [_to_summary_out(cls, int(member_count)) for cls, member_count in rows]
    return StudentClassListOut(items=items, total=int(total))


@router.post("", response_model=StudentClassOut, status_code=status.HTTP_201_CREATED)
async def create_student_class(
    body: StudentClassCreateIn,
    current_user: User = Depends(require_permission("students:manage")),
    db: Session = Depends(get_db),
) -> StudentClassOut:
    """Create a class. 409 on a name conflict within the same institution."""
    student_class = StudentClass(
        institution_id=current_user.institution_id,
        name=body.name,
    )
    db.add(student_class)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Klasse mit Namen '{body.name}' existiert bereits",
        ) from exc
    db.refresh(student_class)
    return _to_summary_out(student_class, member_count=0)


@router.get("/{class_id}", response_model=StudentClassDetailOut)
async def get_student_class(
    class_id: int,
    current_user: User = Depends(require_permission("students:manage")),
    db: Session = Depends(get_db),
) -> StudentClassDetailOut:
    """Class detail with the member list."""
    student_class = (
        db.query(StudentClass)
        .options(
            joinedload(StudentClass.memberships).joinedload(
                StudentClassMembership.student
            )
        )
        .filter(
            StudentClass.id == class_id,
            StudentClass.institution_id == current_user.institution_id,
        )
        .one_or_none()
    )
    if student_class is None:
        raise HTTPException(status_code=404, detail="Klasse nicht gefunden")

    members = sorted(
        (
            StudentRefOut(
                id=m.student.id,
                external_id=m.student.external_id,
                display_name=m.student.display_name,
            )
            for m in student_class.memberships
            if m.student is not None
        ),
        key=lambda m: (m.display_name or "", m.external_id),
    )
    return StudentClassDetailOut(
        id=student_class.id,
        name=student_class.name,
        member_count=len(members),
        created_at=student_class.created_at,
        updated_at=student_class.updated_at,
        members=members,
    )


@router.patch("/{class_id}", response_model=StudentClassOut)
async def update_student_class(
    class_id: int,
    body: StudentClassUpdateIn,
    current_user: User = Depends(require_permission("students:manage")),
    db: Session = Depends(get_db),
) -> StudentClassOut:
    """Rename a class. 409 on a name collision."""
    student_class = _load_class_for_user(db=db, user=current_user, class_id=class_id)
    student_class.name = body.name
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Klasse mit Namen '{body.name}' existiert bereits",
        ) from exc
    db.refresh(student_class)
    member_count = (
        db.query(sa_func.count(StudentClassMembership.id))
        .filter(StudentClassMembership.class_id == student_class.id)
        .scalar()
        or 0
    )
    return _to_summary_out(student_class, int(member_count))


@router.delete("/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student_class(
    class_id: int,
    current_user: User = Depends(require_permission("students:manage")),
    db: Session = Depends(get_db),
) -> Response:
    """Delete a class — memberships are removed via CASCADE.

    Students themselves are retained (they may be enrolled in other
    classes and also reference submissions).
    """
    student_class = _load_class_for_user(db=db, user=current_user, class_id=class_id)
    db.delete(student_class)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------


@router.post(
    "/{class_id}/members",
    response_model=StudentRefOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    class_id: int,
    body: MemberAddIn,
    current_user: User = Depends(require_permission("students:manage")),
    db: Session = Depends(get_db),
) -> StudentRefOut:
    """Assign a student to the class.

    Idempotent would technically be cleaner: if the student is already a
    member, return 200 instead of 201 — we instead respond with 409, so
    the frontend can explicitly surface the conflict.
    """
    student_class = _load_class_for_user(db=db, user=current_user, class_id=class_id)
    student = _load_student_for_user(
        db=db, user=current_user, student_id=body.student_id
    )

    membership = StudentClassMembership(
        student_id=student.id, class_id=student_class.id
    )
    db.add(membership)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Studi ist bereits Mitglied dieser Klasse",
        ) from exc
    return StudentRefOut(
        id=student.id,
        external_id=student.external_id,
        display_name=student.display_name,
    )


@router.delete(
    "/{class_id}/members/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    class_id: int,
    student_id: int,
    current_user: User = Depends(require_permission("students:manage")),
    db: Session = Depends(get_db),
) -> Response:
    """Remove a membership. 404 if not present."""
    student_class = _load_class_for_user(db=db, user=current_user, class_id=class_id)
    membership = (
        db.query(StudentClassMembership)
        .filter(
            StudentClassMembership.class_id == student_class.id,
            StudentClassMembership.student_id == student_id,
        )
        .one_or_none()
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Mitgliedschaft nicht gefunden")
    db.delete(membership)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Cross-exam history (TF-336 Subarea B)
# ---------------------------------------------------------------------------


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


class ClassMemberPerformanceOut(BaseModel):
    model_config = _STRICT_OUT

    student_id: int
    external_id: str
    display_name: str | None
    submission_count: int
    avg_percentage: float | None
    submissions: list[StudentSubmissionRecordOut]


class ClassExamAggregateOut(BaseModel):
    model_config = _STRICT_OUT

    exam_id: int
    exam_title: str
    exam_date: date | None
    submission_count: int
    avg_percentage: float | None
    pass_rate: float | None


class ClassHistoryStatsOut(BaseModel):
    model_config = _STRICT_OUT

    class_id: int
    class_name: str
    member_count: int
    members: list[ClassMemberPerformanceOut]
    exam_aggregates: list[ClassExamAggregateOut]
    topic_coverage: list[TopicAggregateOut]


@router.get("/{class_id}/stats", response_model=ClassHistoryStatsOut)
async def get_class_history(
    class_id: int,
    current_user: User = Depends(require_permission("students:manage")),
    db: Session = Depends(get_db),
) -> ClassHistoryStatsOut:
    """Cross-exam history of a class — spec 7.5 / 8.

    Aggregates are computed on-the-fly from ``submissions`` + ``grades``.
    Membership is an as-of-now view — students who have since been
    removed from the class are not included in the aggregates.

    Tier gate: Enterprise only. 402 with ``error_code`` for the i18n banner.
    """
    assert_class_history_allowed(current_user)
    # 404 before we bother the service — again no 403, so as not to
    # leak cross-tenant existence.
    _load_class_for_user(db=db, user=current_user, class_id=class_id)

    stats = StatisticsService(db).class_history(
        class_id=class_id, institution_id=current_user.institution_id
    )
    if stats is None:
        # Should not happen — _load_class_for_user already verified.
        raise HTTPException(status_code=404, detail="Klasse nicht gefunden")

    return ClassHistoryStatsOut(
        class_id=stats.class_id,
        class_name=stats.class_name,
        member_count=stats.member_count,
        members=[
            ClassMemberPerformanceOut(
                student_id=m.student_id,
                external_id=m.external_id,
                display_name=m.display_name,
                submission_count=m.submission_count,
                avg_percentage=m.avg_percentage,
                submissions=[
                    StudentSubmissionRecordOut(
                        submission_id=r.submission_id,
                        exam_id=r.exam_id,
                        exam_title=r.exam_title,
                        exam_date=r.exam_date,
                        percentage=r.percentage,
                        grade_status=r.grade_status,
                    )
                    for r in m.submissions
                ],
            )
            for m in stats.members
        ],
        exam_aggregates=[
            ClassExamAggregateOut(
                exam_id=a.exam_id,
                exam_title=a.exam_title,
                exam_date=a.exam_date,
                submission_count=a.submission_count,
                avg_percentage=a.avg_percentage,
                pass_rate=a.pass_rate,
            )
            for a in stats.exam_aggregates
        ],
        topic_coverage=[
            TopicAggregateOut(
                topic=t.topic,
                points_awarded=t.points_awarded,
                points_max=t.points_max,
                percentage=t.percentage,
            )
            for t in stats.topic_coverage
        ],
    )
