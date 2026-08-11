"""
Document API Endpoints für ExamCraft AI
Verwaltet Document Upload, Listing und Management
"""

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
    Depends,
    Query,
    Request,
    BackgroundTasks,
)
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.concurrency import run_in_threadpool
from typing import Annotated, List, Literal, Optional
from sqlalchemy import func, or_, and_, select, union_all
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator, model_validator
import mimetypes
import os
from math import ceil
from urllib.parse import quote

from services.document_service import DocumentService
from services.storage_service import (
    storage_service,
    StorageAccessDeniedError,
    StorageConfigurationError,
    StorageThrottledError,
    StorageUnavailableError,
)
from services.translation_service import t, get_request_locale
from services.quality_assessor import EscalationState
from services.vector_service_factory import vector_service
from models.document import Document, DocumentStatus, DocumentVisibility
from models.auth import User
from models.org_unit import OrgUnit
from models.tag import Tag, DocumentTag, DocumentPersonalTag
from utils.document_tags import (
    visible_tags_for_user,
    attach_tags_for_user,
    detach_tag_for_user,
    detach_institution_tags,
    STATUS_GROUPS,
    MIME_FAMILIES,
)
from database import get_db
from utils.auth_utils import get_current_active_user, require_permission
from utils.document_visibility import (
    assert_document_visible_for,
    filter_documents_for_user,
)
from services.org_unit_service import get_user_accessible_org_unit_ids
from tasks.document_tasks import process_document as celery_process_document
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])
document_service = DocumentService()


# Pydantic Models für API Responses
class DocumentTagOut(BaseModel):
    id: int
    name: str
    scope: Literal["user", "institution", "global"]
    is_own: bool = False
    # True when this entry is a *personal* assignment of the current user
    # (document_personal_tags) rather than a shared institution assignment
    # (document_tags). Lets the UI render personal tags distinctly (TF-399).
    is_personal: bool = False
    model_config = {"from_attributes": True}


class DocumentTagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    scope: Literal["user", "institution"] = "user"


class AttachTagsRequest(BaseModel):
    tag_ids: List[int] = Field(..., min_length=1)


class DocumentResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    title: str  # Resolved display title (display_name → metadata → filename)
    display_name: Optional[str] = None  # Raw user override, null when unset
    file_size: int
    mime_type: str
    status: str
    visibility: Optional[str] = (
        None  # 'private' | 'team' | 'institution' (TF-354/TF-620)
    )
    org_unit_id: Optional[int] = None  # Set only when visibility='team' (TF-620)
    org_unit_name: Optional[str] = None  # Resolved OrgUnit.name, for UI display
    user_id: Optional[int]  # Fixed: user_id is Integer in database, not String
    metadata: Optional[dict]
    content_preview: Optional[str]
    vector_collection: Optional[str]
    has_vectors: Optional[bool]
    created_at: Optional[str]
    updated_at: Optional[str]
    processed_at: Optional[str]
    tags: List[DocumentTagOut] = []
    # OCR-/Qualitäts-Eskalation (TF-360/TF-361/TF-365). Ohne diese Felder verwirft
    # Pydantic per Default (``extra`` ist nicht auf ``'allow'`` gesetzt) die von
    # Document.to_dict() gelieferten Werte still, wodurch die Frontend-Badges nie
    # Daten erhielten. ``escalation`` macht eine laufende/fehlgeschlagene
    # OCR-Nachbearbeitung für den Nutzer sichtbar.
    quality: Optional[dict] = None
    processed_with_ocr: bool = False
    # ``escalation`` trägt dieselbe geschlossene Wertemenge wie upstream in
    # quality_assessor.EscalationState — als Literal getypt, statt die Garantie
    # an der API-Grenze auf ``str`` zu verwässern (TF-365 follow-up).
    escalation: Optional[EscalationState] = None


class DocumentPatchRequest(BaseModel):
    """Body for PATCH /documents/{id} — update display name and/or visibility.

    At least one field must be provided (enforced by ``_require_at_least_one``).

    ``display_name`` keeps the original rename semantics: a non-empty string
    overrides the auto-extracted title; ``None``/empty/whitespace clears the
    override and falls back to the resolver chain (filtered metadata title →
    original filename). Trimmed to 1–255 chars; control characters rejected.

    ``visibility`` is owner-only — the ownership check lives in the endpoint,
    not here, because it needs the loaded document and the current user.

    The endpoint distinguishes "field omitted" from "field set to null" via
    ``model_fields_set``, so a passed-but-null ``display_name`` still counts as
    a (clearing) rename rather than a no-op.
    """

    display_name: Optional[str] = None
    visibility: Optional[DocumentVisibility] = None
    org_unit_id: Optional[int] = None

    @field_validator("display_name")
    @classmethod
    def _normalise_display_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("display_name must be a string")
        trimmed = v.strip()
        if not trimmed:
            # Empty/whitespace string is the "clear override" signal
            return None
        if len(trimmed) > 255:
            raise ValueError("display_name must be 255 characters or fewer")
        # Reject ASCII control characters (except tab, which we strip anyway).
        # A document name is a UI label, not a payload — invisible/escape
        # sequences here are almost always malicious or accidental paste.
        if any(ord(c) < 0x20 or ord(c) == 0x7F for c in trimmed):
            raise ValueError("display_name contains invalid control characters")
        return trimmed

    @model_validator(mode="after")
    def _require_at_least_one(self):
        # ``display_name`` counts even when explicitly null (null clears the
        # override). An explicit ``visibility: null`` does NOT count: the
        # endpoint skips a null visibility, so a body of ``{"visibility": null}``
        # would be a silent 200 no-op. Requiring a non-null visibility here turns
        # that dead request into a 422 instead. ``org_unit_id`` follows the same
        # non-null rule (TF-620) — e.g. re-scoping an already team-visible
        # document to a different OrgUnit without also touching ``visibility``.
        has_display = "display_name" in self.model_fields_set
        has_visibility = (
            "visibility" in self.model_fields_set and self.visibility is not None
        )
        has_org_unit_id = (
            "org_unit_id" in self.model_fields_set and self.org_unit_id is not None
        )
        if not (has_display or has_visibility or has_org_unit_id):
            raise ValueError(
                "At least one of 'display_name', 'visibility' or "
                "'org_unit_id' must be provided"
            )
        return self


class DocumentStats(BaseModel):
    total: int
    processed: int
    with_vectors: int
    in_progress: int


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    stats: DocumentStats


class UploadResponse(BaseModel):
    document_id: int
    filename: str
    status: str
    message: str


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    visibility: DocumentVisibility = Form(DocumentVisibility.PRIVATE),
    org_unit_id: Optional[int] = Form(None),
    http_request: Request = None,
    current_user: User = Depends(require_permission("create_documents")),
    db: Session = Depends(get_db),
):
    """
    Upload ein neues Dokument (Asynchrone Verarbeitung mit Celery)

    **Required Permission:** `create_documents` (Dozent, Assistant, Admin)

    - **file**: Dokument zum Upload (PDF, DOC, DOCX, TXT, MD)
    - **visibility**: `private` (nur ich, Default), `team` (geteilt mit einer
      eigenen OrgUnit) oder `institution` (geteilt). `institution` ist nur
      erlaubt, wenn der User einer Institution angehört; `team` erfordert
      zusätzlich **org_unit_id** (siehe unten).
    - **org_unit_id**: Ziel-OrgUnit für `visibility=team`. Muss eine OrgUnit
      sein, der der Uploader selbst angehört (via GET
      `/api/v1/org-units/mine`) — sonst 400.

    Returns:
        UploadResponse mit Document ID und Status

    **Note:** Document wird asynchron verarbeitet. Status kann via GET /documents/{id} abgerufen werden.
    """
    locale = get_request_locale(http_request, current_user)

    try:
        # Visibility (TF-354): validate up front so we never persist a file
        # we then reject. 'institution' requires the user to belong to one.
        # Inside the try/except below (TF-620 fix) so an unexpected DB error
        # from either check gets the same structured logging + localized
        # 500 as the rest of this endpoint, instead of falling through to
        # FastAPI's default handler.
        if (
            visibility == DocumentVisibility.INSTITUTION
            and not current_user.institution_id
        ):
            raise HTTPException(
                status_code=400,
                detail=t("documents_visibility_no_institution", locale=locale),
            )

        # Visibility (TF-620): 'team' requires org_unit_id, and it must be
        # one of the uploader's own OrgUnit memberships (not any OrgUnit in
        # the institution — see GET /org-units/mine).
        if visibility == DocumentVisibility.TEAM:
            accessible = (
                get_user_accessible_org_unit_ids(
                    db, current_user.id, current_user.institution_id
                )
                if current_user.institution_id
                else set()
            )
            if org_unit_id is None or org_unit_id not in accessible:
                raise HTTPException(
                    status_code=400,
                    detail=t("documents_visibility_invalid_org_unit", locale=locale),
                )

        # Check document limit for institution
        from utils.tenant_utils import SubscriptionLimits

        SubscriptionLimits.check_document_limit(
            current_user.institution,
            db,
            user=current_user,
            request=http_request,
        )

        # Check storage limit (if file size is known)
        if file.size and file.size > 0:
            SubscriptionLimits.check_storage_limit(
                current_user.institution,
                db,
                file.size,
                user=current_user,
                request=http_request,
            )

        # Save document file and create DB entry
        document = await document_service.upload_document(
            file=file, user_id=current_user.id, db=db
        )

        # Set institution_id for multi-tenancy + visibility (TF-354)
        document.institution_id = current_user.institution_id
        document.visibility = visibility
        # TF-620: org_unit_id only meaningful for visibility=team — validated above.
        document.org_unit_id = (
            org_unit_id if visibility == DocumentVisibility.TEAM else None
        )
        document.status = DocumentStatus.QUEUED  # Set to QUEUED for async processing
        db.commit()
        db.refresh(document)

        # Dispatch async processing task to Celery
        task = celery_process_document.apply_async(
            args=[str(document.id), str(current_user.id)],
            countdown=0,  # Start immediately
        )

        # Store task ID for tracking
        document.task_id = task.id
        db.commit()

        # Audit log: Document created
        from services.audit_service import AuditService

        AuditService.log_document_action(
            db,
            AuditService.ACTION_CREATE_DOCUMENT,
            current_user.id,
            document.id,
            request=http_request,
            additional_data={
                "original_filename": document.original_filename,
                "filename": document.filename,
                "task_id": task.id,
            },
        )

        return UploadResponse(
            document_id=document.id,
            filename=document.filename,
            status=document.status.value,
            message="Document queued for processing. Check status via GET /documents/{id}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=t("documents_upload_failed", locale=locale)
        )


def _apply_sort(query, sort: str):
    title_col = func.coalesce(Document.display_name, Document.original_filename)
    mapping = {
        "created_at_desc": Document.created_at.desc(),
        "created_at_asc": Document.created_at.asc(),
        "title_asc": title_col.asc(),
        "title_desc": title_col.desc(),
        "size_desc": Document.file_size.desc(),
        "size_asc": Document.file_size.asc(),
    }
    return query.order_by(mapping.get(sort, Document.created_at.desc()))


def _compute_stats(base_query) -> "DocumentStats":
    """Stats over the visibility-scoped base query (ignores content filters).
    Passes enum members (not raw strings) to .in_() so SQLAlchemy maps them
    to the stored column values.
    base_query is a generative Query; each .filter() returns a new query."""
    total = base_query.count()
    processed = base_query.filter(
        Document.status.in_([DocumentStatus.COMPLETED, DocumentStatus.PROCESSED])
    ).count()
    in_progress = base_query.filter(
        Document.status.in_([DocumentStatus.QUEUED, DocumentStatus.PROCESSING])
    ).count()
    with_vectors = base_query.filter(Document.has_vectors.is_(True)).count()
    return DocumentStats(
        total=total,
        processed=processed,
        with_vectors=with_vectors,
        in_progress=in_progress,
    )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    q: Annotated[Optional[str], Query()] = None,
    visibility: Annotated[Optional[Literal["own", "shared"]], Query()] = None,
    status: Annotated[
        List[Literal["uploaded", "processing", "processed", "error"]], Query()
    ] = None,
    mime_family: Annotated[
        List[Literal["pdf", "word", "markdown", "text", "chat"]], Query()
    ] = None,
    tag_ids: Annotated[List[int], Query()] = None,
    sort: Literal[
        "created_at_desc",
        "created_at_asc",
        "title_asc",
        "title_desc",
        "size_desc",
        "size_asc",
    ] = "created_at_desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=96)] = 24,
    request: Request = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Paginated, filterable, sortable document list with embedded stats (TF-355)."""
    locale = get_request_locale(request, current_user)
    try:
        base = filter_documents_for_user(db.query(Document), current_user, db)
        if visibility == "own":
            base = base.filter(Document.user_id == current_user.id)
        elif visibility == "shared":
            base = base.filter(Document.user_id != current_user.id)

        # Stats: from the visibility-scoped base, IGNORING q/status/mime/tag filters.
        stats = _compute_stats(base)

        # Document query: base + content filters.
        query = base
        if q:
            # Escape ILIKE wildcards so a literal "_"/"%" (common in filenames)
            # is matched literally, not as a pattern.
            escaped = (
                q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            pattern = f"%{escaped}%"
            query = query.filter(
                or_(
                    Document.display_name.ilike(pattern, escape="\\"),
                    Document.original_filename.ilike(pattern, escape="\\"),
                    Document.content_preview.ilike(pattern, escape="\\"),
                )
            )
        if status:
            statuses = []
            for group in status:
                if group not in STATUS_GROUPS:
                    raise HTTPException(
                        status_code=400,
                        detail=t("documents_invalid_status", locale=locale),
                    )
                statuses.extend(STATUS_GROUPS[group])
            query = query.filter(Document.status.in_(statuses))
        if mime_family:
            clauses = []
            chat_flag = Document.doc_metadata["source"].as_string() == "chat_export"
            # NULL-safe: doc_metadata is None OR source key absent (SQL NULL) OR
            # source != "chat_export". Without the is_(None) check on the key the
            # `not_(chat_flag)` expression is SQL NULL for docs whose metadata dict
            # exists but lacks a "source" key — those rows would be silently dropped.
            not_chat_flag = or_(
                Document.doc_metadata.is_(None),
                Document.doc_metadata["source"].as_string().is_(None),
                Document.doc_metadata["source"].as_string() != "chat_export",
            )
            for fam in mime_family:
                if fam == "chat":
                    clauses.append(chat_flag)
                elif fam == "text":
                    clauses.append(
                        and_(Document.mime_type == "text/plain", not_chat_flag)
                    )
                elif fam in MIME_FAMILIES:
                    clauses.append(Document.mime_type.in_(MIME_FAMILIES[fam]))
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=t("documents_invalid_filter", locale=locale),
                    )
            query = query.filter(or_(*clauses))
        if tag_ids:
            unique_tag_ids = list(dict.fromkeys(tag_ids))
            # Match across shared assignments (document_tags) AND the caller's
            # own personal assignments (document_personal_tags), so the library
            # can be filtered by personal tags too (TF-399). The two scopes are
            # disjoint, so count(distinct tag_id) gives correct AND-semantics.
            tag_pairs = union_all(
                select(
                    DocumentTag.document_id.label("document_id"),
                    DocumentTag.tag_id.label("tag_id"),
                ),
                select(
                    DocumentPersonalTag.document_id.label("document_id"),
                    DocumentPersonalTag.tag_id.label("tag_id"),
                ).where(DocumentPersonalTag.user_id == current_user.id),
            ).subquery()
            query = (
                query.join(tag_pairs, tag_pairs.c.document_id == Document.id)
                .filter(tag_pairs.c.tag_id.in_(unique_tag_ids))
                .group_by(Document.id)
                .having(
                    func.count(func.distinct(tag_pairs.c.tag_id)) == len(unique_tag_ids)
                )
            )

        query = _apply_sort(query, sort)

        total = db.query(func.count()).select_from(query.subquery()).scalar() or 0
        total_pages = ceil(total / page_size) if total else 0
        rows = query.offset((page - 1) * page_size).limit(page_size).all()

        # Batch-load every page row's tags in ONE query (was an N+1: one Tag
        # join per document, up to page_size round-trips). _document_tags_map
        # groups the rows in Python; _document_response_with_tags is reused for
        # the single-document endpoints.
        tags_by_doc = _document_tags_map([doc.id for doc in rows], current_user, db)
        # Same batching rationale as tags_by_doc — one query for the whole
        # page's Org-Unit names instead of one per team-visible row (TF-620).
        org_unit_names = _org_unit_names_map([doc.org_unit_id for doc in rows], db)
        documents = []
        for doc in rows:
            doc_dict = doc.to_dict()
            doc_dict["tags"] = tags_by_doc.get(doc.id, [])
            doc_dict["org_unit_name"] = org_unit_names.get(doc.org_unit_id)
            documents.append(DocumentResponse(**doc_dict))
        return DocumentListResponse(
            documents=documents,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            stats=stats,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to list documents for user {current_user.id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=t("documents_list_failed", locale=locale)
        )


# Health check endpoint (muss vor parametrisierten Routen stehen)
@router.get("/health")
async def health_check():
    """Health check für Document Service"""
    return {
        "status": "healthy",
        "service": "Document Upload Service",
        "supported_formats": list(document_service.supported_formats.values()),
        "max_file_size_mb": document_service.max_file_size // (1024 * 1024),
    }


@router.get("/tags", response_model=List[DocumentTagOut])
async def list_document_tags(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Tags the user may attach to documents (own user-tags + institution + global)."""
    tags = visible_tags_for_user(db, current_user).order_by(func.lower(Tag.name)).all()
    return [
        DocumentTagOut(
            id=t.id,
            name=t.name,
            scope=t.scope,
            is_own=(t.created_by == current_user.id),
        )
        for t in tags
    ]


@router.post(
    "/tags", response_model=DocumentTagOut, status_code=200
)  # get-or-create: returns existing tag on name match, so 200 (not 201)
async def create_document_tag(
    body: DocumentTagCreate,
    request: Request = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create (or return existing) a document tag. ``user`` scope for everyone;
    ``institution`` scope requires the ``manage_settings`` permission."""
    locale = get_request_locale(request, current_user)
    if body.scope == "institution" and not current_user.has_permission(
        "manage_settings"
    ):
        raise HTTPException(
            status_code=403,
            detail=t("documents_tag_institution_admin_only", locale=locale),
        )

    name = body.name.strip()
    name_lower = name.lower()
    if body.scope == "user":
        existing = (
            db.query(Tag)
            .filter(
                Tag.scope == "user",
                Tag.created_by == current_user.id,
                func.lower(Tag.name) == name_lower,
            )
            .first()
        )
        institution_id = None
    else:  # institution
        existing = (
            db.query(Tag)
            .filter(
                Tag.scope == "institution",
                Tag.institution_id == current_user.institution_id,
                func.lower(Tag.name) == name_lower,
            )
            .first()
        )
        institution_id = current_user.institution_id

    if existing:
        return DocumentTagOut(
            id=existing.id,
            name=existing.name,
            scope=existing.scope,
            is_own=(existing.created_by == current_user.id),
        )

    tag = Tag(
        name=name,
        scope=body.scope,
        institution_id=institution_id,
        created_by=current_user.id,
    )
    db.add(tag)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail=t("documents_tag_exists", locale=locale)
        )
    db.refresh(tag)
    return DocumentTagOut(id=tag.id, name=tag.name, scope=tag.scope, is_own=True)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Hole spezifisches Dokument nach ID

    **Required:** Authenticated user

    - **document_id**: ID des gewünschten Dokuments

    Returns:
        Document Details mit Metadaten
    """
    locale = get_request_locale(request, current_user)
    try:
        document = document_service.get_document_by_id(document_id, db)

        if not document:
            raise HTTPException(
                status_code=404, detail=t("documents_not_found", locale=locale)
            )

        # 404 (not 403) on a hidden doc — rationale on assert_document_visible_for.
        assert_document_visible_for(current_user, document, db, locale=locale)

        return _document_response_with_tags(document, current_user, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get document {document_id} for user {current_user.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=t("documents_load_failed", locale=locale),
        )


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int,
    payload: DocumentPatchRequest,
    request: Request,
    current_user: User = Depends(require_permission("create_documents")),
    db: Session = Depends(get_db),
):
    """Update a document's display name and/or visibility.

    - **display_name**: rename behaviour unchanged — a non-empty string
      overrides the auto-extracted title; ``null``/empty/whitespace clears the
      override (falls back to the metadata-then-filename resolver). Allowed for
      any document the caller can see.
    - **visibility**: ``private``/``team``/``institution``. **Owner-only**
      (SuperUser may also change it) — a non-owner gets 403 even within the
      same institution. ``institution`` requires the document to belong to an
      institution; ``team`` requires **org_unit_id** (below). Every effective
      change is written to the audit log.
    - **org_unit_id**: target OrgUnit for ``visibility=team`` (own membership
      only — see GET ``/org-units/mine``). Providing it without a resulting
      ``visibility=team`` is a 400; leaving ``team`` clears it automatically.

    At least one field must be provided (422 otherwise). Field-level validation
    (length, control characters, enum membership) happens in
    ``DocumentPatchRequest`` and surfaces as 422.

    **Required Permission:** ``create_documents``
    """
    locale = get_request_locale(request, current_user)
    # Each effective metadata change appends one audit-row payload here; all of
    # them commit together with the mutation in a single transaction below.
    audit_entries: list[dict] = []
    try:
        document = document_service.get_document_by_id(document_id, db)
        if not document:
            raise HTTPException(
                status_code=404, detail=t("documents_not_found", locale=locale)
            )

        # 404 (not 403) on a hidden doc — rationale on assert_document_visible_for.
        assert_document_visible_for(current_user, document, db, locale=locale)

        fields_set = payload.model_fields_set

        # --- Rename (display_name): owner-only + audited (TF-399). ---
        # display_name is shared state on the Document row — a rename changes the
        # name for every institution member — so it is now restricted to the
        # owner (SuperUser bypass preserved), mirroring the visibility rule, and
        # every effective change is written to the audit log.
        # The Pydantic validator already normalised empty/whitespace to None and
        # enforced the 255-char + no-control-chars invariant.
        if "display_name" in fields_set:
            is_owner = (
                document.user_id is not None and document.user_id == current_user.id
            )
            if not is_owner and not current_user.is_superuser:
                raise HTTPException(
                    status_code=403,
                    detail=t("documents_rename_owner_only", locale=locale),
                )
            old_display_name = document.display_name
            if old_display_name != payload.display_name:
                document.display_name = payload.display_name
                audit_entries.append(
                    {
                        "field": "display_name",
                        "old_display_name": old_display_name,
                        "new_display_name": payload.display_name,
                    }
                )

        # --- Visibility: stricter — owner-only (SuperUser bypass preserved). ---
        visibility_changed = False
        if "visibility" in fields_set and payload.visibility is not None:
            new_visibility = payload.visibility
            is_owner = (
                document.user_id is not None and document.user_id == current_user.id
            )
            if not is_owner and not current_user.is_superuser:
                raise HTTPException(
                    status_code=403,
                    detail=t("documents_visibility_owner_only", locale=locale),
                )
            if (
                new_visibility == DocumentVisibility.INSTITUTION
                and document.institution_id is None
            ):
                raise HTTPException(
                    status_code=400,
                    detail=t("documents_visibility_no_institution", locale=locale),
                )
            if document.visibility != new_visibility:
                old_visibility = document.visibility
                document.visibility = new_visibility
                visibility_changed = True
                audit_entries.append(
                    {
                        "field": "visibility",
                        "old_visibility": old_visibility.value
                        if old_visibility
                        else None,
                        "new_visibility": new_visibility.value,
                    }
                )
                # Leaving institution visibility: institution-scope tags may no
                # longer be attached (attach block rule). Detach them in the
                # same transaction so we never persist a private doc carrying
                # institution tags — a state the attach path rejects (TF-369
                # follow-up). Runs before the response is built below so the
                # returned tag list reflects the removal.
                if new_visibility != DocumentVisibility.INSTITUTION:
                    detach_institution_tags(db, document)

        # --- Org-Unit scope (TF-620): tied to visibility='team'. Owner-only,
        # same rule as visibility itself — a colleague who merely *sees* a
        # team-scoped doc must not be able to move it to another OrgUnit. ---
        org_unit_id_provided = (
            "org_unit_id" in fields_set and payload.org_unit_id is not None
        )
        if org_unit_id_provided:
            is_owner = (
                document.user_id is not None and document.user_id == current_user.id
            )
            if not is_owner and not current_user.is_superuser:
                raise HTTPException(
                    status_code=403,
                    detail=t("documents_visibility_owner_only", locale=locale),
                )

        effective_visibility = document.visibility  # reflects any change above
        # Whether THIS request actually touches the team scope. A patch that
        # only renames display_name on an already-team document must not
        # re-validate org-unit membership at all (TF-620 fix) — it neither
        # reads nor writes org_unit_id/visibility.
        scope_touched = org_unit_id_provided or visibility_changed
        if effective_visibility == DocumentVisibility.TEAM:
            new_org_unit_id = (
                payload.org_unit_id if org_unit_id_provided else document.org_unit_id
            )
            if scope_touched and not current_user.is_superuser:
                # Only re-validate the CALLER's org-unit membership when this
                # request actually sets/changes the scope. SuperUser keeps
                # the same bypass preserved everywhere else in this endpoint
                # (owner checks above) — without it, a SuperUser editing any
                # team-visible document outside their own membership would
                # always get a 400, even on an unrelated field (TF-620 fix).
                accessible = (
                    get_user_accessible_org_unit_ids(
                        db, current_user.id, current_user.institution_id
                    )
                    if current_user.institution_id
                    else set()
                )
                if new_org_unit_id is None or new_org_unit_id not in accessible:
                    raise HTTPException(
                        status_code=400,
                        detail=t(
                            "documents_visibility_invalid_org_unit", locale=locale
                        ),
                    )
            elif new_org_unit_id is None:
                # Defensive/normally unreachable: the DB constraint requires
                # org_unit_id whenever visibility=team, so an existing team
                # document always already has one. Guards against ever
                # persisting team visibility with no scope (e.g. a SuperUser
                # flipping visibility to 'team' without supplying
                # org_unit_id) if that invariant is ever violated upstream.
                raise HTTPException(
                    status_code=400,
                    detail=t("documents_visibility_invalid_org_unit", locale=locale),
                )
            if document.org_unit_id != new_org_unit_id:
                old_org_unit_id = document.org_unit_id
                document.org_unit_id = new_org_unit_id
                audit_entries.append(
                    {
                        "field": "org_unit_id",
                        "old_org_unit_id": old_org_unit_id,
                        "new_org_unit_id": new_org_unit_id,
                    }
                )
        elif org_unit_id_provided:
            # org_unit_id supplied without a resulting visibility='team' —
            # reject rather than silently drop a client-provided field.
            # Checked BEFORE the "left team" cleanup below: otherwise a
            # simultaneous {visibility: <non-team>, org_unit_id: X} patch
            # would silently clear org_unit_id instead of rejecting it
            # (TF-620 fix).
            raise HTTPException(
                status_code=400,
                detail=t("documents_visibility_invalid_org_unit", locale=locale),
            )
        elif visibility_changed and document.org_unit_id is not None:
            # Left 'team' visibility — clear the now-meaningless scope so no
            # row keeps a stale org_unit_id under private/institution.
            old_org_unit_id = document.org_unit_id
            document.org_unit_id = None
            audit_entries.append(
                {
                    "field": "org_unit_id",
                    "old_org_unit_id": old_org_unit_id,
                    "new_org_unit_id": None,
                }
            )

        # Build the response dict BEFORE persisting so a serialisation failure
        # cannot mask an already-persisted change as a generic 500. Tags are
        # unchanged by a patch, so loading them here (pre-commit) is safe.
        response_payload = document.to_dict()
        response_payload["tags"] = _document_tag_outs(document, current_user, db)
        response_payload["org_unit_name"] = _resolve_org_unit_name(
            document.org_unit_id, db
        )

        if audit_entries:
            # Both a rename and a visibility flip are privileged changes to
            # shared/DSGVO-relevant state: neither may persist without an audit
            # row. Each entry is staged with commit=False so all audit rows plus
            # the document mutation (and any institution-tag detach) commit in
            # ONE transaction below; log_document_action returns None on failure
            # (rolling back the whole transaction). Treating None as a hard 500
            # keeps every change and its audit atomic — we never report success
            # on an un-audited change, nor a 500 on a change that already landed.
            from services.audit_service import AuditService

            for entry in audit_entries:
                audit_log = AuditService.log_document_action(
                    db,
                    AuditService.ACTION_UPDATE_DOCUMENT,
                    current_user.id,
                    document_id,
                    request=request,
                    additional_data=entry,
                    commit=False,
                )
                if audit_log is None:
                    raise HTTPException(
                        status_code=500,
                        detail=t("documents_rename_failed", locale=locale),
                    )
            db.commit()
        else:
            # No effective change (e.g. rename to the current value): persist any
            # no-op cleanly so the request still returns the current state.
            db.commit()

        return DocumentResponse(**response_payload)

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        # DB-level failure (constraint, connection, …) — roll back the open
        # transaction and report an update-specific error so the user knows
        # which action failed and can retry.
        db.rollback()
        logger.error(
            f"DB error updating document {document_id} for user {current_user.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=t("documents_rename_failed", locale=locale),
        )
    except Exception as e:
        # Programming errors / unexpected bugs — log with stack, surface as 500.
        # We deliberately do NOT swallow these as a generic "load failed".
        db.rollback()
        logger.error(
            f"Unexpected error updating document {document_id} for user {current_user.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=t("documents_rename_failed", locale=locale),
        )


def _load_owned_document(document_id: int, current_user: User, db: Session, locale):
    """Load a doc the caller can see; require ownership (SuperUser bypass)."""
    document = document_service.get_document_by_id(document_id, db)
    if not document:
        raise HTTPException(
            status_code=404, detail=t("documents_not_found", locale=locale)
        )
    assert_document_visible_for(current_user, document, db, locale=locale)
    is_owner = document.user_id is not None and document.user_id == current_user.id
    if not is_owner and not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail=t("documents_tag_owner_only", locale=locale)
        )
    return document


def _load_visible_document(document_id: int, current_user: User, db: Session, locale):
    """Load a doc the caller can see (404 otherwise) and report whether the caller
    may mutate *shared* state (owner or SuperUser).

    Unlike ``_load_owned_document`` this does **not** 403 a non-owner:
    ``user``-scope (personal) tag operations are allowed for anyone who can see
    the document (TF-399). The shared-vs-personal permission is decided per tag
    downstream, where shared assignments still require ownership.
    """
    document = document_service.get_document_by_id(document_id, db)
    if not document:
        raise HTTPException(
            status_code=404, detail=t("documents_not_found", locale=locale)
        )
    assert_document_visible_for(current_user, document, db, locale=locale)
    is_owner = (
        document.user_id is not None and document.user_id == current_user.id
    ) or current_user.is_superuser
    return document, is_owner


def _document_response_with_tags(
    document, current_user: User, db: Session
) -> DocumentResponse:
    doc_dict = document.to_dict()
    doc_dict["tags"] = _document_tag_outs(document, current_user, db)
    doc_dict["org_unit_name"] = _resolve_org_unit_name(document.org_unit_id, db)
    return DocumentResponse(**doc_dict)


def _resolve_org_unit_name(org_unit_id, db: Session):
    """Single-document lookup of an OrgUnit's display name (TF-620).

    Used by the single-document response paths (GET/PATCH); the paginated
    list endpoint uses ``_org_unit_names_map`` instead to avoid an N+1.
    """
    if org_unit_id is None:
        return None
    return db.query(OrgUnit.name).filter(OrgUnit.id == org_unit_id).scalar()


def _org_unit_names_map(org_unit_ids, db: Session) -> "dict[int, str]":
    """Batch lookup of OrgUnit names for a page of documents (TF-620).

    Mirrors ``_document_tags_map``'s batching rationale: one query per page
    instead of one per row.
    """
    ids = {oid for oid in org_unit_ids if oid is not None}
    if not ids:
        return {}
    rows = db.query(OrgUnit.id, OrgUnit.name).filter(OrgUnit.id.in_(ids)).all()
    return {row[0]: row[1] for row in rows}


def _document_tag_outs(
    document, current_user: User, db: Session
) -> List[DocumentTagOut]:
    """Tags visible to ``current_user`` on this document, alphabetical by name.

    Unions shared institution assignments (``document_tags``) with the user's own
    personal assignments (``document_personal_tags``); personal entries are
    flagged ``is_personal`` and are never visible to other users (TF-399). The
    two scopes are disjoint, so no de-duplication is needed.
    """
    shared = (
        db.query(Tag)
        .join(DocumentTag, DocumentTag.tag_id == Tag.id)
        .filter(DocumentTag.document_id == document.id)
        .all()
    )
    personal = (
        db.query(Tag)
        .join(DocumentPersonalTag, DocumentPersonalTag.tag_id == Tag.id)
        .filter(
            DocumentPersonalTag.document_id == document.id,
            DocumentPersonalTag.user_id == current_user.id,
        )
        .all()
    )
    outs = [
        DocumentTagOut(
            id=t.id,
            name=t.name,
            scope=t.scope,
            is_own=(t.created_by == current_user.id),
            is_personal=False,
        )
        for t in shared
    ] + [
        DocumentTagOut(
            id=t.id,
            name=t.name,
            scope=t.scope,
            is_own=(t.created_by == current_user.id),
            is_personal=True,
        )
        for t in personal
    ]
    outs.sort(key=lambda o: o.name.lower())
    return outs


def _document_tags_map(
    document_ids: List[int], current_user: User, db: Session
) -> "dict[int, List[DocumentTagOut]]":
    """Load tags for many documents in one query, grouped by document id.

    Avoids the N+1 that calling ``_document_tag_outs`` per row would incur on a
    paginated listing. Tags within each document are alphabetical by name; the
    global ordering by ``lower(name)`` keeps that order stable per group.
    """
    if not document_ids:
        return {}
    shared_rows = (
        db.query(DocumentTag.document_id, Tag)
        .join(Tag, Tag.id == DocumentTag.tag_id)
        .filter(DocumentTag.document_id.in_(document_ids))
        .order_by(func.lower(Tag.name))
        .all()
    )
    # Personal assignments are scoped to the current user (TF-399).
    personal_rows = (
        db.query(DocumentPersonalTag.document_id, Tag)
        .join(Tag, Tag.id == DocumentPersonalTag.tag_id)
        .filter(
            DocumentPersonalTag.document_id.in_(document_ids),
            DocumentPersonalTag.user_id == current_user.id,
        )
        .order_by(func.lower(Tag.name))
        .all()
    )
    result: "dict[int, List[DocumentTagOut]]" = {}
    for document_id, tag in shared_rows:
        result.setdefault(document_id, []).append(
            DocumentTagOut(
                id=tag.id,
                name=tag.name,
                scope=tag.scope,
                is_own=(tag.created_by == current_user.id),
                is_personal=False,
            )
        )
    for document_id, tag in personal_rows:
        result.setdefault(document_id, []).append(
            DocumentTagOut(
                id=tag.id,
                name=tag.name,
                scope=tag.scope,
                is_own=(tag.created_by == current_user.id),
                is_personal=True,
            )
        )
    # Re-sort each group: shared+personal were appended separately above.
    for outs in result.values():
        outs.sort(key=lambda o: o.name.lower())
    return result


def _audit_shared_tag_change(
    db: Session,
    document: Document,
    current_user: User,
    request: Optional[Request],
    operation: str,
    tag_ids: List[int],
    locale: str,
) -> None:
    """Stage an audit row (``commit=False``) for an owner-only **shared**
    (institution/global) tag attach/detach.

    Shared tag links are institution-visible state — attaching/detaching one
    changes what every institution member sees, exactly like a rename. So the
    same contract applies: the change is recorded, a SuperUser acting on a
    document they don't own is flagged as a bypass, and a failure to persist the
    audit row aborts the whole operation (hard 500) rather than letting a shared
    change land un-audited. Personal (``user``-scope) assignments are private and
    are never routed here.
    """
    from services.audit_service import AuditService

    real_owner = document.user_id is not None and document.user_id == current_user.id
    audit_log = AuditService.log_document_action(
        db,
        AuditService.ACTION_UPDATE_DOCUMENT,
        current_user.id,
        document.id,
        request=request,
        additional_data={
            "field": "shared_tags",
            "operation": operation,  # "attach" | "detach"
            "tag_ids": tag_ids,
            "superuser_bypass": current_user.is_superuser and not real_owner,
        },
        commit=False,
    )
    if audit_log is None:
        raise HTTPException(
            status_code=500, detail=t("documents_tag_failed", locale=locale)
        )


@router.post("/{document_id}/tags", response_model=DocumentResponse)
async def attach_document_tags(
    document_id: int,
    body: AttachTagsRequest,
    request: Request = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Attach tags to a document, routing by tag scope (TF-399).

    ``user``-scope tags become **personal** assignments and may be attached to
    any document the caller can see; ``institution``/``global``-scope tags stay
    **owner-only** shared assignments (and keep the institution-tag block rule).
    An effective shared attach is audited atomically with the change.
    """
    locale = get_request_locale(request, current_user)
    document, is_owner = _load_visible_document(document_id, current_user, db, locale)
    try:
        attached_shared = attach_tags_for_user(
            db, document, body.tag_ids, current_user, is_owner=is_owner
        )
        if attached_shared:
            _audit_shared_tag_change(
                db, document, current_user, request, "attach", attached_shared, locale
            )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(
            f"DB error attaching tags to document {document_id} "
            f"for user {current_user.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=t("documents_tag_failed", locale=locale)
        )
    except Exception as e:
        db.rollback()
        logger.error(
            f"Unexpected error attaching tags to document {document_id} "
            f"for user {current_user.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=t("documents_tag_failed", locale=locale)
        )
    db.refresh(document)
    return _document_response_with_tags(document, current_user, db)


@router.delete("/{document_id}/tags/{tag_id}", status_code=204)
async def detach_document_tag(
    document_id: int,
    tag_id: int,
    request: Request = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Detach a tag from a document, routing by tag scope (TF-399).

    A ``user``-scope tag removes only the caller's **personal** assignment (any
    visible document); ``institution``/``global``-scope tags stay **owner-only**.
    An effective shared detach is audited atomically with the change.
    """
    locale = get_request_locale(request, current_user)
    document, is_owner = _load_visible_document(document_id, current_user, db, locale)
    try:
        detached_shared = detach_tag_for_user(
            db, document, tag_id, current_user, is_owner=is_owner
        )
        if detached_shared is not None:
            _audit_shared_tag_change(
                db, document, current_user, request, "detach", [detached_shared], locale
            )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(
            f"DB error detaching tag {tag_id} from document {document_id} "
            f"for user {current_user.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=t("documents_tag_failed", locale=locale)
        )
    except Exception as e:
        db.rollback()
        logger.error(
            f"Unexpected error detaching tag {tag_id} from document {document_id} "
            f"for user {current_user.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=t("documents_tag_failed", locale=locale)
        )
    return Response(status_code=204)


def _content_disposition(filename: str, inline: bool) -> str:
    """RFC 6266 Content-Disposition with both ASCII fallback and UTF-8 form.

    Quotes the ASCII portion via ``urllib.parse.quote`` so a malicious or
    accidental newline / quote in ``original_filename`` cannot inject extra
    response headers.
    """
    disposition_type = "inline" if inline else "attachment"
    encoded = quote(filename or "download", safe="")
    return f"{disposition_type}; filename=\"{encoded}\"; filename*=UTF-8''{encoded}"


def _resolve_media_type(document) -> str:
    """Pick a safe Content-Type for the original bytes.

    - DB ``mime_type`` is the source of truth when set.
    - ``text/*`` without a charset gets ``;charset=utf-8`` appended (we
      always encode UTF-8 ourselves; see chat-export branch).
    - Missing/None falls back to ``mimetypes.guess_type`` then
      ``application/octet-stream`` so the iframe/browser still gets *some*
      Content-Type. Logs a warning so corrupt rows surface.
    """
    media_type = document.mime_type
    if not media_type:
        guessed, _ = mimetypes.guess_type(document.original_filename or "")
        media_type = guessed or "application/octet-stream"
        logger.warning(
            "Document %s has no mime_type; falling back to %s",
            document.id,
            media_type,
        )
    if media_type.startswith("text/") and "charset" not in media_type.lower():
        media_type = f"{media_type}; charset=utf-8"
    return media_type


# Formats whose bytes are already compressed internally (PDF FlateDecode
# streams, Office Open XML / zip containers, ...). GZipMiddleware re-running
# DEFLATE over them costs real CPU for ~0% size reduction (TF-596).
_PRECOMPRESSED_MEDIA_TYPE_PREFIXES = (
    "application/pdf",
    "application/zip",
    "application/vnd.openxmlformats-officedocument.",
)


def _is_precompressed_media_type(media_type: str) -> bool:
    return media_type.startswith(_PRECOMPRESSED_MEDIA_TYPE_PREFIXES)


async def _build_document_file_response(
    document, *, locale: str, inline: bool, caller_id: int | None = None
):
    """Return a FastAPI response carrying the document's original bytes.

    inline=False → ``Content-Disposition: attachment`` (browser downloads).
    inline=True  → ``Content-Disposition: inline`` (browser embeds, e.g. iframe).

    Branch precedence — chat exports MUST come first because their
    ``file_path`` is a synthetic value (``virtual://chat/<id>``) and would not
    pass the later existence checks.

      1. Chat-Export → bytes from ``doc_metadata.full_content``
      2. S3-backed file (``file_path`` starts with ``uploads/`` and
         ``storage_service.is_configured``)
      3. Local file on disk (fallback)

    Callers MUST allow ``HTTPException`` raised here to propagate; the outer
    endpoint catches generic ``Exception`` and would otherwise mask the
    intended 404/403/503 status as a 500.

    NOTE (TF-595): the S3 branch runs ``storage_service.download_file`` via
    ``run_in_threadpool``. Prod runs a single uvicorn worker (``--workers 1``,
    see ``Dockerfile.fly``), so this is one process with one event loop for
    the whole app — calling the blocking ``boto3`` download directly here
    would freeze every other request (for every user) for the entire
    download, not just this one. Bigger document → longer freeze.
    """
    headers = {
        "Content-Disposition": _content_disposition(
            document.original_filename, inline=inline
        )
    }
    media_type = _resolve_media_type(document)
    log_ctx = (
        f"doc={document.id} user={caller_id}" if caller_id else f"doc={document.id}"
    )

    # Chat-Export (virtual file)
    if document.doc_metadata and document.doc_metadata.get("source") == "chat_export":
        content = document.doc_metadata.get("full_content", "")
        if not content:
            raise HTTPException(
                status_code=404,
                detail=t("documents_content_not_available", locale=locale),
            )
        return Response(
            content=content.encode("utf-8"),
            media_type=media_type,
            headers=headers,
        )

    # S3-backed file
    if document.file_path.startswith("uploads/") and storage_service.is_configured:
        try:
            # Blocking boto3 call — MUST run off the event loop (TF-595).
            file_data = await run_in_threadpool(
                storage_service.download_file, document.file_path
            )
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=t("documents_file_not_found_storage", locale=locale),
            )
        except StorageAccessDeniedError:
            logger.error(
                f"S3 access denied while serving {log_ctx} path={document.file_path}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=403,
                detail=t("documents_access_denied", locale=locale),
            )
        except StorageThrottledError:
            logger.warning(
                f"S3 throttled while serving {log_ctx} path={document.file_path}"
            )
            raise HTTPException(
                status_code=503,
                detail=t("documents_storage_unavailable", locale=locale),
                headers={"Retry-After": "5"},
            )
        except (StorageUnavailableError, StorageConfigurationError):
            logger.error(
                f"S3 unavailable/misconfigured while serving {log_ctx} "
                f"path={document.file_path}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=503,
                detail=t("documents_storage_unavailable", locale=locale),
            )
        except Exception as e:
            logger.error(
                f"Unexpected S3 failure while serving {log_ctx} "
                f"path={document.file_path}: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail=t("documents_download_storage_failed", locale=locale),
            )
        # Response(content=...), NOT StreamingResponse(io.BytesIO(...)) (TF-596):
        # file_data is already fully in memory at this point (downloaded
        # above). io.BytesIO is not an AsyncIterable, so StreamingResponse
        # falls back to Starlette's iterate_in_threadpool(), which dispatches
        # ONE thread-pool call per iteration item. Iterating a BytesIO uses
        # the file-object line protocol (splits on b"\n"), not fixed blocks —
        # for binary PDF bytes that is ~1 chunk per ~240 bytes, i.e. ~49k
        # thread dispatches for an 11.86 MB PDF (empirically measured).
        # A plain Response sends the bytes as a single body write instead.
        if _is_precompressed_media_type(media_type):
            # Already-compressed binary formats (PDF, Office Open XML, zip)
            # gain nothing from GZipMiddleware and pay full CPU cost for it
            # (compression runs synchronously on the event loop — the same
            # class of blocking TF-595 removed from the S3 download itself).
            # Content-Encoding makes GZipMiddleware treat the body as already
            # encoded and skip compression.
            headers = {**headers, "Content-Encoding": "identity"}
        return Response(
            content=file_data,
            media_type=media_type,
            headers=headers,
        )

    # Local file
    if not os.path.exists(document.file_path):
        logger.warning(
            f"Local file missing while serving {log_ctx} path={document.file_path}"
        )
        raise HTTPException(
            status_code=404,
            detail=t("documents_file_not_found_disk", locale=locale),
        )
    return FileResponse(
        path=document.file_path,
        filename=document.original_filename,
        media_type=media_type,
        content_disposition_type="inline" if inline else "attachment",
    )


@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Download the original document file as an attachment.

    **Required:** Authenticated user.

    - **document_id**: ID of the document to download.

    Delegates to ``_build_document_file_response`` with ``inline=False`` —
    the helper handles chat-export, S3, and local-disk storage paths.
    """
    locale = get_request_locale(request, current_user)
    try:
        document = document_service.get_document_by_id(document_id, db)

        if not document:
            raise HTTPException(
                status_code=404, detail=t("documents_not_found", locale=locale)
            )

        # 404 (not 403) on a hidden doc — rationale on assert_document_visible_for.
        assert_document_visible_for(current_user, document, db, locale=locale)

        return await _build_document_file_response(
            document, locale=locale, inline=False, caller_id=current_user.id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to download document {document_id} for user {current_user.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=t("documents_download_failed", locale=locale),
        )


@router.get("/{document_id}/raw")
async def get_document_raw(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Liefert die Original-Datei mit Content-Disposition: inline.

    Identisch zu /download, jedoch ohne attachment-Header, sodass das
    Frontend die Datei einbetten kann (z. B. PDF in einem iframe via
    Blob-URL) statt sie herunterzuladen.

    **Required:** Authenticated user.

    - **document_id**: ID des Dokuments.
    """
    locale = get_request_locale(request, current_user)
    try:
        document = document_service.get_document_by_id(document_id, db)

        if not document:
            raise HTTPException(
                status_code=404, detail=t("documents_not_found", locale=locale)
            )

        # 404 (not 403) on a hidden doc — rationale on assert_document_visible_for.
        assert_document_visible_for(current_user, document, db, locale=locale)

        return await _build_document_file_response(
            document, locale=locale, inline=True, caller_id=current_user.id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to fetch raw document {document_id} for user {current_user.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=t("documents_preview_failed", locale=locale),
        )


@router.get("/{document_id}/status")
async def get_document_status(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get the processing status of a document (for async processing)

    **Required:** Authenticated user

    - **document_id**: ID of the document

    Returns:
        Document status, task ID, and processing info
    """
    locale = get_request_locale(request, current_user)
    try:
        document = document_service.get_document_by_id(document_id, db)

        if not document:
            raise HTTPException(
                status_code=404, detail=t("documents_not_found", locale=locale)
            )

        # 404 (not 403) on a hidden doc — rationale on assert_document_visible_for.
        assert_document_visible_for(current_user, document, db, locale=locale)

        # Get Celery task status if task_id exists
        task_status = None
        if document.task_id:
            try:
                from celery_app import celery_app

                task = celery_app.AsyncResult(document.task_id)
                task_status = {
                    "task_id": document.task_id,
                    "state": task.state,
                    "result": task.result if task.successful() else None,
                    "error": str(task.info) if task.failed() else None,
                }
            except Exception as e:
                logger.warning(f"Failed to get Celery task status: {str(e)}")

        return {
            "document_id": document.id,
            "filename": document.filename,
            "status": document.status.value,
            "task_status": task_status,
            "error_message": document.error_message,
            "processing_info": document.processing_info,
            "created_at": document.created_at.isoformat()
            if document.created_at
            else None,
            "processed_at": document.processed_at.isoformat()
            if document.processed_at
            else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get document status for document {document_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=t("documents_status_failed", locale=locale),
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    http_request: Request,
    current_user: User = Depends(require_permission("delete_documents")),
    db: Session = Depends(get_db),
):
    """
    Lösche Dokument und zugehörige Datei

    **Required Permission:** `delete_documents` (Dozent, Admin)

    - **document_id**: ID des zu löschenden Dokuments

    Returns:
        Bestätigung der Löschung
    """
    locale = get_request_locale(http_request, current_user)
    try:
        document = document_service.get_document_by_id(document_id, db)

        if not document:
            raise HTTPException(
                status_code=404, detail=t("documents_not_found", locale=locale)
            )

        # Access policy (in evaluation order):
        #   1. Same-institution admin → allowed + audit (admin_cross_owner if foreign)
        #   2. Owner / orphan / superuser → handled by enforce_resource_access
        #   3. else → 403
        from utils.auth_utils import enforce_resource_access

        is_same_institution_admin = (
            current_user.has_role("admin")
            and document.institution_id == current_user.institution_id
        )
        if is_same_institution_admin:
            if document.user_id and document.user_id != current_user.id:
                from services.audit_service import AuditService

                # Fail-loud auf Audit-Persistenz-Fehler (DSGVO): kein cross-owner
                # DELETE ohne Trail, deshalb log_admin_cross_owner statt
                # log_action — analog log_superuser_bypass.
                AuditService.log_admin_cross_owner(
                    db=db,
                    admin=current_user,
                    resource_type="document",
                    resource_id=document.id,
                    action="delete",
                    owner_user_id=document.user_id,
                    request=http_request,
                )
        else:
            enforce_resource_access(
                obj=document,
                user=current_user,
                action="delete",
                db=db,
                resource_type="document",
                request=http_request,
            )

        # Store filenames for audit log before deletion
        original_filename = document.original_filename

        # Delete document
        success = document_service.delete_document(document_id, db)

        if not success:
            raise HTTPException(
                status_code=500, detail=t("documents_delete_failed", locale=locale)
            )

        # Audit log: Document deleted
        from services.audit_service import AuditService

        AuditService.log_document_action(
            db,
            AuditService.ACTION_DELETE_DOCUMENT,
            current_user.id,
            document_id,
            request=http_request,
            additional_data={"original_filename": original_filename},
        )

        return JSONResponse(
            status_code=200,
            content={
                "message": "Document deleted successfully",
                "document_id": document_id,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to delete document {document_id} for user {current_user.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=t("documents_delete_failed", locale=locale),
        )


@router.post("/{document_id}/process")
async def process_document(
    document_id: int,
    create_vectors: bool = Query(True, description="Erstelle auch Vector Embeddings"),
    background_tasks: BackgroundTasks = None,
    request: Request = None,
    current_user: User = Depends(require_permission("create_documents")),
    db: Session = Depends(get_db),
):
    """
    Verarbeite hochgeladenes Dokument mit Docling (und optional Vector Embeddings)

    **ASYNCHRON:** Diese Endpoint startet die Verarbeitung im Hintergrund und antwortet sofort.
    Nutze GET /{document_id}/status um den Verarbeitungsstatus zu prüfen.

    **Required Permission:** `create_documents` (Dozent, Assistant, Admin)

    - **document_id**: ID des zu verarbeitenden Dokuments
    - **create_vectors**: Ob Vector Embeddings erstellt werden sollen (default: True)
    """
    locale = get_request_locale(request, current_user)
    # Prüfe ob Dokument existiert
    document = document_service.get_document_by_id(document_id, db)
    if not document:
        raise HTTPException(
            status_code=404, detail=t("documents_not_found", locale=locale)
        )

    # Prüfe User-Berechtigung (Superuser-Bypass mit Audit-Log)
    from utils.auth_utils import enforce_resource_access

    enforce_resource_access(
        obj=document,
        user=current_user,
        action="process",
        db=db,
        resource_type="document",
        request=request,
    )

    try:
        # Starte Verarbeitung im Hintergrund
        if background_tasks:
            if create_vectors:
                background_tasks.add_task(
                    document_service.process_document_with_vectors, document_id, db
                )
            else:
                background_tasks.add_task(
                    document_service.process_document_content, document_id, db
                )

        # Antworte sofort mit Status "processing"
        return {
            "message": "Document processing started in background",
            "document_id": document_id,
            "status": "processing",
            "check_status_url": f"/api/v1/documents/{document_id}/status",
        }

    except Exception as e:
        logger.error(
            f"Document processing failed for document {document_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=t("documents_processing_failed", locale=locale),
        )


@router.get("/{document_id}/content")
async def get_document_content(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Hole vollständigen Dokumenteninhalt für Vorschau

    **Required:** Authenticated user

    - **document_id**: ID des Dokuments

    Returns:
        Vollständiger Dokumenteninhalt als Text
    """
    locale = get_request_locale(request, current_user)
    try:
        document = document_service.get_document_by_id(document_id, db)

        if not document:
            raise HTTPException(
                status_code=404, detail=t("documents_not_found", locale=locale)
            )

        # 404 (not 403) on a hidden doc — rationale on assert_document_visible_for.
        assert_document_visible_for(current_user, document, db, locale=locale)

        # Hole vollständigen Inhalt vom Document Service
        content = await document_service.get_full_document_content(document_id, db)

        if content is None:
            # Fallback auf content_preview wenn verfügbar
            if document.content_preview:
                content = document.content_preview
            else:
                raise HTTPException(
                    status_code=404,
                    detail=t("documents_content_not_available", locale=locale),
                )

        return {
            "document_id": document_id,
            "title": document.title,  # resolver: display_name → metadata → filename
            "content": content,
            "content_length": len(content) if content else 0,
            "metadata": document.doc_metadata,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get content for document {document_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=t("documents_content_load_failed", locale=locale),
        )


@router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Hole verarbeitete Text-Chunks eines Dokuments

    **Required:** Authenticated user

    - **document_id**: ID des Dokuments

    Returns:
        Liste der Text-Chunks mit Metadaten
    """
    locale = get_request_locale(request, current_user)
    try:
        document = document_service.get_document_by_id(document_id, db)

        if not document:
            raise HTTPException(
                status_code=404, detail=t("documents_not_found", locale=locale)
            )

        # 404 (not 403) on a hidden doc — rationale on assert_document_visible_for.
        assert_document_visible_for(current_user, document, db, locale=locale)

        if document.status != DocumentStatus.PROCESSED:
            raise HTTPException(
                status_code=400,
                detail=t("documents_not_processed", locale=locale),
            )

        # Hole Chunks
        chunks = await document_service.get_document_chunks(document_id, db)

        if chunks is None:
            raise HTTPException(
                status_code=500,
                detail=t("documents_chunks_load_failed", locale=locale),
            )

        return {
            "document_id": document_id,
            "total_chunks": len(chunks),
            "chunks": chunks,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get chunks for document {document_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=t("documents_chunks_load_failed", locale=locale),
        )


@router.get("/{document_id}/chunks-paginated")
async def get_document_chunks_paginated(
    document_id: int,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of chunks per page"),
    request: Request = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Hole verarbeitete Text-Chunks eines Dokuments mit Pagination (für große Dokumente)

    **Required:** Authenticated user

    - **document_id**: ID des Dokuments
    - **page**: Seitennummer (1-indexed, default: 1)
    - **page_size**: Anzahl Chunks pro Seite (1-100, default: 10)

    Returns:
        Paginierte Liste der Text-Chunks mit Metadaten
    """
    locale = get_request_locale(request, current_user)
    try:
        document = document_service.get_document_by_id(document_id, db)

        if not document:
            raise HTTPException(
                status_code=404, detail=t("documents_not_found", locale=locale)
            )

        # 404 (not 403) on a hidden doc — rationale on assert_document_visible_for.
        assert_document_visible_for(current_user, document, db, locale=locale)

        if document.status != DocumentStatus.PROCESSED:
            raise HTTPException(
                status_code=400,
                detail=t("documents_not_processed", locale=locale),
            )

        # Hole Chunks aus Vector Database (schneller als Neuverarbeitung!)
        search_results = await vector_service.get_document_chunks(document_id)

        if not search_results:
            raise HTTPException(
                status_code=500,
                detail=t("documents_chunks_load_failed", locale=locale),
            )

        # Konvertiere SearchResult zu Dictionary Format
        chunks = []
        for result in search_results:
            chunks.append(
                {
                    "chunk_index": result.chunk_index,
                    "content": result.content,
                    "page_number": result.metadata.get("page_number")
                    if result.metadata
                    else None,
                    "metadata": result.metadata,
                }
            )

        # Berechne Pagination
        total_chunks = len(chunks)
        total_pages = (total_chunks + page_size - 1) // page_size

        # Validiere page
        if page > total_pages and total_chunks > 0:
            raise HTTPException(
                status_code=400,
                detail=t("documents_page_out_of_range", locale=locale),
            )

        # Berechne Start- und End-Index
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        # Hole Chunks für diese Seite
        paginated_chunks = chunks[start_idx:end_idx]

        return {
            "document_id": document_id,
            "total_chunks": total_chunks,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
            "chunks": paginated_chunks,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get paginated chunks for document {document_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=t("documents_chunks_load_failed", locale=locale),
        )
