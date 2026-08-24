"""
Exam Composer API Endpoints for ExamCraft AI
CRUD, question management, auto-fill, finalize, and export.
"""

from typing import List, Optional, Union
from datetime import date, datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import case, func as sa_func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.exam import Exam, ExamQuestion, ExamStatus, ExamVisibility
from models.auth import User
from models.document import Document
from models.question_review import QuestionReview, ReviewStatus, QuestionSourceDocument
from models.tag import QuestionTag
from api.tags import TagOut
from api.question_review import _serialize_competency
from utils.question_options import normalize_options
from services.translation_service import t, get_request_locale
from utils.auth_utils import require_permission
from utils.download_filename import content_disposition, filename_stem
from utils.tenant_utils import TenantFilter, get_tenant_context
from utils.document_visibility import filter_documents_for_user
from utils.question_visibility import (
    assert_question_visible_for,
    filter_questions_for_user,
)
from utils.exam_visibility import assert_exam_visible_for, filter_exams_for_user
from services.org_unit_service import get_user_accessible_org_unit_ids
from services.point_utils import suggest_points
from services.exam_export_service import (
    MarkdownExporter,
    JsonExporter,
    MoodleXmlExporter,
    PdfExporter,
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
    default_document_ids: Optional[List[int]] = None
    # TF-335: omit ⇒ inherit Institution-Default at create time.
    grading_scheme_id: Optional[int] = None
    # TF-643: omit ⇒ 'institution' (matches the DB column default). team
    # visibility requires org_unit_id — validated by
    # _resolve_exam_visibility_for_create.
    visibility: Optional[str] = Field(None, pattern="^(private|team|institution)$")
    org_unit_id: Optional[int] = None


class ExamUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    course: Optional[str] = Field(None, max_length=200)
    exam_date: Optional[date] = None
    time_limit_minutes: Optional[int] = Field(None, ge=1)
    allowed_aids: Optional[str] = None
    instructions: Optional[str] = None
    passing_percentage: Optional[float] = Field(None, ge=0, le=100)
    language: Optional[str] = Field(None, pattern="^(de|en)$")
    default_document_ids: Optional[List[int]] = None
    grading_scheme_id: Optional[int] = None
    # TF-643: change the exam's visibility (owner/SuperUser only, see
    # _resolve_exam_visibility_update). org_unit_id only meaningful together
    # with visibility="team".
    visibility: Optional[str] = Field(None, pattern="^(private|team|institution)$")
    org_unit_id: Optional[int] = None
    updated_at: datetime = Field(..., description="For optimistic locking")


class ExamGradingSchemeUpdate(BaseModel):
    """Body for the dedicated PATCH that changes only the grading scheme.

    Lives on its own endpoint (``PATCH /{exam_id}/grading-scheme``) so
    the grading scheme can be reassigned even on finalized exams —
    ``ExamUpdate`` requires draft status because it can change question
    content, but reassigning the noten-skala is metadata-only and the
    lehrperson must be able to fix it post-finalization (e.g. when the
    import inherited a wrong institution-default).
    """

    grading_scheme_id: Optional[int] = Field(
        None,
        description=(
            "None removes the assignment; the exam falls back to the "
            "institution default at grade export time."
        ),
    )
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
    default_document_ids: Optional[List[int]] = None
    grading_scheme_id: Optional[int] = None
    # TF-643: visibility — see the ExamVisibility docstring.
    visibility: str = "institution"
    org_unit_id: Optional[int] = None
    # Archive axis (TF-398) — orthogonal to ``status``.
    archived_at: Optional[datetime] = None
    archived_by: Optional[int] = None
    archive_reason: Optional[str] = None
    # Whether the exam has submissions — needed by the frontend for the
    # ``canDelete`` logic (disabled state of the delete button).
    has_submissions: bool = False

    class Config:
        from_attributes = True


class ExamDetailOut(ExamOut):
    questions: List[ExamQuestionOut] = []


class ExamListOut(BaseModel):
    total: int
    exams: List[ExamOut]


class ExamArchiveRequest(BaseModel):
    """Optional reason when archiving (TF-398)."""

    reason: Optional[str] = Field(None, max_length=500)


# --- Helpers ---


def _get_exam_or_404(
    exam_id: int,
    db: Session,
    current_user: User,
    locale: str = "de",
    *,
    allow_read_all_bypass: bool = True,
) -> Exam:
    """Load an exam by id, 404 if it doesn't exist or isn't visible.

    Backs every exam endpoint below — both the single read endpoint
    (``get_exam``) and every mutation endpoint (update/update-grading-scheme/
    delete/archive/restore/add-questions/update-question/remove-question/
    reorder/auto-fill/finalize/unfinalize/export).
    Per ADR-0004 the ``exams:read_all`` bypass must stay read-only, so
    ``allow_read_all_bypass`` defaults ``True`` here (safe for the read
    endpoint) and every mutating call site below passes ``False`` explicitly
    (TF-640's gotcha, mirrored here — see ``utils.exam_visibility
    .is_exam_visible_for``).

    ``allow_read_all_bypass=False`` also derives
    ``require_same_institution=True`` for the visibility check, so a
    mutating call additionally closes the one gap the bypass flag alone
    doesn't: an exam creator whose ``institution_id`` has drifted from their
    exam's (e.g. after an institution transfer that left exams behind) can
    still *see* the exam but can no longer mutate it — mirrors
    ``utils.auth_utils.enforce_resource_access``'s ``require_same_institution``,
    which Documents use for the same purpose. Deriving it here (rather than a
    second kwarg at each of the 13 call sites below) means a future
    mutation endpoint can't forget it the way TF-640's original gotcha was
    possible to forget ``allow_read_all_bypass=False`` itself.
    """
    exam = (
        db.query(Exam)
        .options(joinedload(Exam.questions).joinedload(ExamQuestion.question))
        .filter(Exam.id == exam_id)
        .first()
    )
    if not exam:
        raise HTTPException(status_code=404, detail=t("exams_not_found", locale=locale))
    assert_exam_visible_for(
        current_user,
        exam,
        db,
        detail=t("exams_not_found", locale=locale),
        allow_read_all_bypass=allow_read_all_bypass,
        require_same_institution=not allow_read_all_bypass,
    )
    return exam


def _require_draft(exam: Exam, locale: str = "de"):
    if exam.status != ExamStatus.DRAFT.value:
        raise HTTPException(
            status_code=400,
            detail=t("exams_must_be_draft", locale=locale),
        )


def _exam_to_out(exam: Exam, has_submissions: Optional[bool] = None) -> dict:
    # ``has_submissions`` can be precomputed by the caller (list endpoint:
    # bulk query against N+1); if omitted, the relationship is lazy-loaded
    # (single-exam paths — one extra query, non-critical).
    if has_submissions is None:
        has_submissions = bool(exam.submissions)
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
        "default_document_ids": exam.default_document_ids,
        "grading_scheme_id": exam.grading_scheme_id,
        # TF-643: exam.visibility is an ExamVisibility enum member.
        "visibility": exam.visibility.value,
        "org_unit_id": exam.org_unit_id,
        "archived_at": exam.archived_at,
        "archived_by": exam.archived_by,
        "archive_reason": exam.archive_reason,
        "has_submissions": has_submissions,
    }


def _exam_has_submissions(db: Session, exam_id: int) -> bool:
    """Whether the exam has at least one submission (guard for hard delete)."""
    from models.submission import Submission

    return (
        db.query(Submission.id).filter(Submission.exam_id == exam_id).first()
        is not None
    )


def _exam_delete_block_reason(db: Session, exam: Exam, locale: str) -> Optional[str]:
    """i18n reason why the exam may NOT be hard-deleted — or
    ``None`` if all four guards are satisfied (TF-398).

    Order: first archived, then not exported, then no submissions.
    The permission (``delete_exams``) is checked by the endpoint dependency.
    """
    if exam.archived_at is None:
        return t("delete_exam_requires_archive", locale=locale)
    if exam.status == ExamStatus.EXPORTED.value:
        return t("delete_exam_exported", locale=locale)
    if _exam_has_submissions(db, exam.id):
        return t("delete_exam_has_submissions", locale=locale)
    return None


def _resolve_grading_scheme_id(
    *,
    db: Session,
    user: User,
    explicit_id: Optional[int],
    fall_back_to_institution_default: bool,
) -> Optional[int]:
    """Validate an explicit ``grading_scheme_id`` or inherit the
    institution default. Returns the id to persist on the exam.

    Validation rules (Spec 4.6 + 7.6):

    * a system scheme (``institution_id IS NULL``) is always allowed;
    * an institution-scoped scheme must belong to the caller's
      institution; cross-tenant ids return 422 to keep the existence
      side-channel closed (``404`` would also leak the scheme to a
      caller in an unrelated institution).
    """
    from models.grading_scheme import GradingScheme as _GS

    if explicit_id is not None:
        scheme = db.query(_GS).filter(_GS.id == explicit_id).one_or_none()
        if scheme is None or (
            scheme.institution_id is not None
            and scheme.institution_id != user.institution_id
        ):
            raise HTTPException(
                status_code=422,
                detail="Ungültige grading_scheme_id für diese Institution",
            )
        return explicit_id

    if not fall_back_to_institution_default or user.institution_id is None:
        return None

    from models.auth import Institution

    institution = (
        db.query(Institution)
        .filter(Institution.id == user.institution_id)
        .one_or_none()
    )
    return institution.default_grading_scheme_id if institution else None


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


def _resolve_exam_visibility_for_create(
    request: "ExamCreate", user: User, db: Session
) -> tuple:
    """TF-643: validate visibility/org_unit_id at exam creation time.

    Simpler than :func:`_resolve_exam_visibility_update` — no ownership gate
    needed (the creator is always the owner of the row they're about to
    create). Defaults to INSTITUTION (mirrors the DB column default) when
    omitted. Mirrors ``question_review._resolve_question_visibility_update``'s
    TEAM branch; the INSTITUTION-on-orphan guard from that function has no
    equivalent here — unlike ``QuestionReview.institution_id``,
    ``Exam.institution_id`` is NOT NULL, so it can't happen.
    """
    visibility = (
        ExamVisibility(request.visibility)
        if request.visibility is not None
        else ExamVisibility.INSTITUTION
    )
    org_unit_id = request.org_unit_id

    if visibility == ExamVisibility.TEAM:
        if org_unit_id is None:
            raise HTTPException(
                status_code=400,
                detail="Team-Sichtbarkeit erfordert eine Org-Unit (org_unit_id).",
            )
        # SuperUser bugfix (mirrors question_review._resolve_question_visibility_update,
        # TF-642): validating against the ACTING user's own membership would
        # reject a superuser, who typically belongs to no Org-Unit and often
        # has institution_id=None — they may set ANY org_unit_id on behalf of
        # its actual owners.
        if not user.is_superuser:
            accessible = (
                get_user_accessible_org_unit_ids(db, user.id, user.institution_id)
                if user.institution_id
                else set()
            )
            if org_unit_id not in accessible:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Team-Sichtbarkeit erfordert eine eigene Org-Unit "
                        "(org_unit_id), der du selbst angehörst."
                    ),
                )
    else:
        org_unit_id = None

    return visibility, org_unit_id


# --- CRUD Endpoints ---


@router.post("/", response_model=ExamOut, status_code=201)
async def create_exam(
    request: ExamCreate,
    http_request: Request,
    current_user: User = Depends(require_permission("create_exams")),
    db: Session = Depends(get_db),
):
    """Create a new exam (draft status)."""
    locale = get_request_locale(http_request, current_user)
    grading_scheme_id = _resolve_grading_scheme_id(
        db=db,
        user=current_user,
        explicit_id=request.grading_scheme_id,
        fall_back_to_institution_default=True,
    )
    visibility, org_unit_id = _resolve_exam_visibility_for_create(
        request, current_user, db
    )
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
        default_document_ids=request.default_document_ids,
        grading_scheme_id=grading_scheme_id,
        visibility=visibility,
        org_unit_id=org_unit_id,
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

    from services.audit_service import AuditService

    AuditService.log_action(
        db,
        action="create_exam",
        status=AuditService.STATUS_SUCCESS,
        user_id=current_user.id,
        resource_type="exam",
        resource_id=str(exam.id),
        request=http_request,
        additional_data={"title": exam.title},
    )

    return _exam_to_out(exam)


@router.get("/", response_model=ExamListOut)
async def list_exams(
    status: Optional[str] = Query(None, pattern="^(draft|finalized|exported)$"),
    search: Optional[str] = Query(None, max_length=200),
    include_archived: bool = Query(
        False, description="Also include archived exams (TF-398)."
    ),
    archived_only: bool = Query(
        False, description="Show only archived exams (TF-398)."
    ),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission("create_exams")),
    db: Session = Depends(get_db),
):
    """List exams visible to the current user (TF-643).

    By default, archived exams are hidden (``archived_at IS NULL``).
    ``archived_only`` shows only archived ones; ``include_archived``
    shows active + archived. ``archived_only`` takes precedence (TF-398).
    """
    query = db.query(Exam)
    query = filter_exams_for_user(query, current_user, db)

    if archived_only:
        query = query.filter(Exam.archived_at.isnot(None))
    elif not include_archived:
        query = query.filter(Exam.archived_at.is_(None))

    if status:
        query = query.filter(Exam.status == status)
    if search:
        query = query.filter(Exam.title.ilike(f"%{search}%"))

    total = query.count()
    exams = query.order_by(Exam.updated_at.desc()).limit(limit).offset(offset).all()

    # has_submissions via bulk query (avoids an N+1 from lazy-loading the
    # submissions relationship per exam).
    exams_with_subs: set[int] = set()
    exam_ids = [e.id for e in exams]
    if exam_ids:
        from models.submission import Submission

        rows = (
            db.query(Submission.exam_id)
            .filter(Submission.exam_id.in_(exam_ids))
            .distinct()
            .all()
        )
        exams_with_subs = {row[0] for row in rows}

    return ExamListOut(
        total=total,
        exams=[_exam_to_out(e, has_submissions=e.id in exams_with_subs) for e in exams],
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
    tags: List[TagOut] = []

    class Config:
        from_attributes = True


class ApprovedQuestionsListOut(BaseModel):
    total: int
    questions: List[ApprovedQuestionOut]


class ApprovedQuestionOptionOut(BaseModel):
    """TF-405: an answer option flagged with whether it's the correct one."""

    text: str
    is_correct: bool


class ApprovedQuestionSourceDocumentOut(BaseModel):
    id: int
    title: str


class ApprovedQuestionCompetencyOut(BaseModel):
    id: int
    code: str
    title: str
    framework_id: int
    module_code: Optional[str] = None


class ApprovedQuestionDetailOut(BaseModel):
    """TF-405: full, read-only detail for the preview modal in the
    exam composer.

    Deliberately separate from the lean ``ApprovedQuestionOut`` used by the
    50-item list: this detail is fetched on demand for *one* question when
    the preview opens, so the list API stays lightweight.
    """

    id: int
    question_text: str
    question_type: str
    difficulty: str
    topic: str
    language: Optional[str] = None
    bloom_level: Optional[int] = None
    ln_level: Optional[int] = None
    estimated_time_minutes: Optional[int] = None
    # options[].is_correct flags the right choice for MC/TF (derived from
    # correct_answer). correct_answer is also still set and is the sole
    # source of the answer for open-ended questions (sample solution,
    # options is then empty).
    options: List[ApprovedQuestionOptionOut] = []
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    usage_count: int = 0
    competency: Optional[ApprovedQuestionCompetencyOut] = None
    source_documents: List[ApprovedQuestionSourceDocumentOut] = []


class DocumentWithQuestionsOut(BaseModel):
    id: int
    title: str
    approved_question_count: int


@router.get("/documents-with-questions", response_model=List[DocumentWithQuestionsOut])
async def list_documents_with_questions(
    current_user: User = Depends(require_permission("create_exams")),
    db: Session = Depends(get_db),
):
    """Return all documents of the institution.
    approved_question_count is 0 for documents with no approved questions yet."""
    from sqlalchemy import case as sa_case, and_

    query = (
        db.query(
            Document,
            sa_func.count(
                sa_case(
                    (
                        and_(
                            QuestionReview.review_status == ReviewStatus.APPROVED.value,
                            # TF-396: don't count archived questions
                            QuestionReview.archived_at.is_(None),
                        ),
                        QuestionReview.id,
                    ),
                    else_=None,
                )
            ).label("approved_question_count"),
        )
        .outerjoin(
            QuestionSourceDocument, QuestionSourceDocument.document_id == Document.id
        )
        .outerjoin(
            QuestionReview, QuestionReview.id == QuestionSourceDocument.question_id
        )
    )
    # Visibility-aware (TF-354): don't leak titles of colleagues' private docs
    # to other institution members. SuperUser bypass handled in the helper.
    query = filter_documents_for_user(query, current_user, db)
    results = query.group_by(Document.id).order_by(Document.original_filename).all()
    # Use Document.title resolver so users see display_name overrides + the
    # filtered metadata title instead of "1" / "Untitled" leftovers.
    return [
        {
            "id": doc.id,
            "title": doc.title,
            "approved_question_count": count,
        }
        for doc, count in results
    ]


@router.get("/approved-questions", response_model=ApprovedQuestionsListOut)
async def list_approved_questions(
    topic: Optional[str] = None,
    difficulty: Optional[str] = Query(None, pattern="^(easy|medium|hard)$"),
    bloom_level: Optional[int] = Query(None, ge=1, le=6),
    question_type: Optional[str] = Query(
        None, pattern="^(single_choice|multiple_choice|open_ended|true_false)$"
    ),
    # TF-406: subject filter facets (competency level, competency,
    # quality tier) and "never used". Fields live on the QuestionReview
    # model; facets are AND-combined.
    ln_level: Optional[int] = Query(
        None, ge=1, le=4, description="TF-400 competency level (1-4)"
    ),
    competency_id: Optional[int] = Query(None, ge=1, description="Competency ID"),
    quality_tier: Optional[str] = Query(None, pattern="^(A|B|C)$"),
    unused: bool = Query(
        False, description="Only questions with no exam usage (usage_count=0)"
    ),
    search: Optional[str] = Query(None, max_length=500),
    tag_ids: Optional[str] = Query(None, description="Comma-separated tag IDs"),
    document_ids: Optional[str] = Query(
        None, description="Comma-separated document IDs"
    ),
    sort: str = Query(
        "newest",
        pattern="^(most_used|newest|difficulty)$",
        description="Sort order for the results",
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission("create_exams")),
    db: Session = Depends(get_db),
):
    """Browse approved questions for exam composition."""
    query = db.query(QuestionReview).filter(
        QuestionReview.review_status == ReviewStatus.APPROVED.value,
        # TF-396: don't offer archived questions for reuse
        QuestionReview.archived_at.is_(None),
    )
    # TF-642: visibility-aware question pool (private/team/institution +
    # questions:read_all bypass), replaces the plain institution boundary.
    query = filter_questions_for_user(query, current_user, db)

    if topic:
        query = query.filter(QuestionReview.topic.ilike(f"%{topic}%"))
    if difficulty:
        query = query.filter(QuestionReview.difficulty == difficulty)
    if bloom_level:
        query = query.filter(QuestionReview.bloom_level == bloom_level)
    if question_type:
        query = query.filter(QuestionReview.question_type == question_type)
    if ln_level:
        query = query.filter(QuestionReview.ln_level == ln_level)
    if competency_id:
        query = query.filter(QuestionReview.competency_id == competency_id)
    if quality_tier:
        query = query.filter(QuestionReview.quality_tier == quality_tier)
    if search:
        query = query.filter(QuestionReview.question_text.ilike(f"%{search}%"))
    if tag_ids:
        parsed_tag_ids = [int(i) for i in tag_ids.split(",") if i.strip().isdigit()]
        if not parsed_tag_ids:
            raise HTTPException(
                status_code=422,
                detail="tag_ids enthält keine gültigen ganzzahligen Werte.",
            )
        query = query.filter(
            QuestionReview.id.in_(
                db.query(QuestionTag.question_id).filter(
                    QuestionTag.tag_id.in_(parsed_tag_ids)
                )
            )
        )
    if document_ids:
        parsed_ids = [int(i) for i in document_ids.split(",") if i.strip().isdigit()]
        if parsed_ids:
            linked_ids_select = (
                db.query(QuestionSourceDocument.question_id)
                .filter(QuestionSourceDocument.document_id.in_(parsed_ids))
                .distinct()
            )
            query = query.filter(QuestionReview.id.in_(linked_ids_select))

    if unused:
        # "never used" — no ExamQuestion row references the question at
        # all (usage_count=0). Correlated NOT EXISTS subquery.
        query = query.filter(
            ~db.query(ExamQuestion.id)
            .filter(ExamQuestion.question_id == QuestionReview.id)
            .exists()
        )

    total = query.count()

    # TF-406: sorting. "newest" (default) = previous behavior.
    if sort == "most_used":
        usage_sort_sq = (
            db.query(
                ExamQuestion.question_id.label("qid"),
                sa_func.count(ExamQuestion.id).label("uses"),
            )
            .group_by(ExamQuestion.question_id)
            .subquery()
        )
        query = query.outerjoin(
            usage_sort_sq, usage_sort_sq.c.qid == QuestionReview.id
        ).order_by(
            sa_func.coalesce(usage_sort_sq.c.uses, 0).desc(),
            QuestionReview.created_at.desc(),
        )
    elif sort == "difficulty":
        difficulty_rank = case(
            (QuestionReview.difficulty == "easy", 1),
            (QuestionReview.difficulty == "medium", 2),
            (QuestionReview.difficulty == "hard", 3),
            else_=4,
        )
        query = query.order_by(difficulty_rank.asc(), QuestionReview.created_at.desc())
    else:  # "newest"
        query = query.order_by(QuestionReview.created_at.desc())

    questions = query.limit(limit).offset(offset).all()

    question_ids = [q.id for q in questions]
    usage_counts = {}
    if question_ids:
        usage_counts = dict(
            db.query(ExamQuestion.question_id, sa_func.count(ExamQuestion.id))
            .filter(ExamQuestion.question_id.in_(question_ids))
            .group_by(ExamQuestion.question_id)
            .all()
        )

    tag_id_set = {t.id for q in questions for t in q.tags}
    tag_usage_counts: dict[int, int] = {}
    if tag_id_set:
        tag_usage_counts = dict(
            db.query(QuestionTag.tag_id, sa_func.count(QuestionTag.question_id))
            .filter(QuestionTag.tag_id.in_(tag_id_set))
            .group_by(QuestionTag.tag_id)
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
                "tags": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "institution_id": t.institution_id,
                        "scope": t.scope,
                        "usage_count": tag_usage_counts.get(t.id, 0),
                        "is_archived": t.is_archived,
                    }
                    for t in q.tags
                ],
            }
        )

    return ApprovedQuestionsListOut(total=total, questions=result)


@router.get(
    "/approved-questions/{question_id}",
    response_model=ApprovedQuestionDetailOut,
)
async def get_approved_question(
    question_id: int,
    request: Request,
    current_user: User = Depends(require_permission("create_exams")),
    db: Session = Depends(get_db),
):
    """TF-405: read-only detail of a question for the preview in the composer.

    Returns the full question text, options with the correct one flagged,
    explanation, source document(s), and competency/Bloom/LN.

    Deliberately ONLY tenant-scoped (no ``review_status``/``archived_at``
    filter): the preview is opened both from the question pool (approved
    questions only) and from questions already assembled into an exam. A
    question already on an exam must stay previewable even if it has since
    been edited (``edited``) or archived — approval gating is a concern of
    the list API (what may be added), not of the detail view. A question
    belonging to a foreign institution must be indistinguishable from a
    non-existent one (404, not 403) — no existence leak.
    """
    locale = get_request_locale(request, current_user)
    tenant_context = get_tenant_context(current_user)

    query = (
        db.query(QuestionReview)
        .options(joinedload(QuestionReview.source_document_links))
        .filter(QuestionReview.id == question_id)
    )
    query = TenantFilter.filter_by_tenant(query, QuestionReview, tenant_context)
    question = query.first()
    if question is None:
        raise HTTPException(
            status_code=404,
            detail=t("approved_question_not_found", locale=locale),
        )

    # usage_count counts — like the list endpoint — cross-institution how
    # often the question is used in exams (global reuse, no leak, since no
    # foreign exam data is exposed).
    usage_count = (
        db.query(sa_func.count(ExamQuestion.id))
        .filter(ExamQuestion.question_id == question.id)
        .scalar()
        or 0
    )

    correct = question.correct_answer
    options = [
        {"text": opt, "is_correct": opt == correct}
        for opt in (normalize_options(question.options) or [])
    ]

    source_documents: list[dict] = []
    doc_ids = [link.document_id for link in question.source_document_links]
    if doc_ids:
        # Defense-in-depth: also tenant-filter source documents, so that even
        # a faulty cross-institution link can't leak a foreign title.
        docs = (
            db.query(Document)
            .filter(
                Document.id.in_(doc_ids),
                Document.institution_id == tenant_context.institution_id,
            )
            .all()
        )
        if len(docs) < len(doc_ids):
            # A filtered-out document indicates a cross-institution link
            # (data-integrity issue) — surface it instead of silently dropping it.
            logger.warning(
                "approved_question_detail: %d/%d Quelldokument(e) für Frage %s "
                "tenant-gefiltert (institution_id=%s) — möglicher Cross-Institution-Link",
                len(doc_ids) - len(docs),
                len(doc_ids),
                question.id,
                tenant_context.institution_id,
            )
        source_documents = [{"id": doc.id, "title": doc.title} for doc in docs]

    return ApprovedQuestionDetailOut(
        id=question.id,
        question_text=question.question_text,
        question_type=question.question_type,
        difficulty=question.difficulty,
        topic=question.topic,
        language=question.language,
        bloom_level=question.bloom_level,
        ln_level=question.ln_level,
        estimated_time_minutes=question.estimated_time_minutes,
        options=options,
        correct_answer=question.correct_answer,
        explanation=question.explanation,
        usage_count=usage_count,
        competency=_serialize_competency(question),
        source_documents=source_documents,
    )


@router.get("/{exam_id}", response_model=ExamDetailOut)
async def get_exam(
    exam_id: int,
    request: Request,
    current_user: User = Depends(require_permission("create_exams")),
    db: Session = Depends(get_db),
):
    """Get exam with all questions."""
    locale = get_request_locale(request, current_user)
    exam = _get_exam_or_404(exam_id, db, current_user, locale)
    return _exam_detail_to_out(exam)


def _resolve_exam_visibility_update(
    exam: Exam,
    fields: dict,
    user: User,
    db: Session,
) -> Optional[dict]:
    """TF-643: validate a visibility/org_unit_id change on ``PUT /{exam_id}``.

    Mirrors ``question_review._resolve_question_visibility_update`` (TF-642).
    Adapted to ``update_exam``'s ``exclude_unset``-based partial-update
    convention: ``fields`` only contains the keys the caller actually sent
    (popped from ``update_data`` before this runs), so an explicit
    ``"org_unit_id": null`` still clears it even when ``visibility`` isn't
    resent in the same request — whereas ``update_data.get(...) is not None``
    couldn't distinguish "sent null" from "omitted".

    Ownership-gated (owner or SuperUser only), unlike the rest of
    ``update_exam``'s permission+institution-scoped fields — mirrors
    Document/TF-620's identical rule: a colleague who merely *sees* a
    team-scoped exam (e.g. via the visibility filter) must not be able to
    move it to a different Org-Unit or make it institution-wide.

    Returns ``None`` when visibility/org_unit_id weren't touched, else the
    ``{"visibility": ExamVisibility, "org_unit_id": Optional[int]}`` pair to
    apply.
    """
    if not fields:
        return None

    new_visibility = (
        ExamVisibility(fields["visibility"])
        if fields.get("visibility") is not None
        else exam.visibility
    )
    new_org_unit_id = (
        fields["org_unit_id"] if "org_unit_id" in fields else exam.org_unit_id
    )

    if new_visibility == exam.visibility and new_org_unit_id == exam.org_unit_id:
        # No-op: exclude_unset only proves the caller sent the key, not that
        # it changes anything — e.g. an explicit "visibility": null resolves
        # right back to the exam's current value. Don't force the
        # ownership gate below on a request that isn't actually touching
        # visibility; a non-owner colleague editing an unrelated field
        # (title, etc.) shouldn't 403 just because their client serialized
        # an unset optional field as null.
        return None

    is_owner = exam.created_by is not None and exam.created_by == user.id
    if not is_owner and not user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Nur der Ersteller oder ein SuperUser darf die Sichtbarkeit ändern.",
        )

    if new_visibility == ExamVisibility.TEAM:
        if new_org_unit_id is None:
            raise HTTPException(
                status_code=400,
                detail="Team-Sichtbarkeit erfordert eine Org-Unit (org_unit_id).",
            )
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
    else:
        new_org_unit_id = None

    return {"visibility": new_visibility, "org_unit_id": new_org_unit_id}


@router.put("/{exam_id}", response_model=ExamOut)
async def update_exam(
    exam_id: int,
    request: ExamUpdate,
    http_request: Request,
    current_user: User = Depends(require_permission("create_exams")),
    db: Session = Depends(get_db),
):
    """Update exam metadata. Requires updated_at for optimistic locking."""
    locale = get_request_locale(http_request, current_user)
    exam = _get_exam_or_404(
        exam_id, db, current_user, locale, allow_read_all_bypass=False
    )
    _require_draft(exam, locale)

    # Optimistic locking — compare at microsecond precision with UTC normalisation
    if exam.updated_at and request.updated_at:
        if _to_utc(exam.updated_at) != _to_utc(request.updated_at):
            raise HTTPException(
                status_code=409,
                detail=t("exams_conflict", locale=locale),
            )

    update_data = request.model_dump(exclude_unset=True, exclude={"updated_at"})
    # TF-643: pulled out of the generic setattr loop below — needs
    # ownership-gated validation (_resolve_exam_visibility_update), not a
    # raw string assignment.
    visibility_fields = {
        key: update_data.pop(key)
        for key in ("visibility", "org_unit_id")
        if key in update_data
    }
    if "grading_scheme_id" in update_data:
        update_data["grading_scheme_id"] = _resolve_grading_scheme_id(
            db=db,
            user=current_user,
            explicit_id=update_data["grading_scheme_id"],
            fall_back_to_institution_default=False,
        )
    for field, value in update_data.items():
        setattr(exam, field, value)

    old_visibility, old_org_unit_id = exam.visibility, exam.org_unit_id
    visibility_update = _resolve_exam_visibility_update(
        exam, visibility_fields, current_user, db
    )
    if visibility_update is not None:
        exam.visibility = visibility_update["visibility"]
        exam.org_unit_id = visibility_update["org_unit_id"]
        if exam.visibility != old_visibility:
            update_data["visibility"] = exam.visibility.value
        if exam.org_unit_id != old_org_unit_id:
            update_data["org_unit_id"] = exam.org_unit_id

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
    # TF-504: metadata updates were silent while create/delete/grading-scheme
    # were audited — close the asymmetry.
    from services.audit_service import AuditService

    AuditService.log_action(
        db,
        action="update_exam",
        status=AuditService.STATUS_SUCCESS,
        user_id=current_user.id,
        resource_type="exam",
        resource_id=str(exam.id),
        request=http_request,
        additional_data={"changed_fields": sorted(update_data.keys())},
    )
    logger.info(f"Updated exam {exam_id} by user {current_user.id}")
    return _exam_to_out(exam)


@router.patch("/{exam_id}/grading-scheme", response_model=ExamOut)
async def update_exam_grading_scheme(
    exam_id: int,
    request: ExamGradingSchemeUpdate,
    http_request: Request,
    current_user: User = Depends(require_permission("create_exams")),
    db: Session = Depends(get_db),
):
    """Reassign or clear the grading scheme on any exam (incl. finalized).

    Bypasses ``_require_draft`` because reassigning the grading scheme is
    metadata-only and the instructor must be able to fix a wrong
    institution-default after finalisation. ``None`` clears the field
    so the export falls back to the institution default at render time.
    """
    locale = get_request_locale(http_request, current_user)
    exam = _get_exam_or_404(
        exam_id, db, current_user, locale, allow_read_all_bypass=False
    )

    # Optimistic locking — same shape as PUT /{exam_id}. Reassignment
    # is rare but two lehrpersons editing in parallel must not silently
    # overwrite each other.
    if exam.updated_at and request.updated_at:
        if _to_utc(exam.updated_at) != _to_utc(request.updated_at):
            raise HTTPException(
                status_code=409,
                detail=t("exams_conflict", locale=locale),
            )

    previous_id = exam.grading_scheme_id
    new_id = _resolve_grading_scheme_id(
        db=db,
        user=current_user,
        explicit_id=request.grading_scheme_id,
        fall_back_to_institution_default=False,
    )
    exam.grading_scheme_id = new_id

    try:
        db.commit()
        db.refresh(exam)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(
            "Database error in update_exam_grading_scheme for exam %s: %s",
            exam_id,
            exc,
        )
        raise HTTPException(status_code=500, detail=t("exams_db_error", locale=locale))

    # Audit trail mirrors create/finalize/delete on this resource. The
    # grading scheme is the load-bearing input for export, so any change
    # to it on a finalized exam must be reconstructable.
    from services.audit_service import AuditService

    AuditService.log_action(
        db,
        action="update_exam_grading_scheme",
        status=AuditService.STATUS_SUCCESS,
        user_id=current_user.id,
        resource_type="exam",
        resource_id=str(exam.id),
        request=http_request,
        additional_data={
            "previous_grading_scheme_id": previous_id,
            "new_grading_scheme_id": new_id,
            "exam_status": exam.status,
        },
    )

    return _exam_to_out(exam)


@router.delete("/{exam_id}", status_code=204)
async def delete_exam(
    exam_id: int,
    request: Request,
    current_user: User = Depends(require_permission("delete_exams")),
    db: Session = Depends(get_db),
):
    """Hard-delete an exam — guarded (TF-398).

    The former one-click draft delete is gone; every deletion now goes
    through "archive first, then delete". Only allowed when ALL four
    guards are satisfied: previously archived ∧ no submissions ∧ not
    exported ∧ caller has ``delete_exams`` (Admin or Dozent — both roles
    are seeded for it). Otherwise HTTP 409. Before deletion an
    ``audit_logs`` snapshot is written; FK cascade cleans up
    ``exam_questions``.
    """
    locale = get_request_locale(request, current_user)
    exam = _get_exam_or_404(
        exam_id, db, current_user, locale, allow_read_all_bypass=False
    )

    block = _exam_delete_block_reason(db, exam, locale)
    if block is not None:
        raise HTTPException(status_code=409, detail=block)

    # Snapshot BEFORE deletion (forensic recoverability in the audit log).
    snapshot = {
        "title": exam.title,
        "course": exam.course,
        "status": exam.status,
        "language": exam.language,
        "total_points": exam.total_points,
        "question_count": len(exam.questions) if exam.questions else 0,
        "created_by": exam.created_by,
        "institution_id": exam.institution_id,
        "archived_at": exam.archived_at.isoformat() if exam.archived_at else None,
        "archived_by": exam.archived_by,
        "archive_reason": exam.archive_reason,
    }

    from services.audit_service import AuditService

    db.delete(exam)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        logger.error("IntegrityError in delete_exam for exam %s: %s", exam_id, exc)
        raise HTTPException(status_code=409, detail=t("exams_conflict", locale=locale))
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Database error in delete_exam for exam %s: %s", exam_id, exc)
        raise HTTPException(status_code=500, detail=t("exams_db_error", locale=locale))

    # log_action commits the delete + audit atomically; on an audit failure
    # it also rolls back the staged delete and returns None (fail loud).
    audit = AuditService.log_action(
        db,
        action="delete_exam",
        status=AuditService.STATUS_SUCCESS,
        user_id=current_user.id,
        resource_type="exam",
        resource_id=str(exam_id),
        request=request,
        additional_data=snapshot,
    )
    if audit is None:
        raise HTTPException(
            status_code=500, detail=t("delete_exam_failed", locale=locale)
        )
    logger.info(f"Deleted exam {exam_id} by user {current_user.id}")


@router.post("/{exam_id}/archive", response_model=ExamOut)
async def archive_exam(
    exam_id: int,
    request: ExamArchiveRequest,
    http_request: Request,
    current_user: User = Depends(require_permission("create_exams")),
    db: Session = Depends(get_db),
):
    """Archive an exam — allowed in any status (draft / finalized /
    exported). Purpose is cleanup: only sets ``archived_at/by/reason`` and
    hides the exam from the active overview. ``status``, export, and
    submissions stay untouched. 409 if already archived (idempotency-safe).
    **Required Permission:** ``create_exams`` (composer). (TF-398)
    """
    locale = get_request_locale(http_request, current_user)
    exam = _get_exam_or_404(
        exam_id, db, current_user, locale, allow_read_all_bypass=False
    )
    if exam.archived_at is not None:
        raise HTTPException(
            status_code=409,
            detail=t("exam_archive_already_archived", locale=locale),
        )

    exam.archived_at = datetime.utcnow()
    exam.archived_by = current_user.id
    exam.archive_reason = request.reason

    from services.audit_service import AuditService

    audit = AuditService.log_action(
        db,
        action="archive_exam",
        status=AuditService.STATUS_SUCCESS,
        user_id=current_user.id,
        resource_type="exam",
        resource_id=str(exam_id),
        request=http_request,
        additional_data={"reason": request.reason},
    )
    if audit is None:
        raise HTTPException(
            status_code=500, detail=t("exam_archive_failed", locale=locale)
        )
    db.refresh(exam)
    logger.info(f"Archived exam {exam_id} by user {current_user.id}")
    return _exam_to_out(exam)


@router.post("/{exam_id}/restore", response_model=ExamOut)
async def restore_exam(
    exam_id: int,
    http_request: Request,
    current_user: User = Depends(require_permission("create_exams")),
    db: Session = Depends(get_db),
):
    """Restore an archived exam — sets ``archived_at = NULL`` and leaves
    the original ``status`` untouched. 409 if not archived.
    **Required Permission:** ``create_exams``. (TF-398)
    """
    locale = get_request_locale(http_request, current_user)
    exam = _get_exam_or_404(
        exam_id, db, current_user, locale, allow_read_all_bypass=False
    )
    if exam.archived_at is None:
        raise HTTPException(
            status_code=409,
            detail=t("exam_archive_not_archived", locale=locale),
        )

    exam.archived_at = None
    exam.archived_by = None
    exam.archive_reason = None

    from services.audit_service import AuditService

    audit = AuditService.log_action(
        db,
        action="restore_exam",
        status=AuditService.STATUS_SUCCESS,
        user_id=current_user.id,
        resource_type="exam",
        resource_id=str(exam_id),
        request=http_request,
        additional_data={},
    )
    if audit is None:
        raise HTTPException(
            status_code=500, detail=t("exam_restore_failed", locale=locale)
        )
    db.refresh(exam)
    logger.info(f"Restored exam {exam_id} by user {current_user.id}")
    return _exam_to_out(exam)


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
    current_user: User = Depends(require_permission("create_exams")),
    db: Session = Depends(get_db),
):
    """Add approved questions to exam with auto-suggested points."""
    locale = get_request_locale(http_request, current_user)
    exam = _get_exam_or_404(
        exam_id, db, current_user, locale, allow_read_all_bypass=False
    )
    _require_draft(exam, locale)

    max_pos = max((eq.position for eq in exam.questions), default=0)
    existing_qids = {eq.question_id for eq in exam.questions}

    for qid in request.question_ids:
        if qid in existing_qids:
            continue  # Skip duplicates silently

        question = db.query(QuestionReview).filter(QuestionReview.id == qid).first()
        if not question:
            raise HTTPException(
                status_code=404, detail=t("exams_question_not_found", locale=locale)
            )

        # TF-642 bugfix: this previously checked only institution membership
        # (TenantFilter.verify_tenant_access), letting any create_exams
        # holder add a colleague's PRIVATE or off-team TEAM question just by
        # guessing its numeric id — completely bypassing the visibility model
        # this ticket introduces for the rest of the Fragenpool. 404 (not
        # 403) so a hidden question stays indistinguishable from a missing
        # one, same convention as assert_document_visible_for (TF-640).
        assert_question_visible_for(
            current_user,
            question,
            db,
            detail=t("exams_question_not_found", locale=locale),
        )

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
    current_user: User = Depends(require_permission("create_exams")),
    db: Session = Depends(get_db),
):
    """Update points or section of a question in the exam."""
    locale = get_request_locale(http_request, current_user)
    exam = _get_exam_or_404(
        exam_id, db, current_user, locale, allow_read_all_bypass=False
    )
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

    from services.audit_service import AuditService

    AuditService.log_action(
        db,
        action="update_exam_question",
        status=AuditService.STATUS_SUCCESS,
        user_id=current_user.id,
        resource_type="exam",
        resource_id=str(exam.id),
        request=http_request,
        additional_data={
            "exam_question_id": eq_id,
            "points": request.points,
            "section": request.section,
        },
    )

    return _exam_detail_to_out(exam)


@router.delete("/{exam_id}/questions/{eq_id}", response_model=ExamDetailOut)
async def remove_exam_question(
    exam_id: int,
    eq_id: int,
    request: Request,
    current_user: User = Depends(require_permission("create_exams")),
    db: Session = Depends(get_db),
):
    """Remove a question from the exam and re-number remaining positions."""
    locale = get_request_locale(request, current_user)
    exam = _get_exam_or_404(
        exam_id, db, current_user, locale, allow_read_all_bypass=False
    )
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

    from services.audit_service import AuditService

    AuditService.log_action(
        db,
        action="remove_exam_question",
        status=AuditService.STATUS_SUCCESS,
        user_id=current_user.id,
        resource_type="exam",
        resource_id=str(exam.id),
        request=request,
        additional_data={"exam_question_id": eq_id},
    )

    return _exam_detail_to_out(exam)


@router.post("/{exam_id}/reorder", response_model=ExamDetailOut)
async def reorder_questions(
    exam_id: int,
    request: ReorderRequest,
    http_request: Request,
    current_user: User = Depends(require_permission("create_exams")),
    db: Session = Depends(get_db),
):
    """Batch reorder questions in the exam."""
    locale = get_request_locale(http_request, current_user)
    exam = _get_exam_or_404(
        exam_id, db, current_user, locale, allow_read_all_bypass=False
    )
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
    document_ids: Optional[List[int]] = None

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
    current_user: User = Depends(require_permission("create_exams")),
    db: Session = Depends(get_db),
):
    """Auto-fill exam with questions matching criteria.

    Simple mode: random selection by count (default when no composition constraints set).
    Composition mode: constraint-based greedy optimization with optional preview.
    """
    locale = get_request_locale(http_request, current_user)
    exam = _get_exam_or_404(
        exam_id, db, current_user, locale, allow_read_all_bypass=False
    )
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
    query = db.query(QuestionReview).filter(
        QuestionReview.review_status == ReviewStatus.APPROVED.value,
        # TF-396: don't offer archived questions for reuse
        QuestionReview.archived_at.is_(None),
    )
    # TF-642: same question pool as list_approved_questions — auto-compose
    # must not propose questions that manual search hides.
    query = filter_questions_for_user(query, current_user, db)

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
    if request.document_ids:
        linked_ids = (
            db.query(QuestionSourceDocument.question_id)
            .filter(QuestionSourceDocument.document_id.in_(request.document_ids))
            .distinct()
        )
        query = query.filter(QuestionReview.id.in_(linked_ids))

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
    current_user: User = Depends(require_permission("create_exams")),
    db: Session = Depends(get_db),
):
    """Finalize exam. Validates all questions are still approved."""
    locale = get_request_locale(request, current_user)
    exam = _get_exam_or_404(
        exam_id, db, current_user, locale, allow_read_all_bypass=False
    )
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
    current_user: User = Depends(require_permission("create_exams")),
    db: Session = Depends(get_db),
):
    """Revert exam from finalized/exported to draft."""
    locale = get_request_locale(request, current_user)
    exam = _get_exam_or_404(
        exam_id, db, current_user, locale, allow_read_all_bypass=False
    )
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
    current_user: User = Depends(require_permission("create_exams")),
    db: Session = Depends(get_db),
):
    """Export exam in specified format (md, pdf, json, moodle)."""
    locale = get_request_locale(request, current_user)
    exam = _get_exam_or_404(
        exam_id, db, current_user, locale, allow_read_all_bypass=False
    )

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

    safe_title = filename_stem(exam.title)
    # The suffix labels the document, so it follows the exam's language
    # rather than the exporting user's UI locale (TF-656).
    solutions_suffix = (
        "_" + t("export_solutions_suffix", locale=exam_data.get("language") or locale)
        if include_solutions
        else ""
    )

    try:
        if format == "md":
            content = MarkdownExporter.export(
                exam_data, include_solutions=include_solutions
            )
            media_type = "text/markdown"
            filename = f"{safe_title}{solutions_suffix}.md"
        elif format == "pdf":
            content = PdfExporter.export(exam_data, include_solutions=include_solutions)
            media_type = "application/pdf"
            filename = f"{safe_title}{solutions_suffix}.pdf"
        elif format == "json":
            content = JsonExporter.export(exam_data)
            media_type = "application/json"
            filename = f"{safe_title}.json"
        elif format == "moodle":
            content = MoodleXmlExporter.export(exam_data)
            media_type = "application/xml"
            filename = f"{safe_title}_moodle.xml"
        else:
            raise HTTPException(
                status_code=400,
                detail=t("exams_unsupported_format", locale=locale),
            )
    except HTTPException:
        raise
    except Exception:
        # Unhandled exporter exceptions are otherwise logless 500s.
        logger.exception("Exam export failed: format=%s exam_id=%d", format, exam_id)
        raise HTTPException(
            status_code=500,
            detail=t("exams_export_internal_error", locale=locale),
        )

    # Update status to exported if currently finalized
    if exam.status == ExamStatus.FINALIZED.value:
        exam.status = ExamStatus.EXPORTED.value
        db.commit()

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": content_disposition(filename)},
    )
