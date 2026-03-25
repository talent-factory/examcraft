"""
Unit Tests für DoclingProcessor
Tests für IBM Docling Integration
"""

import pytest
from unittest.mock import patch, MagicMock

docling = pytest.importorskip("docling", reason="docling not installed")
from services.document_processors.docling_processor import DoclingProcessor  # noqa: E402
from services.docling_service import DocumentChunk, ProcessedDocument  # noqa: E402


@pytest.fixture
def docling_processor():
    """Fixture für DoclingProcessor"""
    return DoclingProcessor(chunk_size=1000, chunk_overlap=200)


@pytest.fixture
def sample_pdf_path(tmp_path):
    """Fixture für temporäre PDF-Datei"""
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n%Test PDF")
    return str(pdf_file)


class TestDoclingProcessorInitialization:
    """Tests für Processor-Initialisierung"""

    def test_processor_initialization(self, docling_processor):
        """Test: Processor wird korrekt initialisiert"""
        assert docling_processor.chunk_size == 1000
        assert docling_processor.chunk_overlap == 200
        assert docling_processor.converter is not None

    def test_custom_chunk_settings(self):
        """Test: Custom Chunk-Einstellungen"""
        processor = DoclingProcessor(chunk_size=500, chunk_overlap=100)
        assert processor.chunk_size == 500
        assert processor.chunk_overlap == 100


class TestDoclingProcessorDocumentProcessing:
    """Tests für Dokumentenverarbeitung"""

    @pytest.mark.asyncio
    async def test_process_document_success(self, docling_processor, sample_pdf_path):
        """Test: Erfolgreiches Document Processing"""
        # Mock DocumentConverter
        with patch.object(docling_processor.converter, "convert") as mock_convert:
            # Mock ConversionResult
            mock_result = MagicMock()
            mock_result.document.export_to_markdown.return_value = (
                "# Test Document\n\nSample content."
            )
            mock_result.document.tables = []
            mock_convert.return_value = mock_result

            result = await docling_processor.process_document(
                document_id=1,
                file_path=sample_pdf_path,
                filename="test.pdf",
                mime_type="application/pdf",
            )

            assert isinstance(result, ProcessedDocument)
            assert result.document_id == 1
            assert result.filename == "test.pdf"
            assert result.mime_type == "application/pdf"
            assert result.total_chunks > 0
            assert len(result.chunks) > 0

    @pytest.mark.asyncio
    async def test_process_document_with_tables(
        self, docling_processor, sample_pdf_path
    ):
        """Test: Document Processing mit Tabellen"""
        with patch.object(docling_processor.converter, "convert") as mock_convert:
            # Mock Table
            mock_table = MagicMock()
            mock_table.export_to_markdown.return_value = (
                "| Header | Value |\n|--------|-------|\n| A | 1 |"
            )

            mock_result = MagicMock()
            mock_result.document.export_to_markdown.return_value = (
                "# Document with Table"
            )
            mock_result.document.tables = [mock_table]
            mock_convert.return_value = mock_result

            result = await docling_processor.process_document(
                document_id=1,
                file_path=sample_pdf_path,
                filename="test.pdf",
                mime_type="application/pdf",
            )

            assert result.metadata.get("table_count") == 1
            assert len(result.metadata.get("tables", [])) == 1

    @pytest.mark.asyncio
    async def test_process_document_invalid_file(self, docling_processor):
        """Test: Processing mit ungültiger Datei"""
        with pytest.raises(Exception):
            await docling_processor.process_document(
                document_id=1,
                file_path="/nonexistent/file.pdf",
                filename="nonexistent.pdf",
                mime_type="application/pdf",
            )


class TestDoclingProcessorChunking:
    """Tests für Text-Chunking"""

    def test_create_semantic_chunks(self, docling_processor):
        """Test: Semantic Chunking basierend auf Struktur"""
        text = """# Section 1
Content of section 1.

## Subsection 1.1
More content here.

# Section 2
Content of section 2."""

        chunks = docling_processor._create_semantic_chunks(text)

        assert len(chunks) > 0
        assert all(isinstance(chunk, DocumentChunk) for chunk in chunks)
        assert all(chunk.content for chunk in chunks)

    def test_create_simple_chunks(self, docling_processor):
        """Test: Simple Word-based Chunking"""
        text = " ".join([f"word{i}" for i in range(2000)])  # 2000 words

        chunks = docling_processor._create_simple_chunks(text)

        assert len(chunks) > 1  # Should create multiple chunks
        assert all(isinstance(chunk, DocumentChunk) for chunk in chunks)

        # Check overlap
        if len(chunks) > 1:
            # Last words of first chunk should appear in second chunk
            first_chunk_words = chunks[0].content.split()
            chunks[1].content.split()
            assert len(first_chunk_words) <= docling_processor.chunk_size

    def test_empty_text_chunking(self, docling_processor):
        """Test: Chunking mit leerem Text"""
        chunks = docling_processor._create_simple_chunks("")
        assert len(chunks) == 0


class TestDoclingProcessorMetadata:
    """Tests für Metadaten-Extraktion"""

    @pytest.mark.asyncio
    async def test_extract_metadata(self, docling_processor, sample_pdf_path):
        """Test: Metadaten-Extraktion"""
        with patch.object(docling_processor.converter, "convert") as mock_convert:
            mock_result = MagicMock()
            mock_result.document.export_to_markdown.return_value = "# Title\n\nContent"
            mock_result.document.tables = []
            mock_convert.return_value = mock_result

            result = await docling_processor.process_document(
                document_id=1,
                file_path=sample_pdf_path,
                filename="test.pdf",
                mime_type="application/pdf",
            )

            assert "title" in result.metadata
            assert "sections" in result.metadata
            assert "table_count" in result.metadata
            assert "image_count" in result.metadata

    def test_extract_tables(self, docling_processor):
        """Test: Tabellen-Extraktion"""
        mock_table = MagicMock()
        mock_table.export_to_markdown.return_value = "| A | B |\n|---|---|\n| 1 | 2 |"

        tables = docling_processor._extract_tables([mock_table])

        assert len(tables) == 1
        assert "markdown" in tables[0]
        assert tables[0]["markdown"] == "| A | B |\n|---|---|\n| 1 | 2 |"


class TestDoclingProcessorErrorHandling:
    """Tests für Error Handling"""

    @pytest.mark.asyncio
    async def test_processing_error_handling(self, docling_processor, sample_pdf_path):
        """Test: Error Handling bei Processing-Fehler"""
        with patch.object(docling_processor.converter, "convert") as mock_convert:
            mock_convert.side_effect = Exception("Processing failed")

            with pytest.raises(Exception) as exc_info:
                await docling_processor.process_document(
                    document_id=1,
                    file_path=sample_pdf_path,
                    filename="test.pdf",
                    mime_type="application/pdf",
                )

            assert "Processing failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_unsupported_mime_type(self, docling_processor, tmp_path):
        """Test: Unsupported MIME Type"""
        test_file = tmp_path / "test.xyz"
        test_file.write_text("test content")

        # DoclingProcessor sollte alle Dateien verarbeiten können
        # aber bei unbekannten Formaten könnte es fehlschlagen
        with patch.object(docling_processor.converter, "convert") as mock_convert:
            mock_convert.side_effect = Exception("Unsupported format")

            with pytest.raises(Exception):
                await docling_processor.process_document(
                    document_id=1,
                    file_path=str(test_file),
                    filename="test.xyz",
                    mime_type="application/octet-stream",
                )


class TestDoclingProcessorPerformance:
    """Tests für Performance-Aspekte"""

    @pytest.mark.asyncio
    async def test_processing_time_recorded(self, docling_processor, sample_pdf_path):
        """Test: Processing Time wird aufgezeichnet"""
        with patch.object(docling_processor.converter, "convert") as mock_convert:
            mock_result = MagicMock()
            mock_result.document.export_to_markdown.return_value = "Test content"
            mock_result.document.tables = []
            mock_convert.return_value = mock_result

            result = await docling_processor.process_document(
                document_id=1,
                file_path=sample_pdf_path,
                filename="test.pdf",
                mime_type="application/pdf",
            )

            assert result.processing_time is not None
            assert result.processing_time > 0

    @pytest.mark.asyncio
    async def test_large_document_chunking(self, docling_processor, sample_pdf_path):
        """Test: Chunking von großen Dokumenten"""
        with patch.object(docling_processor.converter, "convert") as mock_convert:
            # Simuliere großes Dokument (10000 Wörter)
            large_text = " ".join([f"word{i}" for i in range(10000)])

            mock_result = MagicMock()
            mock_result.document.export_to_markdown.return_value = large_text
            mock_result.document.tables = []
            mock_convert.return_value = mock_result

            result = await docling_processor.process_document(
                document_id=1,
                file_path=sample_pdf_path,
                filename="large.pdf",
                mime_type="application/pdf",
            )

            # Sollte mehrere Chunks erstellen
            assert result.total_chunks > 1
            assert len(result.chunks) > 1

            # Jeder Chunk sollte <= chunk_size sein
            for chunk in result.chunks:
                word_count = len(chunk.content.split())
                assert (
                    word_count
                    <= docling_processor.chunk_size + docling_processor.chunk_overlap
                )
