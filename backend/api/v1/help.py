import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database import get_db
from utils.auth_utils import get_current_active_user
from models.auth import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/help", tags=["Help"])

ONBOARDING_MAX_STEPS = {"teacher": 8, "admin": 13}


# === STATUS ===


class HelpStatusResponse(BaseModel):
    modes: Dict[str, bool]


@router.get("/status", response_model=HelpStatusResponse)
async def get_help_status():
    """Public: returns which help modes are available."""
    qdrant_available = False
    try:
        from services.vector_service_factory import vector_service

        qdrant_available = (
            hasattr(vector_service, "client") and vector_service.client is not None
        )
    except Exception as e:
        logger.warning(f"Qdrant availability check failed: {e}")
    return HelpStatusResponse(
        modes={"onboarding": True, "context": True, "chat": qdrant_available}
    )


# === ONBOARDING ===


class OnboardingStatusResponse(BaseModel):
    id: Optional[int] = None
    role: str
    current_step: int
    completed_steps: List[int]
    skipped_steps: List[int] = []
    completed: bool


class OnboardingStepRequest(BaseModel):
    step: int = Field(..., ge=0)


def _get_user_role(user: User) -> str:
    return "admin" if any(r.name == "admin" for r in user.roles) else "teacher"


def _get_user_tier(user: User) -> str:
    return (
        getattr(user.institution, "subscription_tier", "free")
        if user.institution
        else "free"
    )


@router.get("/onboarding/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    from models.help import HelpOnboardingProgress

    progress = (
        db.query(HelpOnboardingProgress)
        .filter(HelpOnboardingProgress.user_id == current_user.id)
        .first()
    )
    role = _get_user_role(current_user)
    if not progress:
        return OnboardingStatusResponse(
            role=role,
            current_step=0,
            completed_steps=[],
            skipped_steps=[],
            completed=False,
        )
    return OnboardingStatusResponse(
        id=progress.id,
        role=progress.role,
        current_step=progress.current_step,
        completed_steps=progress.completed_steps or [],
        skipped_steps=progress.skipped_steps or [],
        completed=progress.completed_at is not None,
    )


@router.put("/onboarding/step", response_model=OnboardingStatusResponse)
async def complete_onboarding_step(
    request: OnboardingStepRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    from models.help import HelpOnboardingProgress
    from datetime import datetime, timezone

    role = _get_user_role(current_user)
    progress = (
        db.query(HelpOnboardingProgress)
        .filter(HelpOnboardingProgress.user_id == current_user.id)
        .first()
    )
    if not progress:
        progress = HelpOnboardingProgress(
            user_id=current_user.id, role=role, current_step=0, completed_steps=[]
        )
        db.add(progress)

    completed = list(progress.completed_steps or [])
    if request.step not in completed:
        completed.append(request.step)
    progress.completed_steps = completed

    # Catch-up: wenn step in skipped_steps war, daraus entfernen
    skipped = list(progress.skipped_steps or [])
    if request.step in skipped:
        skipped.remove(request.step)
        progress.skipped_steps = skipped

    progress.current_step = request.step + 1

    max_steps = ONBOARDING_MAX_STEPS.get(role, 6)

    if progress.current_step >= max_steps:
        progress.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(progress)
    return OnboardingStatusResponse(
        id=progress.id,
        role=progress.role,
        current_step=progress.current_step,
        completed_steps=progress.completed_steps,
        skipped_steps=progress.skipped_steps or [],
        completed=progress.completed_at is not None,
    )


@router.put("/onboarding/skip", response_model=OnboardingStatusResponse)
async def skip_onboarding_step(
    request: OnboardingStepRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    from models.help import HelpOnboardingProgress
    from datetime import datetime, timezone

    role = _get_user_role(current_user)
    progress = (
        db.query(HelpOnboardingProgress)
        .filter(HelpOnboardingProgress.user_id == current_user.id)
        .first()
    )
    if not progress:
        progress = HelpOnboardingProgress(
            user_id=current_user.id,
            role=role,
            current_step=0,
            completed_steps=[],
            skipped_steps=[],
        )
        db.add(progress)

    skipped = list(progress.skipped_steps or [])
    if request.step not in skipped:
        skipped.append(request.step)
    progress.skipped_steps = skipped
    progress.current_step = request.step + 1

    max_steps = ONBOARDING_MAX_STEPS.get(role, 6)
    if progress.current_step >= max_steps:
        progress.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(progress)
    return OnboardingStatusResponse(
        id=progress.id,
        role=progress.role,
        current_step=progress.current_step,
        completed_steps=progress.completed_steps or [],
        skipped_steps=progress.skipped_steps or [],
        completed=progress.completed_at is not None,
    )


# === CONTEXT HINTS ===


class ContextHintResponse(BaseModel):
    hint_text: Optional[str] = None
    hint_id: Optional[int] = None


@router.get("/context/{route:path}", response_model=ContextHintResponse)
async def get_context_hint(
    route: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    from services.help_context_service import HelpContextService
    from services.translation_service import get_request_locale

    locale = get_request_locale(request, current_user)
    role = _get_user_role(current_user)
    tier = _get_user_tier(current_user)

    service = HelpContextService(db)
    hint = service.get_hint_for_route(
        route, role, tier, locale, user_id=current_user.id
    )
    if hint:
        return ContextHintResponse(hint_text=hint["hint_text"], hint_id=hint["id"])
    return ContextHintResponse()


class DismissHintRequest(BaseModel):
    hint_id: int


@router.post("/context/dismiss", status_code=204)
async def dismiss_hint(
    request_body: DismissHintRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    from models.help import HelpDismissedHint

    existing = (
        db.query(HelpDismissedHint)
        .filter(
            HelpDismissedHint.user_id == current_user.id,
            HelpDismissedHint.hint_id == request_body.hint_id,
        )
        .first()
    )
    if not existing:
        db.add(HelpDismissedHint(user_id=current_user.id, hint_id=request_body.hint_id))
        db.commit()


# === CHAT MESSAGE ===


class ConversationMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., max_length=2000)


class HelpMessageRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)
    route: str = Field(default="/")
    conversation_history: Optional[List[ConversationMessage]] = None


class HelpMessageResponse(BaseModel):
    answer: str
    confidence: float
    sources: List[Dict[str, Any]] = []
    docs_links: List[str] = []
    escalate: bool = False
    from_cache: bool = False


@router.post("/message", response_model=HelpMessageResponse)
async def send_help_message(
    request_body: HelpMessageRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    # Rate limiting: max 20 requests/hour per user
    try:
        from services.redis_service import RedisService

        redis_client = RedisService.get_ratelimit_client()
        rate_key = f"help_message_rate:{current_user.id}"
        pipe = redis_client.pipeline()
        pipe.incr(rate_key)
        pipe.expire(rate_key, 3600, nx=True)
        results = pipe.execute()
        current_count = results[0]
        if current_count > 20:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded: max 20 help questions per hour",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Redis rate limiting unavailable, allowing request: {e}")

    from services.help_service import HelpService
    from services.translation_service import get_request_locale

    locale = get_request_locale(request, current_user)
    role = _get_user_role(current_user)
    tier = _get_user_tier(current_user)

    service = HelpService(db)
    result = await service.answer_question(
        question=request_body.question,
        user_role=role,
        user_tier=tier,
        route=request_body.route,
        conversation_history=request_body.conversation_history,
        locale=locale,
    )

    if result.get("escalate"):
        from models.help import HelpFeedback

        db.add(
            HelpFeedback(
                question=request_body.question,
                answer=result["answer"],
                confidence=result["confidence"],
                user_role=role,
                user_tier=tier,
                route=request_body.route,
                language=locale,
                status="offen",
            )
        )
        db.commit()

    return HelpMessageResponse(**result)


# === FEEDBACK ===


class FeedbackRequest(BaseModel):
    question: str
    answer: Optional[str] = None
    confidence: Optional[float] = None
    rating: str = Field(..., pattern="^(up|down)$")
    route: str = Field(default="/")


class FeedbackResponse(BaseModel):
    id: int
    status: str


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request_body: FeedbackRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    from services.help_feedback_service import HelpFeedbackService
    from services.translation_service import get_request_locale

    locale = get_request_locale(request, current_user)
    role = _get_user_role(current_user)
    tier = _get_user_tier(current_user)

    service = HelpFeedbackService(db)
    feedback = service.submit_feedback(
        question=request_body.question,
        answer=request_body.answer,
        confidence=request_body.confidence,
        rating=request_body.rating,
        user_role=role,
        user_tier=tier,
        route=request_body.route,
        language=locale,
    )
    result = FeedbackResponse(id=feedback.id, status=feedback.status)

    # Dispatch async feedback processing (clustering + triggers)
    try:
        from tasks.feedback_tasks import process_feedback_task

        process_feedback_task.delay(feedback.id)
    except Exception as e:
        logger.warning(f"Could not dispatch feedback processing: {e}")

    return result


# === ADMIN ===


class FeedbackQueueResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int


class FeedbackUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(offen|in_bearbeitung|dokumentiert)$")


class MetricsResponse(BaseModel):
    total_questions: int
    positive_feedback_pct: float
    open_feedback_count: int
    avg_confidence: float


class ClusterResponse(BaseModel):
    id: int
    topic_label: str
    positive_count: int
    negative_count: int
    total_count: int
    status: str
    docs_gap: bool
    suggested_answer_de: Optional[str] = None
    suggested_answer_en: Optional[str] = None


class ClusterListResponse(BaseModel):
    items: List[ClusterResponse]
    total: int


class FaqCandidateResponse(BaseModel):
    id: int
    question_text: str
    answer_de: str
    answer_en: str
    faq_status: str
    cluster_id: Optional[int] = None
    hit_count: int


class FaqCandidateListResponse(BaseModel):
    items: List[FaqCandidateResponse]
    total: int


class FaqApproveRequest(BaseModel):
    answer_de: Optional[str] = None
    answer_en: Optional[str] = None


def _require_admin(user: User):
    if not getattr(user, "is_superuser", False):
        raise HTTPException(status_code=403, detail="Superadmin access required")


@router.get("/admin/feedback-queue", response_model=FeedbackQueueResponse)
async def get_feedback_queue(
    status: Optional[str] = Query(
        default=None, pattern="^(offen|in_bearbeitung|dokumentiert)$"
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    from services.help_feedback_service import HelpFeedbackService

    service = HelpFeedbackService(db)
    items = service.get_feedback_queue(status=status, limit=limit, offset=offset)
    total = service.get_feedback_count(status=status)
    return FeedbackQueueResponse(items=items, total=total)


@router.put("/admin/feedback/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback_status(
    feedback_id: int,
    request_body: FeedbackUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    from services.help_feedback_service import HelpFeedbackService

    service = HelpFeedbackService(db)
    feedback = service.update_feedback_status(feedback_id, request_body.status)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return FeedbackResponse(id=feedback.id, status=feedback.status)


@router.post("/admin/reindex")
async def trigger_reindex(
    full_scan: bool = Query(
        default=False, description="Force full re-scan instead of git-diff"
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    from services.vector_service_factory import vector_service

    qdrant_enabled = (
        hasattr(vector_service, "client") and vector_service.client is not None
    )
    if not qdrant_enabled:
        raise HTTPException(
            status_code=400,
            detail="Re-indexing is only available in Full mode (Qdrant required)",
        )

    from services.docs_indexer_service import DocsIndexerService

    service = DocsIndexerService(db)
    result = await service.run_index(full_scan=full_scan)
    return {"status": "completed", **result}


@router.get("/admin/metrics", response_model=MetricsResponse)
async def get_metrics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    from services.help_feedback_service import HelpFeedbackService

    service = HelpFeedbackService(db)
    return MetricsResponse(**service.get_metrics())


@router.get("/admin/clusters", response_model=ClusterListResponse)
async def get_clusters(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    from models.feedback_cluster import FeedbackCluster

    query = db.query(FeedbackCluster).filter(FeedbackCluster.status == "aktiv")
    total = query.count()
    items = (
        query.order_by(FeedbackCluster.total_count.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return ClusterListResponse(
        items=[ClusterResponse(**c.to_dict()) for c in items],
        total=total,
    )


@router.get("/admin/faq-candidates", response_model=FaqCandidateListResponse)
async def get_faq_candidates(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    from models.help import HelpFaqCache

    items = (
        db.query(HelpFaqCache).filter(HelpFaqCache.faq_status == "vorgeschlagen").all()
    )
    return FaqCandidateListResponse(
        items=[
            FaqCandidateResponse(
                id=f.id,
                question_text=f.question_text,
                answer_de=f.answer_de,
                answer_en=f.answer_en,
                faq_status=f.faq_status,
                cluster_id=f.cluster_id,
                hit_count=f.hit_count,
            )
            for f in items
        ],
        total=len(items),
    )


@router.post("/admin/faq-candidates/{faq_id}/approve")
async def approve_faq_candidate(
    faq_id: int,
    request_body: FaqApproveRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    from models.help import HelpFaqCache

    faq = db.query(HelpFaqCache).filter(HelpFaqCache.id == faq_id).first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ candidate not found")

    if request_body.answer_de:
        faq.answer_de = request_body.answer_de
    if request_body.answer_en:
        faq.answer_en = request_body.answer_en

    faq.faq_status = "freigegeben"
    faq.approved_by = current_user.id
    faq.stale = False
    db.commit()

    # Index in faq_approved Qdrant collection for cache lookups (after DB commit)
    try:
        from services.vector_service_factory import vector_service

        if hasattr(vector_service, "client") and vector_service.client is not None:
            if hasattr(vector_service, "get_or_create_collection"):
                vector_service.get_or_create_collection("faq_approved")

            embeddings = await vector_service.create_embeddings([faq.question_text])
            if len(embeddings) > 0:
                import uuid
                from qdrant_client.http.models import PointStruct

                vector_service.client.upsert(
                    collection_name="faq_approved",
                    points=[
                        PointStruct(
                            id=str(uuid.uuid4()),
                            vector=embeddings[0].tolist(),
                            payload={"faq_id": faq.id},
                        )
                    ],
                )
    except Exception as e:
        logger.error(f"Failed to index approved FAQ in Qdrant: {e}", exc_info=True)

    return {"status": "approved", "id": faq.id}


@router.post("/admin/faq-candidates/{faq_id}/reject")
async def reject_faq_candidate(
    faq_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    from models.help import HelpFaqCache

    faq = db.query(HelpFaqCache).filter(HelpFaqCache.id == faq_id).first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ candidate not found")

    faq.faq_status = "verworfen"
    db.commit()
    return {"status": "rejected", "id": faq.id}


@router.post("/admin/clusters/{cluster_id}/mark-docs-gap")
async def mark_docs_gap(
    cluster_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    from models.feedback_cluster import FeedbackCluster

    cluster = db.query(FeedbackCluster).filter(FeedbackCluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster.docs_gap = True
    db.commit()
    return {"status": "marked", "id": cluster.id, "topic": cluster.topic_label}
