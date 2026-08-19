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
from models.competency import CompetencyFramework
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
from utils.document_visibility import (
    filter_documents_for_user,
    is_document_visible_for,
    get_accessible_org_unit_ids_for,
)
from utils.competency_visibility import is_framework_visible_for
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
        ["single_choice", "open_ended"], description="Fragetypen"
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
        description="Prompt-Konfiguration pro Fragetyp (z.B. {'single_choice': {...}, 'open_ended': {...}})",
    )
    tag_ids: List[int] = Field(
        default_factory=list,
        description="Tag-IDs, die allen generierten Fragen zugewiesen werden",
    )
    framework_id: Optional[int] = Field(
        None,
        description="Handlungskompetenz-Framework-ID (optional)",
    )
    competencies_override: Optional[str] = Field(
        None,
        max_length=20000,
        description="Freitext-Überschreibung der {{ competencies }}-Variable (gewinnt über Framework)",
    )


def resolve_framework_for_user(db, framework_id, user):
    """Resolve+visibility-check a ``framework_id`` for ``user``: exists,
    not archived, same institution, and visible per
    ``utils.competency_visibility.is_framework_visible_for`` (private/team/
    institution + ``competencies:read_all`` admin bypass). Returns the
    ``CompetencyFramework`` or ``None`` (also for ``framework_id is None``).

    Shared by ``resolve_competencies_text`` (drives the ``{{ competencies }}``
    text injected into the generation prompt) and ``generate_rag_exam``
    (drives the ``framework_id`` persisted onto the generated questions for
    competency-code tagging in ``tasks.question_tasks._persist_questions``).

    TF-644 follow-up (PR #194 review): before this split, ``generate_rag_exam``
    passed the raw, unchecked ``request.framework_id`` straight into
    ``RAGExamRequest``/``_persist_questions``, whose ``Competency`` lookup has
    no institution/visibility filter of its own — so even though
    ``resolve_competencies_text`` correctly withheld the *text* for an
    invisible/cross-tenant framework, its id still reached competency-code
    tagging, and a model-emitted ``competency_code`` colliding with one in
    that hidden framework would set ``question_reviews.competency_id`` to a
    competency the requesting user was never allowed to see — surfaced back
    to them via ``CompetencyBrief``. Both callers now resolve through this
    single gate so an unresolvable/invisible id can never reach either path.
    """
    if framework_id is None:
        return None
    fw = (
        db.query(CompetencyFramework)
        .filter(
            CompetencyFramework.id == framework_id,
            CompetencyFramework.institution_id == user.institution_id,
            CompetencyFramework.is_archived.is_(False),
        )
        .first()
    )
    if fw is None or not is_framework_visible_for(user, fw, db):
        return None
    return fw


def resolve_competencies_text(db, framework_id, override, user):
    """Resolve the {{ competencies }} value: free-text override wins; else the
    selected framework's rendered_text (institution-scoped, nicht archiviert,
    für ``user`` sichtbar); else None.

    Ein explizit gewähltes, aber nicht auflösbares ``framework_id`` (gelöscht,
    archiviert, fremde Institution oder — seit TF-644 — für ``user`` nicht
    sichtbar) wird geloggt — sonst generiert die Prüfung still ohne
    Kompetenz-Bezug, obwohl der Nutzer ein Framework gewählt hat.

    TF-644: vor dieser Änderung ignorierte die Framework-Auswahl visibility
    komplett — jedes institutionsweite Framework war per direkt gesetztem
    ``framework_id`` wählbar, auch ein privates/team-gescoptes Framework
    eines anderen Users (das Frontend-Dropdown ist ``list_frameworks``-
    gefiltert, aber die API selbst prüfte nichts). Mirrors wie TF-643 die
    analoge Moodle-Endpunkt-Lücke bei Exams geschlossen hat.
    """
    if override and override.strip():
        return override
    if framework_id is None:
        return None
    fw = resolve_framework_for_user(db, framework_id, user)
    if fw is None:
        logger.warning(
            "resolve_competencies_text: framework_id=%s nicht auflösbar "
            "(gelöscht/archiviert/fremde Institution/nicht sichtbar für "
            "user=%s, institution=%s) — Kompetenz-Injektion entfällt für "
            "diese Generierung",
            framework_id,
            user.id,
            user.institution_id,
        )
        return None
    return fw.rendered_text


class RAGContextResponse(BaseModel):
    """Response Model für RAG-Kontext"""

    query: str
    total_chunks: int
    total_similarity_score: float
    source_documents: List[Dict[str, Any]]
    context_length: int


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
    - **question_types**: Fragetypen (single_choice, open_ended, true_false)
    - **difficulty**: Schwierigkeitsgrad (easy, medium, hard)
    - **language**: Sprache (de, en)
    - **context_chunks_per_question**: Context Chunks pro Frage (1-10)
    """
    locale = get_request_locale(http_request, current_user)
    try:
        # Validiere Document IDs falls angegeben
        if request.document_ids:
            # Computed once per request, not once per document (TF-620 perf
            # fix) — is_document_visible_for's team-visibility branch would
            # otherwise re-run the hierarchical Org-Unit membership lookup
            # for every id in a client-supplied document_ids list.
            accessible_org_unit_ids = get_accessible_org_unit_ids_for(current_user, db)
            for doc_id in request.document_ids:
                document = document_service.get_document_by_id(doc_id, db)
                # Visibility-Check (TF-354): 404 statt 403 — ein fremdes
                # privates Dokument darf nicht über den RAG-Pfad leaken.
                if not document or not is_document_visible_for(
                    current_user,
                    document,
                    db,
                    accessible_org_unit_ids=accessible_org_unit_ids,
                ):
                    raise HTTPException(
                        status_code=404,
                        detail=t("rag_document_not_found", locale=locale),
                    )

                # Prüfe ob Dokument verarbeitet ist
                if document.status != DocumentStatus.PROCESSED:
                    raise HTTPException(
                        status_code=400,
                        detail=t("rag_document_not_processed", locale=locale),
                    )

        # Validiere Question Types
        valid_types = ["single_choice", "multiple_choice", "open_ended", "true_false"]
        if request.question_types:
            for qtype in request.question_types:
                if qtype not in valid_types:
                    raise HTTPException(
                        status_code=400,
                        detail=t("rag_invalid_question_type", locale=locale),
                    )

        if request.tag_ids:
            from models.tag import Tag as TagModel

            visible = (
                db.query(TagModel)
                .filter(
                    TagModel.id.in_(request.tag_ids),
                    (TagModel.institution_id == current_user.institution_id)
                    | (TagModel.scope == "global"),
                )
                .all()
            )
            if len(visible) != len(set(request.tag_ids)):
                raise HTTPException(
                    status_code=422,
                    detail="Ungültige Tag-IDs.",
                )
            for tag in visible:
                if tag.is_archived:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Tag '{tag.name}' ist archiviert.",
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
            current_user.institution,
            db,
            additional_count=request.question_count,
            user=current_user,
            request=http_request,
        )

        competencies_text = resolve_competencies_text(
            db,
            framework_id=request.framework_id,
            override=request.competencies_override,
            user=current_user,
        )
        # TF-644 review follow-up: persist the *resolved* (visibility-checked)
        # framework id, not the raw client-supplied one — see
        # resolve_framework_for_user's docstring. request.framework_id alone
        # would let an invisible/cross-tenant framework's id reach
        # tasks.question_tasks._persist_questions' unfiltered Competency
        # lookup even though its text is correctly withheld above.
        resolved_framework = resolve_framework_for_user(
            db, request.framework_id, current_user
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
            tag_ids=request.tag_ids,
            framework_id=resolved_framework.id if resolved_framework else None,
            competencies=competencies_text,
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
            request_data=request_data,
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

        from services.audit_service import AuditService

        AuditService.log_action(
            db,
            action="create_question",
            status=AuditService.STATUS_SUCCESS,
            user_id=current_user.id,
            resource_type="question",
            resource_id=task_id,
            request=http_request,
            additional_data={
                "topic": request.topic,
                "question_count": request.question_count,
            },
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


@router.post("/retry-generation/{task_id}", response_model=GenerateExamTaskResponse)
async def retry_generation(
    task_id: str,
    http_request: Request,
    current_user: User = Depends(require_permission("create_questions")),
    db: Session = Depends(get_db),
):
    """
    Retry a failed generation job using the same parameters.
    Creates a new Celery task from the stored request_data.
    """
    locale = get_request_locale(http_request, current_user)
    try:
        original_job = (
            db.query(QuestionGenerationJob)
            .filter(QuestionGenerationJob.task_id == task_id)
            .first()
        )

        if not original_job:
            raise HTTPException(
                status_code=404, detail=t("rag_task_not_found", locale=locale)
            )

        # Owner-Check (Superuser-Bypass mit Audit-Log)
        from utils.auth_utils import enforce_resource_access

        enforce_resource_access(
            obj=original_job,
            user=current_user,
            action="retry",
            db=db,
            resource_type="question_generation_job",
            request=http_request,
        )

        if original_job.status not in ("FAILURE", "REVOKED"):
            raise HTTPException(
                status_code=400,
                detail=t("rag_retry_only_failed", locale=locale),
            )

        if not original_job.request_data or not isinstance(
            original_job.request_data, dict
        ):
            raise HTTPException(
                status_code=400,
                detail=t("rag_retry_no_request_data", locale=locale),
            )

        from utils.tenant_utils import SubscriptionLimits

        # Preserve original ownership across retries. For owner-driven retries
        # this is a no-op (original_user is current_user). For superuser-bypass
        # retries this is critical: the original job's request_data is scoped
        # to the original institution (exam_id, document filenames), so
        # creating the new job under the superuser's user/institution would
        # silently move quota consumption and resulting QuestionReview rows
        # into the wrong institution.
        if original_job.user_id == current_user.id:
            owner_user = current_user
        else:
            owner_user = db.query(User).filter(User.id == original_job.user_id).first()
            if owner_user is None or owner_user.institution is None:
                raise HTTPException(
                    status_code=400,
                    detail=t("rag_retry_owner_unavailable", locale=locale),
                )

        if not owner_user.institution:
            raise HTTPException(
                status_code=403, detail=t("rag_no_institution", locale=locale)
            )

        question_count = original_job.request_data.get("question_count", 5)
        SubscriptionLimits.check_question_limit(
            owner_user.institution,
            db,
            additional_count=question_count,
            user=owner_user,
            request=http_request,
        )

        new_task_id = str(uuid.uuid4())
        new_job = QuestionGenerationJob(
            task_id=new_task_id,
            user_id=owner_user.id,
            topic=original_job.topic,
            question_count=original_job.question_count,
            request_data=original_job.request_data,
        )
        db.add(new_job)
        db.commit()

        try:
            generate_questions_task.apply_async(
                args=[
                    original_job.request_data,
                    str(owner_user.id),
                    owner_user.institution_id,
                ],
                task_id=new_task_id,
                queue="question_generation",
            )
        except Exception as broker_error:
            db.delete(new_job)
            db.commit()
            logger.error(
                "Celery broker unreachable during retry: %s",
                broker_error,
                exc_info=True,
            )
            raise HTTPException(
                status_code=503,
                detail=t("rag_task_queue_unavailable", locale=locale),
            )

        # Audit-log the retry trigger so it appears in the dashboard
        # widget and ``/aktivitaeten``. ``user_id`` stays the job owner
        # (also on superuser-bypass retries); ``retry_of_task_id`` lets
        # consumers distinguish original generations from retries.
        # AuditService.log_action swallows its own DB errors and
        # returns None — a None return means the activity feed will be
        # missing this entry, but the Celery task is already enqueued
        # so a 500 here would prompt the user to retry and double-
        # charge quota. The narrow try/except handles the unlikely
        # case where AuditService itself is unimportable.
        from services.audit_service import AuditService

        audit_log = None
        try:
            audit_log = AuditService.log_action(
                db,
                action="create_question",
                status=AuditService.STATUS_SUCCESS,
                user_id=owner_user.id,
                resource_type="question",
                resource_id=new_task_id,
                request=http_request,
                additional_data={
                    "topic": original_job.topic,
                    "question_count": original_job.question_count,
                    "retry_of_task_id": task_id,
                },
            )
        except Exception as audit_error:
            logger.error(
                "Retry audit log raised for new_task_id=%s (job already enqueued): %s",
                new_task_id,
                audit_error,
                exc_info=True,
            )
        if audit_log is None:
            logger.error(
                "Retry audit log returned None for new_task_id=%s — "
                "activity feed will be missing this retry. Job already enqueued.",
                new_task_id,
            )

        logger.info(
            f"Retry started: new_task_id={new_task_id}, "
            f"original_task_id={task_id}, user={current_user.id}"
        )

        return GenerateExamTaskResponse(
            task_id=new_task_id,
            message=t("rag_retry_started", locale=locale),
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Retry generation failed: {e}", exc_info=True)
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
            # Computed once per request, not once per document (TF-620 perf
            # fix) — see generate_exam_from_documents for the same pattern.
            accessible_org_unit_ids = get_accessible_org_unit_ids_for(current_user, db)
            for doc_id in request.document_ids:
                document = document_service.get_document_by_id(doc_id, db)
                # Visibility-Check (TF-354): 404 statt 403 — ein fremdes
                # privates Dokument darf nicht über den RAG-Pfad leaken.
                if not document or not is_document_visible_for(
                    current_user,
                    document,
                    db,
                    accessible_org_unit_ids=accessible_org_unit_ids,
                ):
                    raise HTTPException(
                        status_code=404,
                        detail=t("rag_document_not_found", locale=locale),
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

        # Visibility-aware (TF-354): konsistent mit list_documents — eigene
        # Docs + institution-geteilte Docs der eigenen Institution.
        query = db.query(Document)
        query = filter_documents_for_user(query, current_user, db)

        if processed_only:
            query = query.filter(Document.status == DocumentStatus.PROCESSED)

        documents = query.order_by(Document.created_at.desc()).all()

        # Konvertiere zu Response Format
        available_docs = []
        for doc in documents:
            doc_info = {
                "id": doc.id,
                "filename": doc.original_filename,
                # TF-605: Die Dokumentauswahl der Fragengenerierung soll den in
                # der Bibliothek vergebenen Namen zeigen, nicht den Upload-
                # Dateinamen. `title` löst die Fallback-Kette display_name →
                # doc_metadata['title'] → original_filename (ohne Endung) auf
                # und ist damit praktisch nie leer (nur bei verletztem
                # Schema-Invariant — dann warnt die Property und liefert "");
                # `display_name` bleibt als rohes Override daneben stehen
                # (analog Document.to_dict()).
                "title": doc.title,
                "display_name": doc.display_name,
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
                "type": "single_choice",
                "name": "Einfachauswahl",
                "description": "Frage mit 4 Antwortoptionen (A, B, C, D), genau eine richtig",
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
    http_request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Return all active (non-terminal) generation tasks.

    Normal users see only their own jobs. Superusers see jobs of all users;
    the broadening is audit-logged via AuditService.log_superuser_bypass
    (resource_type="question_generation_job_list", action="list_all_active").

    Defense-in-depth: a job whose DB status is non-terminal but whose Celery
    state is already terminal (e.g. worker died before ``_update_job_status``
    committed) is treated as a phantom — excluded from the response and the
    DB row is synced idempotently via ``_try_update_job_status`` (single attempt
    only — the watchdog from TF-329 reconciles persistent failures, so the HTTP
    handler never blocks on the multi-attempt retry loop in ``_update_job_status``).
    """
    from celery.result import AsyncResult

    from tasks.question_tasks import _try_update_job_status

    # created_at is timezone-aware (UTC) — use aware cutoff
    cutoff = datetime.now(timezone.utc) - ACTIVE_TASK_MAX_AGE
    if current_user.is_superuser:
        jobs = (
            db.query(QuestionGenerationJob)
            .filter(
                QuestionGenerationJob.status.notin_(TERMINAL_STATUSES),
                QuestionGenerationJob.created_at > cutoff,
            )
            .all()
        )
        # Audit only when the bypass actually surfaced a foreign-owned job.
        # The frontend GenerationTasksContext polls this endpoint on a multi-
        # second interval; emitting an audit row every poll cycle (most of
        # which return only the superuser's own jobs) flooded the DSGVO trail
        # with low-signal entries and obscured genuine cross-owner access
        # events. Logging on first foreign-job detection per request keeps
        # the security signal sharp.
        foreign_owned = [j for j in jobs if j.user_id != current_user.id]
        if foreign_owned:
            from services.audit_service import AuditService

            AuditService.log_superuser_bypass(
                db=db,
                superuser=current_user,
                resource_type="question_generation_job_list",
                resource_id=None,
                action="list_all_active",
                owner_user_id=None,
                request=http_request,
            )
    else:
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
        celery_state: Optional[str] = None
        try:
            result = AsyncResult(job.task_id)
            celery_state = result.state
            if celery_state == "PROGRESS" and isinstance(result.info, dict):
                current = result.info.get("current", 0)
                total = result.info.get("total", 1)
                progress = int((current / max(total, 1)) * 100)
                message = result.info.get("message")
            elif celery_state == "STARTED":
                progress = 0
                message = "Gestartet..."
        except Exception as celery_err:
            logger.warning(
                "Failed to fetch Celery state for task %s: %s",
                job.task_id,
                celery_err,
            )

        if celery_state in TERMINAL_STATUSES:
            logger.info(
                "Phantom job detected: task_id=%s db_status=%s celery_state=%s — syncing DB",
                job.task_id,
                job.status,
                celery_state,
            )
            try:
                _try_update_job_status(job.task_id, celery_state)
            except Exception as sync_err:
                # Includes JobNotFoundError, SQLAlchemyError, OSError. We don't
                # retry inline — TF-329's watchdog reconciles persistent
                # failures so the request handler never blocks. ERROR (not
                # WARNING) so log aggregation surfaces a real DB outage; the
                # phantom job stays excluded from the response (same effect as
                # before), but operators see the symptom loudly.
                logger.error(
                    "Failed to sync DB status for phantom job %s (celery_state=%s): %s",
                    job.task_id,
                    celery_state,
                    sync_err,
                    exc_info=True,
                )
            continue

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
