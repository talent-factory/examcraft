"""Statistics API for /api/v1/exams/{exam_id}/stats/* + /submissions/{id}/stats.

Wraps ``StatisticsService`` (read-only, on-the-fly) — spec 8.

Multi-tenancy: every route verifies ``Exam.institution_id`` (respectively
``Submission`` via the exam) against ``current_user.institution_id``.
RBAC: ``submissions:read`` suffices — statistics is read-side analysis.

No ``from __future__ import annotations``: FastAPI/Pydantic v2
needs runtime types for OpenAPI generation.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from database import get_db
from models.auth import User
from models.exam import Exam
from models.submission import Attempt, Submission
from services.statistics_service import StatisticsService
from utils.auth_utils import require_permission

logger = logging.getLogger(__name__)


# Two routers because the URL grammar is different — stats lives under
# /exams/{id}/stats/* but the per-submission endpoint is under
# /submissions/{id}/stats. Mirroring the pattern from grades.py keeps
# main.py's include_router calls explicit.
router_exam_stats = APIRouter(prefix="/api/v1/exams", tags=["Statistics"])
router_submission_stats = APIRouter(prefix="/api/v1/submissions", tags=["Statistics"])


_STRICT = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------


class HistogramBucketOut(BaseModel):
    model_config = _STRICT
    from_pct: int
    to_pct: int
    count: int


class OverviewStatsOut(BaseModel):
    model_config = _STRICT
    submission_count: int
    fully_reviewed_count: int
    avg_percentage: float | None
    median_percentage: float | None
    min_percentage: float | None
    max_percentage: float | None
    pass_rate: float | None
    avg_duration_seconds: float | None
    histogram: list[HistogramBucketOut]


class TopWrongAnswerOut(BaseModel):
    model_config = _STRICT
    answer: str
    count: int


class PerQuestionStatOut(BaseModel):
    model_config = _STRICT
    exam_question_id: int
    question_id: int
    position: int
    question_text: str
    question_type: str
    points_max: float
    answered_count: int
    success_rate: float | None
    difficulty: float | None
    discrimination: float | None
    top_wrong_answers: list[TopWrongAnswerOut]
    learning_effect: float | None


class PerQuestionListOut(BaseModel):
    model_config = _STRICT
    items: list[PerQuestionStatOut]


class PerSubmissionAnswerOut(BaseModel):
    model_config = _STRICT
    position: int
    question_id: int
    question_text: str
    topic: str
    bloom_level: int | None
    points_awarded: float
    points_max: float
    status: str


class TopicHeatmapEntryOut(BaseModel):
    model_config = _STRICT
    topic: str
    points_awarded: float
    points_max: float
    percentage: float


class PerSubmissionStatOut(BaseModel):
    model_config = _STRICT
    submission_id: int
    student_id: int
    student_external_id: str
    student_display_name: str | None
    total_points_awarded: float
    total_points_max: float
    percentage: float
    grade_status: str
    per_question: list[PerSubmissionAnswerOut]
    bloom_mix: dict[str, int]
    topic_heatmap: list[TopicHeatmapEntryOut]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_exam_for_user(db: Session, user: User, exam_id: int) -> Exam:
    exam = (
        db.query(Exam)
        .filter(
            Exam.id == exam_id,
            Exam.institution_id == user.institution_id,
        )
        .one_or_none()
    )
    if exam is None:
        # 404 (instead of 403) prevents the cross-tenant existence leak.
        raise HTTPException(status_code=404, detail="Prüfung nicht gefunden")
    return exam


def _ensure_submission_for_user(
    db: Session, user: User, submission_id: int
) -> Submission:
    submission = (
        db.query(Submission)
        .join(Attempt, Attempt.submission_id == Submission.id, isouter=True)
        .filter(Submission.id == submission_id)
        .first()
    )
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission nicht gefunden")
    # Cross-check via the exam's institution; a submission cannot exist
    # across multiple tenants via multiple attempts, but the exam is the
    # canonical multi-tenancy boundary.
    exam = (
        db.query(Exam)
        .filter(
            Exam.id == submission.exam_id,
            Exam.institution_id == user.institution_id,
        )
        .one_or_none()
    )
    if exam is None:
        raise HTTPException(status_code=404, detail="Submission nicht gefunden")
    return submission


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router_exam_stats.get("/{exam_id}/stats/overview", response_model=OverviewStatsOut)
async def get_exam_stats_overview(
    exam_id: int,
    current_user: User = Depends(require_permission("submissions:read")),
    db: Session = Depends(get_db),
) -> OverviewStatsOut:
    _ensure_exam_for_user(db, current_user, exam_id)
    overview = StatisticsService(db).overview(exam_id=exam_id)
    return OverviewStatsOut(
        submission_count=overview.submission_count,
        fully_reviewed_count=overview.fully_reviewed_count,
        avg_percentage=overview.avg_percentage,
        median_percentage=overview.median_percentage,
        min_percentage=overview.min_percentage,
        max_percentage=overview.max_percentage,
        pass_rate=overview.pass_rate,
        avg_duration_seconds=overview.avg_duration_seconds,
        histogram=[
            HistogramBucketOut(from_pct=b.from_pct, to_pct=b.to_pct, count=b.count)
            for b in overview.histogram
        ],
    )


@router_exam_stats.get(
    "/{exam_id}/stats/per-question", response_model=PerQuestionListOut
)
async def get_exam_stats_per_question(
    exam_id: int,
    current_user: User = Depends(require_permission("submissions:read")),
    db: Session = Depends(get_db),
) -> PerQuestionListOut:
    _ensure_exam_for_user(db, current_user, exam_id)
    items = StatisticsService(db).per_question(exam_id=exam_id)
    return PerQuestionListOut(
        items=[
            PerQuestionStatOut(
                exam_question_id=it.exam_question_id,
                question_id=it.question_id,
                position=it.position,
                question_text=it.question_text,
                question_type=it.question_type,
                points_max=it.points_max,
                answered_count=it.answered_count,
                success_rate=it.success_rate,
                difficulty=it.difficulty,
                discrimination=it.discrimination,
                top_wrong_answers=[
                    TopWrongAnswerOut(answer=ans, count=cnt)
                    for ans, cnt in it.top_wrong_answers
                ],
                learning_effect=it.learning_effect,
            )
            for it in items
        ]
    )


@router_submission_stats.get(
    "/{submission_id}/stats", response_model=PerSubmissionStatOut
)
async def get_submission_stats(
    submission_id: int,
    current_user: User = Depends(require_permission("submissions:read")),
    db: Session = Depends(get_db),
) -> PerSubmissionStatOut:
    _ensure_submission_for_user(db, current_user, submission_id)
    stats = StatisticsService(db).per_submission(submission_id=submission_id)
    if stats is None:
        raise HTTPException(status_code=404, detail="Submission nicht gefunden")
    return PerSubmissionStatOut(
        submission_id=stats.submission_id,
        student_id=stats.student_id,
        student_external_id=stats.student_external_id,
        student_display_name=stats.student_display_name,
        total_points_awarded=stats.total_points_awarded,
        total_points_max=stats.total_points_max,
        percentage=stats.percentage,
        grade_status=stats.grade_status,
        per_question=[PerSubmissionAnswerOut(**q) for q in stats.per_question],
        # Pydantic accepts only str-keys in JSON — convert the int Bloom
        # levels to their string form for transport.
        bloom_mix={str(k): v for k, v in stats.bloom_mix.items()},
        topic_heatmap=[
            TopicHeatmapEntryOut(
                topic=topic,
                points_awarded=v["points_awarded"],
                points_max=v["points_max"],
                percentage=v["percentage"],
            )
            for topic, v in stats.topic_heatmap.items()
        ],
    )
