"""
Exam Composer API Endpoints for ExamCraft AI
CRUD, question management, auto-fill, finalize, and export.
"""

from typing import List, Optional, Union
from datetime import date, datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func as sa_func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.exam import Exam, ExamQuestion, ExamStatus
from models.auth import User
from models.question_review import QuestionReview, ReviewStatus
from services.translation_service import t, get_request_locale
from utils.auth_utils import require_permission
from utils.tenant_utils import TenantFilter, get_tenant_context
from services.point_utils import suggest_points
from services.exam_export_service import (
    MarkdownExporter,
    JsonExporter,
    MoodleXmlExporter,
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/exams", tags=["Exam Composer"])


def _to_utc(dt: datetime) -> datetime:
    """Normalise a datetime to UTC, treating naive datetimes as UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# --- Pydantic Schemas ---


class ExamCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    course: Optional[str] = Field(None, max_length=200)
    exam_date: Optional[date] = None
    time_limit_minutes: Optional[int] = Field(None, ge=1)
    allowed_aids: Optional[str] = None
    instructions: Optional[str] = None
    passing_percentage: float = Field(50.0, ge=0, le=100)
    language: str = Field("de", pattern="^(de|en)$")


class ExamUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    course: Optional[str] = Field(None, max_length=200)
    exam_date: Optional[date] = None
    time_limit_minutes: Optional[int] = Field(None, ge=1)
    allowed_aids: Optional[str] = None
    instructions: Optional[str] = None
    passing_percentage: Optional[float] = Field(None, ge=0, le=100)
    language: Optional[str] = Field(None, pattern="^(de|en)$")
    updated_at: datetime = Field(..., description="For optimistic locking")


class ExamQuestionOut(BaseModel):
    id: int
    question_id: int
    position: int
    points: float
    section: Optional[str]
    question_text: str
    question_type: str
    difficulty: str
    topic: str
    bloom_level: Optional[int]
    review_status: str
    options: Optional[list] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None

    class Config:
        from_attributes = True


class ExamOut(BaseModel):
    id: int
    title: str
    course: Optional[str]
    exam_date: Optional[date]
    time_limit_minutes: Optional[int]
    allowed_aids: Optional[str]
    instructions: Optional[str]
    passing_percentage: float
    total_points: float
    status: str
    language: str
    created_at: datetime
    updated_at: datetime
    question_count: int = 0

    class Config:
        from_attributes = True


class ExamDetailOut(ExamOut):
    questions: List[ExamQuestionOut] = []


class ExamListOut(BaseModel):
    total: int
    exams: List[ExamOut]


# --- Helpers ---


def _get_exam_or_404(
    exam_id: int, db: Session, current_user: User, locale: str = "de"
) -> Exam:
    exam = (
        db.query(Exam)
        .options(joinedload(Exam.questions).joinedload(ExamQuestion.question))
        .filter(Exam.id == exam_id)
        .first()
    )
    if not exam:
        raise HTTPException(status_code=404, detail=t("exams_not_found", locale=locale))
    tenant_context = get_tenant_context(current_user)
    TenantFilter.verify_tenant_access(exam, tenant_context)
    return exam


def _require_draft(exam: Exam, locale: str = "de"):
    if exam.status != ExamStatus.DRAFT.value:
        raise HTTPException(
            status_code=400,
            detail=t("exams_must_be_draft", locale=locale),
        )


def _exam_to_out(exam: Exam) -> dict:
    return {
        "id": exam.id,
        "title": exam.title,
        "course": exam.course,
        "exam_date": exam.exam_date,
        "time_limit_minutes": exam.time_limit_minutes,
        "allowed_aids": exam.allowed_aids,
        "instructions": exam.instructions,
        "passing_percentage": exam.passing_percentage,
        "total_points": exam.total_points,
        "status": exam.status,
        "language": exam.language,
        "created_at": exam.created_at,
        "updated_at": exam.updated_at,
        "question_count": len(exam.questions) if exam.questions else 0,
    }


def _exam_detail_to_out(exam: Exam) -> dict:
    data = _exam_to_out(exam)
    data["questions"] = [
        {
            "id": eq.id,
            "question_id": eq.question_id,
            "position": eq.position,
            "points": eq.points,
            "section": eq.section,
            "question_text": eq.question.question_text,
            "question_type": eq.question.question_type,
            "difficulty": eq.question.difficulty,
            "topic": eq.question.topic,
            "bloom_level": eq.question.bloom_level,
            "review_status": eq.question.review_status,
            "options": eq.question.options,
            "correct_answer": eq.question.correct_answer,
            "explanation": eq.question.explanation,
        }
        for eq in exam.questions
    ]
    return data


# --- CRUD Endpoints ---


@router.post("/", response_model=ExamOut, status_code=201)
async def create_exam(
    request: ExamCreate,
    http_request: Request,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Create a new exam (draft status)."""
    locale = get_request_locale(http_request, current_user)
    exam = Exam(
        title=request.title,
        course=request.course,
        exam_date=request.exam_date,
        time_limit_minutes=request.time_limit_minutes,
        allowed_aids=request.allowed_aids,
        instructions=request.instructions,
        passing_percentage=request.passing_percentage,
        language=request.language,
        institution_id=current_user.institution_id,
        created_by=current_user.id,
    )
    db.add(exam)
    try:
        db.commit()
        db.refresh(exam)
    except IntegrityError as exc:
        db.rollback()
        logger.error("IntegrityError in create_exam: %s", exc)
        raise HTTPException(status_code=409, detail=t("exams_conflict", locale=locale))
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Database error in create_exam: %s", exc)
        raise HTTPException(status_code=500, detail=t("exams_db_error", locale=locale))
    logger.info(f"Created exam {exam.id} by user {current_user.id}")
    return _exam_to_out(exam)


@router.get("/", response_model=ExamListOut)
async def list_exams(
    status: Optional[str] = Query(None, pattern="^(draft|finalized|exported)$"),
    search: Optional[str] = Query(None, max_length=200),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """List exams for the current user's institution."""
    tenant_context = get_tenant_context(current_user)
    query = db.query(Exam)
    query = TenantFilter.filter_by_tenant(query, Exam, tenant_context)

    if status:
        query = query.filter(Exam.status == status)
    if search:
        query = query.filter(Exam.title.ilike(f"%{search}%"))

    total = query.count()
    exams = query.order_by(Exam.updated_at.desc()).limit(limit).offset(offset).all()
    return ExamListOut(
        total=total,
        exams=[_exam_to_out(e) for e in exams],
    )


# --- Approved Questions Schemas (must be before /{exam_id} routes!) ---


class ApprovedQuestionOut(BaseModel):
    id: int
    question_text: str
    question_type: str
    difficulty: str
    topic: str
    bloom_level: Optional[int]
    estimated_time_minutes: Optional[int] = None
    options: Optional[list]
    usage_count: int = 0

    class Config:
        from_attributes = True


class ApprovedQuestionsListOut(BaseModel):
    total: int
    questions: List[ApprovedQuestionOut]


@router.get("/approved-questions", response_model=ApprovedQuestionsListOut)
async def list_approved_questions(
    topic: Optional[str] = None,
    difficulty: Optional[str] = Query(None, pattern="^(easy|medium|hard)$"),
    bloom_level: Optional[int] = Query(None, ge=1, le=6),
    question_type: Optional[str] = Query(
        None, pattern="^(multiple_choice|open_ended|true_false)$"
    ),
    search: Optional[str] = Query(None, max_length=500),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Browse approved questions for exam composition."""
    tenant_context = get_tenant_context(current_user)
    query = db.query(QuestionReview).filter(
        QuestionReview.review_status == ReviewStatus.APPROVED.value
    )
    query = TenantFilter.filter_by_tenant(query, QuestionReview, tenant_context)

    if topic:
        query = query.filter(QuestionReview.topic.ilike(f"%{topic}%"))
    if difficulty:
        query = query.filter(QuestionReview.difficulty == difficulty)
    if bloom_level:
        query = query.filter(QuestionReview.bloom_level == bloom_level)
    if question_type:
        query = query.filter(QuestionReview.question_type == question_type)
    if search:
        query = query.filter(QuestionReview.question_text.ilike(f"%{search}%"))

    total = query.count()
    questions = (
        query.order_by(QuestionReview.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    question_ids = [q.id for q in questions]
    usage_counts = {}
    if question_ids:
        usage_counts = dict(
            db.query(ExamQuestion.question_id, sa_func.count(ExamQuestion.id))
            .filter(ExamQuestion.question_id.in_(question_ids))
            .group_by(ExamQuestion.question_id)
            .all()
        )

    result = []
    for q in questions:
        result.append(
            {
                "id": q.id,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "difficulty": q.difficulty,
                "topic": q.topic,
                "bloom_level": q.bloom_level,
                "options": q.options,
                "usage_count": usage_counts.get(q.id, 0),
            }
        )

    return ApprovedQuestionsListOut(total=total, questions=result)


@router.get("/{exam_id}", response_model=ExamDetailOut)
async def get_exam(
    exam_id: int,
    request: Request,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Get exam with all questions."""
    locale = get_request_locale(request, current_user)
    exam = _get_exam_or_404(exam_id, db, current_user, locale)
    return _exam_detail_to_out(exam)


@router.put("/{exam_id}", response_model=ExamOut)
async def update_exam(
    exam_id: int,
    request: ExamUpdate,
    http_request: Request,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Update exam metadata. Requires updated_at for optimistic locking."""
    locale = get_request_locale(http_request, current_user)
    exam = _get_exam_or_404(exam_id, db, current_user, locale)
    _require_draft(exam, locale)

    # Optimistic locking — compare at microsecond precision with UTC normalisation
    if exam.updated_at and request.updated_at:
        if _to_utc(exam.updated_at) != _to_utc(request.updated_at):
            raise HTTPException(
                status_code=409,
                detail=t("exams_conflict", locale=locale),
            )

    update_data = request.model_dump(exclude_unset=True, exclude={"updated_at"})
    for field, value in update_data.items():
        setattr(exam, field, value)

    try:
        db.commit()
        db.refresh(exam)
    except IntegrityError as exc:
        db.rollback()
        logger.error("IntegrityError in update_exam for exam %s: %s", exam_id, exc)
        raise HTTPException(status_code=409, detail=t("exams_conflict", locale=locale))
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Database error in update_exam for exam %s: %s", exam_id, exc)
        raise HTTPException(status_code=500, detail=t("exams_db_error", locale=locale))
    logger.info(f"Updated exam {exam_id} by user {current_user.id}")
    return _exam_to_out(exam)


@router.delete("/{exam_id}", status_code=204)
async def delete_exam(
    exam_id: int,
    request: Request,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Delete a draft exam."""
    locale = get_request_locale(request, current_user)
    exam = _get_exam_or_404(exam_id, db, current_user, locale)
    _require_draft(exam, locale)
    db.delete(exam)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.error("IntegrityError in delete_exam for exam %s: %s", exam_id, exc)
        raise HTTPException(status_code=409, detail=t("exams_conflict", locale=locale))
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Database error in delete_exam for exam %s: %s", exam_id, exc)
        raise HTTPException(status_code=500, detail=t("exams_db_error", locale=locale))
    logger.info(f"Deleted exam {exam_id} by user {current_user.id}")


# --- Question Management Schemas ---


class AddQuestionsRequest(BaseModel):
    question_ids: List[int] = Field(..., min_length=1)


class UpdateExamQuestionRequest(BaseModel):
    points: Optional[float] = Field(None, ge=0)
    section: Optional[str] = Field(None, max_length=100)


class ReorderItem(BaseModel):
    id: int
    position: int


class ReorderRequest(BaseModel):
    order: List[ReorderItem]


# --- Question Management Endpoints ---


@router.post("/{exam_id}/questions", response_model=ExamDetailOut)
async def add_questions(
    exam_id: int,
    request: AddQuestionsRequest,
    http_request: Request,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Add approved questions to exam with auto-suggested points."""
    locale = get_request_locale(http_request, current_user)
    exam = _get_exam_or_404(exam_id, db, current_user, locale)
    _require_draft(exam, locale)

    max_pos = max((eq.position for eq in exam.questions), default=0)
    existing_qids = {eq.question_id for eq in exam.questions}
    tenant_context = get_tenant_context(current_user)

    for qid in request.question_ids:
        if qid in existing_qids:
            continue  # Skip duplicates silently

        question = db.query(QuestionReview).filter(QuestionReview.id == qid).first()
        if not question:
            raise HTTPException(
                status_code=404, detail=t("exams_question_not_found", locale=locale)
            )

        TenantFilter.verify_tenant_access(question, tenant_context)

        if question.review_status != ReviewStatus.APPROVED.value:
            raise HTTPException(
                status_code=400,
                detail=t("exams_question_not_approved", locale=locale),
            )

        max_pos += 1
        points = suggest_points(question.question_type, question.difficulty)
        eq = ExamQuestion(
            exam_id=exam.id,
            question_id=qid,
            position=max_pos,
            points=points,
        )
        db.add(eq)
        existing_qids.add(qid)

    try:
        db.flush()
        db.refresh(exam)
        exam.recalculate_total_points()
        db.commit()
        db.refresh(exam)
    except IntegrityError as exc:
        db.rollback()
        logger.error("IntegrityError in add_questions for exam %s: %s", exam_id, exc)
        raise HTTPException(status_code=409, detail=t("exams_conflict", locale=locale))
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Database error in add_questions for exam %s: %s", exam_id, exc)
        raise HTTPException(status_code=500, detail=t("exams_db_error", locale=locale))

    return _exam_detail_to_out(exam)


@router.put("/{exam_id}/questions/{eq_id}", response_model=ExamDetailOut)
async def update_exam_question(
    exam_id: int,
    eq_id: int,
    request: UpdateExamQuestionRequest,
    http_request: Request,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Update points or section of a question in the exam."""
    locale = get_request_locale(http_request, current_user)
    exam = _get_exam_or_404(exam_id, db, current_user, locale)
    _require_draft(exam, locale)

    eq = (
        db.query(ExamQuestion)
        .filter(ExamQuestion.id == eq_id, ExamQuestion.exam_id == exam_id)
        .first()
    )
    if not eq:
        raise HTTPException(
            status_code=404, detail=t("exams_exam_question_not_found", locale=locale)
        )

    if request.points is not None:
        eq.points = request.points
    if request.section is not None:
        eq.section = request.section

    try:
        db.flush()
        db.refresh(exam)
        exam.recalculate_total_points()
        db.commit()
        db.refresh(exam)
    except IntegrityError as exc:
        db.rollback()
        logger.error(
            "IntegrityError in update_exam_question for exam %s: %s", exam_id, exc
        )
        raise HTTPException(status_code=409, detail=t("exams_conflict", locale=locale))
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(
            "Database error in update_exam_question for exam %s: %s", exam_id, exc
        )
        raise HTTPException(status_code=500, detail=t("exams_db_error", locale=locale))

    return _exam_detail_to_out(exam)


@router.delete("/{exam_id}/questions/{eq_id}", response_model=ExamDetailOut)
async def remove_exam_question(
    exam_id: int,
    eq_id: int,
    request: Request,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Remove a question from the exam and re-number remaining positions."""
    locale = get_request_locale(request, current_user)
    exam = _get_exam_or_404(exam_id, db, current_user, locale)
    _require_draft(exam, locale)

    eq = (
        db.query(ExamQuestion)
        .filter(ExamQuestion.id == eq_id, ExamQuestion.exam_id == exam_id)
        .first()
    )
    if not eq:
        raise HTTPException(
            status_code=404, detail=t("exams_exam_question_not_found", locale=locale)
        )

    db.delete(eq)

    # Re-number remaining positions
    remaining = (
        db.query(ExamQuestion)
        .filter(ExamQuestion.exam_id == exam_id)
        .order_by(ExamQuestion.position)
        .all()
    )
    for i, item in enumerate(remaining, 1):
        item.position = i

    try:
        db.flush()
        db.refresh(exam)
        exam.recalculate_total_points()
        db.commit()
        db.refresh(exam)
    except IntegrityError as exc:
        db.rollback()
        logger.error(
            "IntegrityError in remove_exam_question for exam %s: %s", exam_id, exc
        )
        raise HTTPException(status_code=409, detail=t("exams_conflict", locale=locale))
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(
            "Database error in remove_exam_question for exam %s: %s", exam_id, exc
        )
        raise HTTPException(status_code=500, detail=t("exams_db_error", locale=locale))

    return _exam_detail_to_out(exam)


@router.post("/{exam_id}/reorder", response_model=ExamDetailOut)
async def reorder_questions(
    exam_id: int,
    request: ReorderRequest,
    http_request: Request,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Batch reorder questions in the exam."""
    locale = get_request_locale(http_request, current_user)
    exam = _get_exam_or_404(exam_id, db, current_user, locale)
    _require_draft(exam, locale)

    eq_map = {eq.id: eq for eq in exam.questions}

    # Validate all IDs first before any mutations
    for item in request.order:
        if item.id not in eq_map:
            raise HTTPException(
                status_code=404,
                detail=t("exams_exam_question_not_found", locale=locale),
            )

    # Temporarily set positions negative to avoid unique constraint violations
    for eq in exam.questions:
        eq.position = -eq.position
    db.flush()

    for item in request.order:
        eq_map[item.id].position = item.position

    try:
        db.commit()
        db.refresh(exam)
    except IntegrityError as exc:
        db.rollback()
        logger.error(
            "IntegrityError in reorder_questions for exam %s: %s", exam_id, exc
        )
        raise HTTPException(status_code=409, detail=t("exams_conflict", locale=locale))
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(
            "Database error in reorder_questions for exam %s: %s", exam_id, exc
        )
        raise HTTPException(status_code=500, detail=t("exams_db_error", locale=locale))
    return _exam_detail_to_out(exam)


# --- Auto-Fill ---


class AutoFillRequest(BaseModel):
    # Simple mode fields
    count: Optional[int] = Field(None, ge=1, le=20)
    topic: Optional[str] = None
    difficulty: Optional[List[str]] = None
    bloom_level_min: Optional[int] = Field(None, ge=1, le=6)
    question_types: Optional[List[str]] = None
    exclude_question_ids: Optional[List[int]] = None

    # Composition mode fields
    target_points: Optional[float] = Field(None, gt=0)
    target_duration_minutes: Optional[int] = Field(None, gt=0)
    bloom_distribution: Optional[dict[int, float]] = None
    difficulty_distribution: Optional[dict[str, float]] = None
    preview: bool = False

    @property
    def is_composition_mode(self) -> bool:
        return (
            self.target_points is not None
            or self.target_duration_minutes is not None
            or self.bloom_distribution is not None
            or self.difficulty_distribution is not None
        )


class DistributionResultOut(BaseModel):
    target_pct: float
    achieved_pct: float
    within_tolerance: bool


class ConstraintReportOut(BaseModel):
    points_target: Optional[float]
    points_achieved: float
    duration_target: Optional[int]
    duration_achieved: int
    bloom_distribution: dict[int, DistributionResultOut]
    difficulty_distribution: dict[str, DistributionResultOut]
    overall_satisfaction: float


class ProposedQuestionOut(BaseModel):
    id: int
    question_text: str
    question_type: str
    difficulty: str
    topic: str
    bloom_level: Optional[int]
    estimated_time_minutes: Optional[int]
    suggested_points: float


class AutoComposePreview(BaseModel):
    mode: str = "preview"
    questions: list[ProposedQuestionOut]
    total_points: float
    total_duration_minutes: int
    constraint_report: ConstraintReportOut


@router.post(
    "/{exam_id}/auto-fill",
    response_model=Union[ExamDetailOut, AutoComposePreview],
)
async def auto_fill_questions(
    exam_id: int,
    request: AutoFillRequest,
    http_request: Request,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Auto-fill exam with questions matching criteria.

    Simple mode: random selection by count (default when no composition constraints set).
    Composition mode: constraint-based greedy optimization with optional preview.
    """
    locale = get_request_locale(http_request, current_user)
    exam = _get_exam_or_404(exam_id, db, current_user, locale)
    _require_draft(exam, locale)

    if request.is_composition_mode:
        return _auto_compose(exam, request, current_user, db, locale=locale)
    else:
        return _auto_fill_simple(exam, request, current_user, db, locale=locale)


def _validate_distribution(
    dist: dict, name: str, valid_keys: set | None = None, locale: str = "de"
):
    """Validate that distribution percentage values sum to ~100 (+/-1) and optionally check keys against a valid set."""
    total = sum(dist.values())
    if abs(total - 100) > 1.0:
        raise HTTPException(
            status_code=422,
            detail=t(
                "exams_distribution_sum_invalid", locale=locale, name=name, total=total
            ),
        )
    if valid_keys:
        invalid = set(dist.keys()) - valid_keys
        if invalid:
            raise HTTPException(
                status_code=422,
                detail=t(
                    "exams_distribution_invalid_keys",
                    locale=locale,
                    name=name,
                    keys=str(invalid),
                ),
            )


def _build_candidate_query(
    exam: Exam, request: AutoFillRequest, current_user: User, db: Session
):
    """Build filtered query for approved question candidates."""
    tenant_context = get_tenant_context(current_user)
    query = db.query(QuestionReview).filter(
        QuestionReview.review_status == ReviewStatus.APPROVED.value
    )
    query = TenantFilter.filter_by_tenant(query, QuestionReview, tenant_context)

    # Exclude already-added and user-excluded questions
    existing_qids = {eq.question_id for eq in exam.questions}
    exclude_ids = existing_qids | set(request.exclude_question_ids or [])
    if exclude_ids:
        query = query.filter(QuestionReview.id.notin_(exclude_ids))

    # Apply filters
    if request.topic:
        query = query.filter(QuestionReview.topic.ilike(f"%{request.topic}%"))
    if request.difficulty:
        query = query.filter(QuestionReview.difficulty.in_(request.difficulty))
    if request.bloom_level_min:
        query = query.filter(QuestionReview.bloom_level >= request.bloom_level_min)
    if request.question_types:
        query = query.filter(QuestionReview.question_type.in_(request.question_types))

    return query


def _commit_exam_changes(
    exam: Exam, db: Session, operation_name: str, locale: str = "de"
):
    """Flush, recalculate points, and commit exam changes with error handling."""
    try:
        db.flush()
        db.refresh(exam)
        exam.recalculate_total_points()
        db.commit()
        db.refresh(exam)
    except IntegrityError as exc:
        db.rollback()
        logger.error(
            "IntegrityError in %s for exam %s: %s", operation_name, exam.id, exc
        )
        raise HTTPException(status_code=409, detail=t("exams_conflict", locale=locale))
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(
            "Database error in %s for exam %s: %s", operation_name, exam.id, exc
        )
        raise HTTPException(status_code=500, detail=t("exams_db_error", locale=locale))


def _auto_compose(
    exam: Exam,
    request: AutoFillRequest,
    current_user: User,
    db: Session,
    locale: str = "de",
):
    """Composition mode: constraint-based greedy optimization."""
    from services.auto_compose_service import (
        compose_questions,
        QuestionCandidate,
        CompositionConstraints,
    )

    # Validate distributions
    if request.bloom_distribution:
        _validate_distribution(
            request.bloom_distribution,
            "bloom_distribution",
            valid_keys={1, 2, 3, 4, 5, 6},
            locale=locale,
        )
    if request.difficulty_distribution:
        _validate_distribution(
            request.difficulty_distribution,
            "difficulty_distribution",
            valid_keys={"easy", "medium", "hard"},
            locale=locale,
        )

    query = _build_candidate_query(exam, request, current_user, db)

    # Exclude NULL metadata when corresponding constraints are active
    if request.bloom_distribution:
        query = query.filter(QuestionReview.bloom_level.isnot(None))
    if request.target_duration_minutes:
        query = query.filter(QuestionReview.estimated_time_minutes.isnot(None))

    all_candidates = query.all()
    if not all_candidates:
        raise HTTPException(
            status_code=404, detail=t("exams_no_matching_questions", locale=locale)
        )

    candidates = [
        QuestionCandidate(
            id=q.id,
            question_text=q.question_text,
            question_type=q.question_type,
            difficulty=q.difficulty,
            topic=q.topic,
            bloom_level=q.bloom_level,
            estimated_time_minutes=q.estimated_time_minutes,
        )
        for q in all_candidates
    ]

    constraints = CompositionConstraints(
        target_points=request.target_points,
        target_duration_minutes=request.target_duration_minutes,
        bloom_distribution=request.bloom_distribution,
        difficulty_distribution=request.difficulty_distribution,
    )

    try:
        result = compose_questions(candidates, constraints)
    except ValueError as exc:
        logger.warning("Composition constraint error for exam %s: %s", exam.id, exc)
        raise HTTPException(
            status_code=422,
            detail=t("exams_composition_constraint_error", locale=locale),
        )

    if not result.questions:
        raise HTTPException(
            status_code=404,
            detail=t("exams_no_questions_fit_constraints", locale=locale),
        )

    # Preview mode: return proposal without modifying exam
    if request.preview:
        from dataclasses import asdict

        report = result.constraint_report
        return AutoComposePreview(
            questions=[ProposedQuestionOut(**asdict(q)) for q in result.questions],
            total_points=result.total_points,
            total_duration_minutes=result.total_duration_minutes,
            constraint_report=ConstraintReportOut(
                points_target=report.points_target,
                points_achieved=report.points_achieved,
                duration_target=report.duration_target,
                duration_achieved=report.duration_achieved,
                bloom_distribution={
                    k: DistributionResultOut(**asdict(v))
                    for k, v in report.bloom_distribution.items()
                },
                difficulty_distribution={
                    k: DistributionResultOut(**asdict(v))
                    for k, v in report.difficulty_distribution.items()
                },
                overall_satisfaction=report.overall_satisfaction,
            ),
        )

    # Apply mode: add questions to exam
    max_pos = max((eq.position for eq in exam.questions), default=0)
    for q in result.questions:
        max_pos += 1
        eq = ExamQuestion(
            exam_id=exam.id,
            question_id=q.id,
            position=max_pos,
            points=q.suggested_points,
        )
        db.add(eq)

    _commit_exam_changes(exam, db, "auto_compose", locale=locale)
    return _exam_detail_to_out(exam)


def _auto_fill_simple(
    exam: Exam,
    request: AutoFillRequest,
    current_user: User,
    db: Session,
    locale: str = "de",
):
    """Simple mode: random selection by count."""
    count = request.count or 5

    query = _build_candidate_query(exam, request, current_user, db)
    candidates = query.order_by(sa_func.random()).limit(count).all()
    if not candidates:
        raise HTTPException(
            status_code=404, detail=t("exams_no_matching_questions", locale=locale)
        )

    max_pos = max((eq.position for eq in exam.questions), default=0)
    for q in candidates:
        max_pos += 1
        eq = ExamQuestion(
            exam_id=exam.id,
            question_id=q.id,
            position=max_pos,
            points=suggest_points(q.question_type, q.difficulty),
        )
        db.add(eq)

    _commit_exam_changes(exam, db, "auto_fill", locale=locale)
    return _exam_detail_to_out(exam)


# --- Finalize / Unfinalize ---


@router.post("/{exam_id}/finalize", response_model=ExamOut)
async def finalize_exam(
    exam_id: int,
    request: Request,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Finalize exam. Validates all questions are still approved."""
    locale = get_request_locale(request, current_user)
    exam = _get_exam_or_404(exam_id, db, current_user, locale)
    _require_draft(exam, locale)

    if not exam.questions:
        raise HTTPException(
            status_code=400, detail=t("exams_cannot_finalize_empty", locale=locale)
        )

    # Check all questions are still approved
    non_approved = [
        eq
        for eq in exam.questions
        if eq.question.review_status != ReviewStatus.APPROVED.value
    ]
    if non_approved:
        raise HTTPException(
            status_code=400,
            detail=t("exams_questions_not_approved", locale=locale),
        )

    exam.status = ExamStatus.FINALIZED.value
    try:
        db.commit()
        db.refresh(exam)
    except IntegrityError as exc:
        db.rollback()
        logger.error("IntegrityError in finalize_exam for exam %s: %s", exam_id, exc)
        raise HTTPException(status_code=409, detail=t("exams_conflict", locale=locale))
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Database error in finalize_exam for exam %s: %s", exam_id, exc)
        raise HTTPException(status_code=500, detail=t("exams_db_error", locale=locale))
    return _exam_to_out(exam)


@router.post("/{exam_id}/unfinalize", response_model=ExamOut)
async def unfinalize_exam(
    exam_id: int,
    request: Request,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Revert exam from finalized/exported to draft."""
    locale = get_request_locale(request, current_user)
    exam = _get_exam_or_404(exam_id, db, current_user, locale)
    if exam.status not in (ExamStatus.FINALIZED.value, ExamStatus.EXPORTED.value):
        raise HTTPException(
            status_code=400, detail=t("exams_already_draft", locale=locale)
        )

    exam.status = ExamStatus.DRAFT.value
    try:
        db.commit()
        db.refresh(exam)
    except IntegrityError as exc:
        db.rollback()
        logger.error("IntegrityError in unfinalize_exam for exam %s: %s", exam_id, exc)
        raise HTTPException(status_code=409, detail=t("exams_conflict", locale=locale))
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Database error in unfinalize_exam for exam %s: %s", exam_id, exc)
        raise HTTPException(status_code=500, detail=t("exams_db_error", locale=locale))
    return _exam_to_out(exam)


# --- Export ---


@router.get("/{exam_id}/export/{format}")
async def export_exam(
    exam_id: int,
    format: str,
    include_solutions: bool = Query(False),
    request: Request = None,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Export exam in specified format (md, json, moodle)."""
    locale = get_request_locale(request, current_user)
    exam = _get_exam_or_404(exam_id, db, current_user, locale)

    if exam.status == ExamStatus.DRAFT.value:
        raise HTTPException(
            status_code=400,
            detail=t("exams_must_finalize_before_export", locale=locale),
        )

    if not exam.questions:
        raise HTTPException(
            status_code=400, detail=t("exams_cannot_export_empty", locale=locale)
        )

    exam_data = _exam_detail_to_out(exam)
    # Convert date to string for export
    if exam_data.get("exam_date"):
        exam_data["exam_date"] = str(exam_data["exam_date"])

    safe_title = exam.title.lower().replace(" ", "_")[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format == "md":
        content = MarkdownExporter.export(
            exam_data, include_solutions=include_solutions
        )
        suffix = "_solutions" if include_solutions else ""
        media_type = "text/markdown"
        filename = f"{safe_title}_{timestamp}{suffix}.md"
    elif format == "json":
        content = JsonExporter.export(exam_data)
        media_type = "application/json"
        filename = f"{safe_title}_{timestamp}.json"
    elif format == "moodle":
        content = MoodleXmlExporter.export(exam_data)
        media_type = "application/xml"
        filename = f"{safe_title}_{timestamp}_moodle.xml"
    else:
        raise HTTPException(
            status_code=400,
            detail=t("exams_unsupported_format", locale=locale),
        )

    # Update status to exported if currently finalized
    if exam.status == ExamStatus.FINALIZED.value:
        exam.status = ExamStatus.EXPORTED.value
        db.commit()

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
