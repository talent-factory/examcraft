"""
Question Review API Endpoints für ExamCraft AI
Implementiert Review-Workflow für generierte Prüfungsfragen
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models.question_review import (
    QuestionReview,
    ReviewComment,
    ReviewHistory,
    ReviewStatus,
)
from models.auth import User
from utils.auth_utils import get_current_active_user, require_permission
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/questions", tags=["Question Review"])


def _attach_reviewer_info(question: QuestionReview, db: Session) -> dict:
    """Convert QuestionReview to dict with reviewer_info joined."""
    data = {
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
        "review_status": question.review_status,
        "reviewed_by": question.reviewed_by,
        "reviewed_at": question.reviewed_at,
        "exam_id": question.exam_id,
        "created_at": question.created_at,
        "updated_at": question.updated_at,
    }
    if question.reviewed_by:
        reviewer = db.query(User).filter(User.id == question.reviewed_by).first()
        if reviewer:
            data["reviewer_info"] = {
                "id": reviewer.id,
                "first_name": reviewer.first_name,
                "last_name": reviewer.last_name,
                "email": reviewer.email,
            }
    return data


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
    estimated_time_minutes: Optional[int]
    quality_tier: Optional[str]
    review_status: str
    reviewed_by: Optional[int]
    reviewer_info: Optional["ReviewerInfo"] = None
    reviewed_at: Optional[datetime]
    exam_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReviewerInfo(BaseModel):
    """Reviewer User Info"""

    id: int
    first_name: str
    last_name: str
    email: str

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
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
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
    try:
        # Base Query
        query = db.query(QuestionReview)

        # Apply Filters
        if status:
            query = query.filter(QuestionReview.review_status == status)
        if difficulty:
            query = query.filter(QuestionReview.difficulty == difficulty)
        if question_type:
            query = query.filter(QuestionReview.question_type == question_type)
        if exam_id:
            query = query.filter(QuestionReview.exam_id == exam_id)

        # Get Statistics
        total = query.count()
        pending = (
            db.query(QuestionReview)
            .filter(QuestionReview.review_status == ReviewStatus.PENDING.value)
            .count()
        )
        approved = (
            db.query(QuestionReview)
            .filter(QuestionReview.review_status == ReviewStatus.APPROVED.value)
            .count()
        )
        rejected = (
            db.query(QuestionReview)
            .filter(QuestionReview.review_status == ReviewStatus.REJECTED.value)
            .count()
        )
        in_review = (
            db.query(QuestionReview)
            .filter(QuestionReview.review_status == ReviewStatus.IN_REVIEW.value)
            .count()
        )

        # Get Questions with Pagination
        question_list = (
            query.order_by(QuestionReview.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

        questions = [_attach_reviewer_info(q, db) for q in question_list]

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
            status_code=500, detail=f"Failed to fetch review queue: {str(e)}"
        )


@router.get("/{question_id}/review", response_model=QuestionReviewDetailResponse)
async def get_question_review(
    question_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Hole detaillierte Question Review mit Comments und History

    **Required:** Authenticated user
    """
    try:
        question = (
            db.query(QuestionReview).filter(QuestionReview.id == question_id).first()
        )

        if not question:
            raise HTTPException(
                status_code=404, detail=f"Question {question_id} not found"
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
            status_code=500, detail=f"Failed to fetch question review: {str(e)}"
        )


@router.post("/review", response_model=QuestionReviewResponse, status_code=201)
async def create_question_review(
    request: QuestionReviewCreate,
    current_user: User = Depends(require_permission("create_questions")),
    db: Session = Depends(get_db),
):
    """
    Erstelle neue Question Review

    **Required Permission:** `create_questions` (Dozent, Assistant, Admin)
    """
    try:
        # Check question generation limit for institution
        from utils.tenant_utils import SubscriptionLimits

        SubscriptionLimits.check_question_limit(current_user.institution, db)

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
        db.commit()
        db.refresh(question)

        # Create History Entry
        history = ReviewHistory(
            question_id=question.id,
            action="created",
            new_status=ReviewStatus.PENDING.value,
            changed_by="system",
            change_reason="Question created",
        )
        db.add(history)
        db.commit()

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

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating question review: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create question review: {str(e)}"
        )


@router.put("/{question_id}/edit", response_model=QuestionReviewResponse)
async def edit_question(
    question_id: int,
    request: QuestionReviewUpdate,
    current_user: User = Depends(require_permission("edit_questions")),
    db: Session = Depends(get_db),
):
    """
    Bearbeite Question (Inline Editing)

    **Required Permission:** `edit_questions` (Dozent, Assistant, Admin)
    """
    try:
        question = (
            db.query(QuestionReview).filter(QuestionReview.id == question_id).first()
        )

        if not question:
            raise HTTPException(
                status_code=404, detail=f"Question {question_id} not found"
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
            status_code=500, detail=f"Failed to edit question: {str(e)}"
        )


@router.post("/{question_id}/start-review", response_model=QuestionReviewResponse)
async def start_review(
    question_id: int,
    current_user: User = Depends(require_permission("approve_questions")),
    db: Session = Depends(get_db),
):
    """
    Markiere Frage als 'In Review'.

    Signalisiert anderen Reviewern, dass diese Frage gerade bearbeitet wird.

    **Required Permission:** `approve_questions` (Dozent, Admin)
    """
    try:
        question = (
            db.query(QuestionReview).filter(QuestionReview.id == question_id).first()
        )

        if not question:
            raise HTTPException(
                status_code=404, detail=f"Question {question_id} not found"
            )

        if question.review_status not in (
            ReviewStatus.PENDING.value,
            ReviewStatus.EDITED.value,
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Frage kann nur aus Status 'pending' oder 'edited' in Review genommen werden (aktuell: {question.review_status}).",
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
            detail="Fehler beim Starten des Reviews. Bitte versuchen Sie es erneut.",
        )


@router.post("/{question_id}/approve", response_model=QuestionReviewResponse)
async def approve_question(
    question_id: int,
    request: ReviewActionRequest,
    current_user: User = Depends(require_permission("approve_questions")),
    db: Session = Depends(get_db),
):
    """
    Genehmige Question

    **Required Permission:** `approve_questions` (Dozent, Admin)
    """
    try:
        question = (
            db.query(QuestionReview).filter(QuestionReview.id == question_id).first()
        )

        if not question:
            raise HTTPException(
                status_code=404, detail=f"Question {question_id} not found"
            )

        # Vier-Augen-Prinzip Check
        if question.institution_id and question.reviewed_by:
            from models.auth import Institution

            institution = (
                db.query(Institution)
                .filter(Institution.id == question.institution_id)
                .first()
            )
            if (
                institution
                and institution.require_second_reviewer
                and current_user.id == question.reviewed_by
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Vier-Augen-Prinzip: Ein anderer Reviewer muss diese Frage genehmigen.",
                )

        old_status = question.review_status

        # Update Question
        question.review_status = ReviewStatus.APPROVED.value
        question.reviewed_at = datetime.utcnow()

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
            additional_data={"reason": request.reason},
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
            detail="Fehler beim Genehmigen der Frage. Bitte versuchen Sie es erneut.",
        )


@router.post("/{question_id}/reject", response_model=QuestionReviewResponse)
async def reject_question(
    question_id: int,
    request: ReviewActionRequest,
    current_user: User = Depends(require_permission("approve_questions")),
    db: Session = Depends(get_db),
):
    """
    Lehne Question ab

    **Required Permission:** `approve_questions` (Dozent, Admin)
    """
    try:
        question = (
            db.query(QuestionReview).filter(QuestionReview.id == question_id).first()
        )

        if not question:
            raise HTTPException(
                status_code=404, detail=f"Question {question_id} not found"
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
            additional_data={"reason": request.reason},
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
            detail="Fehler beim Ablehnen der Frage. Bitte versuchen Sie es erneut.",
        )


@router.get("/{question_id}/comments", response_model=List[CommentResponse])
async def get_comments(
    question_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Hole alle Comments für eine Question

    **Required:** Authenticated user
    """
    try:
        # Check if question exists
        question = (
            db.query(QuestionReview).filter(QuestionReview.id == question_id).first()
        )

        if not question:
            raise HTTPException(
                status_code=404, detail=f"Question {question_id} not found"
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
            status_code=500, detail=f"Failed to fetch comments: {str(e)}"
        )


@router.post("/{question_id}/comments", response_model=CommentResponse, status_code=201)
async def add_comment(
    question_id: int,
    request: CommentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Füge Comment zu Question hinzu

    **Required:** Authenticated user
    """
    try:
        # Check if question exists
        question = (
            db.query(QuestionReview).filter(QuestionReview.id == question_id).first()
        )

        if not question:
            raise HTTPException(
                status_code=404, detail=f"Question {question_id} not found"
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
        raise HTTPException(status_code=500, detail=f"Failed to add comment: {str(e)}")


@router.get("/{question_id}/history", response_model=List[HistoryResponse])
async def get_question_history(question_id: int, db: Session = Depends(get_db)):
    """
    Hole History für Question
    """
    try:
        # Check if question exists
        question = (
            db.query(QuestionReview).filter(QuestionReview.id == question_id).first()
        )

        if not question:
            raise HTTPException(
                status_code=404, detail=f"Question {question_id} not found"
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
            status_code=500, detail=f"Failed to fetch history: {str(e)}"
        )
