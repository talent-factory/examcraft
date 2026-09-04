import logging
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session
from database import get_db
from utils.auth_utils import get_current_active_user
from models.auth import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/help", tags=["Help"])

# Length of the core tour per role — must match the "core" array in
# core/frontend/public/help-onboarding-steps.json. If the constant and the JSON
# drift apart, the tour is marked complete too early or never; that is exactly
# how TF-604 stayed invisible. `test_help_onboarding_steps.py` reads both
# sources and holds them together — deliberately only in the test, so the
# backend does not depend on a frontend asset at runtime.
ONBOARDING_MAX_STEPS = {"teacher": 8, "admin": 8}

# Deep-dive tracks (TF-625). Track ids live in the frontend JSON; the backend
# only validates their shape and caps their number instead of keeping a
# whitelist — a second list here would be the very drift source this ticket
# sets out to remove. An unknown track inside a user's own progress is
# harmless; unbounded growth of the JSON column would not be.
TRACK_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
MAX_TRACKS_PER_USER = 20
MAX_TRACK_STEPS = 50


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


class TrackProgressEntry(BaseModel):
    """Progress within a single deep-dive track."""

    current_step: int = 0
    completed_steps: List[int] = []
    skipped_steps: List[int] = []
    completed: bool = False


class OnboardingStatusResponse(BaseModel):
    id: Optional[int] = None
    role: str
    current_step: int
    completed_steps: List[int]
    skipped_steps: List[int] = []
    completed: bool
    track_progress: Dict[str, TrackProgressEntry] = {}


class OnboardingStepRequest(BaseModel):
    step: int = Field(..., ge=0)


class TrackStepRequest(BaseModel):
    step: int = Field(..., ge=0, lt=MAX_TRACK_STEPS)
    # The client reports the track length because only it knows the frontend
    # JSON. Deliberately not an authorization boundary — the value only drives
    # the user's own progress state.
    total_steps: int = Field(..., ge=1, le=MAX_TRACK_STEPS)
    skipped: bool = False

    @model_validator(mode="after")
    def _step_within_track(self) -> "TrackStepRequest":
        # A cross-field rule, so it cannot live in a single Field(...) bound —
        # moved here rather than left as an `if` beside the route handler so
        # that "step must be smaller than total_steps" is a property of the
        # type itself: an invalid TrackStepRequest can no longer be
        # constructed by any caller, not just the one route that used to
        # check it.
        if self.step >= self.total_steps:
            raise ValueError("step must be smaller than total_steps")
        return self


def _track_entry_response(entry: Dict[str, Any]) -> TrackProgressEntry:
    return TrackProgressEntry(
        current_step=entry.get("current_step", 0),
        completed_steps=entry.get("completed_steps") or [],
        skipped_steps=entry.get("skipped_steps") or [],
        completed=entry.get("completed_at") is not None,
    )


def _build_status_response(progress) -> OnboardingStatusResponse:
    return OnboardingStatusResponse(
        id=progress.id,
        role=progress.role,
        current_step=progress.current_step,
        completed_steps=progress.completed_steps or [],
        skipped_steps=progress.skipped_steps or [],
        completed=progress.completed_at is not None,
        track_progress={
            track_id: _track_entry_response(entry)
            for track_id, entry in (progress.track_progress or {}).items()
        },
    )


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
    return _build_status_response(progress)


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

    # Catch-up: if the step was in skipped_steps, remove it from there
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
    return _build_status_response(progress)


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
    return _build_status_response(progress)


@router.put(
    "/onboarding/track/{track_id}/step", response_model=OnboardingStatusResponse
)
async def update_track_step(
    track_id: str,
    request: TrackStepRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Record progress within an optional deep-dive track (TF-625).

    Deliberately separate from ``/onboarding/step``: a deep dive must neither
    advance the core tour's ``current_step`` nor mark it complete. A track
    counts as finished once its own ``current_step`` reaches the length
    reported by the client — shown and skipped steps count equally, because
    both mean the user has moved past them.
    """
    from models.help import HelpOnboardingProgress
    from datetime import datetime, timezone

    if not TRACK_ID_PATTERN.match(track_id):
        raise HTTPException(status_code=422, detail="Invalid track id")
    # step < total_steps is enforced by TrackStepRequest itself (a
    # model_validator), so an invalid combination never reaches this point —
    # see the model for why that check lives there instead of here.

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
            track_progress={},
        )
        db.add(progress)

    tracks = dict(progress.track_progress or {})
    if track_id not in tracks and len(tracks) >= MAX_TRACKS_PER_USER:
        raise HTTPException(
            status_code=422,
            detail=f"Too many onboarding tracks (max {MAX_TRACKS_PER_USER})",
        )

    entry = dict(tracks.get(track_id) or {})
    completed = list(entry.get("completed_steps") or [])
    skipped = list(entry.get("skipped_steps") or [])

    if request.skipped:
        if request.step not in skipped:
            skipped.append(request.step)
        if request.step in completed:
            completed.remove(request.step)
    else:
        if request.step not in completed:
            completed.append(request.step)
        # Catch-up, mirroring the core tour: a step done later leaves the
        # skip list.
        if request.step in skipped:
            skipped.remove(request.step)

    entry["completed_steps"] = sorted(completed)
    entry["skipped_steps"] = sorted(skipped)
    # max(): replaying an earlier step must not rewind track progress.
    entry["current_step"] = max(entry.get("current_step", 0), request.step + 1)
    # A track in which *every* step fell through the skip path was never
    # actually shown. Marking it complete would repeat the TF-604 lie one level
    # down — a tick in the widget for a tour the user never saw. Leaving it
    # open keeps it restartable and gives the frontend's console/Sentry warning
    # something to correlate with. A partially skipped track still completes:
    # the user did see the rest.
    if (
        entry["current_step"] >= request.total_steps
        and entry["completed_steps"]
        and not entry.get("completed_at")
    ):
        entry["completed_at"] = datetime.now(timezone.utc).isoformat()

    tracks[track_id] = entry
    # A new dict rather than mutating progress.track_progress in place: the
    # column is MutableDict.as_mutable(JSON), which does flag a direct
    # `progress.track_progress[track_id] = entry` as dirty — but a change to
    # `entry` itself (one level deeper, e.g. `entry["current_step"] += 1` on
    # the dict already inside the column) would not be, since MutableDict only
    # instruments the outer dict's own __setitem__/__delitem__. Rebuilding and
    # reassigning the whole `tracks` dict sidesteps that distinction entirely
    # rather than relying on which level of nesting happened to change.
    progress.track_progress = tracks

    db.commit()
    db.refresh(progress)
    return _build_status_response(progress)


# === CONTEXT HINTS ===


class ContextHintResponse(BaseModel):
    # An i18n key, not a text. The client resolves it against its own
    # translation.json, so switching the language switches the hint with
    # everything else instead of leaving it stale until a reload (TF-625).
    i18n_key: Optional[str] = None
    hint_id: Optional[int] = None


@router.get("/context/{route:path}", response_model=ContextHintResponse)
async def get_context_hint(
    route: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    from services.help_context_service import HelpContextService

    role = _get_user_role(current_user)
    tier = _get_user_tier(current_user)

    service = HelpContextService(db)
    hint = service.get_hint_for_route(route, role, tier, user_id=current_user.id)
    if hint:
        return ContextHintResponse(i18n_key=hint["i18n_key"], hint_id=hint["id"])
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


class IndexStateResponse(BaseModel):
    """Persistent lifecycle view for the docs_help indexing job.

    Distinct from the Redis SETNX lock (ephemeral "is running right now"):
    these fields survive restarts and surface the last completed / failed
    run for operators monitoring /admin/index-state.
    """

    status: str  # idle | in_progress | completed | failed
    last_indexed_sha: Optional[str] = None
    last_indexed_at: Optional[datetime] = None
    files_indexed: int = 0
    files_deleted: int = 0
    last_error: Optional[str] = None


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

    from services.docs_indexer_service import (
        DocsIndexerService,
        IndexingInProgressError,
        IndexingLockUnavailableError,
    )

    service = DocsIndexerService(db)
    try:
        result = await service.run_index(full_scan=full_scan)
    except IndexingInProgressError as e:
        # 409 Conflict: another indexing run holds the lock (startup task or
        # a prior /admin/reindex call). Caller can retry once the lock expires.
        raise HTTPException(status_code=409, detail=str(e))
    except IndexingLockUnavailableError as e:
        # 503 Service Unavailable: Redis is down so we can't safely serialize
        # against concurrent indexing. Refuse rather than risk a Qdrant-clear
        # race; operator should retry once Redis is healthy.
        raise HTTPException(status_code=503, detail=str(e))
    return {"status": "completed", **result}


@router.get("/admin/index-state", response_model=IndexStateResponse)
async def get_index_state(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Persistent docs-indexing lifecycle view.

    Returns 'idle' defaults when no run has happened yet. Otherwise reflects
    the last transition — `in_progress` if a run is active, `completed` or
    `failed` (with `last_error` populated) for terminal states.
    """
    _require_admin(current_user)
    from models.help import HelpIndexState

    state = db.query(HelpIndexState).first()
    if state is None:
        return IndexStateResponse(status="idle")
    return IndexStateResponse(
        status=state.indexing_status,
        last_indexed_sha=state.last_indexed_sha,
        last_indexed_at=state.last_indexed_at,
        files_indexed=state.files_indexed,
        files_deleted=state.files_deleted,
        last_error=state.last_error,
    )


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
