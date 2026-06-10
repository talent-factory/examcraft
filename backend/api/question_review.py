"""
Question Review API Endpoints für ExamCraft AI
Implementiert Review-Workflow für generierte Prüfungsfragen
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime

from utils.question_options import normalize_options

from database import get_db
from models.question_review import (
    QuestionReview,
    ReviewComment,
    ReviewHistory,
    ReviewStatus,
)
from models.auth import User
from models.tag import Tag, QuestionTag
from api.tags import TagOut
from schemas.generation_metadata import GenerationMetadata
from services.translation_service import t, get_request_locale
from utils.auth_utils import get_current_active_user, require_permission
from utils.tenant_utils import TenantFilter, get_tenant_context
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/questions", tags=["Question Review"])


def _live_tag_counts(db: Session, tag_ids: list[int]) -> dict[int, int]:
    if not tag_ids:
        return {}
    rows = (
        db.query(QuestionTag.tag_id, func.count(QuestionTag.question_id))
        .filter(QuestionTag.tag_id.in_(tag_ids))
        .group_by(QuestionTag.tag_id)
        .all()
    )
    return dict(rows)


def _serialize_tag(tag: Tag, usage_count: int) -> dict:
    return {
        "id": tag.id,
        "name": tag.name,
        "institution_id": tag.institution_id,
        "scope": tag.scope,
        "usage_count": usage_count,
        "is_archived": tag.is_archived,
    }


def _serialize_competency(question: QuestionReview) -> dict | None:
    """TF-400: Brief der geprüften Handlungskompetenz (HK) für die Anzeige.

    None, wenn der Frage keine Kompetenz zugeordnet ist (Altbestand oder Code
    ohne Treffer). ``module_code`` stammt aus dem zugehörigen Framework.
    """
    competency = question.competency
    if competency is None:
        return None
    framework = competency.framework
    return {
        "id": competency.id,
        "code": competency.code,
        "title": competency.title,
        "framework_id": competency.framework_id,
        "module_code": framework.module_code if framework else None,
    }


def _question_to_dict(
    question: QuestionReview, counts: dict[int, int] | None = None
) -> dict:
    """Convert QuestionReview to dict (without reviewer lookup)."""
    counts = counts or {}
    return {
        "id": question.id,
        "question_text": question.question_text,
        "question_type": question.question_type,
        "options": question.options,
        "correct_answer": question.correct_answer,
        "explanation": question.explanation,
        "difficulty": question.difficulty,
        "topic": question.topic,
        "language": question.language,
        "source_chunks": question.source_chunks,
        "source_documents": question.source_documents,
        "confidence_score": question.confidence_score,
        "bloom_level": question.bloom_level,
        "estimated_time_minutes": question.estimated_time_minutes,
        "quality_tier": question.quality_tier,
        "generation_metadata": question.generation_metadata,
        "review_status": question.review_status,
        "reviewed_by": question.reviewed_by,
        "reviewed_at": question.reviewed_at,
        "exam_id": question.exam_id,
        "archived_at": question.archived_at,
        "archived_by": question.archived_by,
        "archive_reason": question.archive_reason,
        "created_at": question.created_at,
        "updated_at": question.updated_at,
        "tags": [_serialize_tag(t, counts.get(t.id, 0)) for t in question.tags],
        # TF-400: geprüfte Handlungskompetenz + LN-Stufe (Anzeige in der
        # Review-Queue/Detail). None für Fragen ohne HK-Zuordnung.
        "competency_id": question.competency_id,
        "ln_level": question.ln_level,
        "competency": _serialize_competency(question),
    }


def _attach_reviewer_info(question: QuestionReview, db: Session) -> dict:
    """Convert QuestionReview to dict with reviewer_info joined."""
    counts = _live_tag_counts(db, [t.id for t in question.tags])
    data = _question_to_dict(question, counts)
    if question.reviewed_by:
        reviewer = db.query(User).filter(User.id == question.reviewed_by).first()
        if reviewer:
            data["reviewer_info"] = {
                "id": reviewer.id,
                "first_name": reviewer.first_name,
                "last_name": reviewer.last_name,
            }
        else:
            logger.warning(
                "Reviewer user_id=%s not found for question_id=%s",
                question.reviewed_by,
                question.id,
            )
    return data


def _get_scoped_question(
    db: Session, question_id: int, current_user: User
) -> QuestionReview | None:
    """Fetch a QuestionReview by id, scoped to the caller's institution.

    Mirrors the queue endpoint's tenant filtering (superusers bypass). Returns
    ``None`` for questions outside the caller's institution so by-id endpoints
    answer 404 instead of leaking/mutating cross-tenant data (TF-383 review:
    the detail/edit/review endpoints previously fetched by id only).
    """
    tenant_context = get_tenant_context(current_user)
    return (
        TenantFilter.filter_by_tenant(
            db.query(QuestionReview), QuestionReview, tenant_context
        )
        .filter(QuestionReview.id == question_id)
        .first()
    )


# Pydantic Models
class QuestionReviewCreate(BaseModel):
    """Request Model für neue Question Review"""

    question_text: str = Field(..., min_length=10, max_length=5000)
    question_type: str = Field(..., pattern="^(multiple_choice|open_ended|true_false)$")
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    difficulty: str = Field(..., pattern="^(easy|medium|hard)$")
    topic: str = Field(..., min_length=3, max_length=200)
    language: str = Field(default="de", pattern="^(de|en)$")
    source_chunks: Optional[List[str]] = None
    source_documents: Optional[List[str]] = None
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    bloom_level: Optional[int] = Field(None, ge=1, le=6)
    estimated_time_minutes: Optional[int] = Field(None, ge=1, le=180)
    quality_tier: Optional[str] = Field(None, pattern="^[ABC]$")
    exam_id: Optional[str] = None
    tag_ids: list[int] = Field(default_factory=list)


class QuestionReviewUpdate(BaseModel):
    """Request Model für Question Update"""

    question_text: Optional[str] = Field(None, min_length=10, max_length=5000)
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    difficulty: Optional[str] = Field(None, pattern="^(easy|medium|hard)$")
    bloom_level: Optional[int] = Field(None, ge=1, le=6)
    estimated_time_minutes: Optional[int] = Field(None, ge=1, le=180)


class ReviewActionRequest(BaseModel):
    """Request Model fuer Review Actions (Approve/Reject)"""

    comment: Optional[str] = Field(None, max_length=2000)
    reason: Optional[str] = Field(None, max_length=500)


class CommentCreate(BaseModel):
    """Request Model fuer neuen Comment"""

    comment_text: str = Field(..., min_length=1, max_length=2000)
    comment_type: str = Field(
        default="general", pattern="^(general|suggestion|issue|approval_note)$"
    )


class ReviewerInfo(BaseModel):
    """Reviewer User Info"""

    id: int
    first_name: str
    last_name: str

    class Config:
        from_attributes = True


class CompetencyBrief(BaseModel):
    """TF-400: schlanke Sicht auf die geprüfte Handlungskompetenz für die

    Frage-Anzeige (Code + Titel + Modul), ohne den vollen Deskriptor-Baum.
    """

    id: int
    code: str
    title: str
    framework_id: int
    module_code: Optional[str] = None

    class Config:
        from_attributes = True


class QuestionReviewResponse(BaseModel):
    """Response Model für Question Review"""

    id: int
    question_text: str
    question_type: str
    options: Optional[List[str]]
    correct_answer: Optional[str]
    explanation: Optional[str]
    difficulty: str
    topic: str
    language: str
    source_chunks: Optional[List[str]]
    source_documents: Optional[List[str]]
    confidence_score: float
    bloom_level: Optional[int]
    # TF-400: geprüfte Handlungskompetenz (HK) + LN-Stufe (1-4, distinkt von
    # bloom_level). ``competency`` ist der schlanke Brief für die Anzeige.
    competency_id: Optional[int] = None
    ln_level: Optional[int] = Field(None, ge=1, le=4)
    competency: Optional[CompetencyBrief] = None
    estimated_time_minutes: Optional[int]
    quality_tier: Optional[str]
    generation_metadata: Optional[GenerationMetadata] = None
    review_status: str
    reviewed_by: Optional[int]
    reviewer_info: Optional[ReviewerInfo] = None
    reviewed_at: Optional[datetime]
    exam_id: Optional[str]
    archived_at: Optional[datetime] = None
    archived_by: Optional[int] = None
    archive_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    tags: List[TagOut] = []

    # TF-330: legacy records store ``options`` as a dict keyed by
    # 'A'/'B'/'C'/'D'. Normalize on read so the API never 500s on these rows.
    @field_validator("options", mode="before")
    @classmethod
    def _normalize_options(cls, value: Any) -> Any:
        return normalize_options(value)

    class Config:
        from_attributes = True


class CommentResponse(BaseModel):
    """Response Model für Comment"""

    id: int
    question_id: int
    comment_text: str
    comment_type: str
    author: str
    author_role: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HistoryResponse(BaseModel):
    """Response Model für History Entry"""

    id: int
    question_id: int
    action: str
    old_status: Optional[str]
    new_status: Optional[str]
    changed_fields: Optional[Dict[str, Any]]
    changed_by: str
    change_reason: Optional[str]
    changed_at: datetime

    class Config:
        from_attributes = True


class QuestionReviewDetailResponse(QuestionReviewResponse):
    """Detailed Response mit Comments und History"""

    comments: List[CommentResponse] = []
    history: List[HistoryResponse] = []


class ReviewQueueResponse(BaseModel):
    """Response Model für Review Queue"""

    total: int
    pending: int
    approved: int
    rejected: int
    in_review: int
    questions: List[QuestionReviewResponse]


# API Endpoints
@router.get("/review", response_model=ReviewQueueResponse)
async def get_review_queue(
    status: Optional[str] = Query(
        None, pattern="^(pending|approved|rejected|edited|in_review)$"
    ),
    difficulty: Optional[str] = Query(None, pattern="^(easy|medium|hard)$"),
    question_type: Optional[str] = Query(
        None, pattern="^(multiple_choice|open_ended|true_false)$"
    ),
    exam_id: Optional[str] = None,
    include_archived: bool = Query(False),
    archived_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    request: Request = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Hole Review Queue mit Filtern

    **Required:** Authenticated user

    - **status**: Filter nach Review-Status
    - **difficulty**: Filter nach Schwierigkeitsgrad
    - **question_type**: Filter nach Fragetyp
    - **exam_id**: Filter nach Exam ID
    - **limit**: Maximale Anzahl Ergebnisse
    - **offset**: Offset für Pagination
    """
    locale = get_request_locale(request, current_user)
    try:
        # Base Query — institution-scoped
        tenant_context = get_tenant_context(current_user)
        query = TenantFilter.filter_by_tenant(
            db.query(QuestionReview), QuestionReview, tenant_context
        )

        # Apply Filters
        if status:
            query = query.filter(QuestionReview.review_status == status)
        if difficulty:
            query = query.filter(QuestionReview.difficulty == difficulty)
        if question_type:
            query = query.filter(QuestionReview.question_type == question_type)
        if exam_id:
            query = query.filter(QuestionReview.exam_id == exam_id)
        # TF-396: Archiv-Achse. Default: nur aktive Fragen (archived_at IS NULL).
        if archived_only:
            query = query.filter(QuestionReview.archived_at.isnot(None))
        elif not include_archived:
            query = query.filter(QuestionReview.archived_at.is_(None))

        # Get Statistics — ebenfalls institution-scoped
        base_stats = TenantFilter.filter_by_tenant(
            db.query(QuestionReview), QuestionReview, tenant_context
        )
        # TF-396: Stats folgen demselben Archiv-Filter wie die Liste, damit die
        # Badge-Zähler zur angezeigten Menge passen (sonst über-zählen sie, sobald
        # Fragen archiviert sind).
        if archived_only:
            base_stats = base_stats.filter(QuestionReview.archived_at.isnot(None))
        elif not include_archived:
            base_stats = base_stats.filter(QuestionReview.archived_at.is_(None))
        total = query.count()
        pending = base_stats.filter(
            QuestionReview.review_status == ReviewStatus.PENDING.value
        ).count()
        approved = base_stats.filter(
            QuestionReview.review_status == ReviewStatus.APPROVED.value
        ).count()
        rejected = base_stats.filter(
            QuestionReview.review_status == ReviewStatus.REJECTED.value
        ).count()
        in_review = base_stats.filter(
            QuestionReview.review_status == ReviewStatus.IN_REVIEW.value
        ).count()

        # Get Questions with Pagination
        question_list = (
            query.order_by(QuestionReview.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

        # Batch-fetch reviewer info to avoid N+1 queries
        reviewer_ids = {q.reviewed_by for q in question_list if q.reviewed_by}
        reviewer_map = {}
        if reviewer_ids:
            reviewers = db.query(User).filter(User.id.in_(reviewer_ids)).all()
            reviewer_map = {r.id: r for r in reviewers}

        tag_ids = {t.id for q in question_list for t in q.tags}
        counts = _live_tag_counts(db, list(tag_ids))

        questions = []
        for q in question_list:
            data = _question_to_dict(q, counts)
            if q.reviewed_by and q.reviewed_by in reviewer_map:
                r = reviewer_map[q.reviewed_by]
                data["reviewer_info"] = {
                    "id": r.id,
                    "first_name": r.first_name,
                    "last_name": r.last_name,
                }
            elif q.reviewed_by:
                logger.warning(
                    "Reviewer user_id=%s not found for question_id=%s",
                    q.reviewed_by,
                    q.id,
                )
            questions.append(data)

        return ReviewQueueResponse(
            total=total,
            pending=pending,
            approved=approved,
            rejected=rejected,
            in_review=in_review,
            questions=questions,
        )

    except Exception as e:
        logger.error(f"Error fetching review queue: {e}")
        raise HTTPException(
            status_code=500, detail=t("review_fetch_queue_failed", locale=locale)
        )


@router.get("/{question_id}/review", response_model=QuestionReviewDetailResponse)
async def get_question_review(
    question_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Hole detaillierte Question Review mit Comments und History

    **Required:** Authenticated user
    """
    locale = get_request_locale(request, current_user)
    try:
        question = _get_scoped_question(db, question_id, current_user)

        if not question:
            raise HTTPException(
                status_code=404, detail=t("review_question_not_found", locale=locale)
            )

        data = _attach_reviewer_info(question, db)
        data["comments"] = question.comments
        data["history"] = question.history
        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching question review {question_id}: {e}")
        raise HTTPException(
            status_code=500, detail=t("review_fetch_question_failed", locale=locale)
        )


@router.post("/review", response_model=QuestionReviewResponse, status_code=201)
async def create_question_review(
    request: QuestionReviewCreate,
    http_request: Request,
    current_user: User = Depends(require_permission("create_questions")),
    db: Session = Depends(get_db),
):
    """
    Erstelle neue Question Review

    **Required Permission:** `create_questions` (Dozent, Assistant, Admin)
    """
    locale = get_request_locale(http_request, current_user)
    try:
        # Check question generation limit for institution
        from utils.tenant_utils import SubscriptionLimits

        SubscriptionLimits.check_question_limit(
            current_user.institution,
            db,
            user=current_user,
            request=http_request,
        )

        # Create Question Review
        question = QuestionReview(
            question_text=request.question_text,
            question_type=request.question_type,
            options=request.options,
            correct_answer=request.correct_answer,
            explanation=request.explanation,
            difficulty=request.difficulty,
            topic=request.topic,
            language=request.language,
            source_chunks=request.source_chunks,
            source_documents=request.source_documents,
            confidence_score=request.confidence_score,
            bloom_level=request.bloom_level,
            estimated_time_minutes=request.estimated_time_minutes,
            quality_tier=request.quality_tier,
            exam_id=request.exam_id,
            review_status=ReviewStatus.PENDING.value,
            institution_id=current_user.institution_id,  # Multi-tenancy
            created_by=current_user.id,  # Track creator
        )

        db.add(question)
        db.flush()

        if request.tag_ids:
            _assign_tags_to_question(db, question.id, request.tag_ids, current_user)

        history = ReviewHistory(
            question_id=question.id,
            action="created",
            new_status=ReviewStatus.PENDING.value,
            changed_by="system",
            change_reason="Question created",
        )
        db.add(history)
        db.commit()
        db.refresh(question)

        # Audit log: Question created
        from services.audit_service import AuditService

        AuditService.log_question_action(
            db,
            AuditService.ACTION_CREATE_QUESTION,
            current_user.id,
            question.id,
            additional_data={
                "topic": question.topic,
                "difficulty": question.difficulty,
            },
        )

        logger.info(f"Created question review {question.id}")
        return question

    except HTTPException:
        # Audit-Failure-500 aus check_question_limit/log_superuser_bypass nicht
        # in generisches 500 umverpacken — sonst geht das DSGVO-Signal in den
        # Logs verloren.
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating question review: {e}")
        raise HTTPException(
            status_code=500, detail=t("review_create_failed", locale=locale)
        )


@router.put("/{question_id}/edit", response_model=QuestionReviewResponse)
async def edit_question(
    question_id: int,
    request: QuestionReviewUpdate,
    http_request: Request,
    current_user: User = Depends(require_permission("edit_questions")),
    db: Session = Depends(get_db),
):
    """
    Bearbeite Question (Inline Editing)

    **Required Permission:** `edit_questions` (Dozent, Assistant, Admin)
    """
    locale = get_request_locale(http_request, current_user)
    try:
        question = _get_scoped_question(db, question_id, current_user)

        if not question:
            raise HTTPException(
                status_code=404, detail=t("review_question_not_found", locale=locale)
            )

        # Track changes
        changed_fields = {}
        old_status = question.review_status

        # Update fields
        if (
            request.question_text is not None
            and request.question_text != question.question_text
        ):
            changed_fields["question_text"] = {
                "old": question.question_text,
                "new": request.question_text,
            }
            question.question_text = request.question_text

        if request.options is not None and request.options != question.options:
            changed_fields["options"] = {
                "old": question.options,
                "new": request.options,
            }
            question.options = request.options

        if (
            request.correct_answer is not None
            and request.correct_answer != question.correct_answer
        ):
            changed_fields["correct_answer"] = {
                "old": question.correct_answer,
                "new": request.correct_answer,
            }
            question.correct_answer = request.correct_answer

        if (
            request.explanation is not None
            and request.explanation != question.explanation
        ):
            changed_fields["explanation"] = {
                "old": question.explanation,
                "new": request.explanation,
            }
            question.explanation = request.explanation

        if request.difficulty is not None and request.difficulty != question.difficulty:
            changed_fields["difficulty"] = {
                "old": question.difficulty,
                "new": request.difficulty,
            }
            question.difficulty = request.difficulty

        if (
            request.bloom_level is not None
            and request.bloom_level != question.bloom_level
        ):
            changed_fields["bloom_level"] = {
                "old": question.bloom_level,
                "new": request.bloom_level,
            }
            question.bloom_level = request.bloom_level

        if (
            request.estimated_time_minutes is not None
            and request.estimated_time_minutes != question.estimated_time_minutes
        ):
            changed_fields["estimated_time_minutes"] = {
                "old": question.estimated_time_minutes,
                "new": request.estimated_time_minutes,
            }
            question.estimated_time_minutes = request.estimated_time_minutes

        # Set status to EDITED if changes were made
        if changed_fields:
            if (
                question.review_status == ReviewStatus.IN_REVIEW.value
                and current_user.id == question.reviewed_by
            ):
                pass  # Reviewer edits stay in_review
            else:
                question.review_status = ReviewStatus.EDITED.value

        db.commit()
        db.refresh(question)

        # Create History Entry
        if changed_fields:
            history = ReviewHistory(
                question_id=question.id,
                action="edited",
                old_status=old_status,
                new_status=question.review_status,
                changed_fields=changed_fields,
                changed_by=current_user.email,
                change_reason="Question edited",
            )
            db.add(history)
            db.commit()

        logger.info(f"Edited question {question_id} by {current_user.email}")
        return _attach_reviewer_info(question, db)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error editing question {question_id}: {e}")
        raise HTTPException(
            status_code=500, detail=t("review_edit_failed", locale=locale)
        )


@router.post("/{question_id}/start-review", response_model=QuestionReviewResponse)
async def start_review(
    question_id: int,
    request: Request,
    current_user: User = Depends(require_permission("review_questions")),
    db: Session = Depends(get_db),
):
    """
    Markiere Frage als 'In Review'.

    Signalisiert anderen Reviewern, dass diese Frage gerade bearbeitet wird.

    **Required Permission:** `approve_questions` (Dozent, Admin)
    """
    locale = get_request_locale(request, current_user)
    try:
        question = _get_scoped_question(db, question_id, current_user)

        if not question:
            raise HTTPException(
                status_code=404, detail=t("review_question_not_found", locale=locale)
            )

        if question.review_status not in (
            ReviewStatus.PENDING.value,
            ReviewStatus.EDITED.value,
        ):
            raise HTTPException(
                status_code=400,
                detail=t("review_invalid_status_for_review", locale=locale),
            )

        old_status = question.review_status

        question.review_status = ReviewStatus.IN_REVIEW.value
        question.reviewed_by = current_user.id
        question.reviewed_at = datetime.utcnow()

        history = ReviewHistory(
            question_id=question.id,
            action="status_changed",
            old_status=old_status,
            new_status=ReviewStatus.IN_REVIEW.value,
            changed_by=str(current_user.id),
            change_reason="Review gestartet",
        )
        db.add(history)
        db.commit()
        db.refresh(question)

        logger.info(
            f"Started review for question {question_id} by {current_user.email}"
        )
        return _attach_reviewer_info(question, db)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            f"Error starting review for question {question_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=t("review_start_failed", locale=locale),
        )


@router.post("/{question_id}/approve", response_model=QuestionReviewResponse)
async def approve_question(
    question_id: int,
    request: ReviewActionRequest,
    http_request: Request,
    current_user: User = Depends(require_permission("review_questions")),
    db: Session = Depends(get_db),
):
    """
    Genehmige Question

    **Required Permission:** `approve_questions` (Dozent, Admin)
    """
    locale = get_request_locale(http_request, current_user)
    try:
        question = _get_scoped_question(db, question_id, current_user)

        if not question:
            raise HTTPException(
                status_code=404, detail=t("review_question_not_found", locale=locale)
            )

        # Vier-Augen-Prinzip Check
        if question.institution_id:
            from models.auth import Institution

            institution = (
                db.query(Institution)
                .filter(Institution.id == question.institution_id)
                .first()
            )
            if institution and institution.require_second_reviewer:
                is_reviewer = (
                    question.reviewed_by and current_user.id == question.reviewed_by
                )
                is_creator = (
                    question.created_by and current_user.id == question.created_by
                )
                if is_reviewer or is_creator:
                    raise HTTPException(
                        status_code=403,
                        detail=t("review_four_eyes_principle", locale=locale),
                    )

        old_status = question.review_status

        # Update Question
        question.review_status = ReviewStatus.APPROVED.value
        question.reviewed_at = datetime.utcnow()
        if not question.reviewed_by:
            question.reviewed_by = current_user.id

        db.commit()
        db.refresh(question)

        # Create History Entry
        history = ReviewHistory(
            question_id=question.id,
            action="approved",
            old_status=old_status,
            new_status=ReviewStatus.APPROVED.value,
            changed_by=current_user.email,
            change_reason=request.reason or "Question approved",
        )
        db.add(history)

        # Add Comment if provided
        if request.comment:
            comment = ReviewComment(
                question_id=question.id,
                comment_text=request.comment,
                comment_type="approval_note",
                author=f"{current_user.first_name} {current_user.last_name}",
                author_role="reviewer",
            )
            db.add(comment)

        db.commit()

        # Audit log: Question approved
        from services.audit_service import AuditService

        AuditService.log_question_action(
            db,
            AuditService.ACTION_APPROVE_QUESTION,
            current_user.id,
            question_id,
            additional_data={"reason": request.reason, "topic": question.topic},
        )

        logger.info(f"Approved question {question_id} by {current_user.email}")
        return _attach_reviewer_info(question, db)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error approving question {question_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=t("review_approve_failed", locale=locale),
        )


@router.post("/{question_id}/reject", response_model=QuestionReviewResponse)
async def reject_question(
    question_id: int,
    request: ReviewActionRequest,
    http_request: Request,
    current_user: User = Depends(require_permission("review_questions")),
    db: Session = Depends(get_db),
):
    """
    Lehne Question ab

    **Required Permission:** `approve_questions` (Dozent, Admin)
    """
    locale = get_request_locale(http_request, current_user)
    try:
        question = _get_scoped_question(db, question_id, current_user)

        if not question:
            raise HTTPException(
                status_code=404, detail=t("review_question_not_found", locale=locale)
            )

        old_status = question.review_status

        # Update Question
        question.review_status = ReviewStatus.REJECTED.value
        question.reviewed_at = datetime.utcnow()

        db.commit()
        db.refresh(question)

        # Create History Entry
        history = ReviewHistory(
            question_id=question.id,
            action="rejected",
            old_status=old_status,
            new_status=ReviewStatus.REJECTED.value,
            changed_by=current_user.email,
            change_reason=request.reason or "Question rejected",
        )
        db.add(history)

        # Add Comment if provided
        if request.comment:
            comment = ReviewComment(
                question_id=question.id,
                comment_text=request.comment,
                comment_type="issue",
                author=f"{current_user.first_name} {current_user.last_name}",
                author_role="reviewer",
            )
            db.add(comment)

        db.commit()

        # Audit log: Question rejected
        from services.audit_service import AuditService

        AuditService.log_question_action(
            db,
            AuditService.ACTION_REJECT_QUESTION,
            current_user.id,
            question_id,
            additional_data={"reason": request.reason, "topic": question.topic},
        )

        logger.info(f"Rejected question {question_id} by {current_user.email}")
        return _attach_reviewer_info(question, db)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error rejecting question {question_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=t("review_reject_failed", locale=locale),
        )


# ---------------------------------------------------------------------------
# TF-396: Archivieren / Wiederherstellen / Hard-Delete
# ---------------------------------------------------------------------------


class ArchiveRequest(BaseModel):
    """Request Model für Archivieren."""

    reason: Optional[str] = Field(None, max_length=500)


class BulkDeleteRequest(BaseModel):
    """Request Model für Bulk-Hard-Delete."""

    ids: list[int] = Field(..., min_length=1, max_length=200)


class BlockedDeletion(BaseModel):
    """Eine im Bulk-Delete abgewiesene Frage mit i18n-Begründung."""

    id: int
    reason: str


class BulkDeleteResult(BaseModel):
    """Ergebnis eines Bulk-Hard-Delete: gelöschte IDs + abgewiesene Einträge."""

    deleted: list[int]
    blocked: list[BlockedDeletion]


def _question_delete_block_reason(
    db: Session, question: QuestionReview, locale: str
) -> str | None:
    """i18n-Grund, falls die Frage NICHT hart löschbar ist, sonst ``None``.

    Guard (TF-396): nur archivierte Fragen, die in keiner Prüfung verwendet
    werden, dürfen hart gelöscht werden. "In keiner Prüfung" deckt transitiv
    auch Schüler-Antworten ab (attempt_answers -> exam_questions).
    """
    from models.exam import ExamQuestion

    if question.archived_at is None:
        return t("delete_requires_archive", locale=locale)
    in_exam = (
        db.query(ExamQuestion).filter(ExamQuestion.question_id == question.id).first()
    )
    if in_exam is not None:
        return t("delete_in_exam", locale=locale)
    return None


@router.post("/{question_id}/archive", response_model=QuestionReviewResponse)
async def archive_question(
    question_id: int,
    request: ArchiveRequest,
    http_request: Request,
    current_user: User = Depends(require_permission("review_questions")),
    db: Session = Depends(get_db),
):
    """Archiviere eine Frage (orthogonal zum review_status).

    Blendet die Frage aus Bank/Listen aus; in Prüfungen bleibt sie erhalten.

    **Required Permission:** `review_questions`
    """
    locale = get_request_locale(http_request, current_user)
    try:
        question = _get_scoped_question(db, question_id, current_user)
        if not question:
            raise HTTPException(
                status_code=404, detail=t("review_question_not_found", locale=locale)
            )
        if question.archived_at is not None:
            raise HTTPException(
                status_code=409, detail=t("archive_already_archived", locale=locale)
            )

        question.archived_at = datetime.utcnow()
        question.archived_by = current_user.id
        question.archive_reason = request.reason
        db.add(
            ReviewHistory(
                question_id=question.id,
                action="archived",
                old_status=question.review_status,
                new_status=question.review_status,
                changed_by=current_user.email,
                change_reason=request.reason or "Question archived",
            )
        )
        db.commit()
        db.refresh(question)
        logger.info(f"Archived question {question_id} by {current_user.email}")
        return _attach_reviewer_info(question, db)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error archiving question {question_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=t("archive_failed", locale=locale))


@router.post("/{question_id}/restore", response_model=QuestionReviewResponse)
async def restore_question(
    question_id: int,
    http_request: Request,
    current_user: User = Depends(require_permission("review_questions")),
    db: Session = Depends(get_db),
):
    """Stelle eine archivierte Frage wieder her (Status bleibt unverändert).

    **Required Permission:** `review_questions`
    """
    locale = get_request_locale(http_request, current_user)
    try:
        question = _get_scoped_question(db, question_id, current_user)
        if not question:
            raise HTTPException(
                status_code=404, detail=t("review_question_not_found", locale=locale)
            )
        if question.archived_at is None:
            raise HTTPException(
                status_code=409, detail=t("archive_not_archived", locale=locale)
            )

        question.archived_at = None
        question.archived_by = None
        question.archive_reason = None
        db.add(
            ReviewHistory(
                question_id=question.id,
                action="restored",
                old_status=question.review_status,
                new_status=question.review_status,
                changed_by=current_user.email,
                change_reason="Question restored",
            )
        )
        db.commit()
        db.refresh(question)
        logger.info(f"Restored question {question_id} by {current_user.email}")
        return _attach_reviewer_info(question, db)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error restoring question {question_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=t("restore_failed", locale=locale))


@router.delete("/{question_id}", status_code=200)
async def delete_question(
    question_id: int,
    http_request: Request,
    current_user: User = Depends(require_permission("delete_questions")),
    db: Session = Depends(get_db),
):
    """Lösche eine Frage endgültig (Hard-Delete). 3-fach geguarded.

    Voraussetzungen: Frage ist archiviert, in keiner Prüfung verwendet, und der
    Aufrufer hat `delete_questions`. Schreibt einen Audit-Snapshot, bevor die
    Zeile (per FK-Cascade) verschwindet.

    **Required Permission:** `delete_questions`
    """
    locale = get_request_locale(http_request, current_user)
    from services.audit_service import AuditService

    try:
        question = _get_scoped_question(db, question_id, current_user)
        if not question:
            raise HTTPException(
                status_code=404, detail=t("review_question_not_found", locale=locale)
            )

        block = _question_delete_block_reason(db, question, locale)
        if block:
            raise HTTPException(status_code=409, detail=block)

        # Snapshot fürs Audit-Log VOR dem Löschen erfassen (review_history stirbt
        # per Cascade mit). Der Delete wird zuerst gestaged und dann zusammen mit
        # dem Audit-Insert atomar committet: AuditService.log_action besitzt den
        # commit; schlägt der Audit-Insert fehl, rollt er auch den Delete zurück
        # und gibt None zurück -> wir brechen mit 500 ab. So gibt es weder einen
        # Delete ohne Audit noch ein Orphan-Audit für eine noch existierende Frage.
        snapshot = {
            "question_text": question.question_text,
            "review_status": question.review_status,
            "topic": question.topic,
            "created_by": question.created_by,
        }
        db.delete(question)
        db.flush()
        audit = AuditService.log_question_action(
            db,
            AuditService.ACTION_DELETE_QUESTION,
            current_user.id,
            question_id,
            request=http_request,
            additional_data=snapshot,
        )
        if audit is None:
            raise HTTPException(
                status_code=500, detail=t("delete_failed", locale=locale)
            )
        logger.info(f"Hard-deleted question {question_id} by {current_user.email}")
        return {"deleted": True, "id": question_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting question {question_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=t("delete_failed", locale=locale))


@router.post("/bulk-delete", response_model=BulkDeleteResult, status_code=200)
async def bulk_delete_questions(
    request: BulkDeleteRequest,
    http_request: Request,
    current_user: User = Depends(require_permission("delete_questions")),
    db: Session = Depends(get_db),
):
    """Bulk-Hard-Delete. Jede ID einzeln geguarded und einzeln atomar gelöscht.

    Pro Frage wird der Delete gestaged und über den (selbst-committenden)
    Audit-Insert atomar committet; schlägt das Audit fehl, rollt es diesen
    Delete zurück und die ID landet in ``blocked``. Bereits committete IDs
    bleiben bei einem unerwarteten Fehler bestehen; die laufende, nicht
    committete Frage wird zurückgerollt.

    **Required Permission:** `delete_questions`
    """
    locale = get_request_locale(http_request, current_user)
    from services.audit_service import AuditService

    deleted: list[int] = []
    blocked: list[dict] = []
    try:
        for qid in request.ids:
            question = _get_scoped_question(db, qid, current_user)
            if not question:
                blocked.append(
                    {"id": qid, "reason": t("review_question_not_found", locale=locale)}
                )
                continue
            reason = _question_delete_block_reason(db, question, locale)
            if reason:
                blocked.append({"id": qid, "reason": reason})
                continue
            snapshot = {
                "question_text": question.question_text,
                "review_status": question.review_status,
                "bulk": True,
            }
            db.delete(question)
            db.flush()
            audit = AuditService.log_question_action(
                db,
                AuditService.ACTION_DELETE_QUESTION,
                current_user.id,
                qid,
                request=http_request,
                additional_data=snapshot,
            )
            if audit is None:
                # Audit fehlgeschlagen -> log_action hat diesen Delete bereits
                # zurückgerollt; ID als blockiert melden statt still zu löschen.
                blocked.append({"id": qid, "reason": t("delete_failed", locale=locale)})
                continue
            deleted.append(qid)
        logger.info(f"Bulk-deleted {len(deleted)} questions by {current_user.email}")
        return {"deleted": deleted, "blocked": blocked}
    except Exception as e:
        db.rollback()
        logger.error(f"Error in bulk delete: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=t("delete_failed", locale=locale))


@router.get("/{question_id}/comments", response_model=List[CommentResponse])
async def get_comments(
    question_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Hole alle Comments für eine Question

    **Required:** Authenticated user
    """
    locale = get_request_locale(request, current_user)
    try:
        # Check if question exists
        question = _get_scoped_question(db, question_id, current_user)

        if not question:
            raise HTTPException(
                status_code=404, detail=t("review_question_not_found", locale=locale)
            )

        # Get Comments
        comments = (
            db.query(ReviewComment)
            .filter(ReviewComment.question_id == question_id)
            .order_by(ReviewComment.created_at.desc())
            .all()
        )

        return comments

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching comments for question {question_id}: {e}")
        raise HTTPException(
            status_code=500, detail=t("review_fetch_comments_failed", locale=locale)
        )


@router.post("/{question_id}/comments", response_model=CommentResponse, status_code=201)
async def add_comment(
    question_id: int,
    request: CommentCreate,
    http_request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Füge Comment zu Question hinzu

    **Required:** Authenticated user
    """
    locale = get_request_locale(http_request, current_user)
    try:
        # Check if question exists
        question = _get_scoped_question(db, question_id, current_user)

        if not question:
            raise HTTPException(
                status_code=404, detail=t("review_question_not_found", locale=locale)
            )

        # Create Comment
        comment = ReviewComment(
            question_id=question.id,
            comment_text=request.comment_text,
            comment_type=request.comment_type,
            author=f"{current_user.first_name} {current_user.last_name}",
            author_role="reviewer"
            if question.reviewed_by and current_user.id == question.reviewed_by
            else "user",
        )

        db.add(comment)
        db.commit()
        db.refresh(comment)

        logger.info(f"Added comment to question {question_id} by {current_user.email}")
        return comment

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding comment to question {question_id}: {e}")
        raise HTTPException(
            status_code=500, detail=t("review_add_comment_failed", locale=locale)
        )


@router.get("/{question_id}/history", response_model=List[HistoryResponse])
async def get_question_history(
    question_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Hole History für Question

    **Required:** Authenticated user
    """
    locale = get_request_locale(request, current_user)
    try:
        # Check if question exists
        question = _get_scoped_question(db, question_id, current_user)

        if not question:
            raise HTTPException(
                status_code=404,
                detail=t("review_question_not_found", locale=locale),
            )

        # Get History
        history = (
            db.query(ReviewHistory)
            .filter(ReviewHistory.question_id == question_id)
            .order_by(ReviewHistory.changed_at.desc())
            .all()
        )

        return history

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching history for question {question_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=t("review_fetch_history_failed", locale=locale),
        )


# --- Tag-Endpunkte ---


class _SetTagsRequest(BaseModel):
    tag_ids: list[int]


class _QuestionTagsOut(BaseModel):
    tags: list[TagOut]


def _assign_tags_to_question(
    db: Session,
    question_id: int,
    tag_ids: list[int],
    current_user: User,
) -> None:
    """Weist einer Frage Tags zu (ersetzt bestehende vollständig).

    Validiert Institution-Zugehörigkeit und Archiviert-Status. Cross-Tenant-
    Enumeration wird verhindert: unbekannte und fremde Tag-IDs führen zum
    gleichen 422-Response, ohne die IDs zu echoen.
    """
    # Visible to this user: own institution + global
    visible = (
        db.query(Tag)
        .filter(
            Tag.id.in_(tag_ids),
            (Tag.institution_id == current_user.institution_id)
            | (Tag.scope == "global"),
        )
        .all()
    )
    if len(visible) != len(set(tag_ids)):
        raise HTTPException(status_code=422, detail="Ungültige Tag-IDs.")

    for tag in visible:
        if tag.is_archived:
            raise HTTPException(
                status_code=422,
                detail=f"Tag '{tag.name}' ist archiviert.",
            )

    db.query(QuestionTag).filter(QuestionTag.question_id == question_id).delete()
    for tag_id in tag_ids:
        db.add(QuestionTag(question_id=question_id, tag_id=tag_id))

    db.flush()


@router.post("/{question_id}/tags", response_model=_QuestionTagsOut)
async def set_question_tags(
    question_id: int,
    body: _SetTagsRequest,
    current_user: User = Depends(require_permission("edit_questions")),
    db: Session = Depends(get_db),
):
    """Tags einer Frage setzen (ersetzt bestehende Tags vollständig)."""
    question = _get_scoped_question(db, question_id, current_user)
    if not question:
        raise HTTPException(status_code=404, detail="Frage nicht gefunden.")

    _assign_tags_to_question(db, question_id, body.tag_ids, current_user)
    db.commit()
    db.refresh(question)
    return _QuestionTagsOut(tags=question.tags)


@router.delete("/{question_id}/tags/{tag_id}", response_model=_QuestionTagsOut)
async def remove_question_tag(
    question_id: int,
    tag_id: int,
    current_user: User = Depends(require_permission("edit_questions")),
    db: Session = Depends(get_db),
):
    """Einzelnen Tag von einer Frage entfernen."""
    question = _get_scoped_question(db, question_id, current_user)
    if not question:
        raise HTTPException(status_code=404, detail="Frage nicht gefunden.")

    db.query(QuestionTag).filter(
        QuestionTag.question_id == question_id,
        QuestionTag.tag_id == tag_id,
    ).delete()
    db.commit()
    db.refresh(question)
    return _QuestionTagsOut(tags=question.tags)
