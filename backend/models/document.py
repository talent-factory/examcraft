"""
Document Model für ExamCraft AI
Speichert Metadaten hochgeladener Dokumente
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Enum, Boolean
from sqlalchemy.sql import func
import enum
import sys
import os

# Add parent directory to path to import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Base

class DocumentStatus(enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    
    # Processing status
    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED)
    
    # User association (für zukünftige User Authentication)
    user_id = Column(String(100), nullable=True)
    
    # Extracted metadata from document processing
    doc_metadata = Column(JSON, nullable=True)
    
    # Text content (für Fallback-Suche)
    content_preview = Column(Text, nullable=True)
    
    # Vector DB collection name
    vector_collection = Column(String(100), nullable=True)
    
    # Flag ob Vektoren erstellt wurden
    has_vectors = Column(Boolean, default=False, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', status='{self.status}')>"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "status": self.status.value if self.status else None,
            "user_id": self.user_id,
            "metadata": self.doc_metadata,
            "content_preview": self.content_preview[:200] + "..." if self.content_preview and len(self.content_preview) > 200 else self.content_preview,
            "vector_collection": self.vector_collection,
            "has_vectors": self.has_vectors,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None
        }
