"""
RAG-basierte Prüfungserstellung API Endpoints für ExamCraft AI
Implementiert dokumentenbasierte Fragenerstellung mit Retrieval-Augmented Generation
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Literal, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db

# IMPORTANT: Import module reference instead of direct import to allow
# runtime replacement of rag_service singleton by Premium package in main.py
import services.rag_service as rag_service_module
from services.rag_service import RAGExamRequest
from services.document_service import document_service
from models.auth import User
from models.document import Document, DocumentStatus
from models.question_generation_job import QuestionGenerationJob
from tasks.question_tasks import generate_questions_task
from schemas.task import GenerateExamTaskResponse
from schemas.active_tasks import ActiveTaskInfo, ActiveTasksResponse
from services.translation_service import t, get_request_locale
from utils.auth_utils import (
    get_current_active_user,
    require_permission,
)
from utils.tenant_utils import TenantFilter, get_tenant_context
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
    difficulty: Literal["easy", "medium", "hard"] = Field(
        "medium", description="Schwierigkeitsgrad"
    )
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
@router.post("/generate-exam", response_model=GenerateExamTaskResponse)
async def generate_rag_exam(
    request: RAGExamRequestModel,
    http_request: Request,
    current_user: User = Depends(require_permission("create_questions")),
    db: Session = Depends(get_db),
):
    """
    Startet asynchrone Fragengenerierung via Celery Task.
    Gibt sofort task_id zurück — Fortschritt via WebSocket /ws/tasks/{task_id}.

    **Required Permission:** `create_questions` (Dozent, Assistant, Admin)

    - **topic**: Thema der Prüfung (3-200 Zeichen)
    - **document_ids**: Optional spezifische Dokumente
    - **question_count**: Anzahl Fragen (1-20, default: 5)
    - **question_types**: Fragetypen (multiple_choice, open_ended, true_false)
    - **difficulty**: Schwierigkeitsgrad (easy, medium, hard)
    - **language**: Sprache (de, en)
    - **context_chunks_per_question**: Context Chunks pro Frage (1-10)
    """
    locale = get_request_locale(http_request, current_user)
    try:
        # Validiere Document IDs falls angegeben
        if request.document_ids:
            tenant_context = get_tenant_context(current_user)
            for doc_id in request.document_ids:
                document = document_service.get_document_by_id(doc_id, db)
                if not document:
                    raise HTTPException(
                        status_code=404,
                        detail=t("rag_document_not_found", locale=locale),
                    )

                # Tenant-Check: Dokument muss zur Institution des Users gehoeren
                TenantFilter.verify_tenant_access(document, tenant_context)

                # Prüfe ob Dokument verarbeitet ist
                if document.status != DocumentStatus.PROCESSED:
                    raise HTTPException(
                        status_code=400,
                        detail=t("rag_document_not_processed", locale=locale),
                    )

        # Validiere Question Types
        valid_types = ["multiple_choice", "open_ended", "true_false"]
        if request.question_types:
            for qtype in request.question_types:
                if qtype not in valid_types:
                    raise HTTPException(
                        status_code=400,
                        detail=t("rag_invalid_question_type", locale=locale),
                    )

        # Request serialisieren
        prompt_config_dict = None
        if request.prompt_config:
            prompt_config_dict = {}
            for question_type, config in request.prompt_config.items():
                prompt_config_dict[question_type] = {
                    "prompt_id": config.prompt_id,
                    "variables": config.variables,
                }

        # Quota-Check vor Generierung (verhindert unnötige Claude-API-Kosten)
        from utils.tenant_utils import SubscriptionLimits

        if not current_user.institution:
            raise HTTPException(
                status_code=403,
                detail=t("rag_no_institution", locale=locale),
            )
        SubscriptionLimits.check_question_limit(
            current_user.institution, db, additional_count=request.question_count
        )

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
        request_data = rag_request.model_dump(mode="json")

        # UUID vorab generieren — wird sowohl als DB-Record-Key als auch als
        # Celery task_id verwendet.
        task_id = str(uuid.uuid4())
        job = QuestionGenerationJob(
            task_id=task_id,
            user_id=current_user.id,
            topic=request.topic,
            question_count=request.question_count,
        )
        db.add(job)
        db.commit()

        # Celery Task dispatchen — bei Fehler Job bereinigen
        try:
            generate_questions_task.apply_async(
                args=[request_data, str(current_user.id), current_user.institution_id],
                task_id=task_id,
                queue="question_generation",
            )
        except Exception as broker_error:
            db.delete(job)
            db.commit()
            logger.error(f"Celery Broker nicht erreichbar: {broker_error}")
            raise HTTPException(
                status_code=503,
                detail=t("rag_task_queue_unavailable", locale=locale),
            )

        logger.info(
            f"Fragengenerierung gestartet: task_id={task_id}, "
            f"user={current_user.id}, topic='{request.topic}'"
        )

        return GenerateExamTaskResponse(
            task_id=task_id,
            message="Fragengenerierung gestartet",
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"RAG exam generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=t("rag_generation_failed", locale=locale),
        )


@router.post("/retrieve-context", response_model=RAGContextResponse)
async def retrieve_context(
    request: ContextRetrievalRequest,
    http_request: Request,
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
    locale = get_request_locale(http_request, current_user)
    try:
        # Validiere Document IDs falls angegeben
        if request.document_ids:
            tenant_context = get_tenant_context(current_user)
            for doc_id in request.document_ids:
                document = document_service.get_document_by_id(doc_id, db)
                if not document:
                    raise HTTPException(
                        status_code=404,
                        detail=t("rag_document_not_found", locale=locale),
                    )

                # Tenant-Check: Dokument muss zur Institution des Users gehoeren
                TenantFilter.verify_tenant_access(document, tenant_context)

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
        logger.error(f"Context retrieval failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=t("rag_context_retrieval_failed", locale=locale)
        )


@router.get("/available-documents")
async def get_available_documents(
    processed_only: bool = Query(True, description="Nur verarbeitete Dokumente"),
    request: Request = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Hole verfügbare Dokumente für RAG-Prüfungserstellung

    **Required:** Authenticated user

    - **processed_only**: Nur verarbeitete Dokumente anzeigen (empfohlen)
    """
    locale = get_request_locale(request, current_user)
    try:
        if not current_user.institution:
            raise HTTPException(
                status_code=403,
                detail=t("rag_no_institution", locale=locale),
            )

        # Tenant-aware: Alle Dokumente der Institution (konsistent mit list_documents)
        tenant_context = get_tenant_context(current_user)
        query = db.query(Document)
        query = TenantFilter.filter_by_tenant(query, Document, tenant_context)

        if processed_only:
            query = query.filter(Document.status == DocumentStatus.PROCESSED)

        documents = query.order_by(Document.created_at.desc()).all()

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get available documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=t("rag_get_documents_failed", locale=locale)
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
        except Exception as e:
            logger.warning(
                f"Claude Service Health-Check fehlgeschlagen: {type(e).__name__}: {e}"
            )
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


TERMINAL_STATUSES = {"SUCCESS", "FAILURE", "REVOKED"}
ACTIVE_TASK_MAX_AGE = timedelta(hours=2)


@router.get("/active-tasks", response_model=ActiveTasksResponse)
async def get_active_tasks(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Return all active (non-terminal) generation tasks for the current user."""
    from celery.result import AsyncResult

    # created_at is timezone-aware (UTC) — use aware cutoff
    cutoff = datetime.now(timezone.utc) - ACTIVE_TASK_MAX_AGE
    jobs = (
        db.query(QuestionGenerationJob)
        .filter(
            QuestionGenerationJob.user_id == current_user.id,
            QuestionGenerationJob.status.notin_(TERMINAL_STATUSES),
            QuestionGenerationJob.created_at > cutoff,
        )
        .all()
    )

    tasks = []
    for job in jobs:
        progress = 0
        message = None
        try:
            result = AsyncResult(job.task_id)
            if result.state == "PROGRESS" and isinstance(result.info, dict):
                current = result.info.get("current", 0)
                total = result.info.get("total", 1)
                progress = int((current / max(total, 1)) * 100)
                message = result.info.get("message")
            elif result.state == "STARTED":
                progress = 0
                message = "Gestartet..."
        except Exception as celery_err:
            logger.warning(
                "Failed to fetch Celery state for task %s: %s",
                job.task_id,
                celery_err,
            )

        tasks.append(
            ActiveTaskInfo(
                task_id=job.task_id,
                status=job.status,
                progress=progress,
                message=message,
                created_at=job.created_at,
                topic=job.topic,
                question_count=job.question_count,
            )
        )

    return ActiveTasksResponse(tasks=tasks)
