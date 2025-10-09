"""
SQLAlchemy Database Models für Chat-Funktionalität
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from database import Base


class ChatSession(Base):
    """Chat-Session Model"""
    __tablename__ = "chat_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=True)  # Temporär als String, bis User-Management implementiert ist
    title = Column(String(255), nullable=False)
    document_ids = Column(ARRAY(Integer), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    message_count = Column(Integer, default=0, nullable=False)
    is_exported_as_document = Column(Boolean, default=False, nullable=False)
    exported_document_id = Column(Integer, ForeignKey('documents.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ChatSession(id={self.id}, title='{self.title}', messages={self.message_count})>"


class ChatMessage(Base):
    """Chat-Nachricht Model"""
    __tablename__ = "chat_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    sources = Column(JSONB, nullable=True)  # Quellenreferenzen aus RAG
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)
    confidence = Column(Float, nullable=True)  # Confidence score from AI
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, role='{self.role}', session_id={self.session_id})>"

