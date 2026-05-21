"""Review-Queue + Grade-Aktionen API (Spec 6.4 / TF-334).

Endpoints:

* ``GET  /api/v1/exams/{exam_id}/review-queue`` — Liste aller offenen
  ``proposed``-Grades für offene Fragen, optional gefiltert.
* ``POST /api/v1/grades/{id}/approve`` — Lehrperson übernimmt Vorschlag.
* ``POST /api/v1/grades/{id}/override`` — Lehrperson überschreibt.
* ``POST /api/v1/grades/bulk-approve`` — Liste oder Konfidenz-Schwelle.

Multi-Tenancy: jede Route filtert über ``Attempt.institution_id`` und
über das Exam zur Institution. RBAC: ``submissions:read`` zum Lesen,
``submissions:grade`` zum Ändern.

Sortierung der Review-Queue: niedrigste Konfidenz zuerst (Spec 6.4 —
"Vorschläge mit niedrigster Konfidenz zuerst, damit Lehrperson dort
ansetzt, wo Claude unsicher ist").

Kein ``from __future__ import annotations``: FastAPI/Pydantic v2
braucht Runtime-Typen für die OpenAPI-Generierung.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from database import get_db
from enums import GradeStatus
from models.auth import User
from models.exam import Exam, ExamQuestion
from models.question_review import QuestionReview
from models.student import Student
from models.submission import (
    Attempt,
    AttemptAnswer,
    Grade,
    Submission,
)
from services.grading_service import (
    GradeNotFoundError,
    GradingService,
)
from utils.auth_utils import require_permission


logger = logging.getLogger(__name__)


_STRICT_OUT = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ReviewQueueItemOut(BaseModel):
    """Eintrag der Review-Queue: alles, was die Lehrperson zur
    Bewertungs-Entscheidung in einem Klick braucht."""

    model_config = _STRICT_OUT

    grade_id: int
    submission_id: int
    student_id: int
    student_external_id: str
    student_display_name: str | None = None
    exam_question_id: int
    question_id: int
    question_text: str
    correct_answer: str | None = None
    explanation: str | None = None
    given_answer: str | None = None
    points_awarded: float
    points_max: float
    confidence: float | None = None
    rationale: str | None = None
    matched_aspects: list[str] = Field(default_factory=list)
    missing_aspects: list[str] = Field(default_factory=list)
    status: GradeStatus


class ReviewQueueOut(BaseModel):
    model_config = _STRICT_OUT

    items: list[ReviewQueueItemOut]
    total: int


class GradeActionOut(BaseModel):
    """Antwort nach approve/override + bulk-approve-Einzeleintrag."""

    model_config = _STRICT_OUT

    id: int
    points_awarded: float
    points_max: float
    status: GradeStatus
    reviewer_id: int | None = None
    reviewer_note: str | None = None
    reviewed_at: datetime | None = None


class OverrideGradeIn(BaseModel):
    """Request-Body für POST /grades/{id}/override."""

    model_config = ConfigDict(extra="forbid")

    points_awarded: float = Field(ge=0)
    reviewer_note: str | None = None


class BulkApproveIn(BaseModel):
    """Request-Body für POST /grades/bulk-approve.

    Genau einer der beiden Filter ist Pflicht. Ohne Validator würde
    eine Lehrperson, die beide Felder leer lässt, gnadenlos *alle*
    proposed-Grades der Prüfung approven — das ist explizit nicht
    der Auto-Approve-Pfad (Spec 6.4 Abgrenzung).
    """

    model_config = ConfigDict(extra="forbid")

    exam_id: int
    confidence_min: float | None = Field(default=None, ge=0, le=1)
    grade_ids: list[int] | None = None

    @model_validator(mode="after")
    def _xor_filters(self) -> "BulkApproveIn":
        has_ids = bool(self.grade_ids)
        has_threshold = self.confidence_min is not None
        if has_ids == has_threshold:
            raise ValueError(
                "bulk-approve braucht genau einen Filter: grade_ids ODER confidence_min"
            )
        return self


class BulkApproveOut(BaseModel):
    model_config = _STRICT_OUT

    approved_count: int
    grade_ids: list[int]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_exam_for_user(*, db: Session, user: User, exam_id: int) -> Exam:
    """Multi-Tenancy-Check; 404 statt 403, damit Tenant A nicht
    erfahren kann, ob exam_id von Tenant B existiert.
    """
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


def _load_grade_for_user(*, db: Session, user: User, grade_id: int) -> Grade:
    """Lädt einen Grade und prüft, dass er zur Institution des Users
    gehört. Walk: Grade -> AttemptAnswer -> Attempt -> institution_id."""
    row = (
        db.query(Grade)
        .join(AttemptAnswer, AttemptAnswer.id == Grade.attempt_answer_id)
        .join(Attempt, Attempt.id == AttemptAnswer.attempt_id)
        .filter(
            Grade.id == grade_id,
            Attempt.institution_id == user.institution_id,
        )
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Grade nicht gefunden")
    return row


def _grade_to_action_out(grade: Grade) -> GradeActionOut:
    return GradeActionOut(
        id=grade.id,
        points_awarded=grade.points_awarded,
        points_max=grade.points_max,
        status=GradeStatus(grade.status),
        reviewer_id=grade.reviewer_id,
        reviewer_note=grade.reviewer_note,
        reviewed_at=grade.reviewed_at,
    )


# ---------------------------------------------------------------------------
# Review-Queue
# ---------------------------------------------------------------------------


router_grades = APIRouter(prefix="/api/v1/grades", tags=["Grades"])
router_exams_review_queue = APIRouter(prefix="/api/v1/exams", tags=["Grades"])


@router_exams_review_queue.get("/{exam_id}/review-queue", response_model=ReviewQueueOut)
async def get_review_queue(
    exam_id: int,
    confidence_min: float | None = Query(default=None, ge=0, le=1),
    confidence_max: float | None = Query(default=None, ge=0, le=1),
    question_id: int | None = Query(default=None),
    student_id: int | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_permission("submissions:read")),
    db: Session = Depends(get_db),
) -> ReviewQueueOut:
    """Liste aller ``status='proposed'``-Grades für ``open_ended``-
    Antworten dieser Prüfung, sortiert nach Konfidenz aufsteigend.

    Konfidenz ``NULL`` (Stub-Outcomes ohne LLM-Bewertung) zählt als
    "niedrigste Konfidenz" und wird ans Ende sortiert? Nein — andersrum:
    NULL bedeutet "niemand hat sich Gedanken gemacht", also vorne.
    Postgres ``NULLS FIRST`` mit Default-ASC liefert genau das.
    """
    _ensure_exam_for_user(db=db, user=current_user, exam_id=exam_id)
    if (
        confidence_min is not None
        and confidence_max is not None
        and confidence_min > confidence_max
    ):
        raise HTTPException(
            status_code=400,
            detail="confidence_min darf nicht grösser als confidence_max sein",
        )

    query = (
        db.query(
            Grade,
            AttemptAnswer,
            Attempt,
            Submission,
            Student,
            ExamQuestion,
            QuestionReview,
        )
        .join(AttemptAnswer, AttemptAnswer.id == Grade.attempt_answer_id)
        .join(Attempt, Attempt.id == AttemptAnswer.attempt_id)
        .join(Submission, Submission.id == Attempt.submission_id)
        .join(Student, Student.id == Submission.student_id)
        .join(ExamQuestion, ExamQuestion.id == AttemptAnswer.exam_question_id)
        .join(QuestionReview, QuestionReview.id == ExamQuestion.question_id)
        .filter(
            Submission.exam_id == exam_id,
            Attempt.institution_id == current_user.institution_id,
            Grade.status == GradeStatus.PROPOSED.value,
            QuestionReview.question_type == "open_ended",
        )
    )

    if confidence_min is not None:
        query = query.filter(Grade.llm_confidence >= confidence_min)
    if confidence_max is not None:
        query = query.filter(Grade.llm_confidence <= confidence_max)
    if question_id is not None:
        query = query.filter(ExamQuestion.id == question_id)
    if student_id is not None:
        query = query.filter(Student.id == student_id)

    total = query.with_entities(Grade.id).count()
    rows = (
        query.order_by(Grade.llm_confidence.asc().nullsfirst(), Grade.id)
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = [
        ReviewQueueItemOut(
            grade_id=g.id,
            submission_id=submission.id,
            student_id=student.id,
            student_external_id=student.external_id,
            student_display_name=student.display_name,
            exam_question_id=eq.id,
            question_id=qr.id,
            question_text=qr.question_text,
            correct_answer=qr.correct_answer,
            explanation=qr.explanation,
            given_answer=ans.given_answer,
            points_awarded=g.points_awarded,
            points_max=g.points_max,
            confidence=g.llm_confidence,
            rationale=g.llm_rationale,
            matched_aspects=list(g.llm_matched_aspects or []),
            missing_aspects=list(g.llm_missing_aspects or []),
            status=GradeStatus(g.status),
        )
        for (g, ans, _attempt, submission, student, eq, qr) in rows
    ]
    return ReviewQueueOut(items=items, total=total)


# ---------------------------------------------------------------------------
# Single-grade actions
# ---------------------------------------------------------------------------


@router_grades.post("/{grade_id}/approve", response_model=GradeActionOut)
async def approve_grade(
    grade_id: int,
    current_user: User = Depends(require_permission("submissions:grade")),
    db: Session = Depends(get_db),
) -> GradeActionOut:
    """Lehrperson übernimmt LLM-Vorschlag → ``status=approved``."""
    _load_grade_for_user(db=db, user=current_user, grade_id=grade_id)
    try:
        grade = GradingService(db).approve_grade(
            grade_id=grade_id, reviewer_id=current_user.id
        )
    except GradeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    db.refresh(grade)
    return _grade_to_action_out(grade)


@router_grades.post("/{grade_id}/override", response_model=GradeActionOut)
async def override_grade(
    grade_id: int,
    payload: OverrideGradeIn,
    current_user: User = Depends(require_permission("submissions:grade")),
    db: Session = Depends(get_db),
) -> GradeActionOut:
    """Lehrperson überschreibt → ``status=manual_override``.

    Funktioniert auf jedem Grade-Typ (auch MC/W-F), siehe Spec 7.3 —
    "MC/W-F-Antworten haben einen 'Manuell überstimmen'-Button".
    """
    _load_grade_for_user(db=db, user=current_user, grade_id=grade_id)
    try:
        grade = GradingService(db).override_grade(
            grade_id=grade_id,
            reviewer_id=current_user.id,
            points_awarded=payload.points_awarded,
            reviewer_note=payload.reviewer_note,
        )
    except GradeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    db.refresh(grade)
    return _grade_to_action_out(grade)


@router_grades.post("/bulk-approve", response_model=BulkApproveOut)
async def bulk_approve(
    payload: BulkApproveIn,
    current_user: User = Depends(require_permission("submissions:grade")),
    db: Session = Depends(get_db),
) -> BulkApproveOut:
    """Bulk-Approve.

    Multi-Tenancy: ``institution_id=current_user.institution_id`` ist
    Pflicht-Filter im Service — Tenant A kann selbst mit gefälschten
    Grade-IDs keine Grades von Tenant B approven.
    """
    _ensure_exam_for_user(db=db, user=current_user, exam_id=payload.exam_id)
    try:
        approved = GradingService(db).bulk_approve(
            reviewer_id=current_user.id,
            institution_id=current_user.institution_id,
            exam_id=payload.exam_id,
            confidence_min=payload.confidence_min,
            grade_ids=payload.grade_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return BulkApproveOut(
        approved_count=len(approved),
        grade_ids=[g.id for g in approved],
    )


# ---------------------------------------------------------------------------
# Re-Grading-Trigger (Spec 6.6)
# ---------------------------------------------------------------------------


class RegradeQuestionOut(BaseModel):
    model_config = _STRICT_OUT

    exam_question_id: int
    regraded_count: int


@router_exams_review_queue.post(
    "/{exam_id}/questions/{exam_question_id}/regrade",
    response_model=RegradeQuestionOut,
)
async def regrade_question(
    exam_id: int,
    exam_question_id: int,
    current_user: User = Depends(require_permission("submissions:grade")),
    db: Session = Depends(get_db),
) -> RegradeQuestionOut:
    """Setzt alle proposed/approved-Grades der Frage zurück und re-gradet.

    ``manual_override`` bleibt unverändert (Spec 6.6). Multi-Tenant
    via Exam-Lookup, der die institution_id prüft, plus Verify, dass
    die ExamQuestion zu diesem Exam gehört.
    """
    _ensure_exam_for_user(db=db, user=current_user, exam_id=exam_id)

    eq_row: tuple[Any, ...] | None = (
        db.query(ExamQuestion.id)
        .filter(ExamQuestion.id == exam_question_id, ExamQuestion.exam_id == exam_id)
        .one_or_none()
    )
    if eq_row is None:
        raise HTTPException(status_code=404, detail="Frage nicht gefunden")

    try:
        count = GradingService(db).regrade_after_correct_answer_update(
            exam_question_id=exam_question_id,
            triggered_by=current_user.id,
        )
        db.commit()
    except Exception:
        logger.exception(
            "regrade_question failed: exam_id=%s exam_question_id=%s",
            exam_id,
            exam_question_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Re-Grading fehlgeschlagen — siehe Server-Logs.",
        )
    return RegradeQuestionOut(exam_question_id=exam_question_id, regraded_count=count)
