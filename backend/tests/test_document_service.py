"""
Unit Tests für DocumentService
"""

import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from fastapi import UploadFile, HTTPException
from io import BytesIO

from services.document_service import DocumentService
from models.document import Document, DocumentStatus


class TestDocumentService:
    """Test Suite für DocumentService"""

    @pytest.fixture
    def document_service(self, temp_upload_dir):
        """DocumentService Instanz für Tests"""
        return DocumentService(upload_dir=temp_upload_dir)

    @pytest.fixture
    def mock_upload_file(self):
        """Mock UploadFile für Tests"""
        content = b"Test document content for unit testing"
        BytesIO(content)

        upload_file = Mock(spec=UploadFile)
        upload_file.filename = "test_document.txt"
        upload_file.size = len(content)
        upload_file.content_type = "text/plain"
        upload_file.read = AsyncMock(return_value=content)
        upload_file.seek = AsyncMock()

        return upload_file

    def test_init(self, temp_upload_dir):
        """Test DocumentService Initialisierung"""
        service = DocumentService(upload_dir=temp_upload_dir)

        assert service.upload_dir == temp_upload_dir
        assert service.max_file_size == 50 * 1024 * 1024  # 50MB
        assert os.path.exists(temp_upload_dir)
        assert len(service.supported_formats) == 5

    def test_supported_formats(self, document_service):
        """Test unterstützte Dateiformate"""
        expected_formats = {
            "application/pdf": ".pdf",
            "application/msword": ".doc",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "text/plain": ".txt",
            "text/markdown": ".md",
        }

        assert document_service.supported_formats == expected_formats

    def test_get_file_extension(self, document_service):
        """Test Dateierweiterung-Extraktion"""
        assert document_service._get_file_extension("test.txt") == ".txt"
        assert document_service._get_file_extension("document.pdf") == ".pdf"
        assert document_service._get_file_extension("file.DOCX") == ".docx"
        assert document_service._get_file_extension("no_extension") == ""
        assert document_service._get_file_extension("") == ""

    def test_is_supported_format(self, document_service):
        """Test Dateiformate-Validierung"""
        assert document_service._is_supported_format("test.txt") is True
        assert document_service._is_supported_format("document.pdf") is True
        assert document_service._is_supported_format("file.docx") is True
        assert document_service._is_supported_format("unsupported.xyz") is False
        assert document_service._is_supported_format("") is False

    @pytest.mark.asyncio
    async def test_validate_file_success(self, document_service, mock_upload_file):
        """Test erfolgreiche Datei-Validierung"""
        # Sollte keine Exception werfen
        await document_service._validate_file(mock_upload_file)

    @pytest.mark.asyncio
    async def test_validate_file_too_large(self, document_service):
        """Test Datei zu groß"""
        large_file = Mock(spec=UploadFile)
        large_file.filename = "large.txt"
        large_file.size = 100 * 1024 * 1024  # 100MB
        large_file.content_type = "text/plain"

        with pytest.raises(HTTPException) as exc_info:
            await document_service._validate_file(large_file)

        assert exc_info.value.status_code == 413
        assert "File too large" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_validate_file_no_filename(self, document_service):
        """Test Datei ohne Filename"""
        no_name_file = Mock(spec=UploadFile)
        no_name_file.filename = None
        no_name_file.size = 1000

        with pytest.raises(HTTPException) as exc_info:
            await document_service._validate_file(no_name_file)

        assert exc_info.value.status_code == 400
        assert "No filename provided" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_validate_file_unsupported_format(self, document_service):
        """Test nicht unterstütztes Dateiformat"""
        unsupported_file = Mock(spec=UploadFile)
        unsupported_file.filename = "test.xyz"
        unsupported_file.size = 1000
        unsupported_file.content_type = "application/unknown"

        with pytest.raises(HTTPException) as exc_info:
            await document_service._validate_file(unsupported_file)

        assert exc_info.value.status_code == 400
        assert "Unsupported file format" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_save_file_to_disk(
        self, document_service, mock_upload_file, temp_upload_dir
    ):
        """Test Datei auf Festplatte speichern"""
        file_path = os.path.join(temp_upload_dir, "test_save.txt")

        await document_service._save_file_to_disk(mock_upload_file, file_path)

        assert os.path.exists(file_path)

        with open(file_path, "rb") as f:
            content = f.read()

        assert content == b"Test document content for unit testing"

    @patch("magic.from_file")
    def test_detect_mime_type(self, mock_magic, document_service, temp_upload_dir):
        """Test MIME-Type Erkennung"""
        # Setup
        test_file = os.path.join(temp_upload_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        mock_magic.return_value = "text/plain"

        # Test
        mime_type = document_service._detect_mime_type(test_file)

        assert mime_type == "text/plain"
        mock_magic.assert_called_once_with(test_file, mime=True)

    @patch("magic.from_file")
    def test_detect_mime_type_fallback(
        self, mock_magic, document_service, temp_upload_dir
    ):
        """Test MIME-Type Fallback bei Fehlern"""
        # Setup
        test_file = os.path.join(temp_upload_dir, "test.pdf")
        with open(test_file, "w") as f:
            f.write("test content")

        mock_magic.side_effect = Exception("Magic failed")

        # Test
        mime_type = document_service._detect_mime_type(test_file)

        assert mime_type == "application/pdf"  # Fallback basierend auf Extension

    @pytest.mark.asyncio
    @patch("services.document_service.uuid.uuid4")
    async def test_upload_document_success(
        self, mock_uuid, document_service, mock_upload_file
    ):
        """Test erfolgreicher Document Upload"""
        # Setup
        mock_uuid_obj = Mock()
        mock_uuid_obj.hex = "test123"
        mock_uuid.return_value = mock_uuid_obj
        mock_db = Mock()

        with patch.object(
            document_service, "_detect_mime_type_from_bytes", return_value="text/plain"
        ):
            # Test
            document = await document_service.upload_document(
                file=mock_upload_file, user_id="test_user", db=mock_db
            )

        # Assertions
        assert document.original_filename == "test_document.txt"
        assert document.mime_type == "text/plain"
        assert document.status == DocumentStatus.UPLOADED
        assert document.user_id == "test_user"
        # Prüfe dass filename gesetzt wurde (UUID wird als Mock-String dargestellt)
        assert document.filename is not None
        assert ".txt" in document.filename

        # Database interactions
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_get_document_by_id(self, document_service):
        """Test Dokument nach ID holen"""
        mock_db = Mock()
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = "test_document"

        result = document_service.get_document_by_id(123, mock_db)

        assert result == "test_document"
        mock_db.query.assert_called_once()

    def test_get_documents_by_user(self, document_service):
        """Test Dokumente nach User holen"""
        mock_db = Mock()
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = ["doc1", "doc2"]

        result = document_service.get_documents_by_user("test_user", mock_db)

        assert result == ["doc1", "doc2"]
        mock_db.query.assert_called_once()

    def test_update_document_status(self, document_service):
        """Test Dokument Status Update"""
        mock_db = Mock()
        mock_document = Mock()
        mock_document.status = DocumentStatus.UPLOADED

        with patch.object(
            document_service, "get_document_by_id", return_value=mock_document
        ):
            result = document_service.update_document_status(
                123, DocumentStatus.PROCESSED, mock_db, metadata={"test": "data"}
            )

        assert result == mock_document
        assert mock_document.status == DocumentStatus.PROCESSED
        assert mock_document.doc_metadata == {"test": "data"}
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_delete_document_success(self, document_service, temp_upload_dir):
        """Test erfolgreiche Dokument-Löschung"""
        # Setup
        test_file = os.path.join(temp_upload_dir, "test_delete.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        mock_db = Mock()
        mock_document = Mock()
        mock_document.file_path = test_file

        with patch.object(
            document_service, "get_document_by_id", return_value=mock_document
        ):
            result = document_service.delete_document(123, mock_db)

        assert result is True
        assert not os.path.exists(test_file)
        mock_db.delete.assert_called_once_with(mock_document)
        mock_db.commit.assert_called_once()

    def test_delete_document_not_found(self, document_service):
        """Test Dokument-Löschung wenn nicht gefunden"""
        mock_db = Mock()

        with patch.object(document_service, "get_document_by_id", return_value=None):
            result = document_service.delete_document(123, mock_db)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_full_document_content_chat_export(self, document_service):
        """Test get_full_document_content für Chat-Exports (TF-111 Fix)"""
        mock_db = Mock()

        # Mock Chat-Export Dokument
        mock_document = Mock(spec=Document)
        mock_document.id = 1
        mock_document.doc_metadata = {
            "source": "chat_export",
            "full_content": "# Wissensdokumentation\n\nDies ist der vollständige Chat-Content mit mehr als 500 Zeichen. "
            * 20,
        }
        mock_document.content_preview = "# Wissensdokumentation\n\nDies ist..."

        with patch.object(
            document_service, "get_document_by_id", return_value=mock_document
        ):
            content = await document_service.get_full_document_content(1, mock_db)

        # Sollte full_content aus doc_metadata zurückgeben
        assert content is not None
        assert content == mock_document.doc_metadata["full_content"]
        assert len(content) > 500

    @pytest.mark.asyncio
    async def test_get_full_document_content_chat_export_fallback(
        self, document_service
    ):
        """Test get_full_document_content Fallback für alte Chat-Exports"""
        mock_db = Mock()

        # Mock altes Chat-Export Dokument ohne full_content
        mock_document = Mock(spec=Document)
        mock_document.id = 1
        mock_document.doc_metadata = {
            "source": "chat_export"
            # Kein full_content (alte Exports)
        }
        mock_document.content_preview = "# Wissensdokumentation\n\nPreview..."

        with patch.object(
            document_service, "get_document_by_id", return_value=mock_document
        ):
            content = await document_service.get_full_document_content(1, mock_db)

        # Sollte auf content_preview zurückfallen
        assert content == mock_document.content_preview
