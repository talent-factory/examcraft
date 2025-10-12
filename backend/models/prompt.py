"""
Prompt Knowledge Base Models

SQLAlchemy models for centralized prompt management with versioning,
categorization, and usage tracking.
"""

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    ARRAY,
    ForeignKey,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database import Base


class Prompt(Base):
    """
    Central storage for all system and user prompts.
    
    Supports versioning, categorization, and performance tracking.
    """
    
    __tablename__ = "prompts"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Content
    name = Column(String(255), nullable=False, unique=True, index=True)
    content = Column(Text, nullable=False)
    description = Column(Text)
    
    # Categorization
    category = Column(String(100), nullable=False, index=True)
    tags = Column(ARRAY(Text), default=list)
    use_case = Column(String(255), index=True)
    
    # Versioning
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, default=True, index=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("prompts.id"), nullable=True)
    
    # Metadata
    author_id = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used_at = Column(DateTime)
    usage_count = Column(Integer, default=0)
    
    # Performance
    tokens_estimated = Column(Integer)
    
    # Embedding reference (for Qdrant integration)
    qdrant_point_id = Column(String(255))
    
    # Relationships
    parent = relationship("Prompt", remote_side=[id], backref="versions")
    usage_logs = relationship("PromptUsageLog", back_populates="prompt")
    
    __table_args__ = (
        CheckConstraint(
            "category IN ('system_prompt', 'user_prompt', 'few_shot_example', 'template')",
            name="check_category",
        ),
        CheckConstraint("version > 0", name="check_version"),
    )
    
    def __repr__(self):
        return f"<Prompt {self.name} v{self.version}>"


class PromptTemplate(Base):
    """
    Reusable prompt templates with variable placeholders.
    
    Example: "Generate a question about {topic} with difficulty {level}"
    """
    
    __tablename__ = "prompt_templates"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Content
    name = Column(String(255), nullable=False, unique=True, index=True)
    template = Column(Text, nullable=False)  # Template with {placeholders}
    variables = Column(JSONB, nullable=False)  # {"topic": "string", "level": "int"}
    description = Column(Text)
    
    # Categorization
    category = Column(String(100), nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint(
            "category IN ('question_generation', 'chatbot', 'evaluation')",
            name="check_template_category",
        ),
    )
    
    def __repr__(self):
        return f"<PromptTemplate {self.name}>"


class PromptUsageLog(Base):
    """
    Tracks every prompt usage for analytics and optimization.
    
    Stores performance metrics, success rate, and context.
    """
    
    __tablename__ = "prompt_usage_logs"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Prompt Reference
    prompt_id = Column(
        UUID(as_uuid=True), ForeignKey("prompts.id", ondelete="SET NULL")
    )
    prompt_version = Column(Integer)
    
    # Context
    use_case = Column(String(255), index=True)
    context_data = Column(JSONB)  # Additional context about usage
    
    # Performance Metrics
    tokens_used = Column(Integer)
    latency_ms = Column(Integer)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    # Tracking
    user_id = Column(String(255))
    session_id = Column(String(255))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    prompt = relationship("Prompt", back_populates="usage_logs")
    
    def __repr__(self):
        return f"<PromptUsageLog {self.id} - {self.use_case}>"

