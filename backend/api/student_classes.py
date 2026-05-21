"""Student-Classes API — CRUD + Mitglieder-Verwaltung (TF-336).

Endpoints:

* ``GET    /api/v1/student-classes`` — Liste mit Member-Count
* ``POST   /api/v1/student-classes`` — Klasse anlegen
* ``GET    /api/v1/student-classes/{id}`` — Detail inkl. Mitglieder
* ``GET    /api/v1/student-classes/{id}/stats`` — Cross-Exam-Verlauf
* ``PATCH  /api/v1/student-classes/{id}`` — umbenennen
* ``DELETE /api/v1/student-classes/{id}`` — löschen
* ``POST   /api/v1/student-classes/{id}/members`` — Mitglied hinzufügen
* ``DELETE /api/v1/student-classes/{id}/members/{student_id}`` — entfernen

Multi-Tenancy: jeder Endpoint filtert auf
``current_user.institution_id``. Cross-Institution-Lookups liefern 404
(nicht 403), um die Existenz fremder Klassen nicht zu leaken.

RBAC: ``students:manage`` für alle Endpoints — gemäss Spec ist die
Verwaltung von Studierenden- und Klassenstammdaten Admin-Aufgabe.

Note: dieses Modul lässt ``from __future__ import annotations`` bewusst
weg — Pydantic v2 + FastAPI brauchen reale Typen zur Laufzeit für
OpenAPI-Schema und Body-Parsing.
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
    """Liste aller Klassen der Institution mit Mitglieder-Anzahl.

    Default 200 / Max 1000 verhindert OOM bei Institutionen mit vielen
    Klassen; das Frontend paginiert ab dort.
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
    """Klasse anlegen. 409 bei Namens-Konflikt in derselben Institution."""
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
    """Klassen-Detail mit Mitglieder-Liste."""
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
    """Klasse umbenennen. 409 bei Namens-Kollision."""
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
    """Klasse löschen — Mitgliedschaften werden via CASCADE entfernt.

    Studierende selbst bleiben erhalten (sie können in andere Klassen
    eingeordnet sein und referenzieren auch Submissions).
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
    """Studi der Klasse zuordnen.

    Idempotent: ist der Studi schon Mitglied, liefert der Endpoint 200
    statt 201 wäre das technisch sauberer — wir reagieren stattdessen
    mit 409, damit das Frontend den Konflikt explizit anzeigen kann.
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
    """Mitgliedschaft entfernen. 404, wenn nicht vorhanden."""
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
# Cross-Exam-Verlauf (TF-336 Subarea B)
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
    """Cross-Exam-Verlauf einer Klasse — Spec 7.5 / 8.

    Aggregate werden on-the-fly aus ``submissions`` + ``grades``
    gerechnet. Die Mitgliedschaft ist eine As-of-Now-Sicht — Studis,
    die zwischenzeitlich aus der Klasse entfernt wurden, fliessen
    nicht in die Aggregate ein.

    Tier-Gate: nur Enterprise. 402 mit ``error_code`` für i18n-Banner.
    """
    assert_class_history_allowed(current_user)
    # 404 bevor wir den Service bemühen — auch hier kein 403, um
    # Cross-Tenant-Existenz nicht zu leaken.
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
