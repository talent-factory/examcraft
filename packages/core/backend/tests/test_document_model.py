"""
Unit Tests für Document Model
"""

import pytest
from models.document import Document, DocumentStatus


class TestDocumentModel:
    """Test Suite für Document Model"""
    
    def test_document_title_property_from_metadata(self, test_db):
        """Test dass title Property aus doc_metadata gelesen wird (TF-111 Fix)"""
        doc = Document(
            filename="test.md",
            original_filename="test.md",
            file_path="/tmp/test.md",
            file_size=100,
            mime_type="text/markdown",
            status=DocumentStatus.PROCESSED,
            doc_metadata={"title": "Custom Title", "source": "chat_export"}
        )
        
        test_db.add(doc)
        test_db.commit()
        
        # title Property sollte aus doc_metadata lesen
        assert doc.title == "Custom Title"
    
    def test_document_title_property_fallback_to_filename(self, test_db):
        """Test dass title Property auf original_filename zurückfällt"""
        doc = Document(
            filename="abc123.pdf",
            original_filename="My Document.pdf",
            file_path="/tmp/abc123.pdf",
            file_size=100,
            mime_type="application/pdf",
            status=DocumentStatus.PROCESSED,
            doc_metadata={}  # Kein title in metadata
        )
        
        test_db.add(doc)
        test_db.commit()
        
        # Sollte auf original_filename zurückfallen
        assert doc.title == "My Document.pdf"
    
    def test_document_title_property_no_metadata(self, test_db):
        """Test dass title Property funktioniert wenn doc_metadata None ist"""
        doc = Document(
            filename="test.pdf",
            original_filename="Test Document.pdf",
            file_path="/tmp/test.pdf",
            file_size=100,
            mime_type="application/pdf",
            status=DocumentStatus.PROCESSED,
            doc_metadata=None
        )
        
        test_db.add(doc)
        test_db.commit()
        
        # Sollte auf original_filename zurückfallen
        assert doc.title == "Test Document.pdf"
    
    def test_document_to_dict_uses_title_property(self, test_db):
        """Test dass to_dict() die title Property verwendet"""
        doc = Document(
            filename="test.md",
            original_filename="test.md",
            file_path="/tmp/test.md",
            file_size=100,
            mime_type="text/markdown",
            status=DocumentStatus.PROCESSED,
            doc_metadata={"title": "Chat: Zusammenfassung", "source": "chat_export"}
        )
        
        test_db.add(doc)
        test_db.commit()
        
        doc_dict = doc.to_dict()
        
        assert doc_dict["title"] == "Chat: Zusammenfassung"
        assert doc_dict["filename"] == "test.md"
        assert doc_dict["original_filename"] == "test.md"
    
    def test_chat_export_document_structure(self, test_db):
        """Test dass Chat-Export Dokumente korrekte Struktur haben"""
        doc = Document(
            filename="chat_export_20251009_120000.md",
            original_filename="chat_export_20251009_120000.md",
            file_path="/tmp/chat_exports/chat_export_20251009_120000.md",
            file_size=2000,
            mime_type="text/markdown",
            status=DocumentStatus.PROCESSED,
            user_id="demo_user",
            doc_metadata={
                "title": "Chat: Test Session",
                "source": "chat_export",
                "session_id": "abc-123",
                "full_content": "# Wissensdokumentation\n\nTest content..."
            },
            content_preview="# Wissensdokumentation\n\nTest content..."[:500],
            has_vectors=False
        )
        
        test_db.add(doc)
        test_db.commit()
        
        # Prüfe alle wichtigen Felder
        assert doc.title == "Chat: Test Session"
        assert doc.mime_type == "text/markdown"
        assert doc.status == DocumentStatus.PROCESSED
        assert doc.user_id == "demo_user"
        assert doc.doc_metadata["source"] == "chat_export"
        assert "full_content" in doc.doc_metadata
        assert doc.has_vectors is False
    
    def test_document_status_enum(self, test_db):
        """Test DocumentStatus Enum Werte"""
        doc = Document(
            filename="test.pdf",
            original_filename="test.pdf",
            file_path="/tmp/test.pdf",
            file_size=100,
            mime_type="application/pdf",
            status=DocumentStatus.UPLOADED
        )
        
        test_db.add(doc)
        test_db.commit()
        
        assert doc.status == DocumentStatus.UPLOADED
        assert doc.status.value == "uploaded"
        
        # Update Status
        doc.status = DocumentStatus.PROCESSING
        test_db.commit()
        
        assert doc.status == DocumentStatus.PROCESSING
        assert doc.status.value == "processing"

