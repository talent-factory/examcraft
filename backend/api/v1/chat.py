"""
Chat API Endpoints für Document ChatBot
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from uuid import UUID
import logging

from models.chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionListItem,
    ChatRequest,
    ChatMessage,
    ChatExportRequest,
    ChatExportResponse,
    ChatToDocumentRequest,
    ChatToDocumentResponse,
    ChatContextInfo,
    DocumentInfo
)
from services.chatbot_service import chatbot_service
from database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import select, delete, update, func
from models.chat_db import ChatSession as DBChatSession, ChatMessage as DBChatMessage
from models.document import Document as DBDocument

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


# --- Helper Functions ---

def get_chat_session(
    session_id: UUID,
    db: Session
) -> DBChatSession:
    """Lädt Chat-Session aus DB"""
    session = db.query(DBChatSession).filter(
        DBChatSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Chat-Session nicht gefunden")

    return session


def validate_documents_exist(
    document_ids: List[int],
    db: Session
) -> List[DBDocument]:
    """Validiert dass alle Dokumente existieren"""
    documents = db.query(DBDocument).filter(
        DBDocument.id.in_(document_ids)
    ).all()

    if len(documents) != len(document_ids):
        found_ids = {doc.id for doc in documents}
        missing_ids = set(document_ids) - found_ids
        raise HTTPException(
            status_code=404,
            detail=f"Dokumente nicht gefunden: {missing_ids}"
        )

    return documents


# --- API Endpoints ---

@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    session_create: ChatSessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Erstellt neue Chat-Session mit selektierten Dokumenten
    
    - Validiert Dokument-IDs
    - Initialisiert Chat-History
    - Generiert Session-ID
    - Speichert in Datenbank
    """
    try:
        # Validiere Dokumente
        documents = await validate_documents_exist(session_create.document_ids, db)
        
        # Erstelle neue Session
        new_session = db_models.ChatSession(
            title=session_create.title,
            document_ids=session_create.document_ids,
            message_count=0,
            is_exported_as_document=False
        )
        
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        
        logger.info(f"Created chat session {new_session.id} with {len(documents)} documents")
        
        return ChatSessionResponse(
            id=new_session.id,
            user_id=new_session.user_id,
            document_ids=new_session.document_ids,
            title=new_session.title,
            messages=[],
            created_at=new_session.created_at,
            updated_at=new_session.updated_at,
            message_count=0,
            is_exported_as_document=False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create chat session: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Fehler beim Erstellen der Chat-Session")


@router.post("/message", response_model=ChatMessage)
async def send_chat_message(
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Sendet Nachricht an ChatBot und erhält KI-generierte Antwort
    
    - Lädt Chat-Session und zugehörige Dokumente
    - Nutzt RAG für relevanten Kontext
    - Generiert Antwort mit PydanticAI
    - Speichert Konversation
    - Trackt Quellreferenzen
    """
    try:
        # Lade Session
        session = await get_chat_session(chat_request.session_id, db)
        
        # Speichere User-Nachricht
        user_message = db_models.ChatMessage(
            session_id=session.id,
            role="user",
            content=chat_request.message,
            sources=None,
            confidence=None
        )
        db.add(user_message)
        
        # Lade Chat-Historie für Kontext
        result = await db.execute(
            select(db_models.ChatMessage)
            .where(db_models.ChatMessage.session_id == session.id)
            .order_by(db_models.ChatMessage.timestamp)
        )
        history_messages = result.scalars().all()
        
        # Formatiere Historie für ChatBot
        chat_history = [
            {"role": msg.role, "content": msg.content}
            for msg in history_messages
        ]
        
        # Generiere Antwort mit ChatBot Service
        response = await chatbot_service.generate_response(
            user_message=chat_request.message,
            document_ids=session.document_ids,
            chat_history=chat_history,
            max_context_chunks=5
        )
        
        # Speichere Assistant-Nachricht
        assistant_message = db_models.ChatMessage(
            session_id=session.id,
            role="assistant",
            content=response["content"],
            sources=response.get("sources"),
            confidence=response.get("confidence")
        )
        db.add(assistant_message)
        
        # Update Session
        session.message_count = session.message_count + 2  # User + Assistant
        session.updated_at = func.now()
        
        await db.commit()
        await db.refresh(assistant_message)
        
        logger.info(f"Generated response for session {session.id}")
        
        return ChatMessage(
            id=assistant_message.id,
            role=assistant_message.role,
            content=assistant_message.content,
            timestamp=assistant_message.timestamp,
            sources=assistant_message.sources,
            confidence=assistant_message.confidence
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send chat message: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Fehler beim Senden der Nachricht")


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session_endpoint(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Lädt komplette Chat-Session mit Historie"""
    try:
        session = await get_chat_session(session_id, db)
        
        # Lade Messages
        result = await db.execute(
            select(db_models.ChatMessage)
            .where(db_models.ChatMessage.session_id == session.id)
            .order_by(db_models.ChatMessage.timestamp)
        )
        messages = result.scalars().all()
        
        return ChatSessionResponse(
            id=session.id,
            user_id=session.user_id,
            document_ids=session.document_ids,
            title=session.title,
            messages=[
                ChatMessage(
                    id=msg.id,
                    role=msg.role,
                    content=msg.content,
                    timestamp=msg.timestamp,
                    sources=msg.sources,
                    confidence=msg.confidence
                )
                for msg in messages
            ],
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=session.message_count,
            is_exported_as_document=session.is_exported_as_document,
            exported_document_id=session.exported_document_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chat session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Fehler beim Laden der Chat-Session")


@router.get("/sessions", response_model=List[ChatSessionListItem])
async def list_chat_sessions(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Listet alle Chat-Sessions des Benutzers"""
    try:
        result = await db.execute(
            select(db_models.ChatSession)
            .order_by(db_models.ChatSession.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        sessions = result.scalars().all()
        
        # Lade letzte Nachricht für Preview
        session_list = []
        for session in sessions:
            last_msg_result = await db.execute(
                select(db_models.ChatMessage)
                .where(db_models.ChatMessage.session_id == session.id)
                .order_by(db_models.ChatMessage.timestamp.desc())
                .limit(1)
            )
            last_msg = last_msg_result.scalar_one_or_none()
            
            session_list.append(ChatSessionListItem(
                id=session.id,
                title=session.title,
                document_ids=session.document_ids,
                message_count=session.message_count,
                created_at=session.created_at,
                updated_at=session.updated_at,
                last_message_preview=last_msg.content[:100] if last_msg else None
            ))
        
        return session_list
        
    except Exception as e:
        logger.error(f"Failed to list chat sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Fehler beim Laden der Chat-Sessions")


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Löscht Chat-Session und alle Nachrichten"""
    try:
        session = await get_chat_session(session_id, db)
        
        await db.delete(session)
        await db.commit()
        
        logger.info(f"Deleted chat session {session_id}")
        
        return {"success": True, "message": "Chat-Session gelöscht"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete chat session: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Fehler beim Löschen der Chat-Session")

