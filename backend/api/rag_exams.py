"""
RAG-basierte Prüfungserstellung API Endpoints für ExamCraft AI
Implementiert dokumentenbasierte Fragenerstellung mit Retrieval-Augmented Generation
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from services.rag_service import rag_service, RAGExamRequest, RAGExamResponse, RAGQuestion, RAGContext
from services.document_service import document_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rag", tags=["RAG Exams"])


# Pydantic Models
class RAGExamRequestModel(BaseModel):
    """Request Model für RAG-basierte Prüfungserstellung"""
    topic: str = Field(..., description="Thema der Prüfung", min_length=3, max_length=200)
    document_ids: Optional[List[int]] = Field(None, description="Spezifische Dokument-IDs (optional)")
    question_count: int = Field(5, description="Anzahl Fragen", ge=1, le=20)
    question_types: Optional[List[str]] = Field(
        ["multiple_choice", "open_ended"], 
        description="Fragetypen"
    )
    difficulty: str = Field("medium", description="Schwierigkeitsgrad")
    language: str = Field("de", description="Sprache")
    context_chunks_per_question: int = Field(3, description="Context Chunks pro Frage", ge=1, le=10)


class RAGQuestionResponse(BaseModel):
    """Response Model für RAG-Frage"""
    question_text: str
    question_type: str
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    difficulty: str
    source_chunks: List[str]
    source_documents: List[str]
    confidence_score: float


class RAGContextResponse(BaseModel):
    """Response Model für RAG-Kontext"""
    query: str
    total_chunks: int
    total_similarity_score: float
    source_documents: List[Dict[str, Any]]
    context_length: int


class RAGExamResponseModel(BaseModel):
    """Response Model für RAG-Prüfung"""
    exam_id: str
    topic: str
    questions: List[RAGQuestionResponse]
    context_summary: RAGContextResponse
    generation_time: float
    quality_metrics: Dict[str, Any]


class ContextRetrievalRequest(BaseModel):
    """Request Model für Context Retrieval"""
    query: str = Field(..., description="Suchanfrage", min_length=3, max_length=500)
    document_ids: Optional[List[int]] = Field(None, description="Spezifische Dokument-IDs")
    max_chunks: int = Field(5, description="Maximale Anzahl Chunks", ge=1, le=20)
    min_similarity: Optional[float] = Field(0.01, description="Mindest-Similarity (angepasst für Mock Embeddings)", ge=0.0, le=1.0)


# API Endpoints
@router.post("/generate-exam", response_model=RAGExamResponseModel)
async def generate_rag_exam(
    request: RAGExamRequestModel,
    db: Session = Depends(get_db)
):
    """
    Generiere RAG-basierte Prüfung aus Dokumenten
    
    - **topic**: Thema der Prüfung (3-200 Zeichen)
    - **document_ids**: Optional spezifische Dokumente
    - **question_count**: Anzahl Fragen (1-20, default: 5)
    - **question_types**: Fragetypen (multiple_choice, open_ended, true_false)
    - **difficulty**: Schwierigkeitsgrad (easy, medium, hard)
    - **language**: Sprache (de, en)
    - **context_chunks_per_question**: Context Chunks pro Frage (1-10)
    """
    try:
        # Validiere Document IDs falls angegeben
        if request.document_ids:
            for doc_id in request.document_ids:
                document = document_service.get_document_by_id(doc_id, db)
                if not document:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Document with ID {doc_id} not found"
                    )
                
                # Prüfe ob Dokument verarbeitet ist
                from models.document import DocumentStatus
                if document.status != DocumentStatus.PROCESSED:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Document {doc_id} is not processed yet. Please process it first."
                    )
        
        # Validiere Question Types
        valid_types = ["multiple_choice", "open_ended", "true_false"]
        if request.question_types:
            for qtype in request.question_types:
                if qtype not in valid_types:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid question type: {qtype}. Valid types: {valid_types}"
                    )
        
        # Validiere Difficulty
        valid_difficulties = ["easy", "medium", "hard"]
        if request.difficulty not in valid_difficulties:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid difficulty: {request.difficulty}. Valid: {valid_difficulties}"
            )
        
        # Erstelle RAG Request
        rag_request = RAGExamRequest(
            topic=request.topic,
            document_ids=request.document_ids,
            question_count=request.question_count,
            question_types=request.question_types,
            difficulty=request.difficulty,
            language=request.language,
            context_chunks_per_question=request.context_chunks_per_question
        )
        
        # Generiere RAG Exam
        rag_response = await rag_service.generate_rag_exam(rag_request)
        
        # Konvertiere zu Response Model
        questions_response = []
        for question in rag_response.questions:
            questions_response.append(RAGQuestionResponse(
                question_text=question.question_text,
                question_type=question.question_type,
                options=question.options,
                correct_answer=question.correct_answer,
                explanation=question.explanation,
                difficulty=question.difficulty,
                source_chunks=question.source_chunks or [],
                source_documents=question.source_documents or [],
                confidence_score=question.confidence_score
            ))
        
        context_response = RAGContextResponse(
            query=rag_response.context_summary.query,
            total_chunks=len(rag_response.context_summary.retrieved_chunks),
            total_similarity_score=rag_response.context_summary.total_similarity_score,
            source_documents=rag_response.context_summary.source_documents,
            context_length=rag_response.context_summary.context_length
        )
        
        response = RAGExamResponseModel(
            exam_id=rag_response.exam_id,
            topic=rag_response.topic,
            questions=questions_response,
            context_summary=context_response,
            generation_time=rag_response.generation_time,
            quality_metrics=rag_response.quality_metrics
        )
        
        logger.info(f"Generated RAG exam '{rag_response.exam_id}' with {len(questions_response)} questions")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG exam generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Exam generation failed: {str(e)}")


@router.post("/retrieve-context", response_model=RAGContextResponse)
async def retrieve_context(
    request: ContextRetrievalRequest,
    db: Session = Depends(get_db)
):
    """
    Hole relevanten Kontext aus Vector Database
    
    - **query**: Suchanfrage für Kontext
    - **document_ids**: Optional spezifische Dokumente
    - **max_chunks**: Maximale Anzahl Chunks (1-20)
    - **min_similarity**: Mindest-Similarity Score (0.0-1.0)
    """
    try:
        # Validiere Document IDs falls angegeben
        if request.document_ids:
            for doc_id in request.document_ids:
                document = document_service.get_document_by_id(doc_id, db)
                if not document:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Document with ID {doc_id} not found"
                    )
        
        # Hole Kontext (mit angepasstem min_similarity für Mock Embeddings)
        min_sim = request.min_similarity if request.min_similarity is not None else 0.01
        context = await rag_service.retrieve_context(
            query=request.query,
            document_ids=request.document_ids,
            max_chunks=request.max_chunks,
            min_similarity=min_sim
        )
        
        response = RAGContextResponse(
            query=context.query,
            total_chunks=len(context.retrieved_chunks),
            total_similarity_score=context.total_similarity_score,
            source_documents=context.source_documents,
            context_length=context.context_length
        )
        
        logger.info(f"Retrieved context for query '{request.query}': {len(context.retrieved_chunks)} chunks")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Context retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Context retrieval failed: {str(e)}")


@router.get("/available-documents")
async def get_available_documents(
    processed_only: bool = Query(True, description="Nur verarbeitete Dokumente"),
    db: Session = Depends(get_db)
):
    """
    Hole verfügbare Dokumente für RAG-Prüfungserstellung
    
    - **processed_only**: Nur verarbeitete Dokumente anzeigen (empfohlen)
    """
    try:
        # Hole alle Dokumente (vereinfacht für Demo)
        documents = document_service.get_documents_by_user("demo_user", db)
        
        if processed_only:
            from models.document import DocumentStatus
            documents = [
                doc for doc in documents 
                if doc.status == DocumentStatus.PROCESSED
            ]
        
        # Konvertiere zu Response Format
        available_docs = []
        for doc in documents:
            doc_info = {
                "id": doc.id,
                "filename": doc.original_filename,
                "mime_type": doc.mime_type,
                "status": doc.status.value,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
                "file_size": getattr(doc, 'file_size', None),
                "has_vectors": bool(doc.vector_collection)
            }
            
            # Füge Metadaten hinzu falls verfügbar
            if doc.doc_metadata:
                doc_info["metadata"] = {
                    "total_chunks": doc.doc_metadata.get("total_chunks"),
                    "embedding_model": doc.doc_metadata.get("embedding_model"),
                    "processing_time": doc.doc_metadata.get("processing_time")
                }
            
            available_docs.append(doc_info)
        
        return {
            "total_documents": len(available_docs),
            "processed_documents": len([d for d in available_docs if d["status"] == "processed"]),
            "documents_with_vectors": len([d for d in available_docs if d["has_vectors"]]),
            "documents": available_docs
        }
        
    except Exception as e:
        logger.error(f"Failed to get available documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get documents: {str(e)}")


@router.get("/question-types")
async def get_supported_question_types():
    """
    Hole unterstützte Fragetypen für RAG-Prüfungen
    """
    return {
        "supported_types": [
            {
                "type": "multiple_choice",
                "name": "Multiple Choice",
                "description": "Frage mit 4 Antwortoptionen (A, B, C, D)",
                "example": "Welche Aussage ist korrekt?"
            },
            {
                "type": "open_ended", 
                "name": "Offene Frage",
                "description": "Frage die eine ausführliche Antwort erfordert",
                "example": "Erläutern Sie die wichtigsten Konzepte..."
            },
            {
                "type": "true_false",
                "name": "Wahr/Falsch",
                "description": "Aussage die als wahr oder falsch bewertet wird",
                "example": "Die folgende Aussage ist korrekt: ..."
            }
        ],
        "difficulty_levels": [
            {
                "level": "easy",
                "name": "Einfach",
                "description": "Grundlegende Fakten und Definitionen"
            },
            {
                "level": "medium",
                "name": "Mittel", 
                "description": "Anwendung und Verständnis von Konzepten"
            },
            {
                "level": "hard",
                "name": "Schwer",
                "description": "Analyse, Synthese und kritisches Denken"
            }
        ],
        "supported_languages": [
            {"code": "de", "name": "Deutsch"},
            {"code": "en", "name": "English"}
        ]
    }


@router.get("/health")
async def rag_service_health():
    """
    Health Check für RAG Service
    
    Prüft:
    - RAG Service Status
    - Vector Service Verfügbarkeit
    - Claude API Status
    """
    try:
        # Teste Vector Service
        from services.vector_service_mock import vector_service
        vector_stats = vector_service.get_collection_stats()
        
        # Teste Claude Service (vereinfacht)
        claude_available = True
        try:
            claude_service = rag_service.claude_service
            # Einfacher Test ob Service initialisiert ist
            claude_available = claude_service is not None
        except:
            claude_available = False
        
        return {
            "status": "healthy",
            "service": "RAG Service",
            "components": {
                "vector_service": {
                    "status": "available",
                    "total_chunks": vector_stats.get("total_chunks", 0),
                    "embedding_model": vector_stats.get("embedding_model", "unknown")
                },
                "claude_service": {
                    "status": "available" if claude_available else "unavailable",
                    "fallback_enabled": True
                },
                "rag_templates": {
                    "status": "loaded",
                    "template_count": len(rag_service.question_templates)
                }
            },
            "supported_features": [
                "context_retrieval",
                "multi_type_questions", 
                "source_attribution",
                "quality_metrics",
                "fallback_generation"
            ]
        }
        
    except Exception as e:
        logger.error(f"RAG service health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "RAG Service",
            "error": str(e)
        }
