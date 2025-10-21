"""
Vector Search API Endpoints für ExamCraft AI
Implementiert Similarity Search und Vector Database Management
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from services.vector_service_factory import vector_service, get_service_info
from services.document_service import document_service
from models.auth import User
from utils.auth_utils import get_current_active_user
import logging

# SearchResult type - will be provided by vector service
try:
    from services.qdrant_vector_service import SearchResult
except ImportError:
    from services.vector_service import SearchResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["Vector Search"])


# Pydantic Models
class SearchQuery(BaseModel):
    """Request Model für Similarity Search"""
    query: str = Field(..., description="Suchquery", min_length=1, max_length=1000)
    n_results: int = Field(5, description="Anzahl Ergebnisse", ge=1, le=50)
    document_ids: Optional[List[int]] = Field(None, description="Filter für spezifische Dokumente")


class SearchResultResponse(BaseModel):
    """Response Model für Search Result"""
    chunk_id: str
    document_id: int
    content: str
    similarity_score: float
    metadata: Dict[str, Any]
    chunk_index: int
    filename: Optional[str] = None


class SearchResponse(BaseModel):
    """Response Model für Similarity Search"""
    query: str
    total_results: int
    results: List[SearchResultResponse]
    search_time_ms: float


class VectorStatsResponse(BaseModel):
    """Response Model für Vector Database Statistiken"""
    collection_name: str
    total_chunks: int
    embedding_model: str
    persist_directory: str
    sample_document_id: Optional[int] = None
    sample_filename: Optional[str] = None


# API Endpoints
@router.post("/similarity", response_model=SearchResponse)
async def similarity_search(
    search_query: SearchQuery,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Führe Similarity Search in der Vector Database durch

    **Required:** Authenticated user

    - **query**: Suchtext (1-1000 Zeichen)
    - **n_results**: Anzahl Ergebnisse (1-50, default: 5)
    - **document_ids**: Optional Filter für spezifische Dokumente
    """
    try:
        import time
        start_time = time.time()
        
        # Führe Similarity Search durch
        search_results = await vector_service.similarity_search(
            query=search_query.query,
            n_results=search_query.n_results,
            document_ids=search_query.document_ids
        )
        
        end_time = time.time()
        search_time_ms = (end_time - start_time) * 1000
        
        # Erweitere Results um Filename (aus Database)
        enhanced_results = []
        for result in search_results:
            # Hole Dokument-Info aus Database
            document = document_service.get_document_by_id(result.document_id, db)
            filename = document.original_filename if document else None
            
            enhanced_result = SearchResultResponse(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                content=result.content,
                similarity_score=result.similarity_score,
                metadata=result.metadata,
                chunk_index=result.chunk_index,
                filename=filename
            )
            enhanced_results.append(enhanced_result)
        
        logger.info(f"Similarity search for '{search_query.query}' returned {len(enhanced_results)} results in {search_time_ms:.2f}ms")
        
        return SearchResponse(
            query=search_query.query,
            total_results=len(enhanced_results),
            results=enhanced_results,
            search_time_ms=search_time_ms
        )
        
    except Exception as e:
        logger.error(f"Similarity search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/document/{document_id}/chunks", response_model=List[SearchResultResponse])
async def get_document_vector_chunks(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Hole alle Vector Chunks eines spezifischen Dokuments

    **Required:** Authenticated user

    - **document_id**: ID des Dokuments
    """
    try:
        # Prüfe ob Dokument existiert
        document = document_service.get_document_by_id(document_id, db)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Hole Vector Chunks
        search_results = await vector_service.get_document_chunks(document_id)
        
        # Konvertiere zu Response Format
        enhanced_results = []
        for result in search_results:
            enhanced_result = SearchResultResponse(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                content=result.content,
                similarity_score=result.similarity_score,
                metadata=result.metadata,
                chunk_index=result.chunk_index,
                filename=document.original_filename
            )
            enhanced_results.append(enhanced_result)
        
        logger.info(f"Retrieved {len(enhanced_results)} vector chunks for document {document_id}")
        
        return enhanced_results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get vector chunks for document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chunks: {str(e)}")


@router.get("/stats", response_model=VectorStatsResponse)
async def get_vector_database_stats(
    current_user: User = Depends(get_current_active_user)
):
    """
    Hole Statistiken über die Vector Database

    **Required:** Authenticated user

    Zeigt Informationen über:
    - Collection Name und Chunk-Anzahl
    - Verwendetes Embedding Model
    - Sample Dokument-Informationen
    """
    try:
        stats = vector_service.get_collection_stats()
        
        return VectorStatsResponse(
            collection_name=stats["collection_name"],
            total_chunks=stats["total_chunks"],
            embedding_model=stats["embedding_model"],
            persist_directory=stats["persist_directory"],
            sample_document_id=stats.get("sample_document_id"),
            sample_filename=stats.get("sample_filename")
        )
        
    except Exception as e:
        logger.error(f"Failed to get vector database stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.delete("/document/{document_id}/vectors")
async def delete_document_vectors(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Lösche alle Vector Embeddings eines Dokuments
    
    - **document_id**: ID des Dokuments
    """
    try:
        # Prüfe ob Dokument existiert
        document = document_service.get_document_by_id(document_id, db)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Lösche Vector Chunks
        deleted_count = await vector_service.delete_document_chunks(document_id)
        
        # Aktualisiere Dokument (entferne Vector Collection Info)
        if document.doc_metadata:
            # Entferne Vector-bezogene Metadaten
            vector_keys = [
                'embedding_model', 'embedding_dimension', 'total_chunks',
                'embedding_processing_time', 'vector_created_at'
            ]
            for key in vector_keys:
                document.doc_metadata.pop(key, None)
        
        document.vector_collection = None
        db.commit()
        
        logger.info(f"Deleted {deleted_count} vector chunks for document {document_id}")
        
        return {
            "message": "Document vectors deleted successfully",
            "document_id": document_id,
            "deleted_chunks": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete vectors for document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete vectors: {str(e)}")


@router.post("/reindex/{document_id}")
async def reindex_document_vectors(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Erstelle Vector Embeddings für ein bereits verarbeitetes Dokument neu
    
    - **document_id**: ID des Dokuments
    """
    try:
        # Prüfe ob Dokument existiert und verarbeitet ist
        document = document_service.get_document_by_id(document_id, db)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        from models.document import DocumentStatus
        if document.status != DocumentStatus.PROCESSED:
            raise HTTPException(
                status_code=400, 
                detail="Document must be processed before reindexing"
            )
        
        # Lösche existierende Vector Embeddings
        await vector_service.delete_document_chunks(document_id)
        
        # Erstelle neue Vector Embeddings
        result = await document_service.process_document_with_vectors(document_id, db)
        
        if not result:
            raise HTTPException(status_code=500, detail="Reindexing failed")
        
        logger.info(f"Successfully reindexed document {document_id}")
        
        return {
            "message": "Document reindexed successfully",
            "document_id": document_id,
            "processing_stats": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reindex document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Reindexing failed: {str(e)}")


@router.get("/health")
async def vector_search_health():
    """
    Health Check für Vector Search Service
    
    Prüft:
    - Vector Service Status
    - Embedding Model Status
    - Collection Verfügbarkeit
    """
    try:
        # Teste Vector Service
        stats = vector_service.get_collection_stats()

        # Teste Embedding Model (lazy loading)
        model_loaded = vector_service._embedding_model is not None

        # Hole Service-Informationen
        service_info = get_service_info()

        health_data = {
            "status": "healthy",
            "service": "Vector Search Service",
            "service_type": service_info.get("service_type", "unknown"),
            "service_class": service_info.get("service_class", "unknown"),
            "collection_name": stats["collection_name"],
            "total_chunks": stats["total_chunks"],
            "embedding_model": stats["embedding_model"],
            "model_loaded": model_loaded
        }

        # Füge spezifische Service-Informationen hinzu
        if "qdrant_url" in stats:
            health_data["qdrant_url"] = stats["qdrant_url"]
        elif "persist_directory" in stats:
            health_data["persist_directory"] = stats["persist_directory"]

        return health_data

    except Exception as e:
        logger.error(f"Vector search health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "Vector Search Service",
            "error": str(e)
        }


@router.get("/service-info")
async def get_vector_service_info():
    """
    Hole detaillierte Informationen über den aktuell verwendeten Vector Service

    Zeigt:
    - Service Type (Qdrant, ChromaDB, Mock)
    - Konfiguration und URLs
    - Verfügbare Features
    """
    try:
        service_info = get_service_info()
        stats = vector_service.get_collection_stats()

        return {
            "service_info": service_info,
            "collection_stats": stats,
            "features": {
                "async_operations": True,
                "similarity_search": True,
                "document_filtering": True,
                "metadata_support": True,
                "collection_management": True
            }
        }
    except Exception as e:
        logger.error(f"Failed to get service info: {e}")
        return {
            "error": str(e),
            "service_info": get_service_info()
        }
