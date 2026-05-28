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
from fastapi.responses import JSONResponse, FileResponse, Response, StreamingResponse
from typing import List, Optional
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator, model_validator
import mimetypes
import os
import io
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
from services.vector_service_factory import vector_service
from models.document import Document, DocumentStatus, DocumentVisibility
from models.auth import User
from database import get_db
from utils.auth_utils import get_current_active_user, require_permission
from utils.document_visibility import (
    assert_document_visible_for,
    filter_documents_for_user,
)
from tasks.document_tasks import process_document as celery_process_document
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])
document_service = DocumentService()


# Pydantic Models für API Responses
class DocumentResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    title: str  # Resolved display title (display_name → metadata → filename)
    display_name: Optional[str] = None  # Raw user override, null when unset
    file_size: int
    mime_type: str
    status: str
    visibility: Optional[str] = None  # 'private' | 'institution' (TF-354)
    user_id: Optional[int]  # Fixed: user_id is Integer in database, not String
    metadata: Optional[dict]
    content_preview: Optional[str]
    vector_collection: Optional[str]
    has_vectors: Optional[bool]
    created_at: Optional[str]
    updated_at: Optional[str]
    processed_at: Optional[str]


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
        # that dead request into a 422 instead.
        has_display = "display_name" in self.model_fields_set
        has_visibility = (
            "visibility" in self.model_fields_set and self.visibility is not None
        )
        if not (has_display or has_visibility):
            raise ValueError(
                "At least one of 'display_name' or 'visibility' must be provided"
            )
        return self


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


class UploadResponse(BaseModel):
    document_id: int
    filename: str
    status: str
    message: str


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    visibility: DocumentVisibility = Form(DocumentVisibility.PRIVATE),
    http_request: Request = None,
    current_user: User = Depends(require_permission("create_documents")),
    db: Session = Depends(get_db),
):
    """
    Upload ein neues Dokument (Asynchrone Verarbeitung mit Celery)

    **Required Permission:** `create_documents` (Dozent, Assistant, Admin)

    - **file**: Dokument zum Upload (PDF, DOC, DOCX, TXT, MD)
    - **visibility**: `private` (nur ich, Default) oder `institution` (geteilt).
      `institution` ist nur erlaubt, wenn der User einer Institution angehört.

    Returns:
        UploadResponse mit Document ID und Status

    **Note:** Document wird asynchron verarbeitet. Status kann via GET /documents/{id} abgerufen werden.
    """
    locale = get_request_locale(http_request, current_user)

    # Visibility (TF-354): validate up front so we never persist a file we
    # then reject. 'institution' requires the user to belong to one.
    if visibility == DocumentVisibility.INSTITUTION and not current_user.institution_id:
        raise HTTPException(
            status_code=400,
            detail=t("documents_visibility_no_institution", locale=locale),
        )

    try:
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


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    status: Optional[str] = Query(None, description="Filter by status"),
    request: Request = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Liste alle Dokumente des aktuellen Users

    **Required:** Authenticated user

    - **status**: Optional filter by document status

    Returns:
        Liste aller Dokumente mit Metadaten
    """
    locale = get_request_locale(request, current_user)
    try:
        # Convert status string to enum if provided
        status_filter = None
        if status:
            try:
                status_filter = DocumentStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=t("documents_invalid_status", locale=locale),
                )

        # Visibility-aware query (TF-354): owner's docs + institution-shared
        # docs in the user's institution (SuperUser bypass inside the helper).
        query = db.query(Document)
        query = filter_documents_for_user(query, current_user)

        if status_filter:
            query = query.filter(Document.status == status_filter)

        documents = query.order_by(Document.created_at.desc()).all()

        # Convert to response format
        document_responses = []
        for doc in documents:
            doc_dict = doc.to_dict()
            document_responses.append(DocumentResponse(**doc_dict))

        return DocumentListResponse(
            documents=document_responses, total=len(document_responses)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to list documents for user {current_user.id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=t("documents_list_failed", locale=locale),
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
        assert_document_visible_for(current_user, document, locale=locale)

        doc_dict = document.to_dict()
        return DocumentResponse(**doc_dict)

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
    - **visibility**: ``private``/``institution``. **Owner-only** (SuperUser may
      also change it) — a non-owner gets 403 even within the same institution.
      ``institution`` requires the document to belong to an institution. Every
      effective change is written to the audit log.

    At least one field must be provided (422 otherwise). Field-level validation
    (length, control characters, enum membership) happens in
    ``DocumentPatchRequest`` and surfaces as 422.

    **Required Permission:** ``create_documents``
    """
    locale = get_request_locale(request, current_user)
    visibility_change = None
    try:
        document = document_service.get_document_by_id(document_id, db)
        if not document:
            raise HTTPException(
                status_code=404, detail=t("documents_not_found", locale=locale)
            )

        # 404 (not 403) on a hidden doc — rationale on assert_document_visible_for.
        assert_document_visible_for(current_user, document, locale=locale)

        fields_set = payload.model_fields_set

        # --- Rename (display_name): behaviour unchanged, visibility-scoped. ---
        # The Pydantic validator already normalised empty/whitespace to None and
        # enforced the 255-char + no-control-chars invariant.
        if "display_name" in fields_set:
            document.display_name = payload.display_name

        # --- Visibility: stricter — owner-only (SuperUser bypass preserved). ---
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
                visibility_change = (document.visibility, new_visibility)
                document.visibility = new_visibility

        # Build the response dict BEFORE persisting so a serialisation failure
        # cannot mask an already-persisted change as a generic 500.
        response_payload = document.to_dict()

        if visibility_change is not None:
            # A visibility flip is a DSGVO-relevant privileged action: it must
            # never persist without an audit row. log_document_action adds the
            # audit row and commits it together with the pending visibility
            # change in ONE transaction; on failure it rolls back BOTH and
            # returns None. Treating None as a hard 500 (same fail-loud contract
            # as log_admin_cross_owner / log_superuser_bypass) keeps the change
            # and its audit atomic — we never report success on an un-audited
            # flip, nor a 500 on a change that already landed.
            from services.audit_service import AuditService

            old_vis, new_vis = visibility_change
            audit_log = AuditService.log_document_action(
                db,
                AuditService.ACTION_UPDATE_DOCUMENT,
                current_user.id,
                document_id,
                request=request,
                additional_data={
                    "field": "visibility",
                    "old_visibility": old_vis.value if old_vis else None,
                    "new_visibility": new_vis.value,
                },
            )
            if audit_log is None:
                raise HTTPException(
                    status_code=500,
                    detail=t("documents_rename_failed", locale=locale),
                )
        else:
            # display_name-only change — rename was never audited; just persist.
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


def _build_document_file_response(
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
            file_data = storage_service.download_file(document.file_path)
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
        return StreamingResponse(
            io.BytesIO(file_data),
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
        assert_document_visible_for(current_user, document, locale=locale)

        return _build_document_file_response(
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
        assert_document_visible_for(current_user, document, locale=locale)

        return _build_document_file_response(
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
        assert_document_visible_for(current_user, document, locale=locale)

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
        assert_document_visible_for(current_user, document, locale=locale)

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
        assert_document_visible_for(current_user, document, locale=locale)

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
        assert_document_visible_for(current_user, document, locale=locale)

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
