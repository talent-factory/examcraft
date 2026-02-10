"""
Unit Tests für LegacyProcessor
Tests für Fallback Document Processing
"""

import pytest
from services.document_processors.legacy_processor import LegacyProcessor
from services.docling_service import ProcessedDocument


@pytest.fixture
def legacy_processor():
    """Fixture für LegacyProcessor"""
    return LegacyProcessor(chunk_size=1000, chunk_overlap=200)


@pytest.fixture
def sample_pdf_path(tmp_path):
    """Fixture für temporäre PDF-Datei"""
    pdf_file = tmp_path / "test.pdf"
    # Minimales PDF mit Text
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF Content) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
410
%%EOF"""
    pdf_file.write_bytes(pdf_content)
    return str(pdf_file)


@pytest.fixture
def sample_text_path(tmp_path):
    """Fixture für temporäre Text-Datei"""
    text_file = tmp_path / "test.txt"
    text_file.write_text(
        "This is a test document.\nWith multiple lines.\nAnd some content."
    )
    return str(text_file)


@pytest.fixture
def sample_markdown_path(tmp_path):
    """Fixture für temporäre Markdown-Datei"""
    md_file = tmp_path / "test.md"
    md_file.write_text("# Test Document\n\n## Section 1\n\nSome **bold** text.")
    return str(md_file)


class TestLegacyProcessorInitialization:
    """Tests für Processor-Initialisierung"""

    def test_processor_initialization(self, legacy_processor):
        """Test: Processor wird korrekt initialisiert"""
        assert legacy_processor.chunk_size == 1000
        assert legacy_processor.chunk_overlap == 200
        assert len(legacy_processor.supported_types) > 0

    def test_supported_mime_types(self, legacy_processor):
        """Test: Unterstützte MIME-Types"""
        assert "application/pdf" in legacy_processor.supported_types
        assert "text/plain" in legacy_processor.supported_types
        assert "text/markdown" in legacy_processor.supported_types


class TestLegacyProcessorPDFProcessing:
    """Tests für PDF-Verarbeitung"""

    @pytest.mark.asyncio
    async def test_process_pdf_success(self, legacy_processor, sample_pdf_path):
        """Test: Erfolgreiches PDF Processing"""
        result = await legacy_processor.process_document(
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
    async def test_pdf_metadata_extraction(self, legacy_processor, sample_pdf_path):
        """Test: PDF Metadaten-Extraktion"""
        result = await legacy_processor.process_document(
            document_id=1,
            file_path=sample_pdf_path,
            filename="test.pdf",
            mime_type="application/pdf",
        )

        assert "pages" in result.metadata
        assert result.total_pages is not None


class TestLegacyProcessorTextProcessing:
    """Tests für Text-Verarbeitung"""

    @pytest.mark.asyncio
    async def test_process_text_success(self, legacy_processor, sample_text_path):
        """Test: Erfolgreiches Text Processing"""
        result = await legacy_processor.process_document(
            document_id=1,
            file_path=sample_text_path,
            filename="test.txt",
            mime_type="text/plain",
        )

        assert isinstance(result, ProcessedDocument)
        assert result.document_id == 1
        assert result.filename == "test.txt"
        assert result.mime_type == "text/plain"
        assert len(result.chunks) > 0

    @pytest.mark.asyncio
    async def test_text_metadata(self, legacy_processor, sample_text_path):
        """Test: Text Metadaten"""
        result = await legacy_processor.process_document(
            document_id=1,
            file_path=sample_text_path,
            filename="test.txt",
            mime_type="text/plain",
        )

        assert "lines" in result.metadata
        assert "words" in result.metadata
        assert "characters" in result.metadata
        assert "encoding" in result.metadata


class TestLegacyProcessorMarkdownProcessing:
    """Tests für Markdown-Verarbeitung"""

    @pytest.mark.asyncio
    async def test_process_markdown_success(
        self, legacy_processor, sample_markdown_path
    ):
        """Test: Erfolgreiches Markdown Processing"""
        result = await legacy_processor.process_document(
            document_id=1,
            file_path=sample_markdown_path,
            filename="test.md",
            mime_type="text/markdown",
        )

        assert isinstance(result, ProcessedDocument)
        assert result.document_id == 1
        assert result.filename == "test.md"
        assert len(result.chunks) > 0

    @pytest.mark.asyncio
    async def test_markdown_to_plain_text(self, legacy_processor, sample_markdown_path):
        """Test: Markdown wird zu Plain Text konvertiert"""
        result = await legacy_processor.process_document(
            document_id=1,
            file_path=sample_markdown_path,
            filename="test.md",
            mime_type="text/markdown",
        )

        # Markdown-Formatierung sollte entfernt sein
        content = result.chunks[0].content
        assert "Test Document" in content
        assert "Section 1" in content


class TestLegacyProcessorChunking:
    """Tests für Text-Chunking"""

    def test_create_chunks_small_text(self, legacy_processor):
        """Test: Chunking mit kleinem Text"""
        text = "This is a small test document."
        chunks = legacy_processor._create_chunks(text)

        assert len(chunks) == 1
        assert chunks[0].content == text

    def test_create_chunks_large_text(self, legacy_processor):
        """Test: Chunking mit großem Text"""
        # Erstelle Text mit 2000 Wörtern
        text = " ".join([f"word{i}" for i in range(2000)])
        chunks = legacy_processor._create_chunks(text)

        assert len(chunks) > 1

        # Prüfe Chunk-Größen
        for chunk in chunks:
            word_count = len(chunk.content.split())
            assert word_count <= legacy_processor.chunk_size

    def test_chunk_overlap(self, legacy_processor):
        """Test: Chunk-Überlappung"""
        # Erstelle Text mit 1500 Wörtern
        text = " ".join([f"word{i}" for i in range(1500)])
        chunks = legacy_processor._create_chunks(text)

        if len(chunks) > 1:
            # Prüfe ob Überlappung existiert
            first_chunk_words = chunks[0].content.split()
            second_chunk_words = chunks[1].content.split()

            # Letzte Wörter des ersten Chunks sollten im zweiten Chunk sein
            overlap_words = first_chunk_words[-legacy_processor.chunk_overlap :]
            second_chunk_start = second_chunk_words[: legacy_processor.chunk_overlap]

            # Mindestens einige Wörter sollten überlappen
            assert any(word in second_chunk_start for word in overlap_words)

    def test_empty_text_chunking(self, legacy_processor):
        """Test: Chunking mit leerem Text"""
        chunks = legacy_processor._create_chunks("")
        assert len(chunks) == 0


class TestLegacyProcessorErrorHandling:
    """Tests für Error Handling"""

    @pytest.mark.asyncio
    async def test_unsupported_mime_type(self, legacy_processor, tmp_path):
        """Test: Unsupported MIME Type"""
        test_file = tmp_path / "test.xyz"
        test_file.write_text("test content")

        with pytest.raises(ValueError) as exc_info:
            await legacy_processor.process_document(
                document_id=1,
                file_path=str(test_file),
                filename="test.xyz",
                mime_type="application/octet-stream",
            )

        assert "Unsupported MIME type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_nonexistent_file(self, legacy_processor):
        """Test: Nicht-existierende Datei"""
        with pytest.raises(Exception):
            await legacy_processor.process_document(
                document_id=1,
                file_path="/nonexistent/file.pdf",
                filename="nonexistent.pdf",
                mime_type="application/pdf",
            )


class TestLegacyProcessorPerformance:
    """Tests für Performance"""

    @pytest.mark.asyncio
    async def test_processing_time_recorded(self, legacy_processor, sample_text_path):
        """Test: Processing Time wird aufgezeichnet"""
        result = await legacy_processor.process_document(
            document_id=1,
            file_path=sample_text_path,
            filename="test.txt",
            mime_type="text/plain",
        )

        assert result.processing_time is not None
        assert result.processing_time > 0

    @pytest.mark.asyncio
    async def test_large_document_performance(self, legacy_processor, tmp_path):
        """Test: Performance mit großem Dokument"""
        # Erstelle große Text-Datei (10000 Wörter)
        large_text = " ".join([f"word{i}" for i in range(10000)])
        large_file = tmp_path / "large.txt"
        large_file.write_text(large_text)

        result = await legacy_processor.process_document(
            document_id=1,
            file_path=str(large_file),
            filename="large.txt",
            mime_type="text/plain",
        )

        # Sollte mehrere Chunks erstellen
        assert result.total_chunks > 1
        assert len(result.chunks) > 1

        # Processing sollte schnell sein (< 5 Sekunden)
        assert result.processing_time < 5.0
