"""
Question Review API Endpoints for ExamCraft AI
Implements review workflow for generated exam questions
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
    QuestionReviewVisibility,
    ReviewComment,
    ReviewHistory,
    ReviewStatus,
)
from models.auth import User
from models.tag import Tag, QuestionTag
from api.tags import TagOut
from schemas.generation_metadata import GenerationMetadata
from services.org_unit_service import get_user_accessible_org_unit_ids
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
    """TF-400: brief of the assessed competency (HK) for display.

    None if the question has no competency assigned (legacy data or a code
    with no match). ``module_code`` comes from the associated framework.
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
        # TF-400: assessed competency + LN level (shown in the
        # review queue/detail). None for questions without a competency link.
        "competency_id": question.competency_id,
        "ln_level": question.ln_level,
        "competency": _serialize_competency(question),
        # TF-642: question pool visibility — informational here (the review
        # queue does not filter by it, see utils/question_visibility.py).
        "visibility": (
            question.visibility.value if question.visibility is not None else None
        ),
        "org_unit_id": question.org_unit_id,
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
    """Request model for a new question review"""

    question_text: str = Field(..., min_length=10, max_length=5000)
    question_type: str = Field(
        ..., pattern="^(single_choice|multiple_choice|open_ended|true_false)$"
    )
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
    """Request model for a question update"""

    question_text: Optional[str] = Field(None, min_length=10, max_length=5000)
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    difficulty: Optional[str] = Field(None, pattern="^(easy|medium|hard)$")
    bloom_level: Optional[int] = Field(None, ge=1, le=6)
    estimated_time_minutes: Optional[int] = Field(None, ge=1, le=180)
    # TF-642: change visibility in the question pool. org_unit_id is only
    # allowed together with visibility="team" (see
    # _resolve_question_visibility_update) — must be an Org-Unit the editor
    # themselves belongs to.
    visibility: Optional[str] = Field(None, pattern="^(private|team|institution)$")
    org_unit_id: Optional[int] = None


class ReviewActionRequest(BaseModel):
    """Request model for review actions (approve/reject)"""

    comment: Optional[str] = Field(None, max_length=2000)
    reason: Optional[str] = Field(None, max_length=500)


class CommentCreate(BaseModel):
    """Request model for a new comment"""

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
    """TF-400: lean view of the assessed competency for the

    question display (code + title + module), without the full descriptor tree.
    """

    id: int
    code: str
    title: str
    framework_id: int
    module_code: Optional[str] = None

    class Config:
        from_attributes = True


class QuestionReviewResponse(BaseModel):
    """Response model for a question review"""

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
    # TF-400: assessed competency (HK) + LN level (1-4, distinct from
    # bloom_level). ``competency`` is the lean brief for display.
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
    # TF-642: question pool visibility (governs list_approved_questions only —
    # see utils/question_visibility.py). Not the review queue visibility.
    visibility: str = "institution"
    org_unit_id: Optional[int] = None

    # TF-330: legacy records store ``options`` as a dict keyed by
    # 'A'/'B'/'C'/'D'. Normalize on read so the API never 500s on these rows.
    @field_validator("options", mode="before")
    @classmethod
    def _normalize_options(cls, value: Any) -> Any:
        return normalize_options(value)

    # TF-642: ``question.visibility`` is a ``QuestionReviewVisibility`` enum
    # member when this model is built ``from_attributes`` off the ORM object
    # directly (e.g. edit_question's return) — normalize to the plain string
    # value the field declares. ``_question_to_dict`` already passes a plain
    # string, so this is a no-op there.
    @field_validator("visibility", mode="before")
    @classmethod
    def _normalize_visibility(cls, value: Any) -> Any:
        return value.value if isinstance(value, QuestionReviewVisibility) else value

    class Config:
        from_attributes = True


class CommentResponse(BaseModel):
    """Response model for a comment"""

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
    """Response model for a history entry"""

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
    """Detailed response with comments and history"""

    comments: List[CommentResponse] = []
    history: List[HistoryResponse] = []


class ReviewQueueResponse(BaseModel):
    """Response model for the review queue"""

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
        None, pattern="^(single_choice|multiple_choice|open_ended|true_false)$"
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
    Fetch the review queue with filters

    **Required:** Authenticated user

    - **status**: filter by review status
    - **difficulty**: filter by difficulty level
    - **question_type**: filter by question type
    - **exam_id**: filter by exam ID
    - **limit**: maximum number of results
    - **offset**: offset for pagination
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
        # TF-396: archive axis. Default: only active questions (archived_at IS NULL).
        if archived_only:
            query = query.filter(QuestionReview.archived_at.isnot(None))
        elif not include_archived:
            query = query.filter(QuestionReview.archived_at.is_(None))

        # Get Statistics — also institution-scoped
        base_stats = TenantFilter.filter_by_tenant(
            db.query(QuestionReview), QuestionReview, tenant_context
        )
        # TF-396: stats follow the same archive filter as the list, so the
        # badge counters match the displayed set (otherwise they would
        # over-count once questions are archived).
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
    Fetch a detailed question review with comments and history

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
    Create a new question review

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
            request=http_request,
            additional_data={
                "topic": question.topic,
                "difficulty": question.difficulty,
            },
        )

        logger.info(f"Created question review {question.id}")
        return question

    except HTTPException:
        # Don't rewrap an audit-failure 500 from check_question_limit/
        # log_superuser_bypass into a generic 500 — otherwise the GDPR
        # signal is lost in the logs.
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating question review: {e}")
        raise HTTPException(
            status_code=500, detail=t("review_create_failed", locale=locale)
        )


def _resolve_question_visibility_update(
    question: QuestionReview,
    request: QuestionReviewUpdate,
    user: User,
    db: Session,
) -> Optional[tuple]:
    """TF-642: validate a visibility/org_unit_id change on ``PUT .../edit``.

    Mirrors premium's ``_resolve_prompt_tier`` (TF-641): ``team`` visibility
    requires an ``org_unit_id`` the editor themselves has (hierarchical)
    access to, via ``get_user_accessible_org_unit_ids`` — any other
    visibility clears ``org_unit_id``. Returns ``None`` when neither field
    ends up changed (nothing to apply), else the validated
    ``(QuestionReviewVisibility, Optional[int])`` pair to assign.

    Ownership-gated (owner or superuser only), unlike the rest of this
    endpoint's fields, which stay permission+institution scoped per the
    /grilling TF-642 decision — that decision covers *pre-existing*
    review-workflow mutation (question_text, difficulty, ...), not this new
    access-control surface. Mirrors Document/TF-620's identical rule ("a
    colleague who merely *sees* a team-scoped doc must not be able to move
    it") rather than the broader edit-permission gate.
    """
    if request.visibility is None and request.org_unit_id is None:
        return None

    is_owner = question.created_by is not None and question.created_by == user.id
    if not is_owner and not user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Nur der Ersteller oder ein SuperUser darf die Sichtbarkeit ändern.",
        )

    new_visibility = (
        QuestionReviewVisibility(request.visibility)
        if request.visibility is not None
        else question.visibility
    )
    new_org_unit_id = (
        request.org_unit_id if request.org_unit_id is not None else question.org_unit_id
    )

    if new_visibility == QuestionReviewVisibility.TEAM:
        if new_org_unit_id is None:
            raise HTTPException(
                status_code=400,
                detail=("Team-Sichtbarkeit erfordert eine Org-Unit (org_unit_id)."),
            )
        # SuperUser bugfix: validating against the ACTING user's own
        # membership would reject a superuser re-tiering someone else's
        # question, since a superuser typically isn't a member of the
        # question's own Org-Unit at all — mirrors the Document/TF-620
        # update-path superuser gate and Prompt/TF-641's
        # skip_org_unit_membership_check.
        if not user.is_superuser:
            accessible = (
                get_user_accessible_org_unit_ids(db, user.id, user.institution_id)
                if user.institution_id
                else set()
            )
            if new_org_unit_id not in accessible:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Team-Sichtbarkeit erfordert eine eigene Org-Unit "
                        "(org_unit_id), der du selbst angehörst."
                    ),
                )
    elif new_visibility == QuestionReviewVisibility.INSTITUTION:
        # Bugfix: an orphaned question (institution_id IS NULL — reachable by
        # a superuser via _get_scoped_question's tenant-filter bypass) would
        # otherwise pass validation here and then trip
        # ck_question_reviews_institution_visibility_requires_institution on
        # commit, surfacing as an opaque 500 through edit_question's broad
        # except-Exception handler instead of this clear 400. Mirrors
        # documents.py's identical guard (documents_visibility_no_institution).
        if question.institution_id is None:
            raise HTTPException(
                status_code=400,
                detail="Institutions-Sichtbarkeit erfordert eine Institution.",
            )
        new_org_unit_id = None
    else:
        new_org_unit_id = None

    if (
        new_visibility == question.visibility
        and new_org_unit_id == question.org_unit_id
    ):
        return None

    return new_visibility, new_org_unit_id


@router.put("/{question_id}/edit", response_model=QuestionReviewResponse)
async def edit_question(
    question_id: int,
    request: QuestionReviewUpdate,
    http_request: Request,
    current_user: User = Depends(require_permission("edit_questions")),
    db: Session = Depends(get_db),
):
    """
    Edit a question (inline editing)

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

        visibility_update = _resolve_question_visibility_update(
            question, request, current_user, db
        )
        if visibility_update is not None:
            new_visibility, new_org_unit_id = visibility_update
            # Bugfix: record each field that actually changed independently
            # — moving a TEAM question between Org-Units with visibility
            # unchanged previously still wrote {"visibility": {"old": "team",
            # "new": "team"}}, an entry that reads as "nothing changed" while
            # the accessible audience for the question actually did.
            if new_visibility != question.visibility:
                changed_fields["visibility"] = {
                    "old": question.visibility.value if question.visibility else None,
                    "new": new_visibility.value,
                }
            if new_org_unit_id != question.org_unit_id:
                changed_fields["org_unit_id"] = {
                    "old": question.org_unit_id,
                    "new": new_org_unit_id,
                }
            question.visibility = new_visibility
            question.org_unit_id = new_org_unit_id

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

        # TF-504: question edits were only recorded in review_history, not in
        # audit_logs (the edit action was defined but emitted by no code path,
        # unlike create/approve/reject/delete which are audited). Store only the
        # changed-field *keys* here — the full old/new values already live in
        # review_history, so duplicating them into audit_logs would bloat the row
        # without adding signal.
        from services.audit_service import AuditService

        AuditService.log_question_action(
            db,
            AuditService.ACTION_EDIT_QUESTION,
            current_user.id,
            question.id,
            request=http_request,
            additional_data={"changed_fields": sorted(changed_fields.keys())},
        )

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
    Mark a question as 'In Review'.

    Signals to other reviewers that this question is currently being worked on.

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
    Approve a question

    **Required Permission:** `approve_questions` (Dozent, Admin)
    """
    locale = get_request_locale(http_request, current_user)
    try:
        question = _get_scoped_question(db, question_id, current_user)

        if not question:
            raise HTTPException(
                status_code=404, detail=t("review_question_not_found", locale=locale)
            )

        # Four-eyes principle check
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
            request=http_request,
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
    Reject a question

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
            request=http_request,
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
# TF-396: archive / restore / hard delete
# ---------------------------------------------------------------------------


class ArchiveRequest(BaseModel):
    """Request model for archiving."""

    reason: Optional[str] = Field(None, max_length=500)


class BulkDeleteRequest(BaseModel):
    """Request model for bulk hard delete."""

    ids: list[int] = Field(..., min_length=1, max_length=200)


class BlockedDeletion(BaseModel):
    """A question rejected in the bulk delete, with an i18n reason."""

    id: int
    reason: str


class BulkDeleteResult(BaseModel):
    """Result of a bulk hard delete: deleted IDs + rejected entries."""

    deleted: list[int]
    blocked: list[BlockedDeletion]


def _question_delete_block_reason(
    db: Session, question: QuestionReview, locale: str
) -> str | None:
    """i18n reason if the question may NOT be hard-deleted, else ``None``.

    Guard (TF-396): only archived questions that are not used in any exam
    may be hard-deleted. "Not used in any exam" transitively also covers
    student answers (attempt_answers -> exam_questions).
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
    """Archive a question (orthogonal to review_status).

    Hides the question from the bank/lists; it is retained in exams.

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
    """Restore an archived question (status remains unchanged).

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
    """Permanently delete a question (hard delete). Triple-guarded.

    Preconditions: the question is archived, is not used in any exam, and
    the caller has `delete_questions`. Writes an audit snapshot before the
    row disappears (via FK cascade).

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

        # Capture a snapshot for the audit log BEFORE deletion (review_history
        # dies along with it via cascade). The delete is staged first and then
        # committed atomically together with the audit insert:
        # AuditService.log_action owns the commit; if the audit insert fails
        # it also rolls back the delete and returns None -> we abort with 500.
        # This way there's never a delete without an audit, nor an orphan
        # audit for a question that still exists.
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
    """Bulk hard delete. Each ID individually guarded and individually
    committed atomically.

    For each question, the delete is staged and committed atomically via
    the (self-committing) audit insert; if the audit fails, it rolls back
    that delete and the ID ends up in ``blocked``. Already-committed IDs
    remain in place on an unexpected error; the in-flight, uncommitted
    question is rolled back.

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
                # Audit failed -> log_action has already rolled back this
                # delete; report the ID as blocked instead of silently deleting.
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
    Fetch all comments for a question

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
    Add a comment to a question

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
    Fetch the history for a question

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


# --- Tag Endpoints ---


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
    """Assigns tags to a question (fully replaces existing ones).

    Validates institution membership and archived status. Cross-tenant
    enumeration is prevented: unknown and foreign tag IDs produce the same
    422 response, without echoing the IDs back.
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
    """Set tags on a question (fully replaces existing tags)."""
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
    """Remove a single tag from a question."""
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
