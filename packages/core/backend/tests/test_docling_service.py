"""
Unit Tests für DoclingService und LegacyProcessor
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, mock_open

from services.docling_service import DoclingService, DocumentChunk, ProcessedDocument
from services.document_processors.legacy_processor import LegacyProcessor


class TestLegacyProcessor:
    """Test Suite für LegacyProcessor (the actual processing backend)"""

    @pytest.fixture
    def processor(self):
        """LegacyProcessor Instanz für Tests"""
        return LegacyProcessor(chunk_size=100, chunk_overlap=20)

    def test_init(self):
        """Test LegacyProcessor Initialisierung"""
        processor = LegacyProcessor(chunk_size=500, chunk_overlap=50)

        assert processor.chunk_size == 500
        assert processor.chunk_overlap == 50
        assert len(processor.supported_types) == 5
        assert "application/pdf" in processor.supported_types
        assert "text/plain" in processor.supported_types

    def test_create_chunks_small_text(self, processor):
        """Test Chunk-Erstellung für kleinen Text"""
        text = "Dies ist ein kurzer Test-Text mit wenigen Wörtern."

        chunks = processor._create_chunks(text)

        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].chunk_index == 0
        assert chunks[0].metadata["word_count"] == 8  # Korrekte Wort-Anzahl

    def test_create_chunks_large_text(self, processor):
        """Test Chunk-Erstellung für großen Text"""
        # Erstelle Text mit mehr als 100 Wörtern
        words = ["Wort"] * 150
        text = " ".join(words)

        chunks = processor._create_chunks(text)

        assert len(chunks) > 1
        assert chunks[0].chunk_index == 0
        assert chunks[1].chunk_index == 1

        # Prüfe Überlappung
        chunk1_words = chunks[0].content.split()
        chunk2_words = chunks[1].content.split()

        assert len(chunk1_words) <= 100
        assert len(chunk2_words) <= 100

    def test_create_chunks_empty_text(self, processor):
        """Test Chunk-Erstellung für leeren Text"""
        chunks = processor._create_chunks("")
        assert len(chunks) == 0

        chunks = processor._create_chunks("   ")
        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_process_text_file(self, processor):
        """Test Text-Datei Verarbeitung"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Dies ist ein Test-Text.\nMit mehreren Zeilen.\nFür Unit Tests.")
            temp_path = f.name

        try:
            text, metadata = await processor._process_text(temp_path)

            assert "Dies ist ein Test-Text." in text
            assert "Mit mehreren Zeilen." in text
            assert "Für Unit Tests." in text
            assert metadata["lines"] == 3
            assert metadata["encoding"] == "utf-8"
            assert metadata["words"] > 0

        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_process_markdown_file(self, processor):
        """Test Markdown-Datei Verarbeitung"""
        markdown_content = "# Test Überschrift\n\nDies ist **fetter Text** und *kursiver Text*.\n\n- Liste Item 1\n- Liste Item 2"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown_content)
            temp_path = f.name

        try:
            text, metadata = await processor._process_markdown(temp_path)

            assert "Test Überschrift" in text
            assert "fetter Text" in text
            assert "kursiver Text" in text
            assert metadata["format"] == "Markdown"
            assert "original_markdown" in metadata

        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    @patch("pypdf.PdfReader")
    async def test_process_pdf_file(self, mock_pdf_reader, processor):
        """Test PDF-Datei Verarbeitung"""
        # Mock PDF Reader
        mock_reader_instance = Mock()
        mock_pdf_reader.return_value = mock_reader_instance

        # Mock Metadaten
        mock_metadata = {
            "/Title": "Test PDF",
            "/Author": "Test Author",
            "/Subject": "Test Subject",
        }
        mock_reader_instance.metadata = mock_metadata

        # Mock Seiten
        mock_page = Mock()
        mock_page.extract_text.return_value = "Dies ist der Text von Seite 1."
        mock_reader_instance.pages = [mock_page]

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            temp_path = f.name

        try:
            with patch("builtins.open", mock_open(read_data=b"fake pdf content")):
                text, metadata = await processor._process_pdf(temp_path)

            assert "Dies ist der Text von Seite 1." in text
            assert "[Seite 1]" in text
            assert metadata["title"] == "Test PDF"
            assert metadata["author"] == "Test Author"
            assert metadata["pages"] == 1

        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    @patch("docx.Document")
    async def test_process_docx_file(self, mock_docx_document, processor):
        """Test DOCX-Datei Verarbeitung"""
        # Mock DOCX Document
        mock_doc_instance = Mock()
        mock_docx_document.return_value = mock_doc_instance

        # Mock Paragraphen
        mock_paragraph1 = Mock()
        mock_paragraph1.text = "Dies ist der erste Paragraph."
        mock_paragraph2 = Mock()
        mock_paragraph2.text = "Dies ist der zweite Paragraph."
        mock_doc_instance.paragraphs = [mock_paragraph1, mock_paragraph2]

        # Mock Core Properties - alle als Attribute setzen
        mock_core_props = Mock()
        mock_core_props.title = "Test Document"
        mock_core_props.author = "Test Author"
        mock_core_props.subject = "Test Subject"
        mock_core_props.created = None
        mock_core_props.modified = None
        mock_doc_instance.core_properties = mock_core_props

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            temp_path = f.name

        try:
            text, metadata = await processor._process_docx(temp_path)

            assert "Dies ist der erste Paragraph." in text
            assert "Dies ist der zweite Paragraph." in text
            assert metadata["title"] == "Test Document"
            assert metadata["author"] == "Test Author"
            assert metadata["paragraphs"] == 2
            # Prüfe dass subject vorhanden ist (wird vom LegacyProcessor gesetzt)
            assert "subject" in metadata

        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_process_document_success(self, processor):
        """Test vollständige Dokumentenverarbeitung"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(
                "Test-Dokument für die vollständige Verarbeitung.\nMit mehreren Zeilen Text."
            )
            temp_path = f.name

        try:
            processed_doc = await processor.process_document(
                document_id=123,
                file_path=temp_path,
                filename="test.txt",
                mime_type="text/plain",
            )

            assert isinstance(processed_doc, ProcessedDocument)
            assert processed_doc.document_id == 123
            assert processed_doc.filename == "test.txt"
            assert processed_doc.mime_type == "text/plain"
            assert processed_doc.total_chunks > 0
            assert len(processed_doc.chunks) == processed_doc.total_chunks
            assert processed_doc.processing_time > 0

            # Prüfe ersten Chunk
            first_chunk = processed_doc.chunks[0]
            assert isinstance(first_chunk, DocumentChunk)
            assert "Test-Dokument" in first_chunk.content

        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_process_document_unsupported_type(self, processor):
        """Test Verarbeitung mit nicht unterstütztem MIME-Type"""
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            temp_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                await processor.process_document(
                    document_id=123,
                    file_path=temp_path,
                    filename="test.xyz",
                    mime_type="application/unknown",
                )

            assert "Unsupported MIME type" in str(exc_info.value)

        finally:
            os.unlink(temp_path)


class TestDoclingServiceFacade:
    """Test Suite für DoclingService (Facade)"""

    def test_get_document_summary(self):
        """Test Dokument-Zusammenfassung"""
        # Erstelle Mock ProcessedDocument
        chunks = [
            DocumentChunk(content="Erster Chunk mit Text", chunk_index=0),
            DocumentChunk(content="Zweiter Chunk mit mehr Text", chunk_index=1),
        ]

        processed_doc = ProcessedDocument(
            document_id=123,
            filename="test.txt",
            mime_type="text/plain",
            total_pages=None,
            total_chunks=2,
            chunks=chunks,
            metadata={"test": "data"},
            processing_time=0.5,
        )

        service = DoclingService.__new__(DoclingService)
        summary = service.get_document_summary(processed_doc)

        assert summary["document_id"] == 123
        assert summary["filename"] == "test.txt"
        assert summary["total_chunks"] == 2
        assert (
            summary["total_words"] == 9
        )  # "Erster Chunk mit Text" + "Zweiter Chunk mit mehr Text"
        assert summary["processing_time"] == 0.5
        assert summary["avg_chunk_size"] == 4  # 9 words / 2 chunks = 4.5 -> 4
        assert summary["metadata"] == {"test": "data"}


class TestDocumentChunk:
    """Test Suite für DocumentChunk"""

    def test_document_chunk_creation(self):
        """Test DocumentChunk Erstellung"""
        chunk = DocumentChunk(
            content="Test content",
            page_number=1,
            chunk_index=0,
            metadata={"test": "value"},
        )

        assert chunk.content == "Test content"
        assert chunk.page_number == 1
        assert chunk.chunk_index == 0
        assert chunk.metadata == {"test": "value"}

    def test_document_chunk_default_metadata(self):
        """Test DocumentChunk mit Default-Metadaten"""
        chunk = DocumentChunk(content="Test content")

        assert chunk.metadata == {}
        assert chunk.page_number is None
        assert chunk.chunk_index == 0


class TestProcessedDocument:
    """Test Suite für ProcessedDocument"""

    def test_processed_document_creation(self):
        """Test ProcessedDocument Erstellung"""
        chunks = [DocumentChunk(content="Test", chunk_index=0)]

        doc = ProcessedDocument(
            document_id=123,
            filename="test.txt",
            mime_type="text/plain",
            total_pages=1,
            total_chunks=1,
            chunks=chunks,
            metadata={"test": "data"},
            processing_time=0.1,
        )

        assert doc.document_id == 123
        assert doc.filename == "test.txt"
        assert doc.mime_type == "text/plain"
        assert doc.total_pages == 1
        assert doc.total_chunks == 1
        assert len(doc.chunks) == 1
        assert doc.metadata == {"test": "data"}
        assert doc.processing_time == 0.1
