"""
Unit tests for Document model
"""

from models.document import Document, DocumentStatus


class TestDocumentModel:
    """Test suite for Document model"""

    def test_document_title_property_from_metadata(self, test_db):
        """Test that the title property is read from doc_metadata (TF-111 fix)"""
        doc = Document(
            filename="test.md",
            original_filename="test.md",
            file_path="/tmp/test.md",
            file_size=100,
            mime_type="text/markdown",
            status=DocumentStatus.PROCESSED,
            doc_metadata={"title": "Custom Title", "source": "chat_export"},
        )

        test_db.add(doc)
        test_db.commit()

        # title property should read from doc_metadata
        assert doc.title == "Custom Title"

    def test_document_title_property_fallback_to_filename(self, test_db):
        """Test that the title property falls back to original_filename (without extension).

        TF-331: the resolver returns the filename stem without extension,
        because ".pdf"/".docx" at the end of the display neither adds
        information nor improves findability.
        """
        doc = Document(
            filename="abc123.pdf",
            original_filename="My Document.pdf",
            file_path="/tmp/abc123.pdf",
            file_size=100,
            mime_type="application/pdf",
            status=DocumentStatus.PROCESSED,
            doc_metadata={},  # No title in metadata
        )

        test_db.add(doc)
        test_db.commit()

        assert doc.title == "My Document"

    def test_document_title_property_no_metadata(self, test_db):
        """Test that the title property works when doc_metadata is None."""
        doc = Document(
            filename="test.pdf",
            original_filename="Test Document.pdf",
            file_path="/tmp/test.pdf",
            file_size=100,
            mime_type="application/pdf",
            status=DocumentStatus.PROCESSED,
            doc_metadata=None,
        )

        test_db.add(doc)
        test_db.commit()

        assert doc.title == "Test Document"

    def test_document_to_dict_uses_title_property(self, test_db):
        """Test that to_dict() uses the title property"""
        doc = Document(
            filename="test.md",
            original_filename="test.md",
            file_path="/tmp/test.md",
            file_size=100,
            mime_type="text/markdown",
            status=DocumentStatus.PROCESSED,
            doc_metadata={"title": "Chat: Zusammenfassung", "source": "chat_export"},
        )

        test_db.add(doc)
        test_db.commit()

        doc_dict = doc.to_dict()

        assert doc_dict["title"] == "Chat: Zusammenfassung"
        assert doc_dict["filename"] == "test.md"
        assert doc_dict["original_filename"] == "test.md"

    def test_chat_export_document_structure(self, test_db):
        """Test that chat export documents have the correct structure.

        Deliberately without ``user_id`` — the ``test_db`` transaction scope
        has no seeded users, so an FK to ``users.id`` would fail. This test
        verifies the chat-export-specific structure (source, full_content,
        has_vectors=False), not the user relationship.
        """
        doc = Document(
            filename="chat_export_20251009_120000.md",
            original_filename="chat_export_20251009_120000.md",
            file_path="/tmp/chat_exports/chat_export_20251009_120000.md",
            file_size=2000,
            mime_type="text/markdown",
            status=DocumentStatus.PROCESSED,
            doc_metadata={
                "title": "Chat: Test Session",
                "source": "chat_export",
                "session_id": "abc-123",
                "full_content": "# Wissensdokumentation\n\nTest content...",
            },
            content_preview="# Wissensdokumentation\n\nTest content..."[:500],
            has_vectors=False,
        )

        test_db.add(doc)
        test_db.commit()

        # Check all important fields
        assert doc.title == "Chat: Test Session"
        assert doc.mime_type == "text/markdown"
        assert doc.status == DocumentStatus.PROCESSED
        assert doc.doc_metadata["source"] == "chat_export"
        assert "full_content" in doc.doc_metadata
        assert doc.has_vectors is False

    def test_to_dict_exposes_escalation_state(self, test_db):
        """TF-365: the escalation state must be exposed via to_dict().

        TF-361 deliberately kept ``escalation`` internal; as a result, an
        in-progress (``queued``) or failed (``failed``) OCR post-processing
        step was invisible to the user (a PROCESSED document that later
        flips to ERROR with no explanation). The state must be serialized
        so the UI can display it.
        """
        doc = Document(
            filename="scan.pdf",
            original_filename="scan.pdf",
            file_path="/tmp/scan.pdf",
            file_size=100,
            mime_type="application/pdf",
            status=DocumentStatus.PROCESSED,
            processing_info={
                "escalation": "queued",
                "quality": {"ok": False, "reason": "scanned_low_text"},
            },
        )
        test_db.add(doc)
        test_db.commit()

        result = doc.to_dict()

        assert result["escalation"] == "queued"

    def test_to_dict_escalation_none_without_processing_info(self, test_db):
        """to_dict() returns escalation=None when no processing_info is present."""
        doc = Document(
            filename="plain.pdf",
            original_filename="plain.pdf",
            file_path="/tmp/plain.pdf",
            file_size=100,
            mime_type="application/pdf",
            status=DocumentStatus.PROCESSED,
            processing_info=None,
        )
        test_db.add(doc)
        test_db.commit()

        assert doc.to_dict()["escalation"] is None

    def test_document_status_enum(self, test_db):
        """Test DocumentStatus Enum Werte"""
        doc = Document(
            filename="test.pdf",
            original_filename="test.pdf",
            file_path="/tmp/test.pdf",
            file_size=100,
            mime_type="application/pdf",
            status=DocumentStatus.UPLOADED,
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
