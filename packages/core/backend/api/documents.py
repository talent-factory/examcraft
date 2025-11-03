"""
Document API Endpoints für ExamCraft AI
Verwaltet Document Upload, Listing und Management
"""

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends,
    Query,
    Request,
    BackgroundTasks,
)
from fastapi.responses import JSONResponse
from typing import List, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel

from services.document_service import DocumentService
from services.vector_service_factory import vector_service
from models.document import Document, DocumentStatus
from models.auth import User
from database import get_db
from utils.auth_utils import get_current_active_user, require_permission
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
    title: str  # Neues Feld für bessere UI-Anzeige
    file_size: int
    mime_type: str
    status: str
    user_id: Optional[int]  # Fixed: user_id is Integer in database, not String
    metadata: Optional[dict]
    content_preview: Optional[str]
    vector_collection: Optional[str]
    has_vectors: Optional[bool]
    created_at: Optional[str]
    updated_at: Optional[str]
    processed_at: Optional[str]


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
    http_request: Request = None,
    current_user: User = Depends(require_permission("create_documents")),
    db: Session = Depends(get_db),
):
    """
    Upload ein neues Dokument (Asynchrone Verarbeitung mit Celery)

    **Required Permission:** `create_documents` (Dozent, Assistant, Admin)

    - **file**: Dokument zum Upload (PDF, DOC, DOCX, TXT, MD)

    Returns:
        UploadResponse mit Document ID und Status

    **Note:** Document wird asynchron verarbeitet. Status kann via GET /documents/{id} abgerufen werden.
    """
    try:
        # Check document limit for institution
        from utils.tenant_utils import SubscriptionLimits

        SubscriptionLimits.check_document_limit(current_user.institution, db)

        # Save document file and create DB entry
        document = await document_service.upload_document(
            file=file, user_id=current_user.id, db=db
        )

        # Set institution_id for multi-tenancy
        document.institution_id = current_user.institution_id
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
            additional_data={"filename": document.filename, "task_id": task.id},
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
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    status: Optional[str] = Query(None, description="Filter by status"),
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
    try:
        # Convert status string to enum if provided
        status_filter = None
        if status:
            try:
                status_filter = DocumentStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status. Valid options: {[s.value for s in DocumentStatus]}",
                )

        # Tenant-aware query: Filter by institution_id
        from utils.tenant_utils import TenantFilter, get_tenant_context

        tenant_context = get_tenant_context(current_user)

        query = db.query(Document)
        query = TenantFilter.filter_by_tenant(query, Document, tenant_context)

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
        raise HTTPException(
            status_code=500, detail=f"Failed to list documents: {str(e)}"
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
    try:
        document = document_service.get_document_by_id(document_id, db)

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Tenant-aware access control
        from utils.tenant_utils import TenantFilter, get_tenant_context

        tenant_context = get_tenant_context(current_user)
        TenantFilter.verify_tenant_access(document, tenant_context)

        doc_dict = document.to_dict()
        return DocumentResponse(**doc_dict)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")


@router.get("/{document_id}/status")
async def get_document_status(
    document_id: int,
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
    try:
        document = document_service.get_document_by_id(document_id, db)

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Tenant-aware access control
        from utils.tenant_utils import TenantFilter, get_tenant_context

        tenant_context = get_tenant_context(current_user)
        TenantFilter.verify_tenant_access(document, tenant_context)

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
        logger.error(f"Failed to get document status: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get document status: {str(e)}"
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    http_request: Request = None,
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
    try:
        # Check if document exists and user owns it (or is superuser)
        document = document_service.get_document_by_id(document_id, db)

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Only allow deletion if:
        # 1. User is superuser (can delete any document)
        # 2. User owns the document
        # 3. User is admin in the same institution
        if not current_user.is_superuser:
            if document.user_id and document.user_id != current_user.id:
                # Check if user is admin in same institution
                if not (
                    current_user.has_role("admin")
                    and document.institution_id == current_user.institution_id
                ):
                    raise HTTPException(status_code=403, detail="Access denied")

        # Store filename for audit log
        filename = document.filename

        # Delete document
        success = document_service.delete_document(document_id, db)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete document")

        # Audit log: Document deleted
        from services.audit_service import AuditService

        AuditService.log_document_action(
            db,
            AuditService.ACTION_DELETE_DOCUMENT,
            current_user.id,
            document_id,
            request=http_request,
            additional_data={"filename": filename},
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
        raise HTTPException(
            status_code=500, detail=f"Failed to delete document: {str(e)}"
        )


@router.post("/{document_id}/process")
async def process_document(
    document_id: int,
    create_vectors: bool = Query(True, description="Erstelle auch Vector Embeddings"),
    background_tasks: BackgroundTasks = None,
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
    # Prüfe ob Dokument existiert
    document = document_service.get_document_by_id(document_id, db)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Prüfe User-Berechtigung
    if document.user_id and document.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

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
        logger.error(f"Document processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("/{document_id}/content")
async def get_document_content(
    document_id: int,
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
    try:
        document = document_service.get_document_by_id(document_id, db)

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Tenant-aware access control
        from utils.tenant_utils import TenantFilter, get_tenant_context

        tenant_context = get_tenant_context(current_user)
        TenantFilter.verify_tenant_access(document, tenant_context)

        # Hole vollständigen Inhalt vom Document Service
        content = await document_service.get_full_document_content(document_id, db)

        if content is None:
            # Fallback auf content_preview wenn verfügbar
            if document.content_preview:
                content = document.content_preview
            else:
                raise HTTPException(
                    status_code=404, detail="Document content not available"
                )

        return {
            "document_id": document_id,
            "title": document.doc_metadata.get("title", document.original_filename)
            if document.doc_metadata
            else document.original_filename,
            "content": content,
            "content_length": len(content) if content else 0,
            "metadata": document.doc_metadata,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get content: {str(e)}")


@router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: int,
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
    try:
        document = document_service.get_document_by_id(document_id, db)

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Tenant-aware access control
        from utils.tenant_utils import TenantFilter, get_tenant_context

        tenant_context = get_tenant_context(current_user)
        TenantFilter.verify_tenant_access(document, tenant_context)

        if document.status != DocumentStatus.PROCESSED:
            raise HTTPException(
                status_code=400,
                detail=f"Document not processed yet. Current status: {document.status.value}",
            )

        # Hole Chunks
        chunks = await document_service.get_document_chunks(document_id, db)

        if chunks is None:
            raise HTTPException(
                status_code=500, detail="Failed to retrieve document chunks"
            )

        return {
            "document_id": document_id,
            "total_chunks": len(chunks),
            "chunks": chunks,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chunks: {str(e)}")


@router.get("/{document_id}/chunks-paginated")
async def get_document_chunks_paginated(
    document_id: int,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of chunks per page"),
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
    try:
        document = document_service.get_document_by_id(document_id, db)

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Tenant-aware access control
        from utils.tenant_utils import TenantFilter, get_tenant_context

        tenant_context = get_tenant_context(current_user)
        TenantFilter.verify_tenant_access(document, tenant_context)

        if document.status != DocumentStatus.PROCESSED:
            raise HTTPException(
                status_code=400,
                detail=f"Document not processed yet. Current status: {document.status.value}",
            )

        # Hole Chunks aus Vector Database (schneller als Neuverarbeitung!)
        search_results = await vector_service.get_document_chunks(document_id)

        if not search_results:
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve document chunks from vector database",
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
                detail=f"Page {page} out of range. Total pages: {total_pages}",
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
            f"Failed to get paginated chunks for document {document_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to get paginated chunks: {str(e)}"
        )
