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
from services.chat_export_service import chat_export_service
from database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.chat_db import ChatSession as DBChatSession, ChatMessage as DBChatMessage
from models.document import Document as DBDocument, DocumentStatus

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
def create_chat_session(
    session_create: ChatSessionCreate,
    db: Session = Depends(get_db)
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
        documents = validate_documents_exist(session_create.document_ids, db)

        # Erstelle neue Session
        new_session = DBChatSession(
            title=session_create.title,
            document_ids=session_create.document_ids,
            message_count=0,
            is_exported_as_document=False
        )

        db.add(new_session)
        db.commit()
        db.refresh(new_session)

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
        db.rollback()
        raise HTTPException(status_code=500, detail="Fehler beim Erstellen der Chat-Session")


@router.post("/message", response_model=ChatMessage)
def send_chat_message(
    chat_request: ChatRequest,
    db: Session = Depends(get_db)
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
        session = get_chat_session(chat_request.session_id, db)

        # Speichere User-Nachricht
        user_message = DBChatMessage(
            session_id=session.id,
            role="user",
            content=chat_request.message,
            sources=None,
            confidence=None
        )
        db.add(user_message)

        # Lade Chat-Historie für Kontext
        history_messages = db.query(DBChatMessage).filter(
            DBChatMessage.session_id == session.id
        ).order_by(DBChatMessage.timestamp).all()

        # Formatiere Historie für ChatBot
        chat_history = [
            {"role": msg.role, "content": msg.content}
            for msg in history_messages
        ]

        # Generiere Antwort mit ChatBot Service (sync wrapper)
        import asyncio
        response = asyncio.run(chatbot_service.generate_response(
            user_message=chat_request.message,
            document_ids=session.document_ids,
            chat_history=chat_history,
            max_context_chunks=5
        ))

        # Speichere Assistant-Nachricht
        assistant_message = DBChatMessage(
            session_id=session.id,
            role="assistant",
            content=response["content"],
            sources=response.get("sources"),
            confidence=response.get("confidence")
        )
        db.add(assistant_message)

        # Update Session
        session.message_count = session.message_count + 2  # User + Assistant

        db.commit()
        db.refresh(assistant_message)

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
        db.rollback()
        raise HTTPException(status_code=500, detail="Fehler beim Senden der Nachricht")


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
def get_chat_session_endpoint(
    session_id: UUID,
    db: Session = Depends(get_db)
):
    """Lädt komplette Chat-Session mit Historie"""
    try:
        session = get_chat_session(session_id, db)

        # Lade Messages
        messages = db.query(DBChatMessage).filter(
            DBChatMessage.session_id == session.id
        ).order_by(DBChatMessage.timestamp).all()

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
def list_chat_sessions(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Listet alle Chat-Sessions des Benutzers"""
    try:
        sessions = db.query(DBChatSession).order_by(
            DBChatSession.updated_at.desc()
        ).limit(limit).offset(offset).all()

        # Lade letzte Nachricht für Preview
        session_list = []
        for session in sessions:
            last_msg = db.query(DBChatMessage).filter(
                DBChatMessage.session_id == session.id
            ).order_by(DBChatMessage.timestamp.desc()).first()

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
def delete_chat_session(
    session_id: UUID,
    db: Session = Depends(get_db)
):
    """Löscht Chat-Session und alle Nachrichten"""
    try:
        session = get_chat_session(session_id, db)

        db.delete(session)
        db.commit()

        logger.info(f"Deleted chat session {session_id}")

        return {"success": True, "message": "Chat-Session gelöscht"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete chat session: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Fehler beim Löschen der Chat-Session")


@router.post("/sessions/{session_id}/export", response_model=ChatExportResponse)
def export_chat_session(
    session_id: UUID,
    export_format: str = "markdown",
    db: Session = Depends(get_db)
):
    """
    Exportiert Chat-Konversation als Dokument

    - Markdown: Für schnelle Dokumentation
    - JSON: Für maschinelle Verarbeitung
    """
    try:
        if export_format not in ["markdown", "json"]:
            raise HTTPException(status_code=400, detail="Ungültiges Format. Erlaubt: markdown, json")

        session = get_chat_session(session_id, db)

        # Lade Messages
        messages = db.query(DBChatMessage).filter(
            DBChatMessage.session_id == session.id
        ).order_by(DBChatMessage.timestamp).all()

        # Lade Dokumente
        documents = db.query(DBDocument).filter(
            DBDocument.id.in_(session.document_ids)
        ).all()

        # Formatiere für Export
        messages_data = [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "sources": msg.sources,
                "confidence": msg.confidence
            }
            for msg in messages
        ]

        documents_data = [
            {"id": doc.id, "title": doc.title, "filename": doc.filename}
            for doc in documents
        ]

        # Exportiere
        if export_format == "markdown":
            content = chat_export_service.export_as_markdown(
                session_title=session.title,
                created_at=session.created_at,
                documents=documents_data,
                messages=messages_data
            )
            filename = f"chat_{session.title.replace(' ', '_')}_{session.created_at.strftime('%Y%m%d')}.md"
        else:  # json
            content = chat_export_service.export_as_json(
                session_id=session.id,
                session_title=session.title,
                created_at=session.created_at,
                documents=documents_data,
                messages=messages_data
            )
            filename = f"chat_{session.title.replace(' ', '_')}_{session.created_at.strftime('%Y%m%d')}.json"

        logger.info(f"Exported chat session {session_id} as {export_format}")

        return ChatExportResponse(
            session_id=session.id,
            format=export_format,
            content=content,
            filename=filename
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export chat session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Fehler beim Exportieren der Chat-Session")


@router.post("/sessions/{session_id}/to-document", response_model=ChatToDocumentResponse)
def convert_chat_to_document(
    session_id: UUID,
    document_title: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Konvertiert Chat-Konversation in Quell-Dokument für RAG

    - Erstellt strukturiertes Dokument aus Chat
    - Fügt zu Document Library hinzu
    - Ermöglicht Nutzung für Prüfungserstellung
    """
    try:
        session = get_chat_session(session_id, db)

        # Lade Messages
        messages = db.query(DBChatMessage).filter(
            DBChatMessage.session_id == session.id
        ).order_by(DBChatMessage.timestamp).all()

        # Lade Dokumente
        documents = db.query(DBDocument).filter(
            DBDocument.id.in_(session.document_ids)
        ).all()

        # Formatiere für Konvertierung
        messages_data = [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "sources": msg.sources
            }
            for msg in messages
        ]

        documents_data = [
            {"id": doc.id, "title": doc.title}
            for doc in documents
        ]

        # Generiere Dokument-Content
        document_content = chat_export_service.convert_chat_to_document_content(
            session_title=session.title,
            created_at=session.created_at,
            documents=documents_data,
            messages=messages_data
        )

        # Erstelle neues Dokument
        title = document_title or f"Chat: {session.title}"
        filename = f"chat_export_{session.created_at.strftime('%Y%m%d_%H%M%S')}.md"

        # Speichere Titel in doc_metadata (wird von @property title gelesen)
        new_document = DBDocument(
            filename=filename,
            original_filename=filename,
            file_path=f"/tmp/chat_exports/{filename}",  # Virtueller Pfad
            file_size=len(document_content.encode('utf-8')),
            mime_type="text/markdown",
            status=DocumentStatus.PROCESSED,
            doc_metadata={"title": title, "source": "chat_export", "session_id": str(session_id)},
            content_preview=document_content[:500],  # Erste 500 Zeichen
            has_vectors=False
        )

        db.add(new_document)
        db.flush()  # Get ID without committing

        # Update Session
        session.is_exported_as_document = True
        session.exported_document_id = new_document.id

        db.commit()
        db.refresh(new_document)

        logger.info(f"Converted chat session {session_id} to document {new_document.id}")

        return ChatToDocumentResponse(
            session_id=session.id,
            document_id=new_document.id,
            document_title=new_document.title,
            success=True,
            message=f"Chat erfolgreich als Dokument '{new_document.title}' gespeichert"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to convert chat to document: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Fehler beim Konvertieren der Chat-Session")

