"""
Document API Endpoints für ExamCraft AI
Verwaltet Document Upload, Listing und Management
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import List, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel

from services.document_service import DocumentService
from models.document import Document, DocumentStatus

# Database dependency (wird später durch echte DB-Session ersetzt)
def get_db():
    # TODO: Implement proper database session
    return None

# Aktuell ohne User Authentication - wird später hinzugefügt
def get_current_user():
    return "demo_user"  # Placeholder

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])
document_service = DocumentService()

# Pydantic Models für API Responses
class DocumentResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    status: str
    user_id: Optional[str]
    metadata: Optional[dict]
    content_preview: Optional[str]
    vector_collection: Optional[str]
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
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload ein neues Dokument
    
    - **file**: Dokument zum Upload (PDF, DOC, DOCX, TXT, MD)
    - **user_id**: Wird automatisch aus Authentication extrahiert
    
    Returns:
        UploadResponse mit Document ID und Status
    """
    try:
        document = await document_service.upload_document(
            file=file,
            user_id=user_id,
            db=db
        )
        
        return UploadResponse(
            document_id=document.id,
            filename=document.filename,
            status=document.status.value,
            message="Document uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    status: Optional[str] = Query(None, description="Filter by status"),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Liste alle Dokumente des aktuellen Users
    
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
                    detail=f"Invalid status. Valid options: {[s.value for s in DocumentStatus]}"
                )
        
        documents = document_service.get_documents_by_user(
            user_id=user_id,
            db=db,
            status=status_filter
        )
        
        # Convert to response format
        document_responses = []
        for doc in documents:
            doc_dict = doc.to_dict()
            document_responses.append(DocumentResponse(**doc_dict))
        
        return DocumentListResponse(
            documents=document_responses,
            total=len(document_responses)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Hole spezifisches Dokument nach ID
    
    - **document_id**: ID des gewünschten Dokuments
    
    Returns:
        Document Details mit Metadaten
    """
    try:
        document = document_service.get_document_by_id(document_id, db)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check if user owns this document (wenn User Auth implementiert ist)
        if document.user_id and document.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        doc_dict = document.to_dict()
        return DocumentResponse(**doc_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")

@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lösche Dokument und zugehörige Datei
    
    - **document_id**: ID des zu löschenden Dokuments
    
    Returns:
        Bestätigung der Löschung
    """
    try:
        # Check if document exists and user owns it
        document = document_service.get_document_by_id(document_id, db)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if document.user_id and document.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete document
        success = document_service.delete_document(document_id, db)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete document")
        
        return JSONResponse(
            status_code=200,
            content={"message": "Document deleted successfully", "document_id": document_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@router.get("/{document_id}/status")
async def get_document_status(
    document_id: int,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Hole Processing-Status eines Dokuments
    
    - **document_id**: ID des Dokuments
    
    Returns:
        Aktueller Processing-Status
    """
    try:
        document = document_service.get_document_by_id(document_id, db)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if document.user_id and document.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return {
            "document_id": document_id,
            "status": document.status.value,
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "processed_at": document.processed_at.isoformat() if document.processed_at else None,
            "metadata": document.metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check für Document Service"""
    return {
        "status": "healthy",
        "service": "Document Upload Service",
        "supported_formats": list(document_service.supported_formats.values()),
        "max_file_size_mb": document_service.max_file_size // (1024 * 1024)
    }
