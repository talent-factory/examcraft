"""
RAG-basierte Prüfungserstellung API Endpoints für ExamCraft AI
Implementiert dokumentenbasierte Fragenerstellung mit Retrieval-Augmented Generation
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db

# IMPORTANT: Import module reference instead of direct import to allow
# runtime replacement of rag_service singleton by Premium package in main.py
import services.rag_service as rag_service_module
from services.rag_service import RAGExamRequest
from services.document_service import document_service
from models.auth import User
from models.question_review import QuestionReview, ReviewHistory, ReviewStatus
from utils.auth_utils import get_current_active_user, require_permission
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rag", tags=["RAG Exams"])


# Pydantic Models
class PromptConfig(BaseModel):
    """Konfiguration für einen Prompt"""

    prompt_id: str = Field(..., description="Prompt UUID")
    variables: Optional[Dict[str, Any]] = Field(
        None, description="Template-Variablen für den Prompt"
    )


class RAGExamRequestModel(BaseModel):
    """Request Model für RAG-basierte Prüfungserstellung"""

    topic: str = Field(
        ..., description="Thema der Prüfung", min_length=3, max_length=200
    )
    document_ids: Optional[List[int]] = Field(
        None, description="Spezifische Dokument-IDs (optional)"
    )
    question_count: int = Field(5, description="Anzahl Fragen", ge=1, le=20)
    question_types: Optional[List[str]] = Field(
        ["multiple_choice", "open_ended"], description="Fragetypen"
    )
    difficulty: str = Field("medium", description="Schwierigkeitsgrad")
    language: str = Field("de", description="Sprache")
    context_chunks_per_question: int = Field(
        3, description="Context Chunks pro Frage", ge=1, le=10
    )

    prompt_config: Optional[Dict[str, PromptConfig]] = Field(
        None,
        description="Prompt-Konfiguration pro Fragetyp (z.B. {'multiple_choice': {...}, 'open_ended': {...}})",
    )


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
    review_question_ids: List[int] = []
    persistence_warning: Optional[str] = None


class ContextRetrievalRequest(BaseModel):
    """Request Model für Context Retrieval"""

    query: str = Field(..., description="Suchanfrage", min_length=3, max_length=500)
    document_ids: Optional[List[int]] = Field(
        None, description="Spezifische Dokument-IDs"
    )
    max_chunks: int = Field(5, description="Maximale Anzahl Chunks", ge=1, le=20)
    min_similarity: Optional[float] = Field(
        0.01,
        description="Mindest-Similarity Score (niedrig fuer maximalen Recall)",
        ge=0.0,
        le=1.0,
    )


# API Endpoints
@router.post("/generate-exam", response_model=RAGExamResponseModel)
async def generate_rag_exam(
    request: RAGExamRequestModel,
    current_user: User = Depends(require_permission("create_questions")),
    db: Session = Depends(get_db),
):
    """
    Generiere RAG-basierte Prüfung aus Dokumenten

    **Required Permission:** `create_questions` (Dozent, Assistant, Admin)

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
                        status_code=404, detail=f"Document with ID {doc_id} not found"
                    )

                # Prüfe ob Dokument verarbeitet ist
                from models.document import DocumentStatus

                if document.status != DocumentStatus.PROCESSED:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Document {doc_id} is not processed yet. Please process it first.",
                    )

        # Validiere Question Types
        valid_types = ["multiple_choice", "open_ended", "true_false"]
        if request.question_types:
            for qtype in request.question_types:
                if qtype not in valid_types:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid question type: {qtype}. Valid types: {valid_types}",
                    )

        # Validiere Difficulty
        valid_difficulties = ["easy", "medium", "hard"]
        if request.difficulty not in valid_difficulties:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid difficulty: {request.difficulty}. Valid: {valid_difficulties}",
            )

        # Konvertiere prompt_config von Pydantic zu dataclass
        prompt_config_dict = None
        if request.prompt_config:
            from services.rag_service import PromptConfig as RAGPromptConfig

            prompt_config_dict = {}
            for question_type, config in request.prompt_config.items():
                prompt_config_dict[question_type] = RAGPromptConfig(
                    prompt_id=config.prompt_id, variables=config.variables
                )
                logger.info(
                    f"📋 API received prompt_config for '{question_type}': prompt_id={config.prompt_id}, variables={list(config.variables.keys()) if config.variables else []}"
                )
        else:
            logger.info("📋 API received NO prompt_config - will use default templates")

        # Quota-Check vor Generierung (verhindert unnoetige Claude-API-Kosten)
        from utils.tenant_utils import SubscriptionLimits

        if not current_user.institution:
            raise HTTPException(
                status_code=403,
                detail="You must be associated with an institution to generate exams.",
            )
        SubscriptionLimits.check_question_limit(
            current_user.institution, db, additional_count=request.question_count
        )

        # Erstelle RAG Request
        rag_request = RAGExamRequest(
            topic=request.topic,
            document_ids=request.document_ids,
            question_count=request.question_count,
            question_types=request.question_types,
            difficulty=request.difficulty,
            language=request.language,
            context_chunks_per_question=request.context_chunks_per_question,
            prompt_config=prompt_config_dict,
        )

        # Generiere RAG Exam
        rag_response = await rag_service_module.rag_service.generate_rag_exam(
            rag_request
        )

        # Persistiere generierte Fragen in question_reviews
        review_question_ids = []
        persistence_warning = None
        try:
            reviews = []
            for question in rag_response.questions:
                # explanation can be str or list — Premium RAG may return a list of grading criteria
                if isinstance(question.explanation, str):
                    explanation_text = question.explanation
                elif isinstance(question.explanation, list):
                    explanation_text = "; ".join(
                        str(item) for item in question.explanation
                    )
                elif question.explanation is not None:
                    explanation_text = str(question.explanation)
                else:
                    explanation_text = None

                question_review = QuestionReview(
                    question_text=question.question_text,
                    question_type=question.question_type,
                    options=question.options,
                    correct_answer=question.correct_answer,
                    explanation=explanation_text,
                    difficulty=question.difficulty,
                    topic=request.topic,
                    language=request.language,
                    source_chunks=question.source_chunks,
                    source_documents=question.source_documents,
                    confidence_score=question.confidence_score,
                    review_status=ReviewStatus.PENDING.value,
                    exam_id=rag_response.exam_id,
                    created_by=current_user.id,
                    institution_id=current_user.institution_id,
                )
                db.add(question_review)
                reviews.append(question_review)

            db.flush()  # Flush once to populate auto-generated IDs for all pending inserts

            for question_review in reviews:
                history = ReviewHistory(
                    question_id=question_review.id,
                    action="created",
                    new_status=ReviewStatus.PENDING.value,
                    changed_by=str(current_user.id),
                    change_reason="Auto-generated via RAG exam generation",
                )
                db.add(history)
                review_question_ids.append(question_review.id)

            db.commit()
        except Exception as persist_err:
            db.rollback()
            logger.error(
                f"Failed to persist questions for exam '{rag_response.exam_id}': {persist_err}",
                exc_info=True,
            )
            review_question_ids = []
            persistence_warning = "Questions were generated but could not be saved to the review workflow. Please try again."

        # Konvertiere zu Response Model
        questions_response = []
        for question in rag_response.questions:
            questions_response.append(
                RAGQuestionResponse(
                    question_text=question.question_text,
                    question_type=question.question_type,
                    options=question.options,
                    correct_answer=question.correct_answer,
                    explanation=question.explanation,
                    difficulty=question.difficulty,
                    source_chunks=question.source_chunks or [],
                    source_documents=question.source_documents or [],
                    confidence_score=question.confidence_score,
                )
            )

        context_response = RAGContextResponse(
            query=rag_response.context_summary.query,
            total_chunks=len(rag_response.context_summary.retrieved_chunks),
            total_similarity_score=rag_response.context_summary.total_similarity_score,
            source_documents=rag_response.context_summary.source_documents,
            context_length=rag_response.context_summary.context_length,
        )

        response = RAGExamResponseModel(
            exam_id=rag_response.exam_id,
            topic=rag_response.topic,
            questions=questions_response,
            context_summary=context_response,
            generation_time=rag_response.generation_time,
            quality_metrics=rag_response.quality_metrics,
            review_question_ids=review_question_ids,
            persistence_warning=persistence_warning,
        )

        logger.info(
            f"Generated RAG exam '{rag_response.exam_id}' with {len(questions_response)} questions"
        )

        status_code = 207 if persistence_warning else 200
        return JSONResponse(content=response.model_dump(), status_code=status_code)

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"RAG exam generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Exam generation failed. Please try again or contact support.",
        )


@router.post("/retrieve-context", response_model=RAGContextResponse)
async def retrieve_context(
    request: ContextRetrievalRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Hole relevanten Kontext aus Vector Database

    **Required:** Authenticated user

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
                        status_code=404, detail=f"Document with ID {doc_id} not found"
                    )

        min_sim = request.min_similarity if request.min_similarity is not None else 0.01
        context = await rag_service_module.rag_service.retrieve_context(
            query=request.query,
            document_ids=request.document_ids,
            max_chunks=request.max_chunks,
            min_similarity=min_sim,
        )

        response = RAGContextResponse(
            query=context.query,
            total_chunks=len(context.retrieved_chunks),
            total_similarity_score=context.total_similarity_score,
            source_documents=context.source_documents,
            context_length=context.context_length,
        )

        logger.info(
            f"Retrieved context for query '{request.query}': {len(context.retrieved_chunks)} chunks"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Context retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Context retrieval failed: {str(e)}"
        )


@router.get("/available-documents")
async def get_available_documents(
    processed_only: bool = Query(True, description="Nur verarbeitete Dokumente"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Hole verfügbare Dokumente für RAG-Prüfungserstellung

    **Required:** Authenticated user

    - **processed_only**: Nur verarbeitete Dokumente anzeigen (empfohlen)
    """
    try:
        # Hole alle Dokumente des aktuellen Users
        documents = document_service.get_documents_by_user(str(current_user.id), db)

        if processed_only:
            from models.document import DocumentStatus

            documents = [
                doc for doc in documents if doc.status == DocumentStatus.PROCESSED
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
                "processed_at": doc.processed_at.isoformat()
                if doc.processed_at
                else None,
                "file_size": getattr(doc, "file_size", None),
                "has_vectors": bool(doc.vector_collection),
            }

            # Füge Metadaten hinzu falls verfügbar
            if doc.doc_metadata:
                doc_info["metadata"] = {
                    "total_chunks": doc.doc_metadata.get("total_chunks"),
                    "embedding_model": doc.doc_metadata.get("embedding_model"),
                    "processing_time": doc.doc_metadata.get("processing_time"),
                }

            available_docs.append(doc_info)

        return {
            "total_documents": len(available_docs),
            "processed_documents": len(
                [d for d in available_docs if d["status"] == "processed"]
            ),
            "documents_with_vectors": len(
                [d for d in available_docs if d["has_vectors"]]
            ),
            "documents": available_docs,
        }

    except Exception as e:
        logger.error(f"Failed to get available documents: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get documents: {str(e)}"
        )


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
                "example": "Welche Aussage ist korrekt?",
            },
            {
                "type": "open_ended",
                "name": "Offene Frage",
                "description": "Frage die eine ausführliche Antwort erfordert",
                "example": "Erläutern Sie die wichtigsten Konzepte...",
            },
            {
                "type": "true_false",
                "name": "Wahr/Falsch",
                "description": "Aussage die als wahr oder falsch bewertet wird",
                "example": "Die folgende Aussage ist korrekt: ...",
            },
        ],
        "difficulty_levels": [
            {
                "level": "easy",
                "name": "Einfach",
                "description": "Grundlegende Fakten und Definitionen",
            },
            {
                "level": "medium",
                "name": "Mittel",
                "description": "Anwendung und Verständnis von Konzepten",
            },
            {
                "level": "hard",
                "name": "Schwer",
                "description": "Analyse, Synthese und kritisches Denken",
            },
        ],
        "supported_languages": [
            {"code": "de", "name": "Deutsch"},
            {"code": "en", "name": "English"},
        ],
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
        from services.vector_service_factory import vector_service

        vector_stats = vector_service.get_collection_stats()

        # Teste Claude Service (vereinfacht)
        claude_available = True
        try:
            claude_service = rag_service_module.rag_service.claude_service
            # Einfacher Test ob Service initialisiert ist
            claude_available = claude_service is not None
        except Exception:
            claude_available = False

        return {
            "status": "healthy",
            "service": "RAG Service",
            "components": {
                "vector_service": {
                    "status": "available",
                    "total_chunks": vector_stats.get("total_chunks", 0),
                    "embedding_model": vector_stats.get("embedding_model", "unknown"),
                },
                "claude_service": {
                    "status": "available" if claude_available else "unavailable",
                    "fallback_enabled": True,
                },
                "rag_templates": {
                    "status": "loaded",
                    "template_count": len(
                        rag_service_module.rag_service.question_templates
                    ),
                },
            },
            "supported_features": [
                "context_retrieval",
                "multi_type_questions",
                "source_attribution",
                "quality_metrics",
                "fallback_generation",
            ],
        }

    except Exception as e:
        logger.error(f"RAG service health check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "service": "RAG Service"},
        )
