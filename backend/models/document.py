"""
Document Model für ExamCraft AI
Speichert Metadaten hochgeladener Dokumente
"""

import logging
import re
from sqlalchemy import (
    Column,
    CheckConstraint,
    Integer,
    String,
    DateTime,
    Text,
    JSON,
    Enum,
    Boolean,
    ForeignKey,
    false,
)
from sqlalchemy.sql import func
import enum
import sys
import os

# Add parent directory to path to import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Base  # noqa: E402

logger = logging.getLogger(__name__)

_TITLE_BLOCKLIST = {
    # Office defaults across English / German locales — words alone, with
    # trailing digits handled separately by ``_TITLE_BLOCKLIST_PATTERN``.
    "untitled",
    "untitled document",
    "document",
    "dokument",
    "doc",
    "new document",
    "neues dokument",
    "presentation",
    "präsentation",
    "workbook",
    "arbeitsmappe",
}
# Pattern for placeholder names with trailing digits: "Document1",
# "Tabelle 7", "Mappe2", "Presentation 3", "Sheet1", "Book2", …
# Covers the default file-new templates of Word, Excel, PowerPoint and
# OpenOffice/LibreOffice in the locales we care about.
_TITLE_BLOCKLIST_PATTERN = re.compile(
    r"^(document|dokument|doc|datei|file"
    r"|presentation|präsentation"
    r"|workbook|arbeitsmappe|mappe|book"
    r"|tabelle|sheet|tabelle\d|sheet\d)\s*\d+$",
    re.IGNORECASE,
)


def _is_meaningful_title(title: str) -> bool:
    """Return True when ``title`` is worth showing to the user.

    Filters out common Word/Office defaults that hurt findability — pure
    numbers (e.g. "1"), placeholders ("Untitled", "Document1"), and
    suspiciously short strings. Used to decide whether a document's
    extracted ``metadata.title`` should override the original filename.
    """
    if not title:
        return False
    stripped = title.strip()
    if len(stripped) < 3:
        return False
    if stripped.isdigit():
        return False
    lowered = stripped.lower()
    if lowered in _TITLE_BLOCKLIST:
        return False
    if _TITLE_BLOCKLIST_PATTERN.match(lowered):
        return False
    return True


class DocumentStatus(enum.Enum):
    QUEUED = "queued"  # Waiting in Celery queue
    PROCESSING = "processing"  # Currently being processed
    COMPLETED = "completed"  # Successfully processed
    FAILED = "failed"  # Processing failed
    # Legacy statuses (for backward compatibility)
    UPLOADED = "uploaded"
    PROCESSED = "processed"
    ERROR = "error"


class DocumentVisibility(enum.Enum):
    """Who may see a document (TF-354 privacy fix).

    - ``PRIVATE``: only the owner (``user_id``) sees the document.
    - ``INSTITUTION``: every member of the owner's institution sees it.

    The DB enum stores the lowercase *values* ("private"/"institution"),
    not the member names — see ``values_callable`` on the column. This is a
    deliberate divergence from ``DocumentStatus`` (which stores names) so the
    on-disk labels match the spec and the API/UI contract.
    """

    PRIVATE = "private"
    INSTITUTION = "institution"


class Document(Base):
    __tablename__ = "documents"

    # An institution-visible document MUST belong to an institution: "shared with
    # my institution" is meaningless without one, and the read filter only treats
    # such a row consistently when institution_id is set. Enforced in the DB so no
    # write path (current or future) can create the illegal state (TF-354). After
    # migration A every row is 'private', so none violate this.
    __table_args__ = (
        CheckConstraint(
            "visibility <> 'institution' OR institution_id IS NOT NULL",
            name="ck_documents_institution_visibility_requires_institution",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    # User-editable display title — overrides the auto-extracted metadata.title
    # when set. NULL means "fall back to the resolver chain".
    display_name = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)

    # Processing status
    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED)

    # User association
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Multi-Tenancy: Institution association
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Visibility (TF-354): default ``private`` so an upload is only visible to
    # its owner until explicitly shared with the institution. ``values_callable``
    # stores the lowercase enum *values* as the PG enum labels.
    visibility = Column(
        Enum(
            DocumentVisibility,
            name="documentvisibility",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        server_default=DocumentVisibility.PRIVATE.value,
        default=DocumentVisibility.PRIVATE,
        index=True,
    )

    # Qdrant re-index marker (TF-352): set to True when institution_id changes
    # via the SuperAdmin transfer flow. A Celery task picks it up and re-uploads
    # the document's vector payload to Qdrant with the new institution_id.
    pending_reindex = Column(
        Boolean,
        nullable=False,
        server_default=false(),
        default=False,
    )

    # Extracted metadata from document processing
    doc_metadata = Column(JSON, nullable=True)

    # Text content (für Fallback-Suche)
    content_preview = Column(Text, nullable=True)

    # Vector DB collection name
    vector_collection = Column(String(100), nullable=True)

    # Flag ob Vektoren erstellt wurden
    has_vectors = Column(Boolean, default=False, nullable=True)

    # Celery Task Tracking
    task_id = Column(
        String(100), nullable=True, index=True
    )  # Celery task ID for async processing
    error_message = Column(Text, nullable=True)  # Error message if processing failed
    processing_info = Column(JSON, nullable=True)  # Additional processing metadata

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', status='{self.status}')>"

    @property
    def title(self) -> str:
        """User-facing display title with three-tier fallback chain.

        1. ``display_name`` — explicit user override via the rename UI.
        2. ``doc_metadata['title']`` — extracted from the file's own
           properties (PDF Info dict, DOCX core properties, Markdown
           heading, …) — but only if it passes the meaningfulness check
           (filters "1", "Untitled", "Document1", etc. that Office apps
           leave behind).
        3. ``original_filename`` (without extension) — always present,
           always recognisable to the user who uploaded the file.
        """
        if self.display_name and self.display_name.strip():
            return self.display_name.strip()

        if self.doc_metadata and isinstance(self.doc_metadata, dict):
            extracted = self.doc_metadata.get("title", "")
            if isinstance(extracted, str) and _is_meaningful_title(extracted):
                return extracted.strip()

        if self.original_filename:
            stem, _, ext = self.original_filename.rpartition(".")
            return stem or self.original_filename

        # All three resolver tiers exhausted — should be unreachable because
        # ``original_filename`` is ``nullable=False`` in the schema. Log a
        # warning so corrupt rows surface in the logs instead of rendering
        # blank cards in the UI.
        logger.warning(
            "Document %s resolved to empty title (display_name=%r, "
            "metadata.title=%r, original_filename=%r) — schema invariant violated",
            self.id,
            self.display_name,
            (self.doc_metadata or {}).get("title") if self.doc_metadata else None,
            self.original_filename,
        )
        return ""

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "title": self.title,  # resolved via property (display_name → metadata → filename)
            "display_name": self.display_name,  # raw override, null when unset
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "status": self.status.value if self.status else None,
            "visibility": self.visibility.value if self.visibility else None,
            "user_id": self.user_id,
            "metadata": self.doc_metadata,
            "content_preview": self.content_preview[:200] + "..."
            if self.content_preview and len(self.content_preview) > 200
            else self.content_preview,
            "vector_collection": self.vector_collection,
            "has_vectors": self.has_vectors,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "processed_at": self.processed_at.isoformat()
            if self.processed_at
            else None,
            # Qualitäts-Eskalation (TF-360): kuratierte Felder aus processing_info
            # (interne Marker wie escalation/ocr_attempted bleiben intern).
            "quality": (self.processing_info or {}).get("quality"),
            "processed_with_ocr": (self.processing_info or {}).get(
                "processed_with_ocr", False
            ),
            # pending_reindex omitted — internal Celery marker, not exposed to API clients
        }
