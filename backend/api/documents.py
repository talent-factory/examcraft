"""
Document API Endpoints für ExamCraft AI
Verwaltet Document Upload, Listing und Management
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from typing import List, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel

from services.document_service import DocumentService
from models.document import Document, DocumentStatus
from database import get_db
import logging

logger = logging.getLogger(__name__)

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

# Health check endpoint (muss vor parametrisierten Routen stehen)
@router.get("/health")
async def health_check():
    """Health check für Document Service"""
    return {
        "status": "healthy",
        "service": "Document Upload Service",
        "supported_formats": list(document_service.supported_formats.values()),
        "max_file_size_mb": document_service.max_file_size // (1024 * 1024)
    }

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
            "metadata": document.doc_metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@router.post("/{document_id}/process")
async def process_document(
    document_id: int,
    create_vectors: bool = Query(True, description="Erstelle auch Vector Embeddings"),
    db: Session = Depends(get_db)
):
    """
    Verarbeite hochgeladenes Dokument mit Docling (und optional Vector Embeddings)
    
    - **document_id**: ID des zu verarbeitenden Dokuments
    - **create_vectors**: Ob Vector Embeddings erstellt werden sollen (default: True)
    """
    # Prüfe ob Dokument existiert
    document = document_service.get_document_by_id(document_id, db)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Prüfe User-Berechtigung (vereinfacht für Demo)
    if document.user_id != "demo_user":
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        if create_vectors:
            # Verarbeite Dokument mit Vector Embeddings
            result = await document_service.process_document_with_vectors(document_id, db)
            
            if not result:
                raise HTTPException(status_code=500, detail="Document processing failed")
            
            return {
                "message": "Document processed successfully with vector embeddings",
                "document_id": document_id,
                "processing_stats": result
            }
        else:
            # Nur Docling Processing ohne Vector Embeddings
            processed_doc = await document_service.process_document_content(document_id, db)
            
            if not processed_doc:
                raise HTTPException(status_code=500, detail="Document processing failed")
            
            # Erstelle Processing Summary
            processing_summary = document_service.docling_service.get_document_summary(processed_doc)
            
            return {
                "message": "Document processed successfully",
                "document_id": document_id,
                "processing_summary": processing_summary
            }
        
    except Exception as e:
        logger.error(f"Document processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: int,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Hole verarbeitete Text-Chunks eines Dokuments
    
    - **document_id**: ID des Dokuments
    
    Returns:
        Liste der Text-Chunks mit Metadaten
    """
    try:
        document = document_service.get_document_by_id(document_id, db)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if document.user_id and document.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        if document.status != DocumentStatus.PROCESSED:
            raise HTTPException(
                status_code=400, 
                detail=f"Document not processed yet. Current status: {document.status.value}"
            )
        
        # Hole Chunks
        chunks = await document_service.get_document_chunks(document_id, db)
        
        if chunks is None:
            raise HTTPException(status_code=500, detail="Failed to retrieve document chunks")
        
        return {
            "document_id": document_id,
            "total_chunks": len(chunks),
            "chunks": chunks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chunks: {str(e)}")
