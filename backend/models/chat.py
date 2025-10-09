"""
Pydantic Models für Chat-Funktionalität
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class ChatSessionCreate(BaseModel):
    """Request model für neue Chat-Session"""
    document_ids: List[int] = Field(..., min_length=1, description="Liste der Dokument-IDs für Chat-Kontext")
    title: Optional[str] = Field(None, max_length=255, description="Optionaler Titel für die Chat-Session")
    
    @field_validator('title')
    @classmethod
    def generate_title_if_empty(cls, v: Optional[str], info) -> str:
        """Generiert automatischen Titel wenn leer"""
        if not v or not v.strip():
            doc_count = len(info.data.get('document_ids', []))
            return f"Chat mit {doc_count} Dokument{'en' if doc_count > 1 else ''}"
        return v.strip()


class ChatMessage(BaseModel):
    """Chat-Nachricht Model"""
    id: Optional[UUID] = None
    role: str = Field(..., pattern="^(user|assistant)$", description="Rolle: 'user' oder 'assistant'")
    content: str = Field(..., min_length=1, description="Nachrichteninhalt")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sources: Optional[List[Dict[str, Any]]] = Field(None, description="Quellreferenzen aus RAG")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Konfidenz-Score (nur für assistant)")
    
    class Config:
        from_attributes = True


class ChatSessionResponse(BaseModel):
    """Response model für Chat-Session"""
    id: UUID
    user_id: Optional[int] = None
    document_ids: List[int]
    title: str
    messages: List[ChatMessage] = []
    created_at: datetime
    updated_at: datetime
    message_count: int
    is_exported_as_document: bool = False
    exported_document_id: Optional[int] = None
    
    class Config:
        from_attributes = True


class ChatSessionListItem(BaseModel):
    """Kompakte Session-Info für Listen-Ansicht"""
    id: UUID
    title: str
    document_ids: List[int]
    message_count: int
    created_at: datetime
    updated_at: datetime
    last_message_preview: Optional[str] = None
    
    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    """Request model für Chat-Nachricht"""
    message: str = Field(..., min_length=1, max_length=2000, description="Benutzernachricht")
    session_id: UUID = Field(..., description="Chat-Session ID")


class ChatBotResponse(BaseModel):
    """Strukturierte Response vom ChatBot (für PydanticAI)"""
    response: str = Field(..., description="Die generierte Antwort")
    citations: List[Dict[str, Any]] = Field(default_factory=list, description="Quellenreferenzen")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Konfidenz-Score")


class ChatExportRequest(BaseModel):
    """Request model für Chat-Export"""
    session_id: UUID
    format: str = Field("markdown", pattern="^(markdown|pdf|json)$", description="Export-Format")


class ChatExportResponse(BaseModel):
    """Response model für Chat-Export"""
    session_id: UUID
    format: str
    content: Optional[str] = None  # Für markdown/json
    file_url: Optional[str] = None  # Für PDF
    filename: str


class ChatToDocumentRequest(BaseModel):
    """Request model für Chat-zu-Dokument Konvertierung"""
    session_id: UUID
    document_title: Optional[str] = Field(None, description="Titel für das neue Dokument")


class ChatToDocumentResponse(BaseModel):
    """Response model für Chat-zu-Dokument Konvertierung"""
    session_id: UUID
    document_id: int
    document_title: str
    success: bool
    message: str


class DocumentInfo(BaseModel):
    """Dokument-Info für Chat-Kontext"""
    id: int
    title: str
    filename: str
    status: str
    
    class Config:
        from_attributes = True


class ChatContextInfo(BaseModel):
    """Erweiterte Kontext-Informationen für Chat"""
    session_id: UUID
    documents: List[DocumentInfo]
    total_chunks_available: int
    rag_enabled: bool = True

